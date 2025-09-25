import customtkinter as ctk
from tkinter import messagebox
import threading
import pygame
from src import config

# Import UI components and managers
from .interface_builder import InterfaceBuilder
from .button_state_controller import ButtonStateController
from .file_handler import FileHandler
from .transcription_controller import TranscriptionController
from .panel_manager import PanelManager
from .audio_player import AudioPlayer

class App(ctk.CTk):
    """
    Main application class extending ctk.CTk.
    Responsible for window initialization, component assembly and
    managing the core application state.
    
    Architecture:
    - InterfaceBuilder: Creates and positions all UI components
    - ButtonStateController: Manages button enable/disable states
    - FileHandler: Handles file selection, loading and reset operations
    - TranscriptionController: Controls transcription process flow
    - PanelManager: Manages data refresh and view updates
    - AudioPlayer: Manages audio playback
    """
    def __init__(self):
        super().__init__()

        # --- CustomTkinter Theme and Appearance ---
        ctk.set_appearance_mode("System")  # Options: "System", "Dark", "Light"
        ctk.set_default_color_theme("blue") # Options: "blue", "green", "dark-blue"

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
        self.grid_columnconfigure(0, weight=0)
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

        # --- Initialize Core Logic Components ---
        # Singleton instance of the audio player
        self.audio_player = AudioPlayer()

        # --- Initialize Application Components ---
        # Creates and positions all UI elements (buttons, panels, etc.)
        self.interface_builder = InterfaceBuilder(self, self.audio_player)
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
        
        # --- Load Existing Data and Update UI State ---
        # Initialize UI state based on existing tmp files (if any)
        self.button_state_controller.update_ui_state()
        self.panel_manager.refresh_all_views()
        # Update counters after interface is fully initialized
        self.update_all_counters()

        # --- Start background tasks ---
        self._check_audio_events()
    
    def update_files_counter(self, total, approved, long_files):
        """Update file selection counters in the bottom row."""
        if hasattr(self, 'files_counter_label'):
            if total == 0:
                self.files_counter_label.configure(text="")
            else:
                counter_text = f"Razem: {total}  |  Zaznaczone: {approved}"
                if long_files > 0:
                    counter_text += f"  |  Długie: {long_files}"
                self.files_counter_label.configure(text=counter_text)
    
    def update_all_counters(self):
        """Update all dynamic counters based on current data."""
        # Update selected files counter
        if hasattr(self, 'file_selection_panel'):
            total_files = len(self.file_selection_panel.file_widgets)
            approved_files = len(self.file_selection_panel.get_checked_files())
            long_files = sum(1 for _, _, duration, _ in self.file_selection_panel.file_widgets
                           if duration > config.MAX_FILE_DURATION_SECONDS)
            self.update_files_counter(total_files, approved_files, long_files)
        
        # Update loaded files counter
        if hasattr(self, 'loaded_counter_label'):
            loaded_count = len(self._get_list_content(config.LOADED_LIST))
            if loaded_count == 0:
                self.loaded_counter_label.configure(text="")
            else:
                self.loaded_counter_label.configure(text=f"Przygotowane: {loaded_count}")
        
        # Update processing counter
        if hasattr(self, 'processing_counter_label'):
            processing_count = len(self._get_list_content(config.PROCESSING_LIST))
            if processing_count == 0:
                self.processing_counter_label.configure(text="")
            else:
                self.processing_counter_label.configure(text=f"Kolejka: {processing_count}")
        
        # Update processed counter
        if hasattr(self, 'processed_counter_label'):
            processed_count = len(self._get_list_content(config.PROCESSED_LIST))
            if processed_count == 0:
                self.processed_counter_label.configure(text="")
            else:
                self.processed_counter_label.configure(text=f"Gotowe: {processed_count}")
    
    def _get_list_content(self, file_path):
        """Read file content and return list of lines."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return [line.strip() for line in f.readlines() if line.strip()]
        except FileNotFoundError:
            return []

    # --- UI Panel Management Delegation ---
    def refresh_all_views(self):
        """Refresh all data panels - delegates to panel manager."""
        self.panel_manager.refresh_all_views()
        self.update_all_counters()

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

    def _check_audio_events(self):
        """
        Checks for custom pygame events, like the end of a song.
        Updates the UI accordingly. Runs periodically.
        """
        for event in pygame.event.get():
            if event.type == self.audio_player.SONG_END_EVENT:
                self.audio_player.stop()
                # Update the buttons in the file selection panel
                if hasattr(self, 'file_selection_panel'):
                    self.file_selection_panel.update_play_buttons()

        # Schedule the next check
        self.after(100, self._check_audio_events)

    # --- Application Lifecycle ---
    def on_closing(self):
        """
        Handle application window closing event.
        Prevents accidental closure during active transcription processing.
        Stops audio playback and quits pygame.
        """
        # Stop audio playback
        self.audio_player.stop()
        pygame.quit()

        if self.processing_thread and self.processing_thread.is_alive():
            if messagebox.askokcancel("Przetwarzanie w toku", "Proces jest aktywny. Czy na pewno chcesz wyjść?"):
                self.destroy()
        else:
            self.destroy()

def main():
    app = App()
    app.mainloop()