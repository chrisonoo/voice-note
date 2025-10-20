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

        # Wyświetl podsumowanie analizy ze wszystkimi wykrytymi okresami ciszy
        print(f"    Wykryto łącznie {len(silence_periods)} okresów ciszy")
        print("    Szczegóły wykrytych okresów ciszy:")
        for i, silence in enumerate(silence_periods, 1):
            start_time = _format_duration_ffmpeg(silence["start"])
            end_time = _format_duration_ffmpeg(silence["end"])
            duration_time = _format_duration_ffmpeg(silence["duration"])
            print(f"      {i}. {start_time} - {end_time} (długość: {duration_time})")
        print()

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
    Plik wejściowy jest już skonwertowany, więc kopiujemy bez reenkodowania.

    Argumenty:
        audio_path (str): Ścieżka do oryginalnego pliku (już skonwertowanego)
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

        # Plik jest już skonwertowany, więc kopiujemy bez reenkodowania
        command = f'ffmpeg -y -i "{audio_path}" -ss {start_formatted} -t {duration_formatted} -vn -acodec copy "{output_path}"'

        result = subprocess.run(command, capture_output=True, text=True, timeout=600)

        if result.returncode == 0:
            return output_path
        else:
            print(f"    Błąd FFmpeg: {result.stderr}")
            return None

    except Exception as e:
        print(f"    Błąd podczas tworzenia pliku {suffix}: {e}")
        return None


def _split_long_audio_into_chunks(
    audio_path: str, original_path: str
) -> list[tuple[str, str]] | None:
    """
    Dzieli długi plik audio na mniejsze fragmenty o określonej maksymalnej długości.

    Argumenty:
        audio_path (str): Ścieżka do pliku audio do podzielenia (po usunięciu ciszy)
        original_path (str): Ścieżka do oryginalnego pliku źródłowego

    Zwraca:
        list[tuple[str, str]] | None: Lista tupli (original_path, chunk_path) lub None przy błędzie
    """
    try:
        from src.utils.audio.duration_checker import get_file_duration

        duration_sec = get_file_duration(audio_path)
        if duration_sec <= 0:
            print(f"    Błąd: Nie można określić długości pliku {os.path.basename(audio_path)}")
            return None

        max_chunk_duration_sec = config.MAX_CHUNK_DURATION_MINUTES * 60

        # Jeśli plik jest krótszy niż maksymalna długość fragmentu, nie dziel
        if duration_sec <= max_chunk_duration_sec:
            return [(original_path, audio_path)]

        filename = os.path.basename(audio_path)
        formatted_duration = _format_duration_ffmpeg(duration_sec)
        print(
            f"[{filename}] [{formatted_duration}] Plik dłuższy niż {config.MAX_CHUNK_DURATION_MINUTES} minut - rozpoczynam dzielenie..."
        )

        # Oblicz liczbę fragmentów
        num_chunks = int(duration_sec / max_chunk_duration_sec) + 1
        print(
            f"    Dzielę na {num_chunks} fragmentów po ~{config.MAX_CHUNK_DURATION_MINUTES} minut każdy"
        )

        # Twórz fragmenty
        chunks = []
        base_name = os.path.basename(audio_path)
        name_without_ext = os.path.splitext(base_name)[0]

        for i in range(num_chunks):
            start_time = i * max_chunk_duration_sec
            end_time = min((i + 1) * max_chunk_duration_sec, duration_sec)
            chunk_duration = end_time - start_time

            if chunk_duration < 1.0:  # Pomijamy bardzo krótkie końcowe fragmenty
                continue

            chunk_suffix = f"part{i + 1:03d}"
            chunk_path = _create_trimmed_file(audio_path, start_time, end_time, chunk_suffix)

            if chunk_path:
                chunks.append((original_path, chunk_path))
                chunk_formatted_duration = _format_duration_ffmpeg(chunk_duration)
                print(
                    f"    ✓ Utworzono fragment {i + 1}/{num_chunks}: {os.path.basename(chunk_path)} [{chunk_formatted_duration}]"
                )
            else:
                print(f"    ✗ Nie udało się utworzyć fragmentu {i + 1}/{num_chunks}")
                # W przypadku błędu, czyścimy już utworzone fragmenty
                for _, chunk in chunks:
                    try:
                        os.remove(chunk)
                    except:
                        pass
                return None

        if chunks:
            print(f"    ✓ Pomyślnie podzielono plik na {len(chunks)} fragmentów")
            # Usuń oryginalny plik po podzieleniu
            try:
                os.remove(audio_path)
                print(
                    f"    ✓ Usunięto oryginalny plik po podzieleniu: {os.path.basename(audio_path)}"
                )
            except:
                pass
            return chunks
        else:
            return None

    except Exception as e:
        print(f"    Błąd podczas dzielenia pliku na fragmenty: {e}")
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


