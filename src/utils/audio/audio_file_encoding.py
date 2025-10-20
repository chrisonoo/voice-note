# Ten moduł odpowiada za konwersję (enkodowanie) plików audio do jednolitego formatu.
# Głównym celem jest upewnienie się, że wszystkie pliki, niezależnie od ich oryginalnego
# formatu (.mp3, .m4a itp.), zostaną przekonwertowane do standardowego formatu audio,
# który jest zoptymalizowany dla API Whisper.

import os  # Moduł do interakcji z systemem operacyjnym, np. do operacji na ścieżkach plików.
import re  # Moduł wyrażeń regularnych
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
    is_aac_audio_file,  # Funkcja do sprawdzania czy plik jest w AAC
    is_video_file,  # Funkcja do wykrywania plików wideo
)


def _format_duration_ffmpeg(duration_sec: float):
    """
    Formatuje czas trwania w sekundach do formatu FFmpeg (hh:mm:ss.ms).
    """
    hours = int(duration_sec // 3600)
    minutes = int((duration_sec % 3600) // 60)
    seconds = int(duration_sec % 60)
    milliseconds = int((duration_sec % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}"


def _remove_long_silence(
    audio_path: str,
    leading_trailing_threshold: float = 1.0,
    long_silence_threshold: float = config.SILENCE_DETECTION_THRESHOLD,
) -> str | None:
    """
    Usuwa długie okresy ciszy z pliku audio i tworzy jeden plik wyjściowy bez tych fragmentów.

    Algorytm:
    1. Analizuje wszystkie okresy ciszy w pliku
    2. Znajduje długie okresy ciszy (> long_silence_threshold)
    3. Tworzy segmenty dźwięku między tymi okresami ciszy
    4. Łączy wszystkie segmenty w jeden plik wyjściowy

    Argumenty:
        audio_path (str): Ścieżka do pliku audio do przetworzenia
        leading_trailing_threshold (float): Próg ciszy na początku i końcu (sekundy)
        long_silence_threshold (float): Próg długiej ciszy do usunięcia (sekundy)

    Zwraca:
        str | None: Ścieżka do pliku wyjściowego bez długiej ciszy, lub None przy błędzie
    """
    try:
        # Najpierw sprawdzamy długość oryginalnego pliku
        from src.utils.audio.duration_checker import get_file_duration

        original_duration = get_file_duration(audio_path)
        if original_duration <= 0:
            print("    Błąd: Nie można określić długości pliku oryginalnego")
            return None

        # KROK 1: Analizujemy wszystkie okresy ciszy
        filename = os.path.basename(audio_path)
        formatted_duration = _format_duration_ffmpeg(original_duration)
        print(
            f"[{filename}] [{formatted_duration}] Rozpoczynam analizę wszystkich okresów ciszy..."
        )

        command = [
            "ffmpeg",
            "-i",
            audio_path,
            "-af",
            f"silencedetect=noise={config.SILENCE_DETECTION_NOISE_LEVEL}dB:d={leading_trailing_threshold}",
            "-f",
            "null",
            "-",
        ]

        try:
            # Uruchamiamy FFmpeg z wyświetlaniem postępu
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
            )

            # Zmienna do śledzenia czy proces nadal działa
            process_finished = [False]
            silence_periods = []
            current_silence = None
            last_display_time = 0
            display_interval = 5.0  # Wyświetlaj postęp co 5 sekund

            def read_output():
                """Czyta wyjście z FFmpeg w czasie rzeczywistym."""
                nonlocal silence_periods, current_silence, last_display_time
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

                        # Parsowanie linii z silence_start i silence_end
                        if "silence_start:" in line_str:
                            match = re.search(r"silence_start:\s*([0-9.]+)", line_str)
                            if match:
                                current_silence = {"start": float(match.group(1))}

                        elif "silence_end:" in line_str and current_silence is not None:
                            match = re.search(
                                r"silence_end:\s*([0-9.]+).*silence_duration:\s*([0-9.]+)", line_str
                            )
                            if match:
                                current_silence.update(
                                    {
                                        "end": float(match.group(1)),
                                        "duration": float(match.group(2)),
                                    }
                                )
                                silence_periods.append(current_silence)
                                current_silence = None

                        # Wyświetlaj postęp co 5 sekund
                        if line_str and current_time - last_display_time >= display_interval:
                            print(
                                f"[{filename}] [{formatted_duration}] Analiza wszystkich okresów ciszy w toku:\n    {line_str}"
                            )
                            last_display_time = current_time

                except Exception as e:
                    print(f"Błąd podczas czytania wyjścia FFmpeg: {e}")
                finally:
                    process_finished[0] = True

            # Uruchamiamy wątek do czytania wyjścia
            output_thread = threading.Thread(target=read_output, daemon=True)
            output_thread.start()

            # Czekamy na zakończenie procesu z timeout'em
            try:
                process.wait(timeout=300)
                output_thread.join(timeout=1.0)  # Daj czas wątkowi na zakończenie
            except subprocess.TimeoutExpired:
                print(
                    f"    TIMEOUT: Analiza ciszy dla pliku {os.path.basename(audio_path)} przekroczyła limit czasu"
                )
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                return None

        except subprocess.TimeoutExpired:
            print(
                f"    TIMEOUT: Analiza ciszy dla pliku {os.path.basename(audio_path)} przekroczyła limit czasu"
            )
            return None

        if not silence_periods:
            print(f"    Brak okresów ciszy w pliku {os.path.basename(audio_path)}")
            return audio_path  # Zwróć oryginalną ścieżkę jeśli nie ma ciszy

        # KROK 2: Znajdź długie okresy ciszy
        long_silences = []
        for silence in silence_periods:
            if silence["duration"] >= long_silence_threshold:
                long_silences.append(silence)

        # KROK 3: Jeśli nie ma długich okresów ciszy, zwróć oryginalny plik
        if not long_silences:
            print(f"    Brak długich okresów ciszy (> {long_silence_threshold}s) do usunięcia")
            return audio_path

        # KROK 4: Utwórz segmenty dźwięku między długimi okresami ciszy
        print(
            f"    Znaleziono {len(long_silences)} długich okresów ciszy, tworzenie segmentów dźwięku..."
        )

        segments = []
        current_start = 0.0

        # Dodaj segmenty między długimi okresami ciszy
        for long_silence in long_silences:
            segment_end = long_silence["start"]
            segment_duration = segment_end - current_start

            if segment_duration >= 0.5:  # Minimalny segment 0.5 sekundy
                segments.append(
                    {"start": current_start, "end": segment_end, "duration": segment_duration}
                )

            # Przesuń początek następnego segmentu za długą ciszę
            current_start = long_silence["end"]

        # Dodaj ostatni segment (od końca ostatniej długiej ciszy do końca pliku)
        if current_start < original_duration:
            final_segment_duration = original_duration - current_start
            if final_segment_duration >= 0.5:
                segments.append(
                    {
                        "start": current_start,
                        "end": original_duration,
                        "duration": final_segment_duration,
                    }
                )

        if not segments:
            print("    Brak segmentów dźwięku do utworzenia")
            return audio_path

        # KROK 5: Połącz wszystkie segmenty w jeden plik wyjściowy
        print(f"    Łączenie {len(segments)} segmentów w jeden plik wyjściowy...")

        output_path = _create_concatenated_file(audio_path, segments, "no_silence")
        if output_path:
            removed_silence = sum(silence["duration"] for silence in long_silences)
            print(f"    ✓ Utworzono plik bez ciszy, usunięto {removed_silence:.1f}s długiej ciszy")
            return output_path
        else:
            print("    ✗ Nie udało się utworzyć pliku wyjściowego")
            return None

    except Exception as e:
        print(f"    Błąd podczas usuwania długiej ciszy: {e}")
        return None


def _create_concatenated_file(audio_path, segments, suffix):
    """
    Tworzy plik audio poprzez połączenie wielu segmentów w jeden plik.

    Argumenty:
        audio_path (str): Ścieżka do oryginalnego pliku audio
        segments (list): Lista segmentów do połączenia, każdy segment to dict z kluczami 'start', 'end', 'duration'
        suffix (str): Sufiks dla nazwy pliku wyjściowego

    Zwraca:
        str | None: Ścieżka do utworzonego pliku lub None przy błędzie
    """
    try:
        if not segments:
            return None

        # Przygotuj nazwę pliku wyjściowego
        base_name = os.path.basename(audio_path)
        name_without_ext, _ = os.path.splitext(base_name)
        output_filename = f"{name_without_ext}_{suffix}.m4a"
        output_path = os.path.join(config.AUDIO_TMP_DIR, output_filename)

        # Jeśli jest tylko jeden segment, po prostu wytnij go
        if len(segments) == 1:
            segment = segments[0]
            return _create_trimmed_file(audio_path, segment["start"], segment["end"], suffix)

        # Dla wielu segmentów - najpierw wytnij każdy segment do osobnego pliku
        temp_files = []
        concat_list = []

        for i, segment in enumerate(segments):
            # Wytnij segment do pliku tymczasowego
            temp_suffix = f"temp_{suffix}_{i:03d}"
            temp_path = _create_trimmed_file(
                audio_path, segment["start"], segment["end"], temp_suffix
            )

            if temp_path:
                temp_files.append(temp_path)
                concat_list.append(temp_path)
            else:
                print(f"    Błąd podczas tworzenia segmentu tymczasowego {i}")
                # Wyczyść już utworzone pliki tymczasowe
                for temp_file in temp_files:
                    try:
                        os.remove(temp_file)
                    except:
                        pass
                return None

        # Połącz wszystkie segmenty
        concat_file_path = os.path.join(config.AUDIO_TMP_DIR, f"concat_{suffix}.txt")

        try:
            # Utwórz plik listy do konkatenacji
            with open(concat_file_path, "w", encoding="utf-8") as f:
                for temp_file in concat_list:
                    f.write(f"file '{temp_file}'\n")

            # Uruchom FFmpeg do konkatenacji
            command = [
                "ffmpeg",
                "-y",  # Nadpisz plik wyjściowy
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                concat_file_path,
                "-c",
                "copy",  # Kopiuj strumień bez reenkodowania
                output_path,
            ]

            success = _run_ffmpeg_with_progress(command, os.path.basename(output_path))
            if success and os.path.exists(output_path):
                print(f"    ✓ Połączono {len(segments)} segmentów w plik wyjściowy")
            else:
                print("    ✗ Błąd podczas łączenia segmentów")
                try:
                    os.remove(output_path)
                except:
                    pass
                output_path = None

        finally:
            # Wyczyść plik listy
            try:
                os.remove(concat_file_path)
            except:
                pass

            # Wyczyść pliki tymczasowe
            for temp_file in temp_files:
                try:
                    os.remove(temp_file)
                except:
                    pass

        return output_path

    except Exception as e:
        print(f"    Błąd podczas tworzenia pliku połączonego: {e}")
        return None


def _create_trimmed_file(audio_path, start_time, end_time, suffix):
    """
    Tworzy plik audio z określonego zakresu czasowego.

    Argumenty:
        audio_path (str): Ścieżka do oryginalnego pliku
        start_time (float): Czas rozpoczęcia (sekundy)
        end_time (float): Czas zakończenia (sekundy)
        suffix (str): Sufiks dla nazwy pliku wyjściowego

    Zwraca:
        str | None: Ścieżka do utworzonego pliku lub None przy błędzie
    """
    try:
        duration = end_time - start_time
        if duration < 0.1:  # Minimalna długość 0.1 sekundy
            return None

        # Tworzymy nazwę nowego pliku
        base_name = os.path.basename(audio_path)
        name_without_ext = os.path.splitext(base_name)[0]
        output_filename = f"{name_without_ext}_{suffix}.m4a"
        output_path = os.path.join(config.AUDIO_TMP_DIR, output_filename)

        start_formatted = _format_duration_ffmpeg(start_time)
        duration_formatted = _format_duration_ffmpeg(duration)

        # Sprawdzamy czy plik źródłowy jest już w AAC
        is_source_aac = is_aac_audio_file(audio_path)

        if is_source_aac:
            # Dla plików AAC - kopiujemy bez reenkodowania
            command = [
                "ffmpeg",
                "-y",
                "-i",
                audio_path,
                "-ss",
                start_formatted,
                "-t",
                duration_formatted,
                "-vn",
                "-acodec",
                "copy",
                output_path,
            ]
        else:
            # Dla innych formatów - pełna konwersja do AAC
            command = [
                "ffmpeg",
                "-y",
                "-i",
                audio_path,
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
                "-af",
                "loudnorm=I=-12:TP=-1.0:LRA=7:dual_mono=true",
                output_path,
            ]

        result = subprocess.run(command, capture_output=True, text=True, timeout=600)

        if result.returncode == 0:
            return output_path
        else:
            print(f"    Błąd FFmpeg: {result.stderr}")
            return None

    except Exception as e:
        print(f"    Błąd podczas tworzenia pliku {suffix}: {e}")
        return None


# Removed: chunk splitting utilities (_calculate_split_points, _split_audio_file)
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


def _handle_aac_file(original_path, duration_sec, standardized_name):
    """
    Obsługuje pliki, które są już w formacie AAC.
    Dla krótkich plików - kopiuje bez zmian.
    Dla długich plików - dzieli na segmenty bez reenkodowania.

    Argumenty:
        original_path (str): Ścieżka do oryginalnego pliku AAC
        duration_sec (float): Długość pliku w sekundach
        standardized_name (str): Standaryzowana nazwa pliku

    Zwraca:
        list: Lista tupli (source_path, tmp_path) lub None przy błędzie
    """
    try:
        # Sprawdzamy czy plik jest dłuższy niż limit
        if duration_sec > config.MAX_FILE_DURATION_SECONDS:
            print(
                f"  Długi plik AAC wykryty: {os.path.basename(original_path)} ({duration_sec:.1f}s)"
            )

            # Dla plików AAC najpierw usuń długie okresy ciszy
            print("  Strategia AAC: usuwanie długiej ciszy bez reenkodowania")
            processed_path = _remove_long_silence_aac_optimized(original_path)

            if processed_path and processed_path != original_path:
                print("    ✓ Utworzono plik AAC bez długiej ciszy")
                # Zwracamy jeden plik wynikowy, bez dalszego dzielenia
                return [(original_path, processed_path)]
            elif processed_path == original_path:
                print("    Brak długiej ciszy do usunięcia w pliku AAC")
                # Kopiujemy plik do katalogu tymczasowego jako jeden wynikowy plik
                result = _copy_aac_file(original_path, standardized_name)
                return [result] if result else None
            else:
                print("    Błąd podczas przetwarzania pliku AAC, kopiuję bez zmian")
                # Fallback: kopiuj bez zmian jako pojedynczy plik
                result = _copy_aac_file(original_path, standardized_name)
                return [result] if result else None
        else:
            # Plik AAC jest odpowiednio krótki - kopiujemy bez zmian
            print(f"  Krótki plik AAC: {os.path.basename(original_path)} - kopiuję bez zmian")
            result = _copy_aac_file(original_path, standardized_name)
            return [result] if result else None

    except Exception as ex:
        print(f"    BŁĄD podczas obsługi pliku AAC {os.path.basename(original_path)}: {ex}")
        return None


# Removed: AAC segment cutting utility (_cut_aac_segments_optimized)


def _copy_aac_file(original_path, standardized_name):
    """
    Kopiuje plik AAC bez reenkodowania, zachowując oryginalne parametry.

    Argumenty:
        original_path (str): Ścieżka do oryginalnego pliku AAC
        standardized_name (str): Standaryzowana nazwa pliku

    Zwraca:
        tuple: (source_path, tmp_path) lub None przy błędzie
    """
    try:
        output_filename = f"{standardized_name}.m4a"
        tmp_file_path = os.path.join(config.AUDIO_TMP_DIR, output_filename)

        print(
            f"  Kopiowanie AAC: {os.path.basename(original_path)} -> {os.path.basename(tmp_file_path)}"
        )

        # Kopiujemy strumień audio bez reenkodowania
        command = [
            "ffmpeg",
            "-y",
            "-i",
            original_path,
            "-vn",  # Ignoruj wideo jeśli istnieje
            "-acodec",
            "copy",  # Kopiuj bez reenkodowania
            tmp_file_path,
        ]

        result = subprocess.run(command, capture_output=True, text=True, timeout=300)

        if result.returncode == 0:
            return (original_path, tmp_file_path)
        else:
            print(f"    Błąd podczas kopiowania AAC: {result.stderr}")
            return None

    except Exception as ex:
        print(f"    BŁĄD podczas kopiowania pliku AAC {os.path.basename(original_path)}: {ex}")
        return None


def _analyze_silence_points_optimized(audio_path, silence_threshold):
    """
    Analizuje plik audio i zwraca listę punktów ciszy dłuższej niż zadany próg.
    Uproszczona wersja - wykrywa tylko jeden rodzaj ciszy.

    Argumenty:
        audio_path (str): Ścieżka do pliku audio do analizy
        silence_threshold (float): Próg długości ciszy do wykrycia (sekundy)

    Zwraca:
        list: Lista słowników z punktami ciszy zawierającymi 'start', 'end', 'duration'
    """
    import re

    # Pobierz długość pliku dla wyświetlania postępu
    from src.utils.audio.duration_checker import get_file_duration

    try:
        file_duration = get_file_duration(audio_path)
        formatted_duration = _format_duration_ffmpeg(file_duration)
        filename = os.path.basename(audio_path)
        print(
            f"[{filename}] [{formatted_duration}] Analiza ciszy dłuższej niż {silence_threshold}s..."
        )
    except Exception:
        file_duration = None
        formatted_duration = None
        filename = os.path.basename(audio_path)
        print(f"[{filename}] Analiza ciszy dłuższej niż {silence_threshold}s...")

    command = [
        "ffmpeg",
        "-i",
        audio_path,
        "-af",
        f"silencedetect=noise={config.SILENCE_DETECTION_NOISE_LEVEL}dB:d={silence_threshold}",
        "-f",
        "null",
        "-",
    ]

    try:
        # Uruchamiamy FFmpeg z wyświetlaniem postępu
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
        )

        # Zmienna do śledzenia czy proces nadal działa
        silence_periods = []
        current_silence = None
        last_display_time = 0
        display_interval = 5.0  # Wyświetlaj postęp co 5 sekund

        def read_output():
            """Czyta wyjście z FFmpeg w czasie rzeczywistym."""
            nonlocal silence_periods, current_silence, last_display_time
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

                    # Parsowanie linii z silence_start i silence_end
                    if "silence_start:" in line_str:
                        match = re.search(r"silence_start:\s*([0-9.]+)", line_str)
                        if match:
                            start_time = float(match.group(1))
                            current_silence = {"start": start_time}

                    elif "silence_end:" in line_str and current_silence is not None:
                        match = re.search(
                            r"silence_end:\s*([0-9.]+).*silence_duration:\s*([0-9.]+)", line_str
                        )
                        if match:
                            end_time = float(match.group(1))
                            duration = float(match.group(2))
                            current_silence.update({"end": end_time, "duration": duration})
                            silence_periods.append(current_silence)
                            current_silence = None

                    # Wyświetlaj postęp co 5 sekund
                    if line_str and current_time - last_display_time >= display_interval:
                        if file_duration is not None:
                            print(
                                f"[{filename}] [{formatted_duration}] Analiza ciszy w toku... {line_str}"
                            )
                        else:
                            print(f"[{filename}] Analiza ciszy w toku... {line_str}")
                        last_display_time = current_time

            except Exception as e:
                print(f"Błąd podczas czytania wyjścia FFmpeg: {e}")

        # Czytamy wyjście w czasie rzeczywistym
        read_output()

        # Czekamy na zakończenie procesu
        process.wait()

        # Wyświetl podsumowanie analizy
        if file_duration is not None:
            print(
                f"[{filename}] [{formatted_duration}] Zakończono analizę ciszy - znaleziono {len(silence_periods)} okresów ciszy dłuższej niż {silence_threshold}s"
            )
        else:
            print(
                f"[{filename}] Zakończono analizę ciszy - znaleziono {len(silence_periods)} okresów ciszy dłuższej niż {silence_threshold}s"
            )

        # Szczegółowe logowanie wykrytych fragmentów ciszy
        if silence_periods:
            print(f"    Wykryte okresy ciszy (>={silence_threshold}s):")
            for i, silence in enumerate(silence_periods, 1):
                start_time = _format_duration_ffmpeg(silence["start"])
                end_time = _format_duration_ffmpeg(silence["end"])
                duration_time = _format_duration_ffmpeg(silence["duration"])
                print(f"      {i}. {start_time} - {end_time} (długość: {duration_time})")
            print()

        return silence_periods

    except Exception as e:
        print(f"    Błąd podczas analizy ciszy dla pliku {os.path.basename(audio_path)}: {e}")
        return []


def _remove_long_silence_aac_optimized(audio_path):
    """
    OPTYMALIZOWANA FUNKCJA: Usuwa długie okresy ciszy z pliku AAC bez reenkodowania.

    Algorytm dla plików AAC:
    1. Wykonaj jednokrotną analizę ciszy całego pliku AAC
    2. Znajdź okresy ciszy (> SILENCE_DETECTION_THRESHOLD)
    3. Pomiń ciszę na początku i końcu pliku
    4. Utwórz segmenty dźwięku między długimi okresami ciszy
    5. Połącz wszystkie segmenty w jeden plik wyjściowy BEZ reenkodowania

    Argumenty:
        audio_path (str): Ścieżka do pliku AAC

    Zwraca:
        str | None: Ścieżka do pliku wyjściowego bez długiej ciszy, lub None przy błędzie
    """
    try:
        # Najpierw sprawdzamy długość oryginalnego pliku
        from src.utils.audio.duration_checker import get_file_duration

        original_duration = get_file_duration(audio_path)
        if original_duration <= 0:
            print("    Błąd: Nie można określić długości pliku oryginalnego")
            return None

        filename = os.path.basename(audio_path)
        formatted_duration = _format_duration_ffmpeg(original_duration)
        print(f"[{filename}] [{formatted_duration}] Usuwanie długiej ciszy z pliku AAC...")

        # KROK 1: Jednokrotna analiza wszystkich okresów ciszy dłuższej niż próg
        silence_periods = _analyze_silence_points_optimized(
            audio_path, config.SILENCE_DETECTION_THRESHOLD
        )
        if not silence_periods:
            print(
                f"    Brak okresów ciszy dłuższej niż {config.SILENCE_DETECTION_THRESHOLD}s w pliku {filename}"
            )
            return audio_path  # Zwróć oryginalną ścieżkę jeśli nie ma ciszy do usunięcia

        print(
            f"    Znaleziono {len(silence_periods)} okresów ciszy do usunięcia, tworzenie segmentów dźwięku..."
        )

        # KROK 2: Utwórz segmenty dźwięku między okresami ciszy
        segments = []
        current_start = 0.0

        # Dodaj segmenty między okresami ciszy
        for silence_period in silence_periods:
            segment_end = silence_period["start"]
            segment_duration = segment_end - current_start

            if segment_duration >= 0.5:  # Minimalny segment 0.5 sekundy
                segments.append(
                    {"start": current_start, "end": segment_end, "duration": segment_duration}
                )

            # Przesuń początek następnego segmentu za okres ciszy
            current_start = silence_period["end"]

        # Dodaj ostatni segment (od końca ostatniego okresu ciszy do końca pliku)
        if current_start < original_duration:
            final_segment_duration = original_duration - current_start
            if final_segment_duration >= 0.5:
                segments.append(
                    {
                        "start": current_start,
                        "end": original_duration,
                        "duration": final_segment_duration,
                    }
                )

        if not segments:
            print("    Brak segmentów dźwięku do utworzenia")
            return audio_path

        # KROK 4: Połącz wszystkie segmenty w jeden plik wyjściowy BEZ reenkodowania
        print(f"    Łączenie {len(segments)} segmentów w jeden plik wyjściowy AAC...")

        output_path = _create_concatenated_aac_file(audio_path, segments, "no_silence")
        if output_path:
            removed_silence = sum(silence["duration"] for silence in silence_periods)
            print(f"    ✓ Utworzono plik AAC bez ciszy, usunięto {removed_silence:.1f}s ciszy")
            return output_path
        else:
            print("    ✗ Nie udało się utworzyć pliku wyjściowego")
            return None

    except Exception as e:
        print(f"    Błąd podczas usuwania długiej ciszy z AAC: {e}")
        return None


def _create_concatenated_aac_file(audio_path, segments, suffix):
    """
    Tworzy plik AAC poprzez połączenie wielu segmentów w jeden plik BEZ reenkodowania.

    Argumenty:
        audio_path (str): Ścieżka do oryginalnego pliku AAC
        segments (list): Lista segmentów do połączenia, każdy segment to dict z kluczami 'start', 'end', 'duration'
        suffix (str): Sufiks dla nazwy pliku wyjściowego

    Zwraca:
        str | None: Ścieżka do utworzonego pliku lub None przy błędzie
    """
    try:
        if not segments:
            return None

        # Przygotuj nazwę pliku wyjściowego
        base_name = os.path.basename(audio_path)
        name_without_ext, _ = os.path.splitext(base_name)
        output_filename = f"{name_without_ext}_{suffix}.m4a"
        output_path = os.path.join(config.AUDIO_TMP_DIR, output_filename)

        # Jeśli jest tylko jeden segment, po prostu wytnij go BEZ reenkodowania
        if len(segments) == 1:
            segment = segments[0]
            return _create_trimmed_aac_file(audio_path, segment["start"], segment["end"], suffix)

        # Dla wielu segmentów - najpierw wytnij każdy segment do osobnego pliku tymczasowego
        temp_files = []
        concat_list = []

        for i, segment in enumerate(segments):
            # Wytnij segment do pliku tymczasowego BEZ reenkodowania
            temp_suffix = f"temp_aac_{suffix}_{i:03d}"
            temp_path = _create_trimmed_aac_file(
                audio_path, segment["start"], segment["end"], temp_suffix
            )

            if temp_path:
                temp_files.append(temp_path)
                concat_list.append(temp_path)
            else:
                print(f"    Błąd podczas tworzenia segmentu tymczasowego {i}")
                # Wyczyść już utworzone pliki tymczasowe
                for temp_file in temp_files:
                    try:
                        os.remove(temp_file)
                    except:
                        pass
                return None

        # Połącz wszystkie segmenty BEZ reenkodowania
        concat_file_path = os.path.join(config.AUDIO_TMP_DIR, f"concat_aac_{suffix}.txt")

        try:
            # Utwórz plik listy do konkatenacji
            with open(concat_file_path, "w", encoding="utf-8") as f:
                for temp_file in concat_list:
                    f.write(f"file '{temp_file}'\n")

            # Uruchom FFmpeg do konkatenacji BEZ reenkodowania
            command = [
                "ffmpeg",
                "-y",  # Nadpisz plik wyjściowy
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                concat_file_path,
                "-c",
                "copy",  # Kopiuj strumień bez reenkodowania
                output_path,
            ]

            success = _run_ffmpeg_with_progress(command, os.path.basename(output_path))
            if success and os.path.exists(output_path):
                print(f"    ✓ Połączono {len(segments)} segmentów AAC w plik wyjściowy")
            else:
                print("    ✗ Błąd podczas łączenia segmentów AAC")
                try:
                    os.remove(output_path)
                except:
                    pass
                output_path = None

        finally:
            # Wyczyść plik listy
            try:
                os.remove(concat_file_path)
            except:
                pass

            # Wyczyść pliki tymczasowe
            for temp_file in temp_files:
                try:
                    os.remove(temp_file)
                except:
                    pass

        return output_path

    except Exception as e:
        print(f"    Błąd podczas tworzenia pliku AAC połączonego: {e}")
        return None


def _create_trimmed_aac_file(audio_path, start_time, end_time, suffix):
    """
    Tworzy plik AAC z określonego zakresu czasowego BEZ reenkodowania.

    Argumenty:
        audio_path (str): Ścieżka do oryginalnego pliku AAC
        start_time (float): Czas rozpoczęcia (sekundy)
        end_time (float): Czas zakończenia (sekundy)
        suffix (str): Sufiks dla nazwy pliku wyjściowego

    Zwraca:
        str | None: Ścieżka do utworzonego pliku lub None przy błędzie
    """
    try:
        duration = end_time - start_time
        if duration < 0.1:  # Minimalna długość 0.1 sekundy
            return None

        # Tworzymy nazwę nowego pliku
        base_name = os.path.basename(audio_path)
        name_without_ext = os.path.splitext(base_name)[0]
        output_filename = f"{name_without_ext}_{suffix}.m4a"
        output_path = os.path.join(config.AUDIO_TMP_DIR, output_filename)

        start_formatted = _format_duration_ffmpeg(start_time)
        duration_formatted = _format_duration_ffmpeg(duration)

        # Dla plików AAC - kopiujemy bez reenkodowania
        command = [
            "ffmpeg",
            "-y",
            "-i",
            audio_path,
            "-ss",
            start_formatted,
            "-t",
            duration_formatted,
            "-vn",  # Ignoruj wideo jeśli istnieje
            "-acodec",
            "copy",  # Kopiuj bez reenkodowania
            output_path,
        ]

        result = subprocess.run(command, capture_output=True, text=True, timeout=300)

        if result.returncode == 0:
            return output_path
        else:
            print(f"    Błąd FFmpeg podczas cięcia AAC: {result.stderr}")
            return None

    except Exception as e:
        print(f"    Błąd podczas tworzenia pliku AAC {suffix}: {e}")
        return None


# Removed: AAC chunk splitting utility (_split_aac_into_chunks_optimized)


def _convert_single_file(original_path):
    """
    Konwertuje pojedynczy plik i zwraca listę tupli (source, tmp) lub None przy błędzie.
    Zawsze zwraca jeden plik wynikowy; cisza jest usuwana bez generowania chunków.
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

        # SPRAWDZENIE KLUCZOWE: Czy plik jest już w AAC?
        is_aac = is_aac_audio_file(original_path)
        if is_aac:
            print(
                f"  Plik już w AAC wykryty: {os.path.basename(original_path)} - pomijam konwersję"
            )
            return _handle_aac_file(original_path, duration_sec, standardized_name)
        else:
            print(
                f"  Plik wymaga konwersji: {os.path.basename(original_path)} - rozpoczynam konwersję do AAC"
            )

        # Sprawdzamy czy plik jest dłuższy niż limit
        if duration_sec > config.MAX_FILE_DURATION_SECONDS:
            print(f"  Długi plik wykryty: {os.path.basename(original_path)} ({duration_sec:.1f}s)")

            # Używamy metody: najpierw konwertuj cały plik, potem usuń ciszę – wynik to jeden plik
            result = _convert_and_split_file(original_path)
            if result and len(result) > 0:
                return result
            else:
                print("    Błąd podczas optymalizowanej konwersji, fallback do prostej ścieżki")

                # Fallback: standardowa konwersja do jednego pliku i usunięcie ciszy
                std = _convert_single_file_standard(original_path)
                if not std:
                    return None
                _, tmp_path = std
                output_path = _remove_long_silence(tmp_path)
                if output_path and output_path != tmp_path:
                    try:
                        os.remove(tmp_path)
                    except Exception:
                        pass
                    return [(original_path, output_path)]
                elif output_path == tmp_path:
                    return [(original_path, tmp_path)]
                else:
                    # Jeśli usuwanie ciszy się nie powiodło, zwróć plik po konwersji
                    return [(original_path, tmp_path)]
        else:
            # Plik jest odpowiednio krótki - standardowa konwersja do AAC, potem usuń ciszę
            std = _convert_single_file_standard(original_path)
            if not std:
                return None
            _, tmp_path = std
            output_path = _remove_long_silence(tmp_path)
            if output_path and output_path != tmp_path:
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass
                return [(original_path, output_path)]
            elif output_path == tmp_path:
                return [(original_path, tmp_path)]
            else:
                # Jeśli usuwanie ciszy się nie powiodło, zwróć plik po konwersji
                return [(original_path, tmp_path)]

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

        # KROK 2: Usuń długie okresy ciszy z pliku
        print("  Krok 2: Usuwanie długiej ciszy...")
        output_path = _remove_long_silence(full_tmp_path)

        # Jeśli udało się utworzyć plik bez ciszy
        if output_path and output_path != full_tmp_path:
            # Usuń oryginalny skonwertowany plik
            try:
                os.remove(full_tmp_path)
                print(
                    f"    ✓ Usunięto oryginalny plik skonwertowany: {os.path.basename(full_tmp_path)}"
                )
            except:
                pass
            full_tmp_path = output_path
            print("    ✓ Utworzono plik bez długiej ciszy")
        elif output_path == full_tmp_path:
            print("    Brak długiej ciszy do usunięcia, używam oryginalnego pliku")
        else:
            print("    ✗ Nie udało się utworzyć pliku bez ciszy, używam oryginalnego pliku")

        # KROK 3: Wynik zawsze jeden plik – zwróć przetworzony plik (bez ciszy jeśli się udało)
        return [(original_path, full_tmp_path)]

    except Exception as ex:
        print(
            f"    KRYTYCZNY BŁĄD podczas optymalizowanej konwersji pliku {os.path.basename(original_path)}: {ex}"
        )
        return None


# Removed: splitting from converted file utility (_split_from_converted_file)


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
