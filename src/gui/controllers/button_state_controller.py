# Ten moduł zawiera klasę `ButtonStateController`, której jedynym zadaniem jest
# zarządzanie stanem (aktywny/nieaktywny) przycisków w interfejsie użytkownika.
# Decyzje podejmuje na podstawie aktualnego stanu aplikacji, np. czy pliki są
# wczytywane, czy trwa transkrypcja, czy są pliki gotowe do przetworzenia.
# Dzięki temu użytkownik nie może kliknąć przycisku, który w danym momencie
# nie powinien być używany.

from src import database

class ButtonStateController:
    """
    Zarządza stanem (włączony/wyłączony) przycisków w interfejsie,
    opierając się na danych z bazy danych i stanie wątku roboczego.
    """
    
    def __init__(self, app):
        """
        Inicjalizuje kontroler.

        Argumenty:
            app: Referencja do głównego obiektu aplikacji (`App`), aby mieć
                 dostęp do przycisków i stanu aplikacji (np. wątku przetwarzającego).
        """
        self.app = app
    
    def update_ui_state(self, all_files=None):
        """
        Aktualizuje stan całego interfejsu na podstawie dostarczonych danych
        lub pobiera świeże dane z bazy, jeśli nie zostały one podane.
        Jest to centralna metoda, która jest wywoływana po każdej znaczącej
        zmianie stanu aplikacji.
        """
        # Sprawdzamy, czy wątek przetwarzający jest aktywny. To kluczowa informacja,
        # bo w trakcie przetwarzania większość przycisków powinna być zablokowana.
        is_processing = self.app.processing_thread and self.app.processing_thread.is_alive()

        # Optymalizacja: jeśli nie dostaliśmy danych, pobieramy je raz.
        if all_files is None:
            all_files = database.get_all_files()

        # Obliczamy flagi logiczne, które reprezentują aktualny stan danych.
        # Użycie `any()` jest wydajne, bo przestaje sprawdzać po znalezieniu pierwszego `True`.
        # Czy istnieją pliki, które są zaznaczone, ale jeszcze nie wczytane (nie przekonwertowane)?
        has_files_to_load = any(f['is_selected'] and not f['is_loaded'] for f in all_files)
        # Czy istnieją pliki, które są wczytane, ale jeszcze nie przetworzone (bez transkrypcji)?
        has_files_to_process = any(f['is_loaded'] and not f['is_processed'] for f in all_files)
        # Czy istnieją jakiekolwiek pliki, które już mają transkrypcję?
        has_processed_files = any(f['is_processed'] for f in all_files)
        # Czy w bazie danych jest w ogóle jakikolwiek plik?
        any_files_exist = len(all_files) > 0
        # Czy istnieją pliki, które zostały już wczytane (przekonwertowane)?
        has_loaded_files = any(f['is_loaded'] for f in all_files)

        # --- Przycisk wyboru plików ---
        # Powinien być wyłączony, jeśli trwa przetwarzanie LUB transkrypcja została już rozpoczęta.
        # Użytkownik może dodawać pliki dopóki nie kliknie przycisku "Start".
        self.app.file_selector_button.configure(state="disabled" if is_processing or self.app.transcription_started else "normal")

        # --- Przycisk "Wczytaj Pliki" (konwersja) ---
        # Włączony tylko, jeśli są pliki do wczytania ORAZ nie trwa żadne przetwarzanie w tle.
        self.app.convert_files_button.configure(state="normal" if has_files_to_load and not is_processing else "disabled")

        # --- Przycisk "Start" transkrypcji ---
        # Włączony tylko, jeśli są pliki gotowe do transkrypcji ORAZ nie trwa żadne przetwarzanie w tle.
        self.app.start_transcription_button.configure(state="normal" if has_files_to_process and not is_processing else "disabled")

        # --- Przyciski kontroli transkrypcji (Pauza/Wznów) ---
        # Ta sekcja zarządza przyciskiem w kolumnie 3, który służy do pauzowania
        # i wznawiania aktywnego procesu transkrypcji.
        is_paused = self.app.pause_request_event.is_set()

        # Upewniamy się, że przycisk "Start" (w kolumnie 2) jest zawsze widoczny.
        # Jego stan (włączony/wyłączony) jest zarządzany przez osobną logikę powyżej.
        self.app.start_transcription_button.grid(row=0, column=2, sticky="ew", padx=5, pady=(10, 0))
        # Dedykowany przycisk "Wznów" jest nieużywany i powinien być zawsze ukryty.
        self.app.resume_button.grid_remove()

        # Logika dla przycisku w kolumnie 3 (Pauza/Wznów aktywnego procesu)
        if is_processing:
            # Jeśli trwa przetwarzanie, przycisk jest aktywny.
            self.app.transcription_control_button.configure(state="normal")
            if is_paused:
                # Jeśli proces jest spauzowany, zmieniamy tekst i komendę przycisku.
                self.app.transcription_control_button.configure(text="Wznów", command=self.app.resume_transcription)
            else:
                # Jeśli proces jest aktywny, przycisk służy do pauzowania.
                self.app.transcription_control_button.configure(text="Pauza", command=self.app.pause_transcription)
        else:
            # Jeśli nie ma aktywnego przetwarzania, przycisk jest nieaktywny i ma domyślny stan.
            self.app.transcription_control_button.configure(state="disabled", text="Pauza", command=self.app.pause_transcription)


        # --- Przycisk kopiowania ---
        # Logika: przycisk kopiowania jest aktywny tylko wtedy, gdy wszystkie ZAZNACZONE pliki
        # zostały już przetworzone.
        selected_files = [f for f in all_files if f['is_selected']]
        is_copy_enabled = False
        if selected_files: # Sprawdzamy, czy cokolwiek jest zaznaczone.
            # `all()` zwraca True, jeśli warunek jest spełniony dla każdego elementu na liście.
            is_copy_enabled = all(f['is_processed'] for f in selected_files)

        self.app.copy_transcription_button.configure(state="normal" if is_copy_enabled else "disabled")