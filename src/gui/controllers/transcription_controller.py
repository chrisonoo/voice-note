# Ten moduł zawiera klasę `TranscriptionController`, która jest sercem logiki
# sterującej procesem transkrypcji w tle. Odpowiada za uruchamianie,
# pauzowanie i wznawianie operacji, a wszystko to w osobnym wątku,
# aby nie blokować interfejsu użytkownika.

import threading
from tkinter import messagebox
from src import database
from src.transcribe.transcription_processor import TranscriptionProcessor

class TranscriptionController:
    """
    Zarządza procesem transkrypcji, uruchamiając go w osobnym wątku
    i obsługując komunikację (pauza/wznów) z głównym wątkiem GUI.
    """
    
    def __init__(self, app):
        """
        Inicjalizuje kontroler transkrypcji.

        Argumenty:
            app: Referencja do głównego obiektu aplikacji (`App`).
        """
        self.app = app
    
    def start_transcription_process(self):
        """
        Rozpoczyna proces transkrypcji dla wszystkich plików, które są
        wczytane, ale nieprzetworzone.
        """
        # Sprawdzamy, czy w ogóle są pliki do przetworzenia.
        if not database.get_files_to_process():
            messagebox.showwarning("Brak plików", "Brak plików wczytanych do przetworzenia.")
            return

        # Aktualizujemy stan przycisków (np. wyłączamy "Start"), aby zapobiec ponownemu kliknięciu.
        self.app.button_state_controller.update_ui_state()
        # Odświeżamy widoki, aby pokazać, które pliki trafiły do kolejki.
        self.app.refresh_all_views()
        # Wymuszamy przerysowanie GUI.
        self.app.update_idletasks()

        # `clear()` czyści flagę pauzy. To ważne, aby nowy proces nie startował od razu w stanie pauzy.
        self.app.pause_request_event.clear()
        # Tworzymy nowy wątek roboczy.
        self.app.processing_thread = threading.Thread(target=self._transcription_thread_worker, daemon=True)
        # Uruchamiamy wątek. Od tego momentu funkcja `_transcription_thread_worker` działa w tle.
        self.app.processing_thread.start()
        # Ponownie aktualizujemy stan przycisków, tym razem aby pokazać, że proces jest aktywny (np. włączając przycisk "Pauza").
        self.app.button_state_controller.update_ui_state()

    def pause_transcription(self):
        """Wysyła żądanie pauzy do wątku przetwarzającego poprzez ustawienie flagi `Event`."""
        self.app.pause_request_event.set()
        # Aktualizujemy UI, aby np. zmienić przycisk "Pauza" na "Wznów".
        self.app.button_state_controller.update_ui_state()

    def resume_transcription(self):
        """Wycofuje żądanie pauzy, czyszcząc flagę `Event`. Wątek roboczy wznowi pracę."""
        self.app.pause_request_event.clear()
        self.app.button_state_controller.update_ui_state()

    def resume_interrupted_process(self):
        """
        Wznawia przerwany proces. W obecnej logice, gdzie stan aplikacji jest
        trzymany w bazie danych, jest to tożsame z normalnym uruchomieniem procesu,
        ponieważ `start_transcription_process` automatycznie podejmie pracę
        od plików, które nie są jeszcze przetworzone.
        """
        if not database.get_files_to_process():
            messagebox.showinfo("Informacja", "Brak plików w kolejce do wznowienia.")
            self.app.button_state_controller.update_ui_state()
            return

        self.start_transcription_process()

    def _transcription_thread_worker(self):
        """
        Główna metoda robocza wykonywana w osobnym wątku.
        To tutaj dzieje się właściwe przetwarzanie.
        """
        try:
            # Tworzymy funkcję zwrotną (callback) dla procesora transkrypcji.
            # Używamy `lambda`, aby stworzyć prostą funkcję anonimową.
            # Ta funkcja używa `self.app.after(0, ...)` do bezpiecznego zaplanowania
            # wykonania metody `on_transcription_progress` w głównym wątku GUI.
            progress_callback = lambda: self.app.after(0, self.app.on_transcription_progress)

            # Tworzymy instancję procesora, przekazując mu obiekt Event do obsługi pauzy
            # oraz naszą funkcję zwrotną do raportowania postępu.
            processor = TranscriptionProcessor(
                pause_requested_event=self.app.pause_request_event,
                on_progress_callback=progress_callback
            )
            # Uruchamiamy pętlę przetwarzania w procesorze.
            processor.process_transcriptions()
        except Exception as e:
            # Jeśli w wątku wystąpi krytyczny błąd, bezpiecznie wyświetlamy go w GUI.
            self.app.after(0, lambda e=e: messagebox.showerror("Błąd krytyczny", f"Wystąpił błąd: {e}"))
        finally:
            # Blok `finally` wykona się zawsze, niezależnie od tego, czy wystąpił błąd, czy nie.
            # Planujemy wykonanie metody `on_processing_finished` w głównym wątku, aby posprzątać po zakończeniu pracy.
            self.app.after(0, self.app.on_processing_finished)

    def on_processing_finished(self):
        """
        Obsługuje zakończenie procesu transkrypcji od strony tego kontrolera.
        Jest wywoływana z `main_window` po zakończeniu pracy wątku.
        """
        # Resetujemy referencję do wątku i flagę pauzy.
        self.app.processing_thread = None
        self.app.pause_request_event.clear()
        # Unieważniamy cache ponieważ dane zostały przetworzone
        self.app.invalidate_cache()
        # Optymalizujemy bazę danych po zakończeniu przetwarzania
        from src import database
        database.optimize_database()
        # Aktualizujemy finalny stan interfejsu.
        self.app.button_state_controller.update_ui_state()
        self.app.refresh_all_views()