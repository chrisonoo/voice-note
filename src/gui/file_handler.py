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

        # Dodaj nowe pliki do bazy danych
        for p in paths:
            database.add_file(p)

        # Odśwież widoki, aby pokazać nowe pliki
        self.app.button_state_controller.update_ui_state()
        self.app.refresh_all_views()

    def load_selected_files(self):
        """
        Oznacza zaznaczone pliki w bazie danych i uruchamia ich konwersję do WAV.
        """
        self.app.convert_files_button.configure(state="disabled")
        self.app.update_idletasks()

        # Pobierz zaznaczone pliki z panelu GUI
        files_to_load = self.app.file_selection_panel.get_checked_files()
        if not files_to_load:
            messagebox.showwarning("Brak plików", "Nie zaznaczono żadnych plików na liście 'Wybrane'.")
            self.app.button_state_controller.update_ui_state()
            return

        # Najpierw wyczyść wszystkie poprzednie zaznaczenia w bazie
        database.clear_all_gui_selections()
        # Następnie ustaw zaznaczenie dla wybranych plików
        database.set_gui_selection_for_list(files_to_load, is_selected=True)

        # Uruchom konwersję w osobnym wątku
        threading.Thread(target=self._load_files_worker, daemon=True).start()

    def _load_files_worker(self):
        """Wątek roboczy do konwersji plików."""
        try:
            # Wywołaj konwersję w trybie GUI - przetworzy tylko pliki zaznaczone w bazie
            encode_audio_files(gui_mode=True)
            
            # Po zakończeniu odśwież interfejs
            self.app.after(0, self.app.button_state_controller.update_ui_state)
            self.app.after(0, self.app.refresh_all_views)
        except Exception as e:
            self.app.after(0, lambda: messagebox.showerror("Błąd konwersji", f"Wystąpił błąd: {e}"))
            # W przypadku błędu, zresetuj stan przycisków
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
            # Wywołaj funkcję, która usuwa folder tmp i inicjalizuje bazę na nowo
            database.clear_database_and_tmp_folder()

            self.app.button_state_controller.update_ui_state()
            self.app.refresh_all_views()
            messagebox.showinfo("Reset", "Aplikacja została zresetowana, a baza danych wyczyszczona.")
        except Exception as e:
            messagebox.showerror("Błąd resetowania", f"Nie udało się zresetować aplikacji: {e}")
            self.app.button_state_controller.update_ui_state()
            self.app.refresh_all_views()