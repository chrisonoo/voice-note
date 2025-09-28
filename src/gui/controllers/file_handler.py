# Ten moduł zawiera klasę `FileHandler`, która jest kontrolerem odpowiedzialnym
# za logikę związaną z operacjami na plikach inicjowanymi przez użytkownika w GUI.
# Obejmuje to wybieranie plików z dysku i uruchamianie procesu ich wczytywania (konwersji).

import threading  # Moduł do pracy z wątkami, niezbędny do uruchamiania operacji w tle.
from tkinter import filedialog, messagebox  # Moduły Tkinter do okien dialogowych.
from src import config, database  # Nasze własne moduły.
from src.audio import encode_audio_files  # Funkcja do konwersji plików.

class FileHandler:
    """
    Zarządza operacjami na plikach w interfejsie graficznym, takimi jak
    wybieranie plików z dysku i inicjowanie ich ładowania (konwersji).
    """
    
    def __init__(self, app):
        """
        Inicjalizuje kontroler plików.

        Argumenty:
            app: Referencja do głównego obiektu aplikacji (`App`), aby mieć dostęp
                 do komponentów interfejsu i innych kontrolerów.
        """
        self.app = app
    
    def select_source_files(self):
        """Otwiera systemowe okno dialogowe do wyboru plików i dodaje wybrane pliki do bazy danych."""
        # Zabezpieczenie: nie pozwól na dodawanie plików, gdy proces transkrypcji jest w toku.
        if self.app.processing_thread and self.app.processing_thread.is_alive():
            return
            
        # `filedialog.askopenfilenames` otwiera natywne okno systemowe do wyboru jednego lub wielu plików.
        paths = filedialog.askopenfilenames(
            title="Wybierz pliki audio", 
            # `filetypes` filtruje wyświetlane pliki. Tworzymy listę typów na podstawie rozszerzeń z pliku konfiguracyjnego.
            filetypes=[("Pliki audio", " ".join(config.AUDIO_EXTENSIONS))]
        )
        # Jeśli użytkownik zamknie okno bez wybierania plików, `paths` będzie puste.
        if not paths:
            return

        # Sortujemy ścieżki alfabetycznie, aby zapewnić spójną i przewidywalną kolejność w całej aplikacji.
        sorted_paths = sorted(list(paths))

        # Iterujemy przez posortowane ścieżki i dodajemy każdą z nich do bazy danych.
        for p in sorted_paths:
            database.add_file(p)

        # Po dodaniu plików, natychmiast aktualizujemy stan przycisków i odświeżamy widoki,
        # aby użytkownik od razu zobaczył efekt swojej akcji.
        self.app.button_state_controller.update_ui_state()
        self.app.refresh_all_views()

    def load_selected_files(self):
        """
        Uruchamia w osobnym wątku konwersję zaznaczonych plików do formatu WAV.
        Pliki do konwersji są identyfikowane na podstawie flagi 'is_selected' w bazie danych.
        """
        # Natychmiast wyłączamy przycisk, aby zapobiec wielokrotnemu kliknięciu.
        self.app.convert_files_button.configure(state="disabled")
        # `update_idletasks()` wymusza natychmiastowe przerysowanie interfejsu, dzięki czemu zmiana stanu przycisku jest od razu widoczna.
        self.app.update_idletasks()

        # Sprawdzamy, czy są jakiekolwiek pliki do załadowania.
        if not database.get_files_to_load():
            messagebox.showwarning("Brak plików", "Nie zaznaczono żadnych plików do wczytania.")
            # Jeśli nie, ponownie aktywujemy przyciski.
            self.app.button_state_controller.update_ui_state()
            return

        # Kluczowy moment: konwersja plików (operacja I/O) może zająć dużo czasu.
        # Aby nie blokować (nie "zamrażać") interfejsu użytkownika, uruchamiamy ją w osobnym wątku.
        # `target`: funkcja, która ma być wykonana w nowym wątku.
        # `daemon=True`: oznacza, że wątek zostanie gwałtownie zakończony, jeśli główny program się zamknie.
        threading.Thread(target=self._load_files_worker, daemon=True).start()

    def _load_files_worker(self):
        """
        Metoda robocza (worker) wykonywana w osobnym wątku.
        Odpowiada za wywołanie właściwej funkcji konwertującej pliki i obsługę aktualizacji GUI po zakończeniu.
        """
        try:
            # Wywołujemy funkcję, która wykonuje całą logikę konwersji FFMPEG.
            encode_audio_files()
            
            # WAŻNE: Bezpośrednia modyfikacja widżetów Tkinter z innego wątku niż główny jest niebezpieczna.
            # `self.app.after(0, ...)` to bezpieczny sposób na zaplanowanie wykonania funkcji
            # w głównej pętli zdarzeń GUI tak szybko, jak to możliwe.
            self.app.after(0, self.app.button_state_controller.update_ui_state)
            self.app.after(0, self.app.refresh_all_views)
        except Exception as e:
            # Jeśli w wątku roboczym wystąpi błąd, łapiemy go i bezpiecznie wyświetlamy komunikat w GUI.
            self.app.after(0, lambda: messagebox.showerror("Błąd konwersji", f"Wystąpił błąd: {e}"))
            # Nawet po błędzie, musimy zaktualizować stan przycisków.
            self.app.after(0, self.app.button_state_controller.update_ui_state)