# Ten moduł definiuje klasę `TranscriptionProcessor`, która jest "mózgiem"
# operacji transkrypcji. Działa jak menedżer, który koordynuje pracę:
# pobiera informacje z bazy danych, zleca transkrypcję modułowi `whisper`
# i zapisuje wyniki z powrotem do bazy.

import os  # Moduł do operacji na ścieżkach plików, np. do wyciągania nazwy pliku.
import threading  # Moduł do pracy z wątkami, używany tutaj do obsługi pauzy w trybie GUI.
from src.whisper import Whisper  # Importujemy naszą klasę-wrapper dla API OpenAI Whisper.
from src import database  # Importujemy moduł do operacji na bazie danych.
# format_transcription_header usunięty - tag jest teraz tworzony wcześniej w metadanych
from src.utils.error_handlers import with_error_handling, measure_performance  # Dekoratory

class TranscriptionProcessor:
    """
    Zarządza całym procesem transkrypcji. Pobiera pliki, które zostały
    wcześniej skonwertowane do formatu audio gotowego do transkrypcji,
    wysyła je do transkrypcji i zapisuje wyniki z powrotem w bazie danych.
    """
    def __init__(self, pause_requested_event: threading.Event = None, on_progress_callback=None):
        """
        Inicjalizuje obiekt procesora transkrypcji.

        Argumenty:
            pause_requested_event (threading.Event, opcjonalnie):
                Obiekt `Event` z modułu `threading`, który służy do komunikacji między wątkami.
                Główny wątek GUI może ustawić ten event, aby zasygnalizować wątkowi
                roboczemu (który wykonuje transkrypcję), że użytkownik wcisnął pauzę.
            on_progress_callback (function, opcjonalnie):
                Funkcja zwrotna (callback), która jest wywoływana po przetworzeniu każdego pliku.
                Używane w GUI do aktualizowania paska postępu.
        """
        self.pause_requested_event = pause_requested_event
        self.on_progress_callback = on_progress_callback

    @with_error_handling("Transkrypcja plików")
    @measure_performance
    def process_transcriptions(self, allow_long=False):
        """
        Główna metoda orkiestrująca procesem transkrypcji.
        Pobiera pliki, które są już załadowane (skonwertowane do formatu audio gotowego do transkrypcji),
        ale jeszcze nieprzetworzone (nie mają transkrypcji), wykonuje transkrypcję
        dla każdego z nich i aktualizuje odpowiednie wpisy w bazie danych.
        
        Argumenty:
            allow_long (bool): Jeśli True, przetwarza również długie pliki.
                              Jeśli False, pomija długie pliki.
        """
        print("\nKrok 3: Rozpoczynanie transkrypcji plików...")

        # Pobieramy z bazy listę ścieżek do plików źródłowych, które są gotowe do transkrypcji.
        files_to_process = database.get_files_to_process()

        # Jeśli nie ma takich plików, informujemy o tym i kończymy działanie metody.
        if not files_to_process:
            print("Brak plików oczekujących na transkrypcję.")
            return

        # Jeśli allow_long=False, filtrujemy długie pliki
        if not allow_long:
            from src import config
            filtered_files = []
            for source_path in files_to_process:
                file_metadata = database.get_file_metadata(source_path)
                if file_metadata and file_metadata.get('duration_ms'):
                    duration_sec = file_metadata['duration_ms'] / 1000
                    if duration_sec <= config.MAX_FILE_DURATION_SECONDS:
                        filtered_files.append(source_path)
                    else:
                        print(f"    Pominięto długi plik: {os.path.basename(source_path)} ({duration_sec:.1f}s)")
                else:
                    # Jeśli nie ma metadanych, dodaj plik (może być problem z bazą danych)
                    filtered_files.append(source_path)
            files_to_process = filtered_files
            
            if not files_to_process:
                print("Brak krótkich plików do transkrypcji (wszystkie są za długie).")
                return

        # Iterujemy przez każdy plik, który wymaga transkrypcji.
        for source_path in files_to_process:
            # Najpierw sprawdź dostępność pliku źródłowego
            is_valid, error_msg = database.validate_file_access(source_path)
            if not is_valid:
                print(f"    BŁĄD: Plik źródłowy niedostępny - {error_msg}. Pomijanie.")
                continue

            # Pobieramy wszystkie potrzebne metadane pliku z bazy danych jednym zapytaniem.
            file_metadata = database.get_file_metadata(source_path)

            if not file_metadata or not file_metadata['tmp_file_path']:
                print(f"    BŁĄD: Brak metadanych lub ścieżki tymczasowej dla pliku: {source_path}. Pomijanie.")
                continue

            tmp_path = file_metadata['tmp_file_path']

            # Dodatkowe zabezpieczenie: sprawdzamy, czy plik tymczasowy fizycznie istnieje na dysku.
            if not os.path.exists(tmp_path):
                print(f"    BŁĄD: Oczekiwany plik tymczasowy nie istnieje: {tmp_path}. Pomijanie.")
                continue

            print(f"  Przetwarzanie pliku: {os.path.basename(source_path)}")

            # Tworzymy instancję naszej klasy `Whisper`, przekazując jej ścieżkę do przetworzonego pliku audio.
            whisper = Whisper(tmp_path)
            # Wywołujemy metodę, która wysyła plik do API OpenAI i zwraca wynik.
            transcription = whisper.transcribe()

            # Sprawdzamy, czy transkrypcja się powiodła i czy wynik zawiera tekst.
            # `hasattr` sprawdza, czy obiekt `transcription` ma atrybut o nazwie 'text'.
            if transcription and hasattr(transcription, 'text'):
                # Pobieramy tag z bazy danych (został utworzony wcześniej podczas przetwarzania metadanych)
                try:
                    tag = file_metadata['tag'] or ''
                except (KeyError, IndexError):
                    tag = ''
                    print(f"    OSTRZEŻENIE: Brak kolumny 'tag' dla pliku {os.path.basename(source_path)}")

                if not tag:
                    print(f"    OSTRZEŻENIE: Brak tagu dla pliku {os.path.basename(source_path)}")

                # Zapisujemy tylko czystą transkrypcję w bazie danych (tag jest już w osobnej kolumnie)
                database.update_file_transcription(source_path, transcription.text)
                print(f"    Sukces: Transkrypcja z tagiem zapisana w bazie danych.")

                # Jeśli do procesora została przekazana funkcja zwrotna (w trybie GUI)...
                if self.on_progress_callback:
                    # ...wywołujemy ją. To pozwala na aktualizację interfejsu użytkownika w czasie rzeczywistym.
                    self.on_progress_callback()
            else:
                # Jeśli transkrypcja się nie powiodła, drukujemy komunikat.
                print(f"    Pominięto plik {os.path.basename(source_path)} z powodu błędu transkrypcji.")

            # Sprawdzamy, czy z głównego wątku GUI przyszło żądanie pauzy.
            # `is_set()` zwraca True, jeśli inny wątek wywołał `event.set()`.
            if self.pause_requested_event and self.pause_requested_event.is_set():
                print("Żądanie pauzy wykryte. Zatrzymywanie przetwarzania...")
                break  # `break` przerywa całą pętlę `for`.

        print("\nZakończono pętlę przetwarzania transkrypcji.")