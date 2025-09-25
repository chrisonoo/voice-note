import tkinter as tk
from tkinter import messagebox
import threading
from src import config

# Import UI components and managers
from .ui_builder import UIBuilder
from .ui_state_manager import UIStateManager
from .file_operations import FileOperations
from .transcription_controller import TranscriptionController
from .view_manager import ViewManager

class App(tk.Tk):
    """
    Główna klasa aplikacji, dziedzicząca po tk.Tk.
    Odpowiada za inicjalizację okna, składanie komponentów i zarządzanie
    głównym stanem aplikacji.
    """
    def __init__(self):
        super().__init__()

        # --- Application State Variables ---
        self.processing_thread = None
        self.pause_request_event = threading.Event()

        # --- Window Configuration ---
        self.title(config.APP_NAME)
        self.minsize(1024, 600)
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Main grid configuration
        self.grid_columnconfigure(0, weight=4)
        self.grid_columnconfigure(1, weight=0)
        self.grid_columnconfigure(2, weight=0)
        self.grid_columnconfigure(3, weight=0)
        self.grid_columnconfigure(4, weight=3)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=0)  # Row for the reset button

        # --- Initialize Managers and Controllers ---
        self.ui_builder = UIBuilder(self)
        self.ui_state_manager = UIStateManager(self)
        self.file_operations = FileOperations(self)
        self.transcription_controller = TranscriptionController(self)
        self.view_manager = ViewManager(self)

        # --- Create UI and Initialize State ---
        self.ui_builder.create_widgets()
        self.ui_state_manager.update_ui_state()
        self.view_manager.refresh_all_views()

    # --- Delegate methods for backward compatibility ---
    def refresh_all_views(self):
        """Refresh all views - delegates to view manager."""
        self.view_manager.refresh_all_views()

    def pause_transcription(self):
        """Pause transcription - delegates to transcription controller.""" 
        self.transcription_controller.pause_transcription()

    def resume_transcription(self):
        """Resume transcription - delegates to transcription controller."""
        self.transcription_controller.resume_transcription()

    def on_processing_finished(self):
        """Handle processing finished - delegates to transcription controller."""
        self.transcription_controller.on_processing_finished()

    def monitor_processing(self):
        """Monitor processing thread and update UI."""
        if self.processing_thread and self.processing_thread.is_alive():
            self.ui_state_manager.update_ui_state()
            self.refresh_all_views()
            self.after(1000, self.monitor_processing)
        else:
            self.on_processing_finished()

    def start_transcription_process(self):
        """Start transcription process - delegates to transcription controller."""
        self.transcription_controller.start_transcription_process()

    def copy_transcription_to_clipboard(self):
        """Copy transcription to clipboard."""
        text = self.transcription_view.get_text()
        if not text.strip():
            messagebox.showinfo("Informacja", "Brak tekstu do skopiowania.")
            return
        self.clipboard_clear()
        self.clipboard_append(text)
        messagebox.showinfo("Skopiowano", "Transkrypcja została skopiowana do schowka.")

    def on_closing(self):
        """Handle window closing event."""
        if self.processing_thread and self.processing_thread.is_alive():
            if messagebox.askokcancel("Przetwarzanie w toku", "Proces jest aktywny. Czy na pewno chcesz wyjść?"):
                self.destroy()
        else:
            self.destroy()

def main():
    app = App()
    app.mainloop()