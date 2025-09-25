# This module handles transcription process control

import os
import threading
from tkinter import messagebox
from src import config
from src.transcribe.transcription_processor import TranscriptionProcessor


class TranscriptionController:
    """
    Controls the transcription process.
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
    
    def start_transcription_process(self):
        """Start the transcription process."""
        # Merge "prepare_for_processing" logic into this method
        files = self._get_list_content(config.LOADED_LIST)
        if not files:
            messagebox.showwarning("Brak plików", "Brak plików do przetworzenia.")
            return
            
        # Ensure tmp directory exists before writing
        os.makedirs(os.path.dirname(config.PROCESSING_LIST), exist_ok=True)
        with open(config.PROCESSING_LIST, 'w', encoding='utf-8') as f:
            for file in files: 
                f.write(file + '\n')

        # Refresh UI to show files in "Do przetworzenia"
        self.app.ui_state_manager.update_ui_state()
        self.app.refresh_all_views()
        self.app.update_idletasks()  # Ensure UI updates before starting the thread

        self.app.pause_request_event.clear()
        self.app.processing_thread = threading.Thread(target=self._transcription_thread_worker, daemon=True)
        self.app.processing_thread.start()
        self.app.monitor_processing()
        self.app.ui_state_manager.update_ui_state()

    def pause_transcription(self):
        """Pause the transcription process."""
        self.app.pause_request_event.set()
        self.app.ui_state_manager.update_ui_state()

    def resume_transcription(self):
        """Resume the transcription process."""
        self.app.pause_request_event.clear()
        self.app.ui_state_manager.update_ui_state()

    def _transcription_thread_worker(self):
        """Worker thread for transcription processing."""
        try:
            processor = TranscriptionProcessor(self.app.pause_request_event)
            processor.process_transcriptions()
        except Exception as e:
            self.app.after(0, lambda: messagebox.showerror("Błąd krytyczny", f"Wystąpił błąd: {e}"))
        finally:
            self.app.after(0, self.app.on_processing_finished)


    def on_processing_finished(self):
        """Handle processing completion."""
        self.app.processing_thread = None
        self.app.pause_request_event.clear()
        self.app.ui_state_manager.update_ui_state()
        self.app.refresh_all_views()
