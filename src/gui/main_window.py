import customtkinter as ctk
from tkinter import messagebox
import threading
import pygame
from src import config, database

# Import UI components and managers
from .interface_builder import InterfaceBuilder
from .button_state_controller import ButtonStateController
from .file_handler import FileHandler
from .transcription_controller import TranscriptionController
from .panel_manager import PanelManager
from .audio_player import AudioPlayer

class App(ctk.CTk):
    """
    Główna klasa aplikacji, która zarządza oknem, komponentami i stanem aplikacji.
    """
    def __init__(self):
        super().__init__()

        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        self.processing_thread = None
        self.pause_request_event = threading.Event()

        self.title(config.APP_NAME)
        self.minsize(1110, 600)
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=0)
        self.grid_columnconfigure(2, weight=0)
        self.grid_columnconfigure(3, weight=0)
        self.grid_columnconfigure(4, weight=3)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=0)

        self.audio_player = AudioPlayer()
        self.interface_builder = InterfaceBuilder(self, self.audio_player)
        self.button_state_controller = ButtonStateController(self)
        self.file_handler = FileHandler(self)
        self.transcription_controller = TranscriptionController(self)
        self.panel_manager = PanelManager(self)

        self.interface_builder.create_widgets()
        
        self.button_state_controller.update_ui_state()
        self.refresh_all_views()

        self._check_playback_status()
    
    def update_all_counters(self):
        """Aktualizuje wszystkie liczniki na podstawie danych z bazy."""
        try:
            all_files = database.get_all_files()

            total_files = len(all_files)
            selected_files = sum(1 for row in all_files if row['is_selected'])
            long_files = sum(1 for row in all_files if row['duration_seconds'] is not None and row['duration_seconds'] > config.MAX_FILE_DURATION_SECONDS)

            if hasattr(self, 'files_counter_label'):
                if total_files == 0:
                    self.files_counter_label.configure(text="")
                else:
                    counter_text = f"Razem: {total_files}  |  Zaznaczone: {selected_files}"
                    if long_files > 0:
                        counter_text += f"  |  Długie: {long_files}"
                    self.files_counter_label.configure(text=counter_text)

            # Liczniki dla paneli stanu
            loaded_count = sum(1 for row in all_files if row['is_loaded'] and not row['is_processed'])
            processed_count = sum(1 for row in all_files if row['is_processed'])

            if hasattr(self, 'loaded_counter_label'):
                self.loaded_counter_label.configure(text=f"Wczytane: {loaded_count}" if loaded_count > 0 else "")

            # "Kolejka" to teraz pliki wczytane, ale jeszcze nieprzetworzone
            if hasattr(self, 'processing_counter_label'):
                self.processing_counter_label.configure(text=f"Kolejka: {loaded_count}" if loaded_count > 0 else "")

            if hasattr(self, 'processed_counter_label'):
                self.processed_counter_label.configure(text=f"Gotowe: {processed_count}" if processed_count > 0 else "")

        except Exception as e:
            print(f"Błąd podczas aktualizacji liczników: {e}")

    def refresh_all_views(self):
        """Odświeża wszystkie panele danych i aktualizuje liczniki."""
        self.panel_manager.refresh_all_views()
        self.update_all_counters()

    def pause_transcription(self):
        self.transcription_controller.pause_transcription()

    def resume_transcription(self):
        self.transcription_controller.resume_transcription()

    def on_processing_finished(self):
        self.transcription_controller.on_processing_finished()

    def start_transcription_process(self):
        self.transcription_controller.start_transcription_process()

    def monitor_processing(self):
        if self.processing_thread and self.processing_thread.is_alive():
            self.button_state_controller.update_ui_state()
            self.refresh_all_views()
            self.after(1000, self.monitor_processing)
        else:
            self.on_processing_finished()

    def copy_transcription_to_clipboard(self):
        text = self.transcription_output_panel.get_text()
        if not text.strip():
            messagebox.showinfo("Informacja", "Brak tekstu do skopiowania.")
            return
        self.clipboard_clear()
        self.clipboard_append(text)
        messagebox.showinfo("Skopiowano", "Transkrypcja została skopiowana do schowka.")

    def _check_playback_status(self):
        if self.audio_player.is_playing and not pygame.mixer.music.get_busy():
            self.audio_player.stop()
            if hasattr(self, 'file_selection_panel'):
                self.file_selection_panel.update_play_buttons()
        self.after(100, self._check_playback_status)

    def on_closing(self):
        self.audio_player.stop()
        pygame.quit()
        if self.processing_thread and self.processing_thread.is_alive():
            if messagebox.askokcancel("Przetwarzanie w toku", "Proces jest aktywny. Czy na pewno chcesz wyjść?"):
                self.destroy()
        else:
            self.destroy()

def main():
    # Inicjalizacja bazy danych została przeniesiona do głównego pliku main.py,
    # aby uniknąć podwójnego wywołania przy starcie w trybie GUI.
    app = App()
    app.mainloop()