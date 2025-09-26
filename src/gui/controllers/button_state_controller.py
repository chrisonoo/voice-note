from src import database

class ButtonStateController:
    """
    Zarządza stanem przycisków w interfejsie, opierając się na danych z bazy.
    """
    
    def __init__(self, app):
        self.app = app
    
    def update_ui_state(self, all_files=None):
        """
        Aktualizuje stan interfejsu na podstawie dostarczonych danych lub
        pobiera świeże dane, jeśli nie zostały podane.
        """
        is_processing = self.app.processing_thread and self.app.processing_thread.is_alive()

        if all_files is None:
            all_files = database.get_all_files()

        # Oblicz stany na podstawie nowych flag
        has_files_to_load = any(f['is_selected'] and not f['is_loaded'] for f in all_files)
        has_files_to_process = any(f['is_loaded'] and not f['is_processed'] for f in all_files)
        has_processed_files = any(f['is_processed'] for f in all_files)
        any_files_exist = len(all_files) > 0

        # --- Przycisk wyboru plików ---
        # Wyłączony, jeśli jakiekolwiek pliki istnieją lub trwa przetwarzanie
        self.app.file_selector_button.configure(state="disabled" if is_processing or any_files_exist else "normal")

        # --- Przycisk "Wczytaj Pliki" (konwersja) ---
        # Włączony, jeśli są pliki zaznaczone do wczytania i nie trwa przetwarzanie
        self.app.convert_files_button.configure(state="normal" if has_files_to_load and not is_processing else "disabled")

        # --- Przycisk "Start" transkrypcji ---
        # Włączony, jeśli są pliki do przetworzenia i nie trwa przetwarzanie
        self.app.start_transcription_button.configure(state="normal" if has_files_to_process and not is_processing else "disabled")

        # --- Przyciski kontroli transkrypcji (Pauza/Wznów) ---
        is_paused = self.app.pause_request_event.is_set()

        self.app.transcription_control_button.grid(row=0, column=3, sticky="ew", padx=5, pady=(10, 0))
        self.app.transcription_control_button.configure(state="disabled", text="Pauza", command=self.app.pause_transcription)
        self.app.resume_button.grid_remove()

        if is_processing:
            self.app.transcription_control_button.configure(state="normal")
            if is_paused:
                self.app.transcription_control_button.configure(text="Wznów", command=self.app.resume_transcription)
        elif has_files_to_process and has_processed_files:
            self.app.transcription_control_button.grid_remove()
            self.app.resume_button.grid(row=0, column=3, sticky="ew", padx=5, pady=(10, 0))
            self.app.start_transcription_button.configure(state="disabled")

        # --- Przycisk kopiowania ---
        # Aktywny tylko, gdy wszystkie zaznaczone pliki zostaną przetworzone.
        selected_files = [f for f in all_files if f['is_selected']]
        is_copy_enabled = False
        if selected_files:
            is_copy_enabled = all(f['is_processed'] for f in selected_files)

        self.app.copy_transcription_button.configure(state="normal" if is_copy_enabled else "disabled")