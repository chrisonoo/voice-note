# This module manages UI state (enabling/disabling buttons based on application state)

import os
from src import config


class UIStateManager:
    """
    Manages UI state - enables/disables buttons based on application state and file contents.
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

        # Enable/disable buttons based on state
        self.app.select_button.config(state="disabled" if is_processing else "normal")
        self.app.load_button.config(state="normal" if selected_list and not to_transcribe_list and not is_processing else "disabled")
        self.app.reset_button.config(state="disabled" if is_processing else "normal")

        # Start button is enabled if there are loaded files and we are not already processing
        self.app.start_button.config(state="normal" if to_transcribe_list and not is_processing else "disabled")

        # Pause/Resume button logic
        is_paused = self.app.pause_request_event.is_set()

        self.app.pause_resume_button.config(state="disabled")
        self.app.pause_resume_button.config(text="Pauza")
        self.app.pause_resume_button.config(command=self.app.pause_transcription)

        if is_processing:
            self.app.pause_resume_button.config(state="normal")
            if is_paused:
                self.app.pause_resume_button.config(text="Wznów", command=self.app.resume_transcription)

        self.app.copy_button.config(state="normal")
