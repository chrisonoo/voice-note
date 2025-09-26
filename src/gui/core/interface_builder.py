# Ten moduł zawiera klasę `InterfaceBuilder`, która działa zgodnie ze wzorcem projektowym "Builder".
# Jej jedynym zadaniem jest tworzenie i umieszczanie w oknie wszystkich komponentów
# interfejsu użytkownika (przycisków, paneli, etykiet). Oddzielenie tej logiki
# od głównej klasy aplikacji (`App`) sprawia, że kod jest czystszy i łatwiejszy w zarządzaniu.

import customtkinter as ctk  # Importujemy bibliotekę do tworzenia widżetów.

# Importujemy nasze własne, niestandardowe widżety z podfolderu `widgets`.
# Każdy z nich to osobna klasa, która definiuje wygląd i podstawowe zachowanie danego panelu.
from ..widgets.files_view import FilesView
from ..widgets.status_view import StatusView
from ..widgets.transcription_view import TranscriptionView


class InterfaceBuilder:
    """
    Odpowiada za tworzenie i pozycjonowanie wszystkich komponentów interfejsu użytkownika.
    Organizuje główny układ aplikacji w 5 kolumnach:
    - Panel wyboru plików (kolumna 0)
    - Panel statusu konwersji (kolumna 1)
    - Panel kolejki transkrypcji (kolumna 2)
    - Panel ukończonych plików (kolumna 3)
    - Panel z wynikiem transkrypcji (kolumna 4)
    """
    
    def __init__(self, app, audio_player):
        """
        Inicjalizuje budowniczego interfejsu.

        Argumenty:
            app: Referencja do głównego obiektu aplikacji (`App`). Jest potrzebna,
                 aby budowniczy mógł dodawać widżety do głównego okna i przypisywać je
                 jako atrybuty tego okna (np. `self.app.przycisk = ...`).
            audio_player: Referencja do obiektu odtwarzacza audio, potrzebna dla panelu `FilesView`.
        """
        self.app = app
        self.audio_player = audio_player
    
    def create_widgets(self):
        """Tworzy i umieszcza wszystkie komponenty UI w oknie głównym."""
        # Wywołujemy prywatne metody, które grupują tworzenie poszczególnych typów widżetów.
        self._create_buttons()
        self._create_views()
        self._create_counter_labels()
    
    def _create_buttons(self):
        """Tworzy przyciski akcji i umieszcza je w siatce (grid) okna."""
        # --- Kolumna 0: Przycisk wyboru plików ---
        # Tworzymy przycisk i przypisujemy go do atrybutu `file_selector_button` w głównej klasie `App`.
        self.app.file_selector_button = ctk.CTkButton(
            self.app,  # Rodzic widżetu (okno główne).
            text="Wybierz pliki",  # Tekst na przycisku.
            command=self.app.file_handler.select_source_files  # Funkcja, która zostanie wywołana po kliknięciu.
        )
        # `grid()` umieszcza widżet w oknie.
        # `row=0, column=0`: Pozycja w siatce (pierwszy wiersz, pierwsza kolumna).
        # `sticky="ew"`: Rozciąga przycisk w poziomie (East-West), aby wypełnił całą szerokość kolumny.
        # `padx, pady`: Dodaje marginesy (w pikselach) na zewnątrz widżetu.
        self.app.file_selector_button.grid(row=0, column=0, sticky="ew", padx=(10, 5), pady=(10, 0))

        # --- Przycisk resetowania ---
        self.app.reset_button = ctk.CTkButton(
            self.app,
            text="Resetuj",
            command=self.app.reset_application,
            fg_color="darkred",  # Kolor przycisku.
            hover_color="red"  # Kolor po najechaniu myszką.
        )
        self.app.reset_button.grid(row=2, column=4, sticky="ew", padx=(5, 10), pady=(5, 10))

        # --- Kolumna 1: Przycisk wczytywania (konwersji) plików ---
        self.app.convert_files_button = ctk.CTkButton(
            self.app,
            text="Wczytaj Pliki",
            command=self.app.file_handler.load_selected_files
        )
        self.app.convert_files_button.grid(row=0, column=1, sticky="ew", padx=(10, 5), pady=(10, 0))

        # --- Kolumna 2: Przycisk startu transkrypcji ---
        self.app.start_transcription_button = ctk.CTkButton(
            self.app,
            text="Start",
            command=self.app.transcription_controller.start_transcription_process
        )
        self.app.start_transcription_button.grid(row=0, column=2, sticky="ew", padx=5, pady=(10, 0))

        # --- Kolumna 3: Przycisk kontroli transkrypcji (Pauza/Wznów) ---
        self.app.transcription_control_button = ctk.CTkButton(
            self.app,
            text="Pauza",
            command=self.app.transcription_controller.pause_transcription
        )
        self.app.transcription_control_button.grid(row=0, column=3, sticky="ew", padx=5, pady=(10, 0))

        # --- Dedykowany przycisk "Wznów" dla stanu przerwanego ---
        # Ten przycisk jest tworzony, ale celowo nie jest umieszczany w siatce (`grid()`).
        # Jego widocznością będzie zarządzał `ButtonStateController`, który zamieni go
        # miejscami z przyciskiem `start_transcription_button` w odpowiednich sytuacjach.
        self.app.resume_button = ctk.CTkButton(
            self.app,
            text="Wznów",
            command=lambda: self.app.transcription_controller.resume_interrupted_process()
        )

        # --- Kolumna 4: Przycisk kopiowania transkrypcji ---
        self.app.copy_transcription_button = ctk.CTkButton(
            self.app,
            text="Kopiuj Transkrypcję",
            command=self.app.copy_transcription_to_clipboard
        )
        self.app.copy_transcription_button.grid(row=0, column=4, sticky="ew", padx=(5, 10), pady=(10, 0))
    
    def _create_views(self):
        """Tworzy komponenty paneli danych, używając naszych niestandardowych klas widżetów."""
        # --- Kolumna 0: Panel wyboru plików (z checkboxami, informacjami o czasie trwania) ---
        self.app.file_selection_panel = FilesView(self.app, self.audio_player, "Wybrane")
        self.app.file_selection_panel.grid(row=1, column=0, sticky="nsew", padx=(10, 5), pady=5)
        # `sticky="nsew"`: Rozciąga panel we wszystkich kierunkach (North-South-East-West), aby wypełnił komórkę siatki.

        # --- Kolumna 1: Panel statusu konwersji ---
        self.app.conversion_status_panel = StatusView(self.app, text="Wczytane")
        self.app.conversion_status_panel.grid(row=1, column=1, sticky="nsew", padx=(10, 5), pady=5)

        # --- Kolumna 2: Panel kolejki do transkrypcji ---
        self.app.transcription_queue_panel = StatusView(self.app, text="Do przetworzenia")
        self.app.transcription_queue_panel.grid(row=1, column=2, sticky="nsew", padx=5, pady=5)

        # --- Kolumna 3: Panel plików ukończonych ---
        self.app.completed_files_panel = StatusView(self.app, text="Przetworzone")
        self.app.completed_files_panel.grid(row=1, column=3, sticky="nsew", padx=5, pady=5)

        # --- Kolumna 4: Panel wyjściowy z transkrypcją ---
        self.app.transcription_output_panel = TranscriptionView(self.app, text="Transkrypcja")
        self.app.transcription_output_panel.grid(row=1, column=4, sticky="nsew", padx=(5, 10), pady=5)
    
    def _create_counter_labels(self):
        """Tworzy etykiety liczników do dynamicznego podsumowania stanu."""
        # --- Kolumna 0: Liczniki wyboru plików ---
        self.app.files_counter_label = ctk.CTkLabel(
            self.app,
            text="",  # Tekst będzie ustawiany dynamicznie.
            anchor="center"  # Wyśrodkowanie tekstu w etykiecie.
        )
        self.app.files_counter_label.grid(row=2, column=0, sticky="ew", padx=(10, 5), pady=(5, 10))

        # --- Kolumna 1: Licznik plików wczytanych ---
        self.app.loaded_counter_label = ctk.CTkLabel(self.app, text="", anchor="center")
        self.app.loaded_counter_label.grid(row=2, column=1, sticky="ew", padx=(10, 5), pady=(5, 10))

        # --- Kolumna 2: Licznik plików w kolejce ---
        self.app.processing_counter_label = ctk.CTkLabel(self.app, text="", anchor="center")
        self.app.processing_counter_label.grid(row=2, column=2, sticky="ew", padx=5, pady=(5, 10))

        # --- Kolumna 3: Licznik plików przetworzonych ---
        self.app.processed_counter_label = ctk.CTkLabel(self.app, text="", anchor="center")
        self.app.processed_counter_label.grid(row=2, column=3, sticky="ew", padx=5, pady=(5, 10))