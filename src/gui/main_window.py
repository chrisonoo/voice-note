import tkinter as tk
from tkinter import messagebox
import threading
from src import config

# Import UI components and managers
from .interface_builder import InterfaceBuilder
from .button_state_controller import ButtonStateController
from .file_handler import FileHandler
from .transcription_controller import TranscriptionController
from .panel_manager import PanelManager

class App(tk.Tk):
    """
    Main application class extending tk.Tk.
    Responsible for window initialization, component assembly and 
    managing the core application state.
    
    Architecture:
    - InterfaceBuilder: Creates and positions all UI components
    - ButtonStateController: Manages button enable/disable states
    - FileHandler: Handles file selection, loading and reset operations
    - TranscriptionController: Controls transcription process flow
    - PanelManager: Manages data refresh and view updates
    """
    def __init__(self):
        super().__init__()

        # --- Core Application State ---
        # Thread handling background transcription processing
        self.processing_thread = None
        # Event flag for pausing/resuming transcription process
        self.pause_request_event = threading.Event()

        # --- Main Window Configuration ---
        self.title(config.APP_NAME)
        self.minsize(1024, 600)  # Minimum window size for proper UI layout
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        # --- UI Grid Layout Configuration ---
        # Column 0: File Selection Panel (wider for file list with details)
        self.grid_columnconfigure(0, weight=4)
        # Columns 1-3: Status Panels (fixed width for consistency)  
        self.grid_columnconfigure(1, weight=0)  # Conversion Status
        self.grid_columnconfigure(2, weight=0)  # Transcription Queue
        self.grid_columnconfigure(3, weight=0)  # Completed Files
        # Column 4: Transcription Output (wider for text display)
        self.grid_columnconfigure(4, weight=3)
        # Row 1: Main content area (expandable)
        self.grid_rowconfigure(1, weight=1)
        # Row 2: Reset button area (fixed height)
        self.grid_rowconfigure(2, weight=0)

        # --- Initialize Application Components ---
        # Creates and positions all UI elements (buttons, panels, etc.)
        self.interface_builder = InterfaceBuilder(self)
        # Manages button enable/disable states based on application flow
        self.button_state_controller = ButtonStateController(self)
        # Handles file operations (select, load, convert, reset)
        self.file_handler = FileHandler(self)
        # Controls transcription process (start, pause, resume, monitor)
        self.transcription_controller = TranscriptionController(self)
        # Manages panel data updates and view refreshing
        self.panel_manager = PanelManager(self)

        # --- Initialize User Interface ---
        self.interface_builder.create_widgets()
        self.button_state_controller.update_ui_state()
        self.panel_manager.refresh_all_views()

    # --- UI Panel Management Delegation ---
    def refresh_all_views(self):
        """Refresh all data panels - delegates to panel manager."""
        self.panel_manager.refresh_all_views()

    # --- Transcription Process Control Delegation ---
    def pause_transcription(self):
        """Pause transcription process - delegates to transcription controller.""" 
        self.transcription_controller.pause_transcription()

    def resume_transcription(self):
        """Resume transcription process - delegates to transcription controller."""
        self.transcription_controller.resume_transcription()

    def on_processing_finished(self):
        """Handle transcription completion - delegates to transcription controller."""
        self.transcription_controller.on_processing_finished()

    def start_transcription_process(self):
        """Start transcription process - delegates to transcription controller."""
        self.transcription_controller.start_transcription_process()

    def monitor_processing(self):
        """
        Monitor active transcription thread and update UI accordingly.
        Runs every 1 second while transcription is active.
        """
        if self.processing_thread and self.processing_thread.is_alive():
            # Update button states based on current process status
            self.button_state_controller.update_ui_state()
            # Refresh all data panels to show current progress
            self.refresh_all_views()
            # Schedule next update in 1 second
            self.after(1000, self.monitor_processing)
        else:
            # Processing finished, perform cleanup
            self.on_processing_finished()

    # --- User Actions ---
    def copy_transcription_to_clipboard(self):
        """
        Copy transcription output text to system clipboard.
        Shows info dialog if no text available or confirms successful copy.
        """
        text = self.transcription_output_panel.get_text()
        if not text.strip():
            messagebox.showinfo("Informacja", "Brak tekstu do skopiowania.")
            return
        self.clipboard_clear()
        self.clipboard_append(text)
        messagebox.showinfo("Skopiowano", "Transkrypcja została skopiowana do schowka.")

    # --- Application Lifecycle ---
    def on_closing(self):
        """
        Handle application window closing event.
        Prevents accidental closure during active transcription processing.
        """
        if self.processing_thread and self.processing_thread.is_alive():
            if messagebox.askokcancel("Przetwarzanie w toku", "Proces jest aktywny. Czy na pewno chcesz wyjść?"):
                self.destroy()
        else:
            self.destroy()

def main():
    app = App()
    app.mainloop()