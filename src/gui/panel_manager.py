# This module manages view updates and data refresh

import os
from tkinter import messagebox
from src import config
from src.audio import get_file_duration


class PanelManager:
    """
    Manages data panel updates and view refreshing throughout the application.
    Coordinates updates across all 5 main panels: file selection, conversion status,
    transcription queue, completed files, and transcription output.
    """
    
    def __init__(self, app):
        self.app = app
    
    def _get_list_content(self, file_path):
        """Read file content and return list of lines."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return [line.strip() for line in f.readlines() if line.strip()]
        except FileNotFoundError:
            return []

    def refresh_all_views(self):
        """Refresh all views with current data."""
        self._refresh_selected_files_view()
        self._refresh_status_views()

    def _refresh_selected_files_view(self):
        """Refresh selected files view with duration information."""
        files_data = []
        error_files = []
        selected_files = self._get_list_content(config.SELECTED_LIST)
        print(f"DEBUG: Znaleziono {len(selected_files)} plików w {config.SELECTED_LIST}")

        for path in selected_files:
            print(f"DEBUG: Przetwarzam plik: {path}")
            try:
                duration = get_file_duration(path)
                files_data.append((path, duration))
                print(f"DEBUG: Czas trwania: {duration}s")
            except Exception as e:
                error_files.append(os.path.basename(path))
                print(f"Could not get duration for file {path}: {e}")
                files_data.append((path, 0.0))

        self.app.file_selection_panel.populate_files(files_data)
        if error_files:
            messagebox.showwarning(
                "Błąd odczytu plików",
                "Nie udało się odczytać metadanych dla następujących plików (zostały pominięte):\n\n" + "\n".join(error_files)
            )

    def _refresh_status_views(self):
        """Refresh all status views."""
        self.app.conversion_status_panel.update_from_file(config.LOADED_LIST)
        self.app.transcription_queue_panel.update_from_file(config.PROCESSING_LIST)
        self.app.completed_files_panel.update_from_file(config.PROCESSED_LIST)
        self.app.transcription_output_panel.update_from_file(config.TRANSCRIPTIONS)
