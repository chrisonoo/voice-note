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
        except Exception as e:
            print(f"Krytyczny błąd podczas odświeżania widoków: {e}")
            messagebox.showerror("Błąd Bazy Danych", f"Nie można odświeżyć widoków: {e}")

    def _refresh_selected_files_view(self, all_files):
        """Odświeża panel z listą plików do wyboru."""
        files_data = []
        files_to_update_duration = []

        for file_row in all_files:
            file_path = file_row['file_path']
            duration = file_row['duration_seconds']

            # Jeśli czas trwania nie został jeszcze obliczony, zrób to teraz
            if duration is None:
                try:
                    duration = get_file_duration(file_path)
                    # Oznacz do aktualizacji w bazie danych
                    files_to_update_duration.append((file_path, duration))
                except Exception as e:
                    print(f"Nie udało się pobrać czasu trwania dla {file_path}: {e}")
                    duration = 0.0

            files_data.append((file_path, duration))

        # Zaktualizuj czasy trwania w bazie danych za jednym razem
        if files_to_update_duration:
            for path, dur in files_to_update_duration:
                database.update_file_duration(path, dur)

        self.app.file_selection_panel.populate_files(files_data)

    def _refresh_status_views(self, all_files):
        """Odświeża wszystkie panele statusu i panel transkrypcji."""
        # Filtruj pliki według statusu
        encoded_files = [row['file_path'] for row in all_files if row['status'] == 'encoded']
        processing_files = [row['file_path'] for row in all_files if row['status'] == 'processing']
        processed_files = [row['file_path'] for row in all_files if row['status'] == 'processed']

        # Zbierz wszystkie gotowe transkrypcje
        transcriptions = [row['transcription'] for row in all_files if row['status'] == 'processed' and row['transcription']]

        # Zaktualizuj widoki
        self.app.conversion_status_panel.update_from_list(encoded_files)
        self.app.transcription_queue_panel.update_from_list(processing_files)
        self.app.completed_files_panel.update_from_list(processed_files)
        self.app.transcription_output_panel.update_text("\n\n".join(transcriptions))