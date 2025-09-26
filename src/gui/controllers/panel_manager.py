# Ten moduł zawiera klasę `PanelManager`, która jest kontrolerem odpowiedzialnym za
# aktualizowanie zawartości paneli w interfejsie użytkownika. Działa jak pośrednik,
# który pobiera dane z bazy, przetwarza je i przekazuje do odpowiednich widżetów (paneli),
# aby wyświetliły aktualne informacje.

import os
from tkinter import messagebox
from src import database
from src.audio import get_file_duration

class PanelManager:
    """
    Zarządza odświeżaniem zawartości wszystkich paneli w interfejsie,
    pobierając i filtrując dane bezpośrednio z bazy danych.
    """

    def __init__(self, app):
        """
        Inicjalizuje menedżera paneli.

        Argumenty:
            app: Referencja do głównego obiektu aplikacji (`App`), aby mieć dostęp
                 do poszczególnych paneli (np. `self.app.file_selection_panel`).
        """
        self.app = app

    def refresh_all_views(self, data=None):
        """
        Odświeża wszystkie widoki w aplikacji. Jeśli dane (`data`) nie są dostarczone,
        pobiera je z bazy. W przeciwnym razie używa dostarczonych danych, co jest
        optymalizacją zapobiegającą wielokrotnym zapytaniom do bazy danych.
        """
        try:
            # Jeśli nie otrzymaliśmy gotowych danych, pobieramy je z bazy.
            all_files = data if data is not None else database.get_all_files()

            # Sprawdzamy, czy dla nowo dodanych plików został obliczony czas trwania.
            # Jeśli nie (`duration_seconds` jest None), obliczamy go teraz.
            files_to_update_duration = []
            for file_row in all_files:
                if file_row['duration_seconds'] is None:
                    try:
                        duration = get_file_duration(file_row['source_file_path'])
                        # Dodajemy parę (ścieżka, czas_trwania) do listy do aktualizacji.
                        files_to_update_duration.append((file_row['source_file_path'], duration))
                    except Exception as e:
                        print(f"Nie udało się pobrać czasu trwania dla {file_row['source_file_path']}: {e}")

            # Jeśli znaleziono pliki wymagające aktualizacji czasu trwania...
            if files_to_update_duration:
                # ...wykonujemy jedną, masową aktualizację w bazie danych.
                database.update_file_durations_bulk(files_to_update_duration)
                # Po aktualizacji musimy ponownie pobrać dane, aby mieć ich najnowszą wersję.
                all_files = database.get_all_files()

            # Odświeżamy poszczególne panele, przekazując im już przygotowane i aktualne dane.
            self._refresh_selected_files_view(all_files)
            self._refresh_status_views(all_files)

        except Exception as e:
            # Obsługa błędów, na wypadek problemów z bazą danych lub odświeżaniem.
            print(f"Krytyczny błąd podczas odświeżania widoków: {e}")
            messagebox.showerror("Błąd Bazy Danych", f"Nie można odświeżyć widoków: {e}")

    def _refresh_selected_files_view(self, all_files):
        """Odświeża panel z listą plików do wyboru (z checkboxami), używając dostarczonych danych."""
        self.app.file_selection_panel.populate_files(all_files)

    def _refresh_status_views(self, all_files):
        """
        Odświeża wszystkie panele statusu (Wczytane, Kolejka, Gotowe) oraz panel z transkrypcją,
        używając tych samych, raz pobranych danych.
        """
        # Filtrujemy pliki dla panelu "Wczytane". Są to pliki, które zostały już przekonwertowane na .wav.
        files_to_load = [
            os.path.basename(row['tmp_file_path']) for row in all_files
            if row['is_loaded']
        ]

        # Filtrujemy pliki dla panelu "Do przetworzenia" (Kolejka).
        # Są to pliki, które są wczytane, ale nie mają jeszcze transkrypcji.
        files_in_queue = [
            os.path.basename(row['tmp_file_path']) for row in all_files
            if row['is_loaded'] and not row['is_processed']
        ]

        # Filtrujemy pliki dla panelu "Przetworzone".
        processed_files = [
            os.path.basename(row['tmp_file_path']) for row in all_files
            if row['is_processed']
        ]

        # Zbieramy gotowe transkrypcje, aby wyświetlić je w głównym panelu tekstowym.
        transcriptions = [
            row['transcription']
            for row in all_files
            if row['is_processed'] and row['transcription']
        ]

        # Wywołujemy metody `update` na odpowiednich panelach, przekazując im przefiltrowane listy.
        self.app.conversion_status_panel.update_from_list(files_to_load)
        self.app.transcription_queue_panel.update_from_list(files_in_queue)
        self.app.completed_files_panel.update_from_list(processed_files)
        # Łączymy wszystkie transkrypcje w jeden tekst i aktualizujemy panel wyjściowy.
        self.app.transcription_output_panel.update_text("\n\n".join(transcriptions))

    def refresh_transcription_progress_views(self, data=None):
        """
        Odświeża tylko te widoki, które są związane z postępem transkrypcji.
        Jest to lżejsza wersja `refresh_all_views`, używana w pętli postępu,
        ponieważ nie ma potrzeby odświeżania panelu wyboru plików (`FilesView`),
        który w tym czasie się nie zmienia.
        """
        try:
            all_files = data if data is not None else database.get_all_files()
            self._refresh_status_views(all_files)
        except Exception as e:
            print(f"Błąd podczas odświeżania postępu transkrypcji: {e}")