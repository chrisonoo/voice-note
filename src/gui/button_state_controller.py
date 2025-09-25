# This module manages UI state (enabling/disabling buttons based on application state)

from src import database

class ButtonStateController:
    """
    Zarządza stanem przycisków w interfejsie, opierając się na danych z bazy.
    Zapewnia prawidłowy przepływ pracy: Wybierz -> Wczytaj -> Start -> Kopiuj/Resetuj.
    """
    
    def __init__(self, app):
        self.app = app
    
    def update_ui_state(self):
        """Aktualizuje stan interfejsu na podstawie danych z bazy."""
        is_processing = self.app.processing_thread and self.app.processing_thread.is_alive()

        # Pobierz wszystkie pliki i pogrupuj je według statusu
        all_files = database.get_all_files()
        status_counts = {
            'selected': 0,
            'encoded': 0,
            'processing': 0,
            'processed': 0
        }
        for row in all_files:
            if row['status'] in status_counts:
                status_counts[row['status']] += 1

        has_selected = status_counts['selected'] > 0
        has_encoded = status_counts['encoded'] > 0
        has_processed = status_counts['processed'] > 0

        # --- Przycisk wyboru plików ---
        # Wyłącz, jeśli jakiekolwiek pliki są w systemie lub trwa przetwarzanie
        any_files_exist = len(all_files) > 0
        self.app.file_selector_button.configure(state="disabled" if is_processing or any_files_exist else "normal")

        # --- Przycisk konwersji ("Wczytaj Pliki") ---
        # Włącz, jeśli są pliki do wybrania i nie trwa przetwarzanie
        self.app.convert_files_button.configure(state="normal" if has_selected and not is_processing else "disabled")

        # --- Przycisk resetowania ---
        self.app.reset_application_button.configure(state="disabled" if is_processing else "normal")

        # --- Przycisk startu transkrypcji ---
        # Włącz, jeśli są pliki po konwersji (encoded) i nie trwa przetwarzanie
        self.app.start_transcription_button.configure(state="normal" if has_encoded and not is_processing else "disabled")

        # --- Przyciski kontroli transkrypcji (Pauza/Wznów) ---
        is_paused = self.app.pause_request_event.is_set()

        # Domyślne stany
        self.app.transcription_control_button.grid(row=0, column=3, sticky="ew", padx=5, pady=(10, 0))
        self.app.transcription_control_button.configure(state="disabled", text="Pauza", command=self.app.pause_transcription)
        self.app.resume_button.grid_remove() # Domyślnie ukryj

        if is_processing:
            # Stan aktywnego przetwarzania: pokaż przycisk Pauza/Wznów
            self.app.transcription_control_button.configure(state="normal")
            if is_paused:
                self.app.transcription_control_button.configure(text="Wznów", command=self.app.resume_transcription)
        elif has_encoded and has_processed:
            # Stan przerwania (są pliki do przetworzenia i już przetworzone)
            self.app.transcription_control_button.grid_remove()
            self.app.resume_button.grid(row=0, column=3, sticky="ew", padx=5, pady=(10, 0))
            self.app.start_transcription_button.configure(state="disabled")

        # Przycisk kopiowania jest zawsze aktywny
        self.app.copy_transcription_button.configure(state="normal")