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
    
    def refresh_all_views(self):
        """Odświeża wszystkie widoki, pobierając aktualne dane z bazy."""
        try:
            all_files = database.get_all_files()
            self._refresh_selected_files_view(all_files)
            self._refresh_status_views(all_files)
            self.app.update_all_counters() # Upewnij się, że liczniki są aktualne
        except Exception as e:
            print(f"Krytyczny błąd podczas odświeżania widoków: {e}")
            messagebox.showerror("Błąd Bazy Danych", f"Nie można odświeżyć widoków: {e}")

    def _refresh_selected_files_view(self, all_files):
        """Odświeża panel z listą plików do wyboru."""
        files_to_update_duration = []

        for file_row in all_files:
            if file_row['duration_seconds'] is None:
                file_path = file_row['source_file_path']
                try:
                    duration = get_file_duration(file_path)
                    files_to_update_duration.append((file_path, duration))
                except Exception as e:
                    print(f"Nie udało się pobrać czasu trwania dla {file_path}: {e}")

        if files_to_update_duration:
            for path, dur in files_to_update_duration:
                database.update_file_duration(path, dur)
            # Pobierz dane ponownie po aktualizacji
            all_files = database.get_all_files()

        self.app.file_selection_panel.populate_files(all_files)

    def _refresh_status_views(self, all_files):
        """Odświeża wszystkie panele statusu i panel transkrypcji."""
        # Filtruj pliki na podstawie nowych flag
        loaded_files = [
            os.path.basename(row['source_file_path']) for row in all_files
            if row['is_loaded'] and not row['is_processed']
        ]
        processed_files = [
            os.path.basename(row['source_file_path']) for row in all_files
            if row['is_processed']
        ]
        transcriptions = [
            row['transcription'] for row in all_files
            if row['is_processed'] and row['transcription']
        ]

        # Zaktualizuj widoki
        self.app.conversion_status_panel.update_from_list(loaded_files)
        # Panel "w kolejce" teraz również pokazuje pliki wczytane, ale nieprzetworzone
        self.app.transcription_queue_panel.update_from_list(loaded_files)
        self.app.completed_files_panel.update_from_list(processed_files)
        self.app.transcription_output_panel.update_text("\n\n".join(transcriptions))