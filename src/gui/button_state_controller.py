# This module manages UI state (enabling/disabling buttons based on application state)

import os
from src import config


class ButtonStateController:
    """
    Controls button states throughout the application workflow.
    Enables/disables buttons based on current processing state and file availability.
    Ensures proper user flow: Select → Convert → Transcribe → Copy/Reset
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
    
    def update_ui_state(self):
        """Update UI state based on current application state and file contents."""
        is_processing = self.app.processing_thread and self.app.processing_thread.is_alive()

        selected_list = self._get_list_content(config.SELECTED_LIST)
        to_transcribe_list = self._get_list_content(config.LOADED_LIST)
        processing_list = self._get_list_content(config.PROCESSING_LIST)
        processed_list = self._get_list_content(config.PROCESSED_LIST)

        # Enable/disable buttons based on current application state
        self.app.file_selector_button.config(state="disabled" if is_processing else "normal")
        self.app.convert_files_button.config(state="normal" if selected_list and not to_transcribe_list and not is_processing else "disabled")
        self.app.reset_application_button.config(state="disabled" if is_processing else "normal")

        # Transcription start button is enabled if there are loaded files and we are not already processing
        self.app.start_transcription_button.config(state="normal" if to_transcribe_list and not is_processing else "disabled")

        # Transcription control button (pause/resume) logic
        is_paused = self.app.pause_request_event.is_set()

        self.app.transcription_control_button.config(state="disabled")
        self.app.transcription_control_button.config(text="Pauza")
        self.app.transcription_control_button.config(command=self.app.pause_transcription)

        if is_processing:
            self.app.transcription_control_button.config(state="normal")
            if is_paused:
                self.app.transcription_control_button.config(text="Wznów", command=self.app.resume_transcription)

        # Copy transcription button is always enabled (shows info if no text)
        self.app.copy_transcription_button.config(state="normal")
