# Ten moduł odpowiada za konwersję (enkodowanie) plików audio do jednolitego formatu.
# Głównym celem jest upewnienie się, że wszystkie pliki, niezależnie od ich oryginalnego
# formatu (.mp3, .m4a itp.), zostaną przekonwertowane do standardowego formatu audio,
# który jest zoptymalizowany dla API Whisper.

import os  # Moduł do interakcji z systemem operacyjnym, np. do operacji na ścieżkach plików.
import subprocess  # Moduł pozwalający na uruchamianie zewnętrznych programów, w tym przypadku FFMPEG.
import threading  # Dodane dla obsługi timeout'u z postępem w czasie rzeczywistym
import time  # Dodane dla kontrolowania odstępów czasowych wyświetlania postępu
import concurrent.futures  # Dodane dla równoległego przetwarzania
from concurrent.futures import ThreadPoolExecutor
from src import config, database  # Importujemy własne moduły: konfigurację i operacje na bazie danych.
from src.utils.error_handlers import with_error_handling, measure_performance  # Dekoratory
from src.utils.file_type_helper import is_video_file  # Funkcja do wykrywania plików wideo

def _format_duration_ffmpeg(duration_sec):
    """
    Formatuje czas trwania w sekundach do formatu FFmpeg (hh:mm:ss.ms).
    """
    hours = int(duration_sec // 3600)
    minutes = int((duration_sec % 3600) // 60)
    seconds = int(duration_sec % 60)
    milliseconds = int((duration_sec % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}"

def _run_ffmpeg_with_progress(command, timeout_sec, filename=None, total_duration=None):
    """
    Uruchamia FFmpeg z wyświetlaniem postępu w czasie rzeczywistym.
    Zwraca True jeśli się udało, False przy błędzie lub timeout'cie.
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
            universal_newlines=True
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

        # Czekamy na zakończenie procesu z timeout'em
        try:
            process.wait(timeout=timeout_sec)
            output_thread.join(timeout=1.0)  # Daj czas wątkowi na zakończenie
            return process.returncode == 0
        except subprocess.TimeoutExpired:
            print(f"    TIMEOUT: FFmpeg przekroczył limit czasu {timeout_sec} sekund")
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
    Konwertuje pojedynczy plik i zwraca tuple (source, tmp) lub None przy błędzie.
    Funkcja przeznaczona do równoległego przetwarzania.
    Dla plików wideo ekstrahuje tylko ścieżkę audio (-vn), dla audio używa standardowych parametrów.
    """
    try:
        # Tworzymy standardową, bezpieczną nazwę pliku wyjściowego.
        base_name = os.path.basename(original_path)
        standardized_name, _ = os.path.splitext(base_name.lower().replace(' ', '_'))
        output_filename = f"{standardized_name}.m4a"
        tmp_file_path = os.path.join(config.AUDIO_TMP_DIR, output_filename)

        print(f"  Konwertowanie: {os.path.basename(original_path)} -> {os.path.basename(tmp_file_path)}")

        # Sprawdzamy czy plik jest wideo
        is_video = is_video_file(original_path)

        # Budujemy komendę FFMPEG
        if is_video:
            # Dla plików wideo ekstrahujemy tylko audio (-vn ignoruje strumień wideo)
            command = f'ffmpeg -y -i "{original_path}" -vn {config.FFMPEG_PARAMS} "{tmp_file_path}"'
        else:
            # Dla plików audio używamy standardowych parametrów
            command = f'ffmpeg -y -i "{original_path}" {config.FFMPEG_PARAMS} "{tmp_file_path}"'

        # Obliczamy timeout proporcjonalny do długości pliku + 5 minut bufora
        # Dla pliku 139 min: ~147 min timeout, dla krótkich plików: minimum 10 min
        from src.audio.duration_checker import get_file_duration
        duration_sec = get_file_duration(original_path)
        timeout_sec = max(600, int(duration_sec * 1.1) + 300)  # 10% + 5 min bufora, minimum 10 min

        print(f"    Timeout dla tego pliku: {timeout_sec//60} minut")

        # Uruchamiamy FFmpeg z wyświetlaniem postępu w czasie rzeczywistym
        filename = os.path.basename(original_path)
        success = _run_ffmpeg_with_progress(command, timeout_sec, filename, duration_sec)

        if success:
            return (original_path, tmp_file_path)
        else:
            return None

    except Exception as ex:
        print(f"    KRYTYCZNY BŁĄD podczas przetwarzania pliku {os.path.basename(original_path)}: {ex}")
        return None

@with_error_handling("Konwersja plików audio")
@measure_performance
def encode_audio_files(app=None):
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
        if result:
            source_path, tmp_path = result
            successful_conversions.append(result)

            # Aktualizuj bazę danych natychmiast po przetworzeniu pliku
            database.set_files_as_loaded([source_path], [tmp_path])
            print(f"    ✓ Przetworzono i dodano do bazy: {os.path.basename(source_path)}")

            # Odśwież GUI jeśli mamy referencję do aplikacji
            if app:
                app.after(0, lambda: app.invalidate_cache())
                app.after(0, lambda: app.panel_manager.refresh_transcription_progress_views())
                app.after(0, lambda: app.update_all_counters())
        else:
            print(f"    ✗ Nie udało się przetworzyć: {os.path.basename(original_path)}")

    if successful_conversions:
        print(f"Pomyślnie przekonwertowano i oznaczono jako załadowane: {len(successful_conversions)} plików.")

    if len(successful_conversions) < len(files_to_encode):
        failed_count = len(files_to_encode) - len(successful_conversions)
        print(f"Nie udało się przekonwertować: {failed_count} plików.")

    print("Zakończono konwersję plików.")