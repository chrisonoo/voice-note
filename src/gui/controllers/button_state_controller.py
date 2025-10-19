# Ten moduł zawiera klasę `ButtonStateController`, której jedynym zadaniem jest
# zarządzanie stanem (aktywny/nieaktywny) przycisków w interfejsie użytkownika.
# Decyzje podejmuje na podstawie aktualnego stanu aplikacji, np. czy pliki są
# wczytywane, czy trwa transkrypcja, czy są pliki gotowe do przetworzenia.
# Dzięki temu użytkownik nie może kliknąć przycisku, który w danym momencie
# nie powinien być używany.

from typing import Any

from src import database
from src.gui.core.main_window import App


class ButtonStateController:
    """
    Zarządza stanem (włączony/wyłączony) przycisków w interfejsie,
    opierając się na danych z bazy danych i stanie wątku roboczego.
    """

    def __init__(self, app: App):
        """
        Inicjalizuje kontroler.

        Argumenty:
            app: Referencja do głównego obiektu aplikacji (`App`), aby mieć
                 dostęp do przycisków i stanu aplikacji (np. wątku przetwarzającego).
        """
        self.app = app

    def update_ui_state(self, all_files: list[Any] | None = None):
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
        assert all_files is not None

        # Obliczamy flagi logiczne, które reprezentują aktualny stan danych.
        # Użycie `any()` jest wydajne, bo przestaje sprawdzać po znalezieniu pierwszego `True`.
        # Czy istnieją pliki, które są zaznaczone, ale jeszcze nie wczytane (nie przekonwertowane)?
        has_files_to_load = any(f["is_selected"] and not f["is_loaded"] for f in all_files)
        # Czy istnieją pliki, które są wczytane, ale jeszcze nie przetworzone (bez transkrypcji)?
        has_files_to_process = any(f["is_loaded"] and not f["is_processed"] for f in all_files)

        # --- Przycisk wyboru plików ---
        # Powinien być wyłączony, jeśli trwa przetwarzanie LUB transkrypcja została już rozpoczęta.
        # Użytkownik może dodawać pliki dopóki nie kliknie przycisku "Start".
        self.app.file_selector_button.configure(  # type: ignore
            state="disabled" if is_processing or self.app.transcription_started else "normal"
        )

        # --- Przycisk "Wczytaj Pliki" (konwersja) ---
        # Włączony tylko, jeśli są pliki do wczytania ORAZ nie trwa żadne przetwarzanie w tle.
        self.app.convert_files_button.configure(  # type: ignore
            state="normal" if has_files_to_load and not is_processing else "disabled"
        )

        # --- Przycisk "Start" transkrypcji ---
        # Włączony tylko jeśli są pliki gotowe do transkrypcji i nie trwa przetwarzanie.
        self.app.start_transcription_button.configure(  # type: ignore
            state="normal" if has_files_to_process and not is_processing else "disabled"
        )

        # --- Przycisk kontroli transkrypcji (Pauza) ---
        # Ta sekcja zarządza przyciskiem w kolumnie 3, który służy do zatrzymywania
        # aktywnego procesu transkrypcji.
        # Upewniamy się, że przycisk "Start" (w kolumnie 2) jest zawsze widoczny.
        # Jego stan (włączony/wyłączony) jest zarządzany przez osobną logikę powyżej.
        self.app.start_transcription_button.grid(row=0, column=2, sticky="ew", padx=5, pady=(10, 0))  # type: ignore
        # Dedykowany przycisk "Wznów" jest nieużywany i powinien być zawsze ukryty.
        self.app.resume_button.grid_remove()

        # Logika dla przycisku w kolumnie 3 (Zatrzymaj aktywny proces)
        if is_processing:
            # Jeśli trwa przetwarzanie, przycisk "Pauza" jest aktywny i pozwala zatrzymać proces.
            self.app.transcription_control_button.configure(  # type: ignore
                state="normal", text="Pauza", command=self.app.stop_transcription
            )
        else:
            # Jeśli nie ma aktywnego przetwarzania, przycisk jest nieaktywny.
            self.app.transcription_control_button.configure(state="disabled", text="Pauza")  # type: ignore

        # --- Przycisk kopiowania ---
        # Logika: przycisk kopiowania jest aktywny tylko wtedy, gdy wszystkie ZAZNACZONE pliki
        # zostały już przetworzone.
        selected_files = [f for f in all_files if f["is_selected"]]
        is_copy_enabled = False
        if selected_files:  # Sprawdzamy, czy cokolwiek jest zaznaczone.
            # `all()` zwraca True, jeśli warunek jest spełniony dla każdego elementu na liście.
            is_copy_enabled = all(f["is_processed"] for f in selected_files)

        self.app.copy_transcription_button.configure(  # type: ignore
            state="normal" if is_copy_enabled else "disabled"
        )
