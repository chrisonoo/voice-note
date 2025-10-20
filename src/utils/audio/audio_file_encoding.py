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


def _format_duration_ffmpeg(duration_sec):
    """
    Formatuje czas trwania w sekundach do formatu FFmpeg (hh:mm:ss.ms).
    """
    hours = int(duration_sec // 3600)
    minutes = int((duration_sec % 3600) // 60)
    seconds = int(duration_sec % 60)
    milliseconds = int((duration_sec % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}"


def _split_by_long_silence(audio_path, leading_trailing_threshold=1.0, long_silence_threshold=5.0):
    """
    Dzieli plik audio na segmenty dźwięku, usuwając długie okresy ciszy.

    Algorytm:
    1. Usuwa ciszę z początku i końca (jeśli > leading_trailing_threshold)
    2. Dzieli pozostały plik na segmenty dźwięku, pomijając długie okresy ciszy (> long_silence_threshold)
    3. Każdy segment dźwięku staje się osobnym plikiem

    Argumenty:
        audio_path (str): Ścieżka do pliku audio do przetworzenia
        leading_trailing_threshold (float): Próg ciszy na początku i końcu (sekundy)
        long_silence_threshold (float): Próg długiej ciszy do pominięcia (sekundy)

    Zwraca:
        list: Lista ścieżek do plików-segmentów dźwięku, lub [oryginalna_ścieżka] jeśli nie ma zmian
    """
    try:
        # Najpierw sprawdzamy długość oryginalnego pliku
        from src.utils.audio.duration_checker import get_file_duration

        original_duration = get_file_duration(audio_path)
        if original_duration <= 0:
            print("    Błąd: Nie można określić długości pliku oryginalnego")
            return [audio_path]

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
            f"silencedetect=noise=-30dB:d={leading_trailing_threshold}",
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
                return [audio_path]

        except subprocess.TimeoutExpired:
            print(
                f"    TIMEOUT: Analiza ciszy dla pliku {os.path.basename(audio_path)} przekroczyła limit czasu"
            )
            return [audio_path]

        if not silence_periods:
            print(f"    Brak okresów ciszy w pliku {os.path.basename(audio_path)}")
            return [audio_path]

        # KROK 2: Znajdź ciszę na początku i końcu
        leading_silence = None
        for silence in silence_periods:
            if silence["start"] < 1.0 and silence["duration"] >= leading_trailing_threshold:
                leading_silence = silence
                break

        trailing_silence = None
        for silence in reversed(silence_periods):
            if (
                abs(silence["end"] - original_duration) < 1.0
                and silence["duration"] >= leading_trailing_threshold
            ):
                trailing_silence = silence
                break

        # KROK 3: Oblicz efektywny zakres dźwięku (bez ciszy na początku i końcu)
        effective_start = leading_silence["end"] if leading_silence else 0.0
        effective_end = trailing_silence["start"] if trailing_silence else original_duration

        if effective_start >= effective_end:
            print("    Efektywny zakres dźwięku jest nieprawidłowy")
            return [audio_path]

        effective_duration = effective_end - effective_start
        if effective_duration < 5.0:
            print(
                f"    Efektywny dźwięk jest za krótki ({effective_duration:.1f}s), pozostawiam oryginalny plik"
            )
            return [audio_path]

        # KROK 4: Znajdź długie okresy ciszy w efektywnym zakresie
        long_silences = []
        for silence in silence_periods:
            # Sprawdź czy cisza jest w efektywnym zakresie i jest odpowiednio długa
            if (
                silence["start"] >= effective_start
                and silence["end"] <= effective_end
                and silence["duration"] >= long_silence_threshold
            ):
                long_silences.append(silence)

        # KROK 5: Jeśli nie ma długich okresów ciszy, zwróć plik po usunięciu ciszy z początku i końca
        if not long_silences:
            print(f"    Brak długich okresów ciszy (> {long_silence_threshold}s) do usunięcia")
            # Utwórz plik bez ciszy z początku i końca
            return _create_trimmed_file(audio_path, effective_start, effective_end, "trimmed")

        # KROK 6: Podziel na segmenty dźwięku
        print(
            f"    Znaleziono {len(long_silences)} długich okresów ciszy, dzielenie na segmenty dźwięku..."
        )

        segments = []
        current_start = effective_start

        # Dodaj segmenty między długimi okresami ciszy
        for long_silence in long_silences:
            segment_end = long_silence["start"]
            segment_duration = segment_end - current_start

            if segment_duration >= 1.0:  # Minimalny segment 1 sekunda
                segments.append(
                    {"start": current_start, "end": segment_end, "duration": segment_duration}
                )

            # Przesuń początek następnego segmentu za długą ciszę
            current_start = long_silence["end"]

        # Dodaj ostatni segment (od końca ostatniej długiej ciszy do końca efektywnego zakresu)
        if current_start < effective_end:
            final_segment_duration = effective_end - current_start
            if final_segment_duration >= 1.0:
                segments.append(
                    {
                        "start": current_start,
                        "end": effective_end,
                        "duration": final_segment_duration,
                    }
                )

        if not segments:
            print("    Brak segmentów dźwięku do utworzenia")
            return [audio_path]

        # KROK 7: Utwórz pliki dla każdego segmentu, sprawdzając długość
        print(f"    Tworzenie {len(segments)} segmentów dźwięku...")
        segment_paths = []

        for i, segment in enumerate(segments):
            # Sprawdź czy segment przekracza maksymalną długość
            if segment["duration"] > config.MAX_FILE_DURATION_SECONDS:
                print(
                    f"      Segment {i + 1} jest za długi ({segment['duration']:.1f}s > {config.MAX_FILE_DURATION_SECONDS}s), dzielenie dalej..."
                )
                # Podziel długi segment na mniejsze części
                sub_segments = _split_long_segment(
                    audio_path, segment["start"], segment["end"], f"segment_{i + 1:03d}"
                )
                segment_paths.extend(sub_segments)
            else:
                # Segment ma odpowiednią długość - utwórz plik
                segment_path = _create_trimmed_file(
                    audio_path, segment["start"], segment["end"], f"segment_{i + 1:03d}"
                )
                if segment_path:
                    segment_paths.append(segment_path)
                    print(
                        f"      ✓ Segment {i + 1}: {segment['start']:.1f}s - {segment['end']:.1f}s ({segment['duration']:.1f}s)"
                    )
                else:
                    print(f"      ✗ Błąd podczas tworzenia segmentu {i + 1}")

        if segment_paths:
            removed_silence = sum(silence["duration"] for silence in long_silences)
            print(
                f"    ✓ Utworzono {len(segment_paths)} segmentów, usunięto {removed_silence:.1f}s długiej ciszy"
            )
            return segment_paths
        else:
            print("    ✗ Nie udało się utworzyć żadnego segmentu")
            return [audio_path]

    except Exception as e:
        print(f"    Błąd podczas dzielenia przez długą ciszę: {e}")
        return [audio_path]


def _split_long_segment(audio_path, start_time, end_time, prefix):
    """
    Dzieli długi segment audio na mniejsze części, które nie przekraczają MAX_FILE_DURATION_SECONDS.

    Argumenty:
        audio_path (str): Ścieżka do oryginalnego pliku audio
        start_time (float): Czas rozpoczęcia segmentu (sekundy)
        end_time (float): Czas zakończenia segmentu (sekundy)
        prefix (str): Prefix dla nazw plików wyjściowych

    Zwraca:
        list: Lista ścieżek do utworzonych plików-segmentów
    """
    try:
        segment_duration = end_time - start_time
        print(
            f"        Dzielenie segmentu {prefix}: {start_time:.1f}s - {end_time:.1f}s ({segment_duration:.1f}s)"
        )

        # KROK 1: Spróbuj znaleźć punkty ciszy w tym segmencie z mniejszym progiem
        command = [
            "ffmpeg",
            "-i",
            audio_path,
            "-ss",
            _format_duration_ffmpeg(start_time),
            "-t",
            _format_duration_ffmpeg(segment_duration),
            "-af",
            "silencedetect=noise=-30dB:d=2.0",  # Mniejszy próg ciszy (2s zamiast 5s)
            "-f",
            "null",
            "-",
        ]

        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=300)
        except subprocess.TimeoutExpired:
            print(f"        TIMEOUT: Analiza ciszy dla segmentu {prefix} przekroczyła limit czasu")
            # Fallback: dziel na równe części
            return _split_segment_into_equal_chunks(audio_path, start_time, end_time, prefix)

        silence_periods = []
        current_silence = None
        for line in result.stderr.split("\n"):
            if "silence_start:" in line:
                match = re.search(r"silence_start:\s*([0-9.]+)", line)
                if match:
                    current_silence = {"start": float(match.group(1)) + start_time}  # Dodaj offset

            elif "silence_end:" in line and current_silence is not None:
                match = re.search(r"silence_end:\s*([0-9.]+).*silence_duration:\s*([0-9.]+)", line)
                if match:
                    current_silence.update(
                        {
                            "end": float(match.group(1)) + start_time,  # Dodaj offset
                            "duration": float(match.group(2)),
                        }
                    )
                    silence_periods.append(current_silence)
                    current_silence = None

        # KROK 2: Oblicz punkty podziału na podstawie znalezionych ciszy
        split_points = _calculate_split_points(
            segment_duration, silence_periods, config.MAX_FILE_DURATION_SECONDS
        )

        # Dodaj offset do wszystkich punktów podziału
        split_points = [point + start_time for point in split_points]

        # KROK 3: Utwórz pliki dla każdego podsegmentu
        sub_segment_paths = []
        for i in range(len(split_points) - 1):
            sub_start = split_points[i]
            sub_end = split_points[i + 1]
            sub_duration = sub_end - sub_start

            if sub_duration >= 1.0:  # Minimalny segment 1 sekunda
                sub_suffix = f"{prefix}_{i + 1:02d}"
                sub_path = _create_trimmed_file(audio_path, sub_start, sub_end, sub_suffix)
                if sub_path:
                    sub_segment_paths.append(sub_path)
                    print(
                        f"          ✓ Podsegment {i + 1}: {sub_start:.1f}s - {sub_end:.1f}s ({sub_duration:.1f}s)"
                    )
                else:
                    print(f"          ✗ Błąd podczas tworzenia podsegmentu {i + 1}")

        return (
            sub_segment_paths
            if sub_segment_paths
            else _split_segment_into_equal_chunks(audio_path, start_time, end_time, prefix)
        )

    except Exception as e:
        print(f"        Błąd podczas dzielenia długiego segmentu {prefix}: {e}")
        # Fallback: dziel na równe części
        return _split_segment_into_equal_chunks(audio_path, start_time, end_time, prefix)


def _split_segment_into_equal_chunks(audio_path, start_time, end_time, prefix):
    """
    Dzieli segment na równe części co MAX_FILE_DURATION_SECONDS sekund.
    Fallback gdy nie można znaleźć punktów ciszy.

    Argumenty:
        audio_path (str): Ścieżka do oryginalnego pliku audio
        start_time (float): Czas rozpoczęcia segmentu (sekundy)
        end_time (float): Czas zakończenia segmentu (sekundy)
        prefix (str): Prefix dla nazw plików wyjściowych

    Zwraca:
        list: Lista ścieżek do utworzonych plików-segmentów
    """
    try:
        segment_duration = end_time - start_time
        print(f"        Fallback: dzielenie na równe części co {config.MAX_FILE_DURATION_SECONDS}s")

        chunk_paths = []
        current_time = start_time

        chunk_index = 1
        while current_time < end_time:
            chunk_end = min(current_time + config.MAX_FILE_DURATION_SECONDS, end_time)
            chunk_duration = chunk_end - current_time

            if chunk_duration >= 1.0:  # Minimalny segment 1 sekunda
                chunk_suffix = f"{prefix}_chunk_{chunk_index:02d}"
                chunk_path = _create_trimmed_file(audio_path, current_time, chunk_end, chunk_suffix)
                if chunk_path:
                    chunk_paths.append(chunk_path)
                    print(
                        f"          ✓ Chunk {chunk_index}: {current_time:.1f}s - {chunk_end:.1f}s ({chunk_duration:.1f}s)"
                    )
                else:
                    print(f"          ✗ Błąd podczas tworzenia chunk {chunk_index}")

            current_time = chunk_end
            chunk_index += 1

        return chunk_paths

    except Exception as e:
        print(f"        Błąd podczas fallback dzielenia segmentu {prefix}: {e}")
        return []


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


def _analyze_and_split_optimized(audio_path):
    """
    OPTYMALIZOWANA FUNKCJA: Wykonuje jednokrotną analizę ciszy całego pliku
    i na podstawie tej analizy oblicza wszystkie punkty podziału.

    Argumenty:
        audio_path (str): Ścieżka do pliku audio do analizy i podziału

    Zwraca:
        list: Lista punktów podziału (timestampy w sekundach) lub None przy błędzie
    """
    import re
    import time

    from src.utils.audio.duration_checker import get_file_duration

    # Pobierz długość pliku
    try:
        file_duration = get_file_duration(audio_path)
        formatted_duration = _format_duration_ffmpeg(file_duration)
        filename = os.path.basename(audio_path)
        print(
            f"[{filename}] [{formatted_duration}] Jednokrotna analiza ciszy i obliczanie punktów podziału..."
        )
    except Exception as ex:
        print(f"    Błąd podczas pobierania długości pliku: {ex}")
        return None

    # JEDNOKROTNA ANALIZA CISZY dla całego pliku
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
        last_display_time = time.time()
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
                        print(
                            f"[{filename}] [{formatted_duration}] Analiza ciszy w toku:\n    {line_str}"
                        )
                        last_display_time = current_time

            except Exception as e:
                print(f"    Błąd podczas czytania wyjścia FFmpeg: {e}")

        # Czytamy wyjście w czasie rzeczywistym
        read_output()

        # Czekamy na zakończenie procesu
        process.wait()

        print(f"    Znaleziono {len(silence_periods)} okresów ciszy")

        # OBLICZAMY WSZYSTKIE PUNKTY PODZIAŁU na podstawie pojedynczej analizy
        split_points = _calculate_split_points_optimized(file_duration, silence_periods)

        if split_points and len(split_points) >= 2:
            print(f"    ✓ Obliczono {len(split_points) - 1} punktów podziału")
            return split_points
        else:
            print("    ✗ Nie udało się obliczyć punktów podziału")
            return None

    except subprocess.TimeoutExpired:
        print("    TIMEOUT: Analiza ciszy przekroczyła limit czasu (10 minut)")
        return None
    except Exception as ex:
        print(f"    Błąd podczas analizy ciszy: {ex}")
        return None


def _calculate_split_points_optimized(
    total_duration, silence_periods, chunk_duration=config.MAX_FILE_DURATION_SECONDS
):
    """
    OPTYMALIZOWANA FUNKCJA: Oblicza wszystkie punkty podziału na podstawie pojedynczej analizy ciszy.

    NOWA STRATEGIA:
    1. Wszystkie końce długich okresów ciszy (>5s) są obowiązkowymi punktami podziału
    2. Dla odcinków między tymi punktami dłuższych niż 10 min, dzielimy na 10 min + reszta

    Argumenty:
        total_duration (float): Całkowity czas trwania pliku w sekundach
        silence_periods (list): Lista słowników z punktami ciszy
        chunk_duration (int): Docelowa długość chunk'a w sekundach (domyślnie 600s = 10min)

    Zwraca:
        list: Lista punktów podziału (timestampy w sekundach)
    """
    # Filtruj tylko znaczące okresy ciszy (> 5 sekund)
    significant_silences = [s for s in silence_periods if s["duration"] > 5.0]

    # Zbierz wszystkie obowiązkowe punkty podziału: początek pliku, końce długich ciszy, koniec pliku
    mandatory_split_points = [0.0]  # Zawsze zaczynaj od początku

    for silence in significant_silences:
        # Koniec długiej ciszy = obowiązkowy początek nowego chunk'a
        mandatory_split_points.append(silence["end"])

    mandatory_split_points.append(total_duration)  # Koniec pliku
    mandatory_split_points = sorted(list(set(mandatory_split_points)))  # Usuń duplikaty i posortuj

    # Teraz dla każdego odcinka między obowiązkowymi punktami, sprawdź czy nie jest za długi
    final_split_points = [0.0]  # Zawsze zaczynaj od początku

    for i in range(len(mandatory_split_points) - 1):
        segment_start = mandatory_split_points[i]
        segment_end = mandatory_split_points[i + 1]
        segment_duration = segment_end - segment_start

        if segment_duration <= chunk_duration:
            # Odcinek OK, dodaj tylko koniec
            final_split_points.append(segment_end)
        else:
            # Odcinek za długi - dziel na chunk_duration + reszta
            current_time = segment_start
            while current_time < segment_end:
                next_split = min(current_time + chunk_duration, segment_end)
                if next_split < segment_end:  # Jeśli nie jesteśmy przy końcu segmentu
                    final_split_points.append(next_split)
                else:  # Jesteśmy przy końcu segmentu - dodaj go
                    final_split_points.append(segment_end)
                current_time = next_split

    # Usuń duplikaty i posortuj
    final_split_points = sorted(list(set(final_split_points)))

    # Upewnij się, że koniec pliku jest uwzględniony
    if final_split_points[-1] < total_duration - 1:
        final_split_points.append(total_duration)

    print(f"    ✓ Obliczono {len(final_split_points) - 1} punktów podziału:")
    print(f"      - {len(significant_silences)} obowiązkowych (końce długich ciszy)")
    print(f"      - Dzielenie długich odcinków na ~{chunk_duration // 60}min + reszta")

    return final_split_points


def _analyze_silence_points(audio_path):
    """
    Analizuje plik audio i zwraca listę punktów ciszy dłuższej niż 2 sekundy.

    Argumenty:
        audio_path (str): Ścieżka do pliku audio do analizy

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
        print(f"[{filename}] [{formatted_duration}] Rozpoczynam analizę ciszy...")
    except Exception:
        file_duration = None
        formatted_duration = None
        filename = os.path.basename(audio_path)
        print(f"[{filename}] Rozpoczynam analizę ciszy...")

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
                        # Wyciągnij timestamp początku ciszy
                        match = re.search(r"silence_start:\s*([0-9.]+)", line_str)
                        if match:
                            start_time = float(match.group(1))
                            current_silence = {"start": start_time}

                    elif "silence_end:" in line_str and current_silence is not None:
                        # Wyciągnij timestamp końca ciszy i czas trwania
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
            return []

        # Wyświetl podsumowanie analizy
        if file_duration is not None:
            print(
                f"[{filename}] [{formatted_duration}] Zakończono analizę ciszy - znaleziono {len(silence_periods)} okresów ciszy"
            )
        else:
            print(
                f"[{filename}] Zakończono analizę ciszy - znaleziono {len(silence_periods)} okresów ciszy"
            )

        # Szczegółowe logowanie wykrytych fragmentów ciszy
        if silence_periods:
            print("    Wykryte fragmenty ciszy:")
            for i, silence in enumerate(silence_periods, 1):
                print(
                    f"      {i}. {silence['start']:.1f}s - {silence['end']:.1f}s (długość: {silence['duration']:.1f}s)"
                )

        return silence_periods

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

            # Dla plików AAC dzielimy bez reenkodowania
            result = _split_aac_file(original_path, duration_sec, standardized_name)
            if result and len(result) > 0:
                return result
            else:
                print("    Błąd podczas dzielenia pliku AAC, kopiuję bez zmian")
                # Fallback: kopiuj bez zmian
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


def _cut_aac_segments_optimized(original_path, split_points, standardized_name):
    """
    OPTYMALIZOWANA FUNKCJA: Dzieli plik AAC na segmenty bez reenkodowania
    używając obliczonych punktów podziału.

    Argumenty:
        original_path (str): Ścieżka do oryginalnego pliku AAC
        split_points (list): Lista punktów podziału (timestampy w sekundach)
        standardized_name (str): Standaryzowana nazwa pliku

    Zwraca:
        list: Lista tupli (source_path, segment_path) lub None przy błędzie
    """
    if not split_points or len(split_points) < 2:
        print("    Błąd: Za mało punktów podziału")
        return None

    try:
        segment_tuples = []

        print(f"  Fizyczne cięcie AAC na {len(split_points) - 1} segmentów bez reenkodowania")

        # Iterujemy przez pary punktów podziału
        for i in range(len(split_points) - 1):
            start_time = split_points[i]
            end_time = split_points[i + 1]
            duration = end_time - start_time

            # Pomiń segmenty krótsze niż 1 sekunda
            if duration < 1.0:
                print(f"    Pomijanie segmentu {i + 1}: zbyt krótki ({duration:.1f}s)")
                continue

            # Utwórz nazwę pliku wyjściowego
            segment_number = i + 1
            output_filename = f"{standardized_name}_{segment_number:03d}.m4a"
            output_path = os.path.join(config.AUDIO_TMP_DIR, output_filename)

            # Przygotuj komendę FFmpeg do wycięcia segmentu BEZ reenkodowania
            start_formatted = _format_duration_ffmpeg(start_time)
            duration_formatted = _format_duration_ffmpeg(duration)

            command = [
                "ffmpeg",
                "-y",
                "-i",
                original_path,
                "-ss",
                start_formatted,  # Start time
                "-t",
                duration_formatted,  # Duration
                "-vn",  # Ignoruj wideo jeśli istnieje
                "-acodec",
                "copy",  # Kopiuj bez reenkodowania
                output_path,
            ]

            print(
                f"  Cięcie segmentu {segment_number}: {start_formatted} - {_format_duration_ffmpeg(end_time)} ({duration:.1f}s)"
            )

            # Uruchom FFmpeg
            result = subprocess.run(command, capture_output=True, text=True, timeout=300)

            if result.returncode == 0:
                segment_tuples.append((original_path, output_path))
                print(f"    ✓ Utworzono segment: {os.path.basename(output_path)}")
            else:
                print(f"    ✗ Błąd podczas cięcia segmentu {segment_number}: {result.stderr}")
                # Spróbuj usunąć niekompletny plik jeśli istnieje
                if os.path.exists(output_path):
                    try:
                        os.remove(output_path)
                    except:
                        pass
                return None

        if segment_tuples:
            print(f"    ✓ Utworzono {len(segment_tuples)} segmentów AAC bez reenkodowania")
            return segment_tuples
        else:
            print("    ✗ Nie udało się utworzyć żadnego segmentu")
            return None

    except Exception as ex:
        print(f"    BŁĄD podczas cięcia pliku AAC {os.path.basename(original_path)}: {ex}")
        return None


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


def _split_aac_file(original_path, duration_sec, standardized_name):
    """
    Dzieli długi plik AAC na segmenty bez reenkodowania, usuwając długie okresy ciszy.

    Argumenty:
        original_path (str): Ścieżka do oryginalnego pliku AAC
        duration_sec (float): Długość pliku w sekundach
        standardized_name (str): Standaryzowana nazwa pliku

    Zwraca:
        list: Lista tupli (source_path, segment_path) lub None przy błędzie
    """
    try:
        print("  Strategia AAC: dzielenie bez reenkodowania z usunięciem długiej ciszy")

        # KROK 1: Podziel plik na segmenty dźwięku, usuwając długie okresy ciszy
        segment_paths = _split_by_long_silence_aac(original_path)

        if segment_paths and len(segment_paths) > 0:
            if len(segment_paths) > 1:
                print(f"    ✓ Utworzono {len(segment_paths)} segmentów AAC (długa cisza usunięta)")
                return [(original_path, segment_path) for segment_path in segment_paths]
            else:
                # Tylko jeden segment - sprawdzamy czy trzeba dzielić na chunk'y
                from src.utils.audio.duration_checker import get_file_duration

                single_segment = segment_paths[0]
                segment_duration = get_file_duration(single_segment)

                if segment_duration > config.MAX_FILE_DURATION_SECONDS:
                    # Segment nadal za długi - dzielimy na równe chunk'y
                    print("    Segment nadal za długi, dzielenie na chunk'y...")
                    chunk_paths = _split_aac_into_chunks(
                        single_segment, standardized_name, original_path
                    )
                    # Usuń tymczasowy segment
                    try:
                        os.remove(single_segment)
                    except:
                        pass
                    return chunk_paths if chunk_paths else None
                else:
                    # Segment odpowiedniej długości
                    return [(original_path, single_segment)]
        else:
            print("    Nie udało się utworzyć segmentów, dzielenie na równe chunk'y")
            return _split_aac_into_chunks(original_path, standardized_name, original_path)

    except Exception as ex:
        print(f"    BŁĄD podczas dzielenia pliku AAC {os.path.basename(original_path)}: {ex}")
        return None


def _split_by_long_silence_aac(audio_path):
    """
    OPTYMALIZOWANA FUNKCJA: Dzieli plik AAC na segmenty dźwięku, usuwając długie okresy ciszy.
    Wersja dla plików AAC - bez reenkodowania z jednokrotną analizą ciszy.

    Argumenty:
        audio_path (str): Ścieżka do pliku AAC

    Zwraca:
        list: Lista ścieżek do plików-segmentów lub [oryginalna_ścieżka] jeśli nie ma zmian
    """
    try:
        print("  OPTYMALIZACJA: Jednokrotna analiza ciszy dla usuwania długich okresów ciszy")

        # JEDNOKROTNA ANALIZA CISZY
        split_points = _analyze_and_split_optimized(audio_path)

        if not split_points or len(split_points) < 2:
            print("    Brak segmentów do podziału, zwracam oryginalny plik")
            return [audio_path]

        # FIZYCZNE CIĘCIE SEGMENTÓW BEZ REENKODOWANIA
        # Tworzymy tymczasową nazwę dla segmentów
        base_name = os.path.basename(audio_path)
        standardized_name, _ = os.path.splitext(base_name.lower().replace(" ", "_"))

        segment_tuples = _cut_aac_segments_optimized(audio_path, split_points, standardized_name)

        if segment_tuples:
            # Zwracamy tylko ścieżki segmentów (bez source_path jak w innych funkcjach)
            return [segment_path for _, segment_path in segment_tuples]
        else:
            print("    Błąd podczas cięcia segmentów, zwracam oryginalny plik")
            return [audio_path]

    except Exception as ex:
        print(f"    BŁĄD podczas optymalizacji AAC: {ex}")
        # Fallback do starej metody
        return _split_by_long_silence(
            audio_path, leading_trailing_threshold=1.0, long_silence_threshold=5.0
        )


def _split_aac_into_chunks(original_path, standardized_name, source_path):
    """
    OPTYMALIZOWANA FUNKCJA: Dzieli plik AAC na chunk'y bez reenkodowania
    używając jednokrotnej analizy ciszy i fizycznego cięcia.

    Argumenty:
        original_path (str): Ścieżka do pliku do podzielenia
        standardized_name (str): Standaryzowana nazwa pliku
        source_path (str): Oryginalna ścieżka źródłowa

    Zwraca:
        list: Lista tupli (source_path, chunk_path) lub None przy błędzie
    """
    try:
        print("  OPTYMALIZACJA: Jednokrotna analiza ciszy + fizyczne cięcie")

        # JEDNOKROTNA ANALIZA CISZY I OBLICZENIE PUNKTÓW PODZIAŁU
        split_points = _analyze_and_split_optimized(original_path)

        if not split_points or len(split_points) < 2:
            print("    Za mało punktów podziału, kopiuję bez zmian")
            return [_copy_aac_file(original_path, standardized_name)]

        # FIZYCZNE CIĘCIE PLIKU BEZ REENKODOWANIA
        chunk_tuples = _cut_aac_segments_optimized(original_path, split_points, standardized_name)

        if chunk_tuples:
            return chunk_tuples
        else:
            print("    Błąd podczas cięcia, kopiuję bez zmian")
            return [_copy_aac_file(original_path, standardized_name)]

    except Exception as ex:
        print(f"    BŁĄD podczas dzielenia pliku AAC {os.path.basename(original_path)}: {ex}")
        return None


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

        # KROK 2: Podziel plik na segmenty dźwięku, usuwając długie okresy ciszy
        print("  Krok 2: Dzielenie na segmenty dźwięku z usunięciem długiej ciszy...")
        segment_paths = _split_by_long_silence(full_tmp_path)

        # Jeśli utworzono segmenty, użyj pierwszego segmentu do dalszego przetwarzania
        if segment_paths and len(segment_paths) > 0:
            first_segment_path = segment_paths[0]
            if first_segment_path != full_tmp_path:
                # Usuń oryginalny skonwertowany plik
                try:
                    os.remove(full_tmp_path)
                    print(
                        f"    ✓ Usunięto oryginalny plik skonwertowany: {os.path.basename(full_tmp_path)}"
                    )
                except:
                    pass
                full_tmp_path = first_segment_path

            # Jeśli mamy wiele segmentów, zwróć je wszystkie jako finalne pliki
            if len(segment_paths) > 1:
                print(
                    f"    ✓ Utworzono {len(segment_paths)} segmentów dźwięku (długa cisza usunięta)"
                )
                # Usuń oryginalny skonwertowany plik jeśli został zastąpiony
                if full_tmp_path != segment_paths[0]:
                    try:
                        os.remove(full_tmp_path)
                    except:
                        pass
                return [(original_path, segment_path) for segment_path in segment_paths]
        else:
            print("    ✗ Nie udało się utworzyć segmentów, używam oryginalnego pliku")

        # KROK 3: Jeśli nie mamy wielu segmentów, analizuj ciszę dla dzielenia na chunk'y
        print("  Krok 3: Analiza ciszy w przetworzonym pliku...")
        silence_periods = _analyze_silence_points(full_tmp_path)
        if silence_periods is None:
            print("    Błąd podczas analizy ciszy, dzielenie na równe części")
            silence_periods = []

        # KROK 4: Oblicz punkty podziału
        print("  Krok 4: Obliczanie punktów podziału...")
        split_points = _calculate_split_points(duration_sec, silence_periods)

        # KROK 5: Podziel skonwertowany plik na chunk'y
        print("  Krok 5: Dzielenie na chunk'y...")
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
