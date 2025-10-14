# Ten moduł odpowiada za konwersję (enkodowanie) plików audio do jednolitego formatu.
# Głównym celem jest upewnienie się, że wszystkie pliki, niezależnie od ich oryginalnego
# formatu (.mp3, .m4a itp.), zostaną przekonwertowane do standardowego formatu audio,
# który jest zoptymalizowany dla API Whisper.

import os  # Moduł do interakcji z systemem operacyjnym, np. do operacji na ścieżkach plików.
import av  # PyAV do konwersji audio
import numpy as np  # Do normalizacji głośności
import threading  # Dodane dla obsługi timeout'u z postępem w czasie rzeczywistym
import time  # Dodane dla kontrolowania odstępów czasowych wyświetlania postępu
import concurrent.futures  # Dodane dla równoległego przetwarzania
from concurrent.futures import ThreadPoolExecutor
from src import config, database  # Importujemy własne moduły: konfigurację i operacje na bazie danych.
from src.utils.error_handlers import with_error_handling, measure_performance  # Dekoratory
from src.utils.file_type_helper import is_video_file  # Funkcja do wykrywania plików wideo

def _convert_audio_with_pyav(input_path, output_path, timeout_sec, filename=None, total_duration=None):
    """
    Konwertuje plik audio używając PyAV z wyświetlaniem postępu.
    Zwraca True jeśli się udało, False przy błędzie lub timeout'cie.
    """
    start_time = time.time()

    try:
        # Otwórz plik wejściowy
        input_container = av.open(input_path)

        # Znajdź strumień audio
        audio_stream = None
        for stream in input_container.streams:
            if stream.type == 'audio':
                audio_stream = stream
                break

        if audio_stream is None:
            print(f"    Nie znaleziono strumienia audio w pliku {filename}")
            input_container.close()
            return False

        # Przygotuj wyjściowy kontener
        output_container = av.open(output_path, mode='w')

        # Skonfiguruj strumień wyjściowy zgodnie z parametrami z config.py
        output_stream = output_container.add_stream(config.PYAV_AUDIO_CODEC)
        output_stream.codec_context.sample_rate = config.PYAV_SAMPLE_RATE
        output_stream.codec_context.bit_rate = config.PYAV_BIT_RATE

        last_display_time = 0
        display_interval = 5.0

        # Przetwarzaj audio i koduj
        for frame in input_container.decode(audio_stream):
            # Sprawdź timeout
            if time.time() - start_time > timeout_sec:
                print(f"    TIMEOUT: Konwersja PyAV przekroczyła limit czasu {timeout_sec} sekund")
                input_container.close()
                output_container.close()
                return False

            # Normalizacja głośności używając numpy
            if config.PYAV_ENABLE_LOUDNESS_NORMALIZATION:
                # Konwertuj ramkę na numpy array
                audio_array = frame.to_ndarray()

                # Oblicz aktualny poziom RMS głośności
                rms_current = np.sqrt(np.mean(audio_array**2))

                # Docelowy poziom głośności (-12 dBFS jak w FFmpeg loudnorm)
                target_level_db = config.PYAV_LOUDNESS_TARGET_I
                target_rms = 10**(target_level_db / 20.0)

                # Oblicz współczynnik wzmocnienia
                if rms_current > 0:
                    gain = target_rms / rms_current

                    # Ogranicz wzmocnienie żeby nie przekroczyć 0 dBFS
                    max_gain = 1.0 / np.max(np.abs(audio_array))
                    gain = min(gain, max_gain)

                    # Zastosuj wzmocnienie
                    audio_array = audio_array * gain

                # Stwórz nową ramkę z znormalizowanym audio
                frame = av.AudioFrame.from_ndarray(audio_array, layout=frame.layout.name)
                frame.sample_rate = frame.sample_rate
                frame.time_base = frame.time_base
                frame.pts = frame.pts

            # Koduj ramkę do pakietów i muxuj je
            for packet in output_stream.encode(frame):
                output_container.mux(packet)

            # Wyświetl postęp co 5 sekund
            current_time = time.time()
            if current_time - last_display_time >= display_interval:
                if filename and total_duration is not None:
                    progress = min(100.0, (frame.time or 0) / total_duration * 100)
                    print(f"[{filename}] [{progress:.1f}%] Konwertowanie...")
                last_display_time = current_time

        # Dokonaj flush enkodera (wypchnij pozostałe pakiety)
        for packet in output_stream.encode(None):
            output_container.mux(packet)

        # Zakończ
        output_container.close()
        input_container.close()

        return True

    except Exception as e:
        print(f"    BŁĄD podczas konwersji PyAV: {e}")
        try:
            input_container.close()
        except:
            pass
        try:
            output_container.close()
        except:
            pass
        return False

def _convert_single_file(original_path):
    """
    Konwertuje pojedynczy plik i zwraca tuple (source, tmp) lub None przy błędzie.
    Funkcja przeznaczona do równoległego przetwarzania.
    Dla plików wideo ekstrahuje tylko ścieżkę audio, dla audio używa standardowych parametrów.
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

        # Zarówno pliki audio jak i wideo są obsługiwane - dla wideo zostanie wyciągnięte tylko audio
        if is_video:
            print(f"    Przetwarzanie pliku wideo - ekstrakcja ścieżki audio")

        # Obliczamy timeout proporcjonalny do długości pliku + 5 minut bufora
        # Dla pliku 139 min: ~147 min timeout, dla krótkich plików: minimum 10 min
        from src.audio.duration_checker import get_file_duration
        duration_sec = get_file_duration(original_path)
        timeout_sec = max(600, int(duration_sec * 1.1) + 300)  # 10% + 5 min bufora, minimum 10 min

        print(f"    Timeout dla tego pliku: {timeout_sec//60} minut")

        # Uruchamiamy konwersję PyAV z wyświetlaniem postępu
        filename = os.path.basename(original_path)
        success = _convert_audio_with_pyav(original_path, tmp_file_path, timeout_sec, filename, duration_sec)

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
    za pomocą PyAV z sekwencyjnym przetwarzaniem,
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