# Ten moduł odpowiada za konwersję (enkodowanie) plików audio do jednolitego formatu.
# Głównym celem jest upewnienie się, że wszystkie pliki, niezależnie od ich oryginalnego
# formatu (.mp3, .m4a itp.), zostaną przekonwertowane do standardowego formatu .wav,
# który jest optymalny dla API Whisper.

import os  # Moduł do interakcji z systemem operacyjnym, np. do operacji na ścieżkach plików.
import subprocess  # Moduł pozwalający na uruchamianie zewnętrznych programów, w tym przypadku FFMPEG.
from src import config, database  # Importujemy własne moduły: konfigurację i operacje na bazie danych.

def encode_audio_files():
    """
    Pobiera z bazy danych listę plików do przetworzenia, konwertuje je do formatu WAV
    za pomocą zewnętrznego narzędzia FFMPEG, a następnie aktualizuje ich status w bazie danych,
    oznaczając je jako 'załadowane' i zapisując ścieżkę do nowo utworzonego pliku tymczasowego.
    """
    print("\nKrok 2: Konwertowanie plików audio do formatu WAV...")

    # Pobieramy z bazy danych listę plików, które zostały zaznaczone przez użytkownika i nie były jeszcze konwertowane.
    files_to_encode = database.get_files_to_load()
    # Jeśli lista jest pusta, nie ma nic do roboty. Wyświetlamy komunikat i kończymy funkcję.
    if not files_to_encode:
        print("Brak nowych plików do konwersji.")
        return

    # Upewniamy się, że folder na przekonwertowane pliki audio istnieje.
    # `exist_ok=True` zapobiega błędowi, jeśli folder już istnieje.
    os.makedirs(config.AUDIO_TMP_DIR, exist_ok=True)

    # Inicjalizujemy pustą listę, w której będziemy przechowywać informacje o pomyślnie przekonwertowanych plikach.
    successful_conversions = []

    # Iterujemy przez każdy plik, który wymaga konwersji.
    for original_path in files_to_encode:
        try:
            # `try...except` pozwala nam "złapać" błędy, które mogą wystąpić podczas konwersji,
            # i kontynuować pętlę dla pozostałych plików, zamiast przerywać cały program.

            # Tworzymy standardową, bezpieczną nazwę pliku wyjściowego.
            # 1. `os.path.basename`: Pobieramy samą nazwę pliku z pełnej ścieżki (np. "Mój Nagłówek.mp3").
            base_name = os.path.basename(original_path)
            # 2. `os.path.splitext`: Dzielimy nazwę na część główną i rozszerzenie.
            # 3. `.lower()`: Zamieniamy wszystko na małe litery.
            # 4. `.replace(' ', '_')`: Zamieniamy spacje na podkreślenia.
            standardized_name, _ = os.path.splitext(base_name.lower().replace(' ', '_'))
            # 5. Tworzymy finalną nazwę pliku z rozszerzeniem .wav.
            output_filename = f"{standardized_name}.wav"
            # 6. Tworzymy pełną ścieżkę do pliku tymczasowego w folderze `tmp/audio`.
            tmp_file_path = os.path.join(config.AUDIO_TMP_DIR, output_filename)

            print(f"  Konwertowanie: {os.path.basename(original_path)} -> {os.path.basename(tmp_file_path)}")

            # Budujemy komendę FFMPEG, która zostanie wykonana w terminalu.
            # `ffmpeg -y -i "{oryginal}" {parametry} "{wynikowy}"`
            # -y: nadpisuje plik wyjściowy bez pytania.
            # -i: określa plik wejściowy.
            # {config.FFMPEG_PARAMS}: wstawia parametry z pliku konfiguracyjnego (np. mono, 44100Hz).
            # Używamy cudzysłowów wokół ścieżek, aby obsłużyć nazwy plików ze spacjami.
            command = f'ffmpeg -y -i "{original_path}" {config.FFMPEG_PARAMS} "{tmp_file_path}"'

            # Uruchamiamy komendę FFMPEG.
            # `shell=True`: pozwala na wykonanie komendy jako string.
            # `check=True`: rzuci wyjątkiem `CalledProcessError`, jeśli FFMPEG zwróci kod błędu.
            # `capture_output=True`: przechwytuje standardowe wyjście i wyjście błędów.
            # `text=True`: dekoduje przechwycone wyjścia jako tekst.
            subprocess.run(command, shell=True, check=True, capture_output=True, text=True)

            # Jeśli konwersja się udała (nie było wyjątku), dodajemy parę (ścieżka_oryginalna, ścieżka_tymczasowa) do listy.
            successful_conversions.append((original_path, tmp_file_path))

        except subprocess.CalledProcessError as e:
            # Ten blok jest wykonywany, jeśli FFMPEG zwrócił błąd.
            print(f"    BŁĄD: Nie udało się przekonwertować pliku {original_path}.")
            # `e.stderr` zawiera komunikat błędu zwrócony przez FFMPEG, co jest bardzo pomocne w diagnozowaniu problemu.
            print(f"    Komunikat FFMPEG: {e.stderr}")
            continue  # `continue` przerywa bieżącą iterację pętli i przechodzi do następnego pliku.
        except Exception as ex:
            # Ten blok łapie wszystkie inne, nieoczekiwane błędy.
            print(f"    KRYTYCZNY BŁĄD podczas przetwarzania pliku {original_path}: {ex}")
            continue

    # Po zakończeniu pętli, jeśli były jakiekolwiek udane konwersje...
    if successful_conversions:
        # `zip(*...)` to sprytny sposób na "rozpakowanie" listy par do dwóch oddzielnych list.
        # Np. [(a,1), (b,2)] -> [a,b] i [1,2]
        source_paths, tmp_paths = zip(*successful_conversions)
        # Wywołujemy jedną, masową operację na bazie danych, aby zaktualizować wszystkie pliki naraz.
        # Jest to znacznie wydajniejsze niż aktualizowanie każdego pliku w pętli.
        database.set_files_as_loaded(source_paths, tmp_paths)
        print(f"Pomyślnie przekonwertowano i oznaczono jako załadowane: {len(successful_conversions)} plików.")

    print("Zakończono konwersję plików.")