# Removed: AAC segment cutting utility (_cut_aac_segments_optimized)


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

            print(
                f"  Konwertowanie pliku: {os.path.basename(original_path)} - rozpoczynam konwersję do standardowego formatu"
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
                # Sprawdź czy plik po usunięciu ciszy jest dłuższy niż limit i podziel jeśli potrzeba
                chunks = _split_long_audio_into_chunks(output_path, original_path)
                if chunks:
                    return chunks
                else:
                    # Jeśli dzielenie się nie powiodło, zwróć cały plik
                    return [(original_path, output_path)]
            elif output_path == tmp_path:
                # Sprawdź czy plik jest dłuższy niż limit i podziel jeśli potrzeba
                chunks = _split_long_audio_into_chunks(tmp_path, original_path)
                if chunks:
                    return chunks
                else:
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

        filename = os.path.basename(original_path)
        formatted_duration = _format_duration_ffmpeg(duration_sec)
        print(
            f"[{filename}] [{formatted_duration}] Długi plik wykryty - rozpoczynam transkodowanie..."
        )
        print("  Strategia: najpierw konwertuj cały plik, potem usuń ciszę")

        # KROK 1: Konwertuj cały plik do jednego dużego pliku tymczasowego
        print("  Krok 1: Konwertowanie całego pliku...")
        is_video = is_video_file(original_path)

        if is_video:
            command = f'ffmpeg -y -i "{original_path}" -vn {config.FFMPEG_PARAMS} "{full_tmp_path}"'
        else:
            command = f'ffmpeg -y -i "{original_path}" {config.FFMPEG_PARAMS} "{full_tmp_path}"'

        success = _run_ffmpeg_with_progress(command, filename, duration_sec)
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

        # KROK 3: Sprawdź czy plik po usunięciu ciszy jest dłuższy niż limit i podziel jeśli potrzeba
        print("  Krok 3: Sprawdzanie długości i ewentualne dzielenie...")
        chunks = _split_long_audio_into_chunks(full_tmp_path, original_path)
        if chunks:
            return chunks
        else:
            # Jeśli dzielenie się nie powiodło, zwróć cały plik
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
        # Pobierz długość pliku dla wyświetlania
        from src.utils.audio.duration_checker import get_file_duration

        duration_sec = get_file_duration(original_path)
        filename = os.path.basename(original_path)

        if duration_sec > 0:
            formatted_duration = _format_duration_ffmpeg(duration_sec)
            print(f"[{filename}] [{formatted_duration}] Rozpoczynam transkodowanie...")
        else:
            print(f"[{filename}] Rozpoczynam transkodowanie...")

        # Tworzymy standardową, bezpieczną nazwę pliku wyjściowego.
        base_name = os.path.basename(original_path)
        standardized_name, _ = os.path.splitext(base_name.lower().replace(" ", "_"))
        output_filename = f"{standardized_name}.m4a"
        tmp_file_path = os.path.join(config.AUDIO_TMP_DIR, output_filename)

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
        success = _run_ffmpeg_with_progress(
            command, filename, duration_sec if duration_sec > 0 else None
        )

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
                # Wielokrotne wyniki (fragmenty) - oryginalny plik został podzielony
                print(f"    Plik został podzielony na {len(result)} fragmentów")

                # Odznacz oryginalny plik (nie będzie widoczny w interfejsie)
                database.mark_file_as_chunked(original_path)
                print(f"    ✓ Oryginalny plik odznaczony: {os.path.basename(original_path)}")

                # Dodaj każdy fragment jako osobny plik do bazy
                for source_path, tmp_path in result:
                    database.add_chunk_file(tmp_path)
                    successful_conversions.append((source_path, tmp_path))
                    print(f"    ✓ Dodano fragment do bazy: {os.path.basename(tmp_path)}")
            else:
                # Pojedynczy wynik - plik nie został podzielony
                source_path, tmp_path = result[0]
                successful_conversions.append((source_path, tmp_path))
                print(f"    ✓ Przetworzono plik: {os.path.basename(source_path)}")

                # Standardowa aktualizacja bazy dla pojedynczego pliku
                database.set_files_as_loaded([source_path], [tmp_path])

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
