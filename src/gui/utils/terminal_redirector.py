# Ten moduł zawiera klasę `TerminalRedirector`, która pozwala na przekierowanie
# standardowego wyjścia (stdout) i błędów (stderr) do widgetu GUI zamiast konsoli.

import sys
import threading
from queue import Queue


class TerminalRedirector:
    """
    Klasa do przekierowywania stdout/stderr do widgetu GUI.
    Używa kolejki do bezpiecznej komunikacji między wątkami.
    """

    def __init__(self, app_callback):
        """
        Inicjalizuje redirector.

        Argumenty:
            app_callback: Funkcja zwrotna do aktualizacji GUI (np. app.append_to_terminal)
        """
        self.app_callback = app_callback
        self.queue = Queue()
        self.running = True

        # Zapisz oryginalne stdout i stderr
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr

        # Uruchom wątek do przetwarzania kolejki
        self.processing_thread = threading.Thread(target=self._process_queue, daemon=True)
        self.processing_thread.start()

    def write(self, text):
        """Metoda write zgodna z interfejsem stream - dodaje tekst do kolejki."""
        if text:  # Nie ignoruj pustych linii - zawierają znaki nowej linii
            self.queue.put(text)

    def flush(self):
        """Metoda flush wymagana przez interfejs stream."""
        pass

    def _process_queue(self):
        """Przetwarza elementy z kolejki w osobnym wątku."""
        while self.running:
            try:
                # Pobierz tekst z kolejki z timeout'em
                text = self.queue.get(timeout=0.1)

                # Wywołaj callback w głównym wątku GUI
                if hasattr(self.app_callback, '__self__'):
                    # To jest bound method, wywołaj przez after
                    self.app_callback.__self__.after(0, lambda t=text: self.app_callback(t))
                else:
                    # To jest funkcja, wywołaj bezpośrednio
                    self.app_callback(text)

            except Exception:
                # Ignoruj timeout i inne błędy
                continue

    def start_redirect(self):
        """Rozpoczyna przekierowanie stdout i stderr."""
        sys.stdout = self
        sys.stderr = self

    def stop_redirect(self):
        """Kończy przekierowanie i przywraca oryginalne stdout/stderr."""
        self.running = False
        sys.stdout = self.original_stdout
        sys.stderr = self.original_stderr

        # Poczekaj na zakończenie wątku przetwarzania
        if self.processing_thread.is_alive():
            self.processing_thread.join(timeout=1.0)
