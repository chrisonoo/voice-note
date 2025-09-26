import threading
from tkinter import filedialog, messagebox
from src import config, database
from src.audio import encode_audio_files

class FileHandler:
    """
    Zarządza operacjami na plikach w interfejsie graficznym,
    integrując je z bazą danych.
    """
    
    def __init__(self, app):
        self.app = app
    
    def select_source_files(self):
        """Otwiera dialog wyboru plików i dodaje je do bazy danych."""
        if self.app.processing_thread and self.app.processing_thread.is_alive():
            return
            
        paths = filedialog.askopenfilenames(
            title="Wybierz pliki audio", 
            filetypes=[("Pliki audio", " ".join(config.AUDIO_EXTENSIONS))]
        )
        if not paths:
            return

        # Sortuj ścieżki alfabetycznie, aby zapewnić spójną kolejność
        sorted_paths = sorted(list(paths))

        for p in sorted_paths:
            database.add_file(p)

        self.app.button_state_controller.update_ui_state()
        self.app.refresh_all_views()

    def load_selected_files(self):
        """
        Uruchamia konwersję zaznaczonych plików do formatu WAV.
        Pliki są pobierane na podstawie flagi 'is_selected' w bazie danych.
        """
        self.app.convert_files_button.configure(state="disabled")
        self.app.update_idletasks()

        if not database.get_files_to_load():
            messagebox.showwarning("Brak plików", "Nie zaznaczono żadnych plików do wczytania.")
            self.app.button_state_controller.update_ui_state()
            return

        threading.Thread(target=self._load_files_worker, daemon=True).start()

    def _load_files_worker(self):
        """Wątek roboczy do konwersji plików."""
        try:
            encode_audio_files()
            
            self.app.after(0, self.app.button_state_controller.update_ui_state)
            self.app.after(0, self.app.refresh_all_views)
        except Exception as e:
            self.app.after(0, lambda: messagebox.showerror("Błąd konwersji", f"Wystąpił błąd: {e}"))
            self.app.after(0, self.app.button_state_controller.update_ui_state)

    def clear_database_and_reset_gui(self):
        """Czyści bazę danych, folder tymczasowy i resetuje GUI."""
        if self.app.processing_thread and self.app.processing_thread.is_alive():
            messagebox.showerror("Błąd", "Nie można zresetować aplikacji podczas przetwarzania.")
            return
            
        if not messagebox.askokcancel("Potwierdzenie", "Czy na pewno chcesz wyczyścić wszystko? Wszystkie dane i pliki tymczasowe zostaną trwale usunięte."):
            return

        if self.app.processing_thread:
            self.app.on_processing_finished()

        try:
            database.clear_database_and_tmp_folder()

            self.app.button_state_controller.update_ui_state()
            self.app.refresh_all_views()
            messagebox.showinfo("Reset", "Aplikacja została zresetowana, a baza danych wyczyszczona.")
        except Exception as e:
            messagebox.showerror("Błąd resetowania", f"Nie udało się zresetować aplikacji: {e}")
            self.app.button_state_controller.update_ui_state()
            self.app.refresh_all_views()