import os
from tkinter import messagebox
from src import database
from src.audio import get_file_duration

class PanelManager:
    """
    Zarządza odświeżaniem paneli interfejsu, pobierając dane
    bezpośrednio z bazy danych.
    """

    def __init__(self, app):
        self.app = app

    def refresh_all_views(self, data=None):
        """
        Odświeża wszystkie widoki. Jeśli 'data' nie jest dostarczona,
        pobiera ją z bazy. W przeciwnym razie używa dostarczonych danych.
        """
        try:
            all_files = data if data is not None else database.get_all_files()

            # Sprawdzenie i aktualizacja brakujących czasów trwania
            files_to_update_duration = []
            for file_row in all_files:
                if file_row['duration_seconds'] is None:
                    try:
                        duration = get_file_duration(file_row['source_file_path'])
                        files_to_update_duration.append((file_row['source_file_path'], duration))
                    except Exception as e:
                        print(f"Nie udało się pobrać czasu trwania dla {file_row['source_file_path']}: {e}")

            if files_to_update_duration:
                database.update_file_durations_bulk(files_to_update_duration)
                all_files = database.get_all_files()

            # Odświeżenie paneli z użyciem tych samych danych
            self._refresh_selected_files_view(all_files)
            self._refresh_status_views(all_files)

            # Liczniki są teraz aktualizowane w App.refresh_all_views
            # self.app.update_all_counters()

        except Exception as e:
            print(f"Krytyczny błąd podczas odświeżania widoków: {e}")
            messagebox.showerror("Błąd Bazy Danych", f"Nie można odświeżyć widoków: {e}")

    def _refresh_selected_files_view(self, all_files):
        """Odświeża panel z listą plików do wyboru, używając dostarczonych danych."""
        self.app.file_selection_panel.populate_files(all_files)

    def _refresh_status_views(self, all_files):
        """Odświeża panele statusu i transkrypcji, używając dostarczonych danych."""
        loaded_files = [
            os.path.basename(row['tmp_file_path']) for row in all_files
            if row['is_loaded'] and not row['is_processed']
        ]
        processed_files = [
            os.path.basename(row['tmp_file_path']) for row in all_files
            if row['is_processed']
        ]
        transcriptions = [
            row['transcription']
            for row in all_files
            if row['is_processed'] and row['transcription']
        ]

        self.app.conversion_status_panel.update_from_list(loaded_files)
        self.app.transcription_queue_panel.update_from_list(loaded_files)
        self.app.completed_files_panel.update_from_list(processed_files)
        self.app.transcription_output_panel.update_text("\n\n".join(transcriptions))

    def refresh_transcription_progress_views(self, data=None):
        """Odświeża tylko widoki związane z postępem transkrypcji."""
        try:
            all_files = data if data is not None else database.get_all_files()
            self._refresh_status_views(all_files)
            # Liczniki są aktualizowane w głównym cyklu monitorowania
        except Exception as e:
            print(f"Błąd podczas odświeżania postępu transkrypcji: {e}")