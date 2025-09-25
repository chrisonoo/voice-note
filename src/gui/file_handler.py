# This module handles file operations (select, load, reset)

import os
import shutil
import threading
from tkinter import filedialog, messagebox
from src import config
from src.audio import encode_audio_files


class FileHandler:
    """
    Handles all file-related operations in the application workflow.
    Manages: file selection, audio conversion, and application state reset.
    Works with temporary file lists to track processing stages.
    """
    
    def __init__(self, app):
        self.app = app
    
    def select_source_files(self):
        """Select source audio files via file dialog."""
        if self.app.processing_thread and self.app.processing_thread.is_alive(): 
            return
            
        paths = filedialog.askopenfilenames(
            title="Wybierz pliki audio", 
            filetypes=[("Pliki audio", " ".join(config.AUDIO_EXTENSIONS))]
        )
        if not paths: 
            return

        # Ensure tmp directory exists before writing
        os.makedirs(os.path.dirname(config.SELECTED_LIST), exist_ok=True)
        with open(config.SELECTED_LIST, 'w', encoding='utf-8') as f:
            for p in paths: 
                f.write(p + '\n')

        # Clear other file lists
        for f_path in [config.LOADED_LIST, config.PROCESSING_LIST, config.PROCESSED_LIST, config.TRANSCRIPTIONS]:
            if os.path.exists(f_path): 
                os.remove(f_path)

        self.app.button_state_controller.update_ui_state()
        self.app.refresh_all_views()

    def load_selected_files(self):
        """Load selected files and convert them to WAV format."""
        self.app.convert_files_button.config(state="disabled")
        self.app.update_idletasks()

        files_to_load = self.app.file_selection_panel.get_checked_files()
        if not files_to_load:
            messagebox.showwarning("Brak plików", "Nie zaznaczono żadnych plików na liście 'Wybrane'.")
            self.app.button_state_controller.update_ui_state()
            return

        # Save only checked files to a separate list for processing, 
        # but keep the original SELECTED_LIST intact
        files_to_process_list = os.path.join(config.TMP_DIR, 'files_to_process.txt')
        with open(files_to_process_list, 'w', encoding='utf-8') as f:
            for file_path in files_to_load:
                f.write(file_path + '\n')

        threading.Thread(target=self._load_files_worker, args=(files_to_process_list,), daemon=True).start()

    def _load_files_worker(self, files_to_process_list):
        """Worker thread for loading files."""
        try:
            # Temporarily use the files_to_process list for encoding
            original_selected = config.SELECTED_LIST
            config.SELECTED_LIST = files_to_process_list
            
            encode_audio_files()
            wav_files = sorted([
                os.path.join(config.OUTPUT_DIR, f) 
                for f in os.listdir(config.OUTPUT_DIR) 
                if f.endswith('.wav')
            ])
            
            # Ensure tmp directory exists before writing
            os.makedirs(os.path.dirname(config.LOADED_LIST), exist_ok=True)
            with open(config.LOADED_LIST, 'w', encoding='utf-8') as f:
                for path in wav_files: 
                    f.write(path + '\n')

            # Restore original selected list
            config.SELECTED_LIST = original_selected

            self.app.after(0, self.app.button_state_controller.update_ui_state)
            self.app.after(0, self.app.refresh_all_views)
        except Exception as e:
            # Restore original selected list in case of error
            config.SELECTED_LIST = original_selected
            self.app.after(0, lambda: messagebox.showerror("Błąd konwersji", f"Wystąpił błąd: {e}"))
            self.app.after(0, self.reset_app_state)

    def reset_app_state(self):
        """Reset application state and clean up temporary files."""
        if self.app.processing_thread and self.app.processing_thread.is_alive():
            messagebox.showerror("Błąd", "Nie można zresetować aplikacji podczas przetwarzania.")
            return
            
        if not messagebox.askokcancel("Potwierdzenie", "Czy na pewno chcesz zresetować aplikację? Cały stan zostanie usunięty."):
            return

        # Stop monitoring if active
        if self.app.processing_thread:
            self.app.on_processing_finished()

        try:
            # Remove entire tmp directory if it exists
            if os.path.exists(config.TMP_DIR):
                shutil.rmtree(config.TMP_DIR)

            self.app.button_state_controller.update_ui_state()
            self.app.refresh_all_views()
            messagebox.showinfo("Reset", "Aplikacja została zresetowana.")
        except Exception as e:
            messagebox.showerror("Błąd resetowania", f"Nie udało się zresetować aplikacji: {e}")
            self.app.button_state_controller.update_ui_state()
            self.app.refresh_all_views()
