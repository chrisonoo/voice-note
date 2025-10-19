# Ten moduł odpowiada za konwersję (enkodowanie) plików audio do jednolitego formatu.
# Głównym celem jest upewnienie się, że wszystkie pliki, niezależnie od ich oryginalnego
# formatu (.mp3, .m4a itp.), zostaną przekonwertowane do standardowego formatu audio,
# który jest zoptymalizowany dla API Whisper.

import os  # Moduł do interakcji z systemem operacyjnym, np. do operacji na ścieżkach plików.
import subprocess  # Moduł pozwalający na uruchamianie zewnętrznych programów, w tym przypadku FFMPEG.
import threading  # Dodane dla obsługi postępu w czasie rzeczywistym
import time  # Dodane dla kontrolowania odstępów czasowych wyświetlania postępu
from typing import TYPE_CHECKING

from src import (  # Importujemy własne moduły: konfigurację i operacje na bazie danych.
    config,
    database,
)

if TYPE_CHECKING:
    from src.gui.core.main_window import App
from src.utils.error_handlers import (  # Dekoratory
    measure_performance,
    with_error_handling,
)
from src.utils.file_type_helper import (
    is_video_file,  # Funkcja do wykrywania plików wideo
)


def _format_duration_ffmpeg(duration_sec):
    """
    Formatuje czas trwania w sekundach do formatu FFmpeg (hh:mm:ss.ms).
    """
    hours = int(duration_sec // 3600)
    minutes = int((duration_sec % 3600) // 60)
    seconds = int(duration_sec % 60)
    milliseconds = int((duration_sec % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}"


def _analyze_silence_points(audio_path):
    """
    Analizuje plik audio i zwraca listę punktów ciszy dłuższej niż 2 sekundy.

    Argumenty:
        audio_path (str): Ścieżka do pliku audio do analizy

    Zwraca:
        list: Lista słowników z punktami ciszy zawierającymi 'start', 'end', 'duration'
    """
    import re

    command = [
        "ffmpeg",
        "-i",
        audio_path,
        "-af",
        "silencedetect=noise=-30dB:d=2.0",
        "-f",
        "null",
        "-",
    ]

    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=300)

        silence_periods = []
        current_silence = None

        # Parsowanie wyjścia FFmpeg - szukamy linii z silence_start i silence_end
        for line in result.stderr.split("\n"):
            if "silence_start:" in line:
                # Wyciągnij timestamp początku ciszy
                match = re.search(r"silence_start:\s*([0-9.]+)", line)
                if match:
                    start_time = float(match.group(1))
                    current_silence = {"start": start_time}

            elif "silence_end:" in line and current_silence is not None:
                # Wyciągnij timestamp końca ciszy i czas trwania
                match = re.search(r"silence_end:\s*([0-9.]+).*silence_duration:\s*([0-9.]+)", line)
                if match:
                    end_time = float(match.group(1))
                    duration = float(match.group(2))
                    current_silence.update({"end": end_time, "duration": duration})
                    silence_periods.append(current_silence)
                    current_silence = None

        print(
            f"    Znaleziono {len(silence_periods)} okresów ciszy w pliku {os.path.basename(audio_path)}"
        )

        # Szczegółowe logowanie wykrytych fragmentów ciszy
        if silence_periods:
            print("    Wykryte fragmenty ciszy:")
            for i, silence in enumerate(silence_periods, 1):
                print(
                    f"      {i}. {silence['start']:.1f}s - {silence['end']:.1f}s (długość: {silence['duration']:.1f}s)"
                )

        return silence_periods

    except subprocess.TimeoutExpired:
        print(
            f"    TIMEOUT: Analiza ciszy dla pliku {os.path.basename(audio_path)} przekroczyła limit czasu"
        )
        return []
    except Exception as e:
        print(f"    Błąd podczas analizy ciszy dla pliku {os.path.basename(audio_path)}: {e}")
        return []


def _calculate_split_points(
    total_duration, silence_periods, chunk_duration=config.MAX_FILE_DURATION_SECONDS
):
    """
    Oblicza optymalne punkty podziału pliku audio na podstawie punktów ciszy.

    Argumenty:
        total_duration (float): Całkowity czas trwania pliku w sekundach
        silence_periods (list): Lista słowników z punktami ciszy
        chunk_duration (int): Docelowa długość chunk'a w sekundach (domyślnie 600s = 10min)

    Zwraca:
        list: Lista punktów podziału (timestampy w sekundach), zawierająca początek i koniec
    """
    if not silence_periods:
        # Jeśli nie ma punktów ciszy, dziel na równe części co chunk_duration sekund
        split_points = [0.0]
        current_time = chunk_duration
        while current_time < total_duration:
            split_points.append(current_time)
            current_time += chunk_duration
        split_points.append(total_duration)
        return split_points

    # Przygotuj listę wszystkich timestampów ciszy
    silence_timestamps = []
    for silence in silence_periods:
        # Użyj środka okresu ciszy jako punktu podziału
        silence_timestamps.append((silence["start"] + silence["end"]) / 2)

    split_points = [0.0]  # Zawsze zaczynaj od początku
    current_time = chunk_duration

    while current_time < total_duration:
        # Znajdź najbliższą ciszę w promieniu ±60 sekund od current_time
        best_silence = None
        min_distance = float("inf")

        for silence_time in silence_timestamps:
            if current_time - 60 <= silence_time <= current_time + 60:
                distance = abs(silence_time - current_time)
                if distance < min_distance:
                    min_distance = distance
                    best_silence = silence_time

        if best_silence is not None:
            # Znaleziono ciszę w akceptowalnym zakresie
            split_points.append(best_silence)
            current_time = best_silence + chunk_duration
        else:
            # Nie znaleziono ciszy, użyj dokładnego punktu
            split_points.append(current_time)
            current_time += chunk_duration

    # Dodaj koniec pliku jeśli nie jest już dodany
    if split_points[-1] < total_duration - 1:  # -1 dla tolerancji
        split_points.append(total_duration)

    print(
        f"    Obliczono {len(split_points) - 1} punktów podziału dla pliku trwającego {total_duration:.1f}s"
    )
    return split_points


def _split_audio_file(audio_path, split_points, output_prefix):
    """
    Dzieli plik audio na chunk'y używając obliczonych punktów podziału.

    Argumenty:
        audio_path (str): Ścieżka do oryginalnego pliku audio
        split_points (list): Lista punktów podziału (timestampy w sekundach)
        output_prefix (str): Prefix nazwy pliku wyjściowego (bez rozszerzenia)

    Zwraca:
        list: Lista ścieżek do utworzonych chunków, lub None przy błędzie
    """
    chunk_paths = []

    try:
        # Sprawdź czy mamy co najmniej 2 punkty (początek i koniec)
        if len(split_points) < 2:
            print(f"    Błąd: Za mało punktów podziału ({len(split_points)})")
            return None

        # Iteruj przez pary punktów podziału
        for i in range(len(split_points) - 1):
            start_time = split_points[i]
            end_time = split_points[i + 1]
            duration = end_time - start_time

            # Pomiń segmenty krótsze niż 1 sekunda
            if duration < 1.0:
                print(f"    Pomijanie segmentu {i + 1}: zbyt krótki ({duration:.1f}s)")
                continue

            # Utwórz nazwę pliku wyjściowego
            chunk_number = i + 1
            output_filename = f"{output_prefix}_{chunk_number:03d}.m4a"
            output_path = os.path.join(config.AUDIO_TMP_DIR, output_filename)

            # Przygotuj komendę FFmpeg do wycięcia segmentu
            start_formatted = _format_duration_ffmpeg(start_time)
            duration_formatted = _format_duration_ffmpeg(duration)

            command = [
                "ffmpeg",
                "-y",
                "-i",
                audio_path,
                "-ss",
                start_formatted,  # Start time
                "-t",
                duration_formatted,  # Duration
                "-acodec",
                "aac",  # Audio codec
                "-b:a",
                "32k",  # Bitrate
                "-ac",
                "1",  # Mono
                "-ar",
                "16000",  # Sample rate
                "-af",
                "loudnorm=I=-12:TP=-1.0:LRA=7:dual_mono=true",  # Normalization
                output_path,
            ]

            print(
                f"  Tworzenie chunk {chunk_number}: {start_formatted} - {_format_duration_ffmpeg(end_time)} ({duration:.1f}s)"
            )

            # Uruchom FFmpeg (zwiększony timeout dla dłuższych chunków - 15 minut na 10-minutowy chunk)
            chunk_timeout = max(
                900, int(duration * 1.5)
            )  # co najmniej 15 minut lub 1.5x długości chunk'a
            print(f"      Timeout dla tego chunk'a: {chunk_timeout}s")
            result = subprocess.run(command, capture_output=True, text=True, timeout=chunk_timeout)

            if result.returncode == 0:
                chunk_paths.append(output_path)
                print(f"    ✓ Utworzono chunk: {os.path.basename(output_path)}")
            else:
                print(f"    ✗ Błąd podczas tworzenia chunk {chunk_number}: {result.stderr}")
                # Spróbuj usunąć niekompletny plik jeśli istnieje
                if os.path.exists(output_path):
                    try:
                        os.remove(output_path)
                    except:
                        pass
                return None

        if chunk_paths:
            print(
                f"    ✓ Utworzono {len(chunk_paths)} chunków z pliku {os.path.basename(audio_path)}"
            )
            return chunk_paths
        else:
            print(
                f"    ✗ Nie udało się utworzyć żadnego chunk'a z pliku {os.path.basename(audio_path)}"
            )
            return None

    except subprocess.TimeoutExpired:
        print(
            f"    TIMEOUT: Dzielenie pliku {os.path.basename(audio_path)} przekroczyło limit czasu"
        )
        return None
    except Exception as e:
        print(f"    Błąd podczas dzielenia pliku {os.path.basename(audio_path)}: {e}")
        return None


def _run_ffmpeg_with_progress(command, filename=None, total_duration=None):
    """
    Uruchamia FFmpeg z wyświetlaniem postępu w czasie rzeczywistym.
    Zwraca True jeśli się udało, False przy błędzie.
    """
    try:
        # Uruchamiamy FFmpeg z przekierowaniem stdout i stderr do PIPE
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # Łączymy stderr z stdout aby zobaczyć postęp
            text=True,
            bufsize=1,  # Line buffered
            universal_newlines=True,
        )

        # Zmienna do śledzenia czy proces nadal działa
        process_finished = [False]

        def read_output():
            """Czyta wyjście z FFmpeg w czasie rzeczywistym, wyświetlając postęp co 5 sekund."""
            last_display_time = 0
            display_interval = 5.0  # Wyświetlaj postęp co 5 sekund
            try:
                while True:
                    # Czytaj dostępne linie bez blokowania
                    line = process.stdout.readline()
                    if not line:  # Brak więcej danych
                        if process.poll() is not None:  # Proces zakończył się
                            break
                        time.sleep(0.1)  # Krótkie czekanie przed następną próbą
                        continue

                    current_time = time.time()
                    line_str = line.strip()
                    if line_str:  # Wyświetlaj tylko niepuste linie
                        # Wyświetlaj tylko jeśli minęło 5 sekund od ostatniego wyświetlenia
                        if current_time - last_display_time >= display_interval:
                            if filename and total_duration is not None:
                                formatted_duration = _format_duration_ffmpeg(total_duration)
                                print(f"[{filename}] [{formatted_duration}] {line_str}")
                            else:
                                print(line_str)  # Wyślij do naszego redirectora terminala
                            last_display_time = current_time

            except Exception as e:
                print(f"Błąd podczas czytania wyjścia FFmpeg: {e}")
            finally:
                process_finished[0] = True

        # Uruchamiamy wątek do czytania wyjścia
        output_thread = threading.Thread(target=read_output, daemon=True)
        output_thread.start()

        # Czekamy na zakończenie procesu
        try:
            process.wait()
            output_thread.join(timeout=1.0)  # Daj czas wątkowi na zakończenie
            return process.returncode == 0
        except Exception:
            print("    BŁĄD: FFmpeg napotkał błąd podczas przetwarzania")
            process.terminate()
            try:
                process.wait(timeout=5)  # Daj czas na zamknięcie
            except subprocess.TimeoutExpired:
                process.kill()  # Wymuś zamknięcie jeśli terminate nie działa
            return False

    except Exception as e:
        print(f"    BŁĄD podczas uruchamiania FFmpeg: {e}")
        return False


def _convert_single_file(original_path):
    """
    Konwertuje pojedynczy plik i zwraca listę tupli (source, tmp) lub None przy błędzie.
    Dla plików dłuższych niż MAX_FILE_DURATION_SECONDS dzieli je na chunk'y.
    Funkcja przeznaczona do równoległego przetwarzania.
    """
    try:
        # Najpierw sprawdzamy długość pliku
        from src.utils.audio.duration_checker import get_file_duration

        duration_sec = get_file_duration(original_path)

        if duration_sec <= 0:
            print(f"    Błąd: Nie można określić długości pliku {os.path.basename(original_path)}")
            return None

        # Tworzymy standardową, bezpieczną nazwę pliku wyjściowego.
        base_name = os.path.basename(original_path)
        standardized_name, _ = os.path.splitext(base_name.lower().replace(" ", "_"))

        # Sprawdzamy czy plik jest dłuższy niż limit
        if duration_sec > config.MAX_FILE_DURATION_SECONDS:
            print(f"  Długi plik wykryty: {os.path.basename(original_path)} ({duration_sec:.1f}s)")

            # Używamy optymalizowanej metody: najpierw konwertuj, potem dziel
            result = _convert_and_split_file(original_path)
            if result and len(result) > 0:
                return result
            else:
                print("    Błąd podczas optymalizowanej konwersji, fallback do starej metody")
                # Fallback do starej metody jeśli nowa się nie powiedzie

                # Analizujemy punkty ciszy w oryginalnym pliku
                silence_periods = _analyze_silence_points(original_path)
                if silence_periods is None:
                    print("    Błąd podczas analizy ciszy, używam standardowej konwersji")
                    # Fallback do standardowej konwersji jeśli analiza ciszy się nie powiedzie
                    return _convert_single_file_standard(original_path)

                # Obliczamy punkty podziału
                split_points = _calculate_split_points(duration_sec, silence_periods)

                # Dzielimy plik na chunk'y
                chunk_paths = _split_audio_file(original_path, split_points, standardized_name)

                if chunk_paths and len(chunk_paths) > 0:
                    # Zwracamy listę tupli (source_path, chunk_path) dla każdego chunk'a
                    return [(original_path, chunk_path) for chunk_path in chunk_paths]
                else:
                    print("    Błąd podczas dzielenia pliku, używam standardowej konwersji")
                    # Fallback do standardowej konwersji
                    return _convert_single_file_standard(original_path)
        else:
            # Plik jest odpowiednio krótki - standardowa konwersja
            result = _convert_single_file_standard(original_path)
            return [result] if result else None

    except Exception as ex:
        print(
            f"    KRYTYCZNY BŁĄD podczas przetwarzania pliku {os.path.basename(original_path)}: {ex}"
        )
        return None


def _convert_and_split_file(original_path):
    """
    Optymalizowana konwersja i podział pliku: najpierw konwertuje cały plik,
    potem dzieli na chunk'y. Znacznie szybsze niż wielokrotne wycinanie z oryginału.

    Argumenty:
        original_path (str): Ścieżka do oryginalnego pliku audio

    Zwraca:
        list: Lista tupli (source_path, chunk_path) dla każdego chunk'a lub None przy błędzie
    """
    try:
        # Najpierw sprawdzamy długość pliku
        from src.utils.audio.duration_checker import get_file_duration

        duration_sec = get_file_duration(original_path)

        if duration_sec <= 0:
            print(f"    Błąd: Nie można określić długości pliku {os.path.basename(original_path)}")
            return None

        # Tworzymy standardową nazwę dla pełnego pliku tymczasowego
        base_name = os.path.basename(original_path)
        standardized_name, _ = os.path.splitext(base_name.lower().replace(" ", "_"))
        full_tmp_filename = f"{standardized_name}_full.m4a"
        full_tmp_path = os.path.join(config.AUDIO_TMP_DIR, full_tmp_filename)

        print(f"  Długi plik wykryty: {os.path.basename(original_path)} ({duration_sec:.1f}s)")
        print("  Strategia: najpierw konwertuj cały plik, potem dziel na chunk'y")

        # KROK 1: Konwertuj cały plik do jednego dużego pliku tymczasowego
        print("  Krok 1: Konwertowanie całego pliku...")
        is_video = is_video_file(original_path)

        if is_video:
            command = f'ffmpeg -y -i "{original_path}" -vn {config.FFMPEG_PARAMS} "{full_tmp_path}"'
        else:
            command = f'ffmpeg -y -i "{original_path}" {config.FFMPEG_PARAMS} "{full_tmp_path}"'

        success = _run_ffmpeg_with_progress(command, os.path.basename(original_path))
        if not success:
            print("    Błąd podczas konwersji całego pliku")
            return None

        print("    ✓ Cały plik został skonwertowany")

        # KROK 2: Analizuj ciszę w skonwertowanym pliku
        print("  Krok 2: Analiza ciszy w skonwertowanym pliku...")
        silence_periods = _analyze_silence_points(full_tmp_path)
        if silence_periods is None:
            print("    Błąd podczas analizy ciszy, dzielenie na równe części")
            silence_periods = []

        # KROK 3: Oblicz punkty podziału
        print("  Krok 3: Obliczanie punktów podziału...")
        split_points = _calculate_split_points(duration_sec, silence_periods)

        # KROK 4: Podziel skonwertowany plik na chunk'y
        print("  Krok 4: Dzielenie na chunk'y...")
        chunk_paths = _split_from_converted_file(
            full_tmp_path, split_points, standardized_name, original_path
        )

        if chunk_paths and len(chunk_paths) > 0:
            print(f"    ✓ Utworzono {len(chunk_paths)} chunków")
            # Usuń tymczasowy pełny plik - już niepotrzebny
            try:
                os.remove(full_tmp_path)
                print(f"    ✓ Usunięto tymczasowy plik pełny: {os.path.basename(full_tmp_path)}")
            except:
                pass

            return [(original_path, chunk_path) for chunk_path in chunk_paths]
        else:
            print("    Błąd podczas dzielenia pliku")
            # Usuń tymczasowy pełny plik w przypadku błędu
            try:
                os.remove(full_tmp_path)
            except:
                pass
            return None

    except Exception as ex:
        print(
            f"    KRYTYCZNY BŁĄD podczas optymalizowanej konwersji pliku {os.path.basename(original_path)}: {ex}"
        )
        return None


def _split_from_converted_file(converted_file_path, split_points, output_prefix, original_path):
    """
    Dzieli już skonwertowany plik audio na chunk'y. Znacznie szybsze niż wycinanie z oryginału.

    Argumenty:
        converted_file_path (str): Ścieżka do skonwertowanego pliku audio
        split_points (list): Lista punktów podziału (timestampy w sekundach)
        output_prefix (str): Prefix nazwy pliku wyjściowego
        original_path (str): Oryginalna ścieżka (dla komunikatów)

    Zwraca:
        list: Lista ścieżek do utworzonych chunków, lub None przy błędzie
    """
    chunk_paths = []

    try:
        if len(split_points) < 2:
            print(f"    Błąd: Za mało punktów podziału ({len(split_points)})")
            return None

        print(
            f"    Dzielenie {os.path.basename(converted_file_path)} na {len(split_points) - 1} chunków..."
        )

        # Iteruj przez pary punktów podziału
        for i in range(len(split_points) - 1):
            start_time = split_points[i]
            end_time = split_points[i + 1]
            duration = end_time - start_time

            if duration < 1.0:
                print(f"    Pomijanie segmentu {i + 1}: zbyt krótki ({duration:.1f}s)")
                continue

            chunk_number = i + 1
            output_filename = f"{output_prefix}_{chunk_number:03d}.m4a"
            output_path = os.path.join(config.AUDIO_TMP_DIR, output_filename)

            start_formatted = _format_duration_ffmpeg(start_time)
            duration_formatted = _format_duration_ffmpeg(duration)

            command = [
                "ffmpeg",
                "-y",
                "-i",
                converted_file_path,
                "-ss",
                start_formatted,
                "-t",
                duration_formatted,
                "-acodec",
                "aac",
                "-b:a",
                "32k",
                "-ac",
                "1",
                "-ar",
                "16000",
                "-c",
                "copy",  # Bez re-kodowania - znacznie szybsze!
                output_path,
            ]

            print(
                f"    Tworzenie chunk {chunk_number}: {start_formatted} - {_format_duration_ffmpeg(end_time)} ({duration:.1f}s)"
            )

            # Krótszy timeout dla dzielenia skonwertowanego pliku
            chunk_timeout = max(60, int(duration * 0.5))  # co najmniej 1 minuta lub 0.5x długości
            result = subprocess.run(command, capture_output=True, text=True, timeout=chunk_timeout)

            if result.returncode == 0:
                chunk_paths.append(output_path)
                print(f"      ✓ Chunk {chunk_number} utworzony")
            else:
                print(f"      ✗ Błąd podczas tworzenia chunk {chunk_number}: {result.stderr}")
                if os.path.exists(output_path):
                    try:
                        os.remove(output_path)
                    except:
                        pass
                return None

        return chunk_paths if chunk_paths else None

    except subprocess.TimeoutExpired:
        print(
            f"    TIMEOUT: Dzielenie pliku {os.path.basename(converted_file_path)} przekroczyło limit czasu"
        )
        return None
    except Exception as e:
        print(f"    Błąd podczas dzielenia pliku {os.path.basename(converted_file_path)}: {e}")
        return None


def _convert_single_file_standard(original_path):
    """
    Standardowa konwersja pojedynczego pliku (bez dzielenia na chunk'y).
    Zwraca tuple (source, tmp) lub None przy błędzie.
    """
    try:
        # Tworzymy standardową, bezpieczną nazwę pliku wyjściowego.
        base_name = os.path.basename(original_path)
        standardized_name, _ = os.path.splitext(base_name.lower().replace(" ", "_"))
        output_filename = f"{standardized_name}.m4a"
        tmp_file_path = os.path.join(config.AUDIO_TMP_DIR, output_filename)

        print(
            f"  Konwertowanie: {os.path.basename(original_path)} -> {os.path.basename(tmp_file_path)}"
        )

        # Sprawdzamy czy plik jest wideo
        is_video = is_video_file(original_path)

        # Budujemy komendę FFMPEG
        if is_video:
            # Dla plików wideo ekstrahujemy tylko audio (-vn ignoruje strumień wideo)
            command = f'ffmpeg -y -i "{original_path}" -vn {config.FFMPEG_PARAMS} "{tmp_file_path}"'
        else:
            # Dla plików audio używamy standardowych parametrów
            command = f'ffmpeg -y -i "{original_path}" {config.FFMPEG_PARAMS} "{tmp_file_path}"'

        # Uruchamiamy FFmpeg z wyświetlaniem postępu w czasie rzeczywistym
        filename = os.path.basename(original_path)
        success = _run_ffmpeg_with_progress(command, filename)

        if success:
            return (original_path, tmp_file_path)
        else:
            return None

    except Exception as ex:
        print(
            f"    KRYTYCZNY BŁĄD podczas przetwarzania pliku {os.path.basename(original_path)}: {ex}"
        )
        return None


@with_error_handling("Konwersja plików audio")
@measure_performance
def encode_audio_files(app: "App | None" = None):
    """
    Pobiera z bazy danych listę plików do przetworzenia, konwertuje je do formatu audio gotowego do transkrypcji
    za pomocą zewnętrznego narzędzia FFMPEG z sekwencyjnym przetwarzaniem,
    aktualizując GUI po każdym przetworzonym pliku.
    """
    print("\nKrok 2: Konwertowanie plików audio do formatu gotowego do transkrypcji...")

    # Pobieramy z bazy danych listę plików, które zostały zaznaczone przez użytkownika i nie były jeszcze konwertowane.
    files_to_encode = database.get_files_to_load()
    if not files_to_encode:
        print("Brak nowych plików do konwersji.")
        return

    # Upewniamy się, że folder na przekonwertowane pliki audio istnieje.
    os.makedirs(config.AUDIO_TMP_DIR, exist_ok=True)

    print(f"Rozpoczynam sekwencyjną konwersję {len(files_to_encode)} plików...")

    successful_conversions = []

    # Przetwarzaj pliki sekwencyjnie
    for i, original_path in enumerate(files_to_encode, 1):
        print(f"Przetwarzanie pliku {i}/{len(files_to_encode)}: {os.path.basename(original_path)}")

        result = _convert_single_file(original_path)
        if result and len(result) > 0:
            # result może być listą tupli (source, tmp) dla chunków lub pojedynczej tupli
            if len(result) > 1:
                # Wielokrotne wyniki (chunk'y)
                for source_path, tmp_path in result:
                    successful_conversions.append((source_path, tmp_path))
                    print(f"    ✓ Przetworzono chunk: {os.path.basename(tmp_path)}")
            else:
                # Pojedynczy wynik
                source_path, tmp_path = result[0]
                successful_conversions.append((source_path, tmp_path))
                print(f"    ✓ Przetworzono i dodano do bazy: {os.path.basename(source_path)}")

            # Zbierz wszystkie ścieżki źródłowe i tymczasowe do aktualizacji bazy
            source_paths = [r[0] for r in result]
            tmp_paths = [r[1] for r in result]

            # Aktualizuj bazę danych natychmiast po przetworzeniu pliku/chunków
            database.set_files_as_loaded(source_paths, tmp_paths)

            # Odśwież GUI jeśli mamy referencję do aplikacji
            if app:
                app.after(0, lambda: app.invalidate_cache())
                app.after(0, lambda: app.panel_manager.refresh_transcription_progress_views())
                app.after(0, lambda: app.update_all_counters())
        else:
            print(f"    ✗ Nie udało się przetworzyć: {os.path.basename(original_path)}")

    if successful_conversions:
        print(
            f"Pomyślnie przekonwertowano i oznaczono jako załadowane: {len(successful_conversions)} plików."
        )

    if len(successful_conversions) < len(files_to_encode):
        failed_count = len(files_to_encode) - len(successful_conversions)
        print(f"Nie udało się przekonwertować: {failed_count} plików.")

    print("Zakończono konwersję plików.")
