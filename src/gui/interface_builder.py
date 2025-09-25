# This module builds the UI components

from tkinter import ttk

from .files_view import FilesView
from .status_view import StatusView
from .transcription_view import TranscriptionView


class InterfaceBuilder:
    """
    Responsible for creating and positioning all user interface components.
    Organizes the main application layout with 5 columns:
    - File Selection Panel (column 0)
    - Conversion Status Panel (column 1) 
    - Transcription Queue Panel (column 2)
    - Completed Files Panel (column 3)
    - Transcription Output Panel (column 4)
    """
    
    def __init__(self, app):
        self.app = app
    
    def create_widgets(self):
        """Create and place all UI components in the window."""
        self._create_buttons()
        self._create_views()
        self._create_reset_button()
    
    def _create_buttons(self):
        """Create action buttons with descriptive names for better code understanding."""
        # --- Column 0: File Selection Button ---
        self.app.file_selector_button = ttk.Button(
            self.app, 
            text="Wybierz pliki", 
            command=self.app.file_handler.select_source_files
        )
        self.app.file_selector_button.grid(row=0, column=0, sticky="ew", padx=(10, 5), pady=(10, 0))

        # --- Column 1: File Conversion Button ---
        self.app.convert_files_button = ttk.Button(
            self.app, 
            text="Wczytaj Pliki", 
            command=self.app.file_handler.load_selected_files
        )
        self.app.convert_files_button.grid(row=0, column=1, sticky="ew", padx=(10, 5), pady=(10, 0))

        # --- Column 2: Transcription Start Button ---
        self.app.start_transcription_button = ttk.Button(
            self.app, 
            text="Start", 
            command=self.app.transcription_controller.start_transcription_process
        )
        self.app.start_transcription_button.grid(row=0, column=2, sticky="ew", padx=5, pady=(10, 0))

        # --- Column 3: Transcription Control Button ---
        self.app.transcription_control_button = ttk.Button(
            self.app, 
            text="Pauza", 
            command=self.app.transcription_controller.pause_transcription
        )
        self.app.transcription_control_button.grid(row=0, column=3, sticky="ew", padx=5, pady=(10, 0))

        # --- Column 4: Copy Transcription Button ---
        self.app.copy_transcription_button = ttk.Button(
            self.app, 
            text="Kopiuj Transkrypcję", 
            command=self.app.copy_transcription_to_clipboard
        )
        self.app.copy_transcription_button.grid(row=0, column=4, sticky="ew", padx=(5, 10), pady=(10, 0))
    
    def _create_views(self):
        """Create data panel components with descriptive names."""
        # --- Column 0: File Selection Panel (with checkboxes, duration info) ---
        self.app.file_selection_panel = FilesView(self.app, "Wybrane")
        self.app.file_selection_panel.grid(row=1, column=0, sticky="nsew", padx=(10, 5), pady=5)

        # --- Column 1: Conversion Status Panel (modified StatusView with tk.Text) ---
        self.app.conversion_status_panel = StatusView(self.app, text="Wczytane")
        self.app.conversion_status_panel.grid(row=1, column=1, sticky="nsew", padx=(10, 5), pady=5)

        # --- Column 2: Transcription Queue Panel (modified StatusView with tk.Text) ---
        self.app.transcription_queue_panel = StatusView(self.app, text="Do przetworzenia")
        self.app.transcription_queue_panel.grid(row=1, column=2, sticky="nsew", padx=5, pady=5)

        # --- Column 3: Completed Files Panel (modified StatusView with tk.Text) ---
        self.app.completed_files_panel = StatusView(self.app, text="Przetworzone")
        self.app.completed_files_panel.grid(row=1, column=3, sticky="nsew", padx=5, pady=5)

        # --- Column 4: Transcription Output Panel (final text results) ---
        self.app.transcription_output_panel = TranscriptionView(self.app, text="Transkrypcja")
        self.app.transcription_output_panel.grid(row=1, column=4, sticky="nsew", padx=(5, 10), pady=5)
    
    def _create_reset_button(self):
        """Create reset button with custom styling."""
        # --- Row 2: Reset Button ---
        style = ttk.Style(self.app)
        style.configure("Red.TButton", foreground="white", background="red", borderwidth=0, relief="flat")
        style.map("Red.TButton",
            background=[('active', '#C00000'), ('pressed', '!disabled', '#C00000')]
        )
        self.app.reset_application_button = ttk.Button(
            self.app, 
            text="Resetuj", 
            command=self.app.file_handler.reset_app_state, 
            style="Red.TButton"
        )
        self.app.reset_application_button.grid(row=2, column=4, sticky="e", padx=10, pady=(5, 10), ipady=5)
