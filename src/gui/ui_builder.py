# This module builds the UI components

from tkinter import ttk

from .files_view import FilesView
from .status_view import StatusView
from .transcription_view import TranscriptionView


class UIBuilder:
    """
    Builds UI components for the application.
    """
    
    def __init__(self, app):
        self.app = app
    
    def create_widgets(self):
        """Create and place all UI components in the window."""
        self._create_buttons()
        self._create_views()
        self._create_reset_button()
    
    def _create_buttons(self):
        """Create action buttons."""
        # --- Column 0: Select Files Button ---
        self.app.select_button = ttk.Button(
            self.app, 
            text="Wybierz pliki", 
            command=self.app.file_operations.select_source_files
        )
        self.app.select_button.grid(row=0, column=0, sticky="ew", padx=(10, 5), pady=(10, 0))

        # --- Column 1: Load Files Button ---
        self.app.load_button = ttk.Button(
            self.app, 
            text="Wczytaj Pliki", 
            command=self.app.file_operations.load_selected_files
        )
        self.app.load_button.grid(row=0, column=1, sticky="ew", padx=(10, 5), pady=(10, 0))

        # --- Column 2: Start Button ---
        self.app.start_button = ttk.Button(
            self.app, 
            text="Start", 
            command=self.app.transcription_controller.start_transcription_process
        )
        self.app.start_button.grid(row=0, column=2, sticky="ew", padx=5, pady=(10, 0))

        # --- Column 3: Pause/Resume Button ---
        self.app.pause_resume_button = ttk.Button(
            self.app, 
            text="Pauza", 
            command=self.app.transcription_controller.pause_transcription
        )
        self.app.pause_resume_button.grid(row=0, column=3, sticky="ew", padx=5, pady=(10, 0))

        # --- Column 4: Copy Button ---
        self.app.copy_button = ttk.Button(
            self.app, 
            text="Kopiuj Transkrypcję", 
            command=self.app.copy_transcription_to_clipboard
        )
        self.app.copy_button.grid(row=0, column=4, sticky="ew", padx=(5, 10), pady=(10, 0))
    
    def _create_views(self):
        """Create view components."""
        # --- Column 0: Selected Files View ---
        self.app.selected_files_view = FilesView(self.app, "Wybrane")
        self.app.selected_files_view.grid(row=1, column=0, sticky="nsew", padx=(10, 5), pady=5)

        # --- Column 1: Loaded Files View ---
        self.app.loaded_files_view = StatusView(self.app, text="Wczytane")
        self.app.loaded_files_view.grid(row=1, column=1, sticky="nsew", padx=(10, 5), pady=5)

        # --- Column 2: Processing View ---
        self.app.processing_view = StatusView(self.app, text="Do przetworzenia")
        self.app.processing_view.grid(row=1, column=2, sticky="nsew", padx=5, pady=5)

        # --- Column 3: Processed View ---
        self.app.processed_view = StatusView(self.app, text="Przetworzone")
        self.app.processed_view.grid(row=1, column=3, sticky="nsew", padx=5, pady=5)

        # --- Column 4: Transcription View ---
        self.app.transcription_view = TranscriptionView(self.app, text="Transkrypcja")
        self.app.transcription_view.grid(row=1, column=4, sticky="nsew", padx=(5, 10), pady=5)
    
    def _create_reset_button(self):
        """Create reset button with custom styling."""
        # --- Row 2: Reset Button ---
        style = ttk.Style(self.app)
        style.configure("Red.TButton", foreground="white", background="red", borderwidth=0, relief="flat")
        style.map("Red.TButton",
            background=[('active', '#C00000'), ('pressed', '!disabled', '#C00000')]
        )
        self.app.reset_button = ttk.Button(
            self.app, 
            text="Resetuj", 
            command=self.app.file_operations.reset_app_state, 
            style="Red.TButton"
        )
        self.app.reset_button.grid(row=2, column=4, sticky="e", padx=10, pady=(5, 10), ipady=5)
