import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import shutil
import os
import threading
from src import config

# Importowanie naszych niestandardowych komponentów GUI
from .control_panel import ControlPanel
from .files_view import FilesView
from .status_view import StatusView
from .transcription_view import TranscriptionView
from .action_panel import ActionPanel

# Importowanie logiki biznesowej
from src.audio import get_file_duration, encode_audio_files
from src.transcribe.transcription_processor import TranscriptionProcessor

class App(tk.Tk):
    """
    Główna klasa aplikacji, dziedzicząca po tk.Tk.
    Odpowiada za inicjalizację okna, składanie komponentów i zarządzanie
    głównym stanem aplikacji.
    """
    def __init__(self):
        super().__init__()

        # --- Zmienne Stanu Aplikacji ---
        self.processing_thread = None
        self.pause_request_event = threading.Event()

        # --- Konfiguracja Głównego Okna ---
        self.title(config.APP_NAME)
        self.minsize(1024, 600)
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Konfiguracja głównej siatki
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=1)
        self.grid_columnconfigure(3, weight=1)
        self.grid_columnconfigure(4, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.create_widgets()
        self._update_ui_from_file_state()

    def create_widgets(self):
        """Tworzy i umieszcza w oknie wszystkie komponenty interfejsu."""
        self.control_panel = ControlPanel(
            self,
            reset_command=self.reset_app_state,
            select_command=self.select_source_files,
            load_command=self.load_selected_files
        )
        self.control_panel.grid(row=0, column=0, columnspan=5, sticky="ew", padx=10, pady=(10, 0))

        self.selected_files_view = FilesView(self, "Wybrane")
        self.selected_files_view.grid(row=1, column=0, sticky="nsew", padx=(10, 5), pady=5)

        self.loaded_files_view = FilesView(self, "Wczytane")
        self.loaded_files_view.grid(row=1, column=1, sticky="nsew", padx=(10, 5), pady=5)

        self.processing_view = StatusView(self, text="Do przetworzenia")
        self.processing_view.grid(row=1, column=2, sticky="nsew", padx=5, pady=5)

        self.processed_view = StatusView(self, text="Przetworzone")
        self.processed_view.grid(row=1, column=3, sticky="nsew", padx=5, pady=5)

        self.transcription_view = TranscriptionView(self, text="Transkrypcja")
        self.transcription_view.grid(row=1, column=4, sticky="nsew", padx=(5, 10), pady=5)

        self.action_panel = ActionPanel(
            self,
            process_command=self.prepare_for_processing,
            start_command=self.start_transcription_process,
            pause_resume_command=self.pause_transcription,
            copy_command=self.copy_transcription_to_clipboard
        )
        self.action_panel.grid(row=2, column=0, columnspan=5, sticky="ew", padx=10, pady=(5, 10))

    def _get_list_content(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return [line.strip() for line in f.readlines() if line.strip()]
        except FileNotFoundError:
            return []

    def _refresh_all_views(self):
        self.selected_files_view.populate_files([(path, get_file_duration(path)) for path in self._get_list_content(config.SELECTED_AUDIO_FILES_LIST)])
        self.loaded_files_view.populate_files([(path, get_file_duration(path)) for path in self._get_list_content(config.AUDIO_LIST_TO_TRANSCRIBE_FILE)])
        self.processing_view.update_from_file(config.PROCESSING_LIST_FILE)
        self.processed_view.update_from_file(config.PROCESSED_LIST_FILE)
        self.transcription_view.update_from_file(config.TRANSCRIPTIONS_FILE)

    def _update_ui_from_file_state(self):
        self._refresh_all_views()
        is_processing = self.processing_thread and self.processing_thread.is_alive()

        selected_list = self._get_list_content(config.SELECTED_AUDIO_FILES_LIST)
        to_transcribe_list = self._get_list_content(config.AUDIO_LIST_TO_TRANSCRIBE_FILE)
        processing_list = self._get_list_content(config.PROCESSING_LIST_FILE)
        processed_list = self._get_list_content(config.PROCESSED_LIST_FILE)

        self.control_panel.set_button_state("select", "disabled" if is_processing else "normal")
        self.control_panel.set_button_state("load", "normal" if selected_list and not to_transcribe_list and not is_processing else "disabled")
        self.control_panel.set_button_state("reset", "disabled" if is_processing else "normal")

        self.action_panel.set_button_state("process", "normal" if to_transcribe_list and not processing_list and not is_processing else "disabled")

        is_ready_to_start = processing_list and not processed_list
        is_paused = processing_list and processed_list

        # Domyślny stan przycisków (aplikacja bezczynna)
        self.action_panel.set_button_state("start", "normal" if is_ready_to_start else "disabled")
        self.action_panel.show_button("pause_resume", False)
        self.action_panel.set_button_state("pause_resume", "disabled")
        self.action_panel.set_pause_resume_button_config("Pauza", self.pause_transcription)

        # Stan: Wstrzymano
        if is_paused:
            self.action_panel.set_button_state("start", "disabled")
            self.action_panel.show_button("pause_resume", True)
            self.action_panel.set_button_state("pause_resume", "normal")
            self.action_panel.set_pause_resume_button_config("Wznów", self.start_transcription_process)

        # Stan: Przetwarzanie (nadpisuje stan wstrzymania, jeśli aktywny)
        if is_processing:
            self.action_panel.set_button_state("start", "disabled")
            self.action_panel.show_button("pause_resume", True)
            self.action_panel.set_button_state("pause_resume", "normal")
            self.action_panel.set_pause_resume_button_config("Pauza", self.pause_transcription)

        self.action_panel.set_button_state("copy", "normal")

    def select_source_files(self):
        if self.processing_thread and self.processing_thread.is_alive(): return
        paths = filedialog.askopenfilenames(title="Wybierz pliki audio", filetypes=[("Pliki audio", " ".join(config.AUDIO_EXTENSIONS))])
        if not paths: return

        self.control_panel.set_info_label(f"Wybrano plików: {len(paths)}")

        with open(config.SELECTED_AUDIO_FILES_LIST, 'w', encoding='utf-8') as f:
            for p in paths: f.write(p + '\n')

        for f_path in [config.AUDIO_LIST_TO_ENCODE_FILE, config.AUDIO_LIST_TO_TRANSCRIBE_FILE, config.PROCESSING_LIST_FILE, config.PROCESSED_LIST_FILE, config.TRANSCRIPTIONS_FILE]:
            if os.path.exists(f_path): os.remove(f_path)

        self._update_ui_from_file_state()

    def load_selected_files(self):
        self.control_panel.set_button_state("load", "disabled")
        self.update_idletasks()

        files_to_load = self.selected_files_view.get_checked_files()
        if not files_to_load:
            messagebox.showwarning("Brak plików", "Nie zaznaczono żadnych plików na liście 'Wybrane'.")
            self._update_ui_from_file_state()
            return

        with open(config.AUDIO_LIST_TO_ENCODE_FILE, 'w', encoding='utf-8') as f:
            for file_path in files_to_load:
                f.write(file_path + '\n')

        threading.Thread(target=self._load_files_worker, daemon=True).start()

    def _load_files_worker(self):
        try:
            encode_audio_files()
            wav_files = sorted([os.path.join(config.OUTPUT_DIR, f) for f in os.listdir(config.OUTPUT_DIR) if f.endswith('.wav')])
            with open(config.AUDIO_LIST_TO_TRANSCRIBE_FILE, 'w', encoding='utf-8') as f:
                for path in wav_files: f.write(path + '\n')

            # Po załadowaniu, czyścimy listę wybranych plików, aby uniknąć ponownego ładowania
            if os.path.exists(config.SELECTED_AUDIO_FILES_LIST):
                os.remove(config.SELECTED_AUDIO_FILES_LIST)
            if os.path.exists(config.AUDIO_LIST_TO_ENCODE_FILE):
                os.remove(config.AUDIO_LIST_TO_ENCODE_FILE)

            self.after(0, self._update_ui_from_file_state)
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Błąd konwersji", f"Wystąpił błąd: {e}"))
            self.after(0, self.reset_app_state)

    def prepare_for_processing(self):
        files = self.loaded_files_view.get_checked_files()
        if not files:
            messagebox.showwarning("Brak plików", "Nie zaznaczono żadnych plików.")
            return
        with open(config.PROCESSING_LIST_FILE, 'w', encoding='utf-8') as f:
            for file in files: f.write(file + '\n')
        self._update_ui_from_file_state()

    def start_transcription_process(self):
        self.pause_request_event.clear()
        self.processing_thread = threading.Thread(target=self._transcription_thread_worker, daemon=True)
        self.processing_thread.start()
        self.monitor_processing()
        self._update_ui_from_file_state()

    def pause_transcription(self):
        self.pause_request_event.set()
        self._update_ui_from_file_state()

    def _transcription_thread_worker(self):
        try:
            processor = TranscriptionProcessor(self.pause_request_event)
            processor.process_transcriptions()
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Błąd krytyczny", f"Wystąpił błąd: {e}"))
        finally:
            self.after(0, self.on_processing_finished)

    def monitor_processing(self):
        if self.processing_thread and self.processing_thread.is_alive():
            self._update_ui_from_file_state()
            self.after(1000, self.monitor_processing)
        else:
            self.on_processing_finished()

    def on_processing_finished(self):
        self.processing_thread = None
        self.pause_request_event.clear()
        self._update_ui_from_file_state()

    def copy_transcription_to_clipboard(self):
        text = self.transcription_view.get_text()
        if not text.strip():
            messagebox.showinfo("Informacja", "Brak tekstu do skopiowania.")
            return
        self.clipboard_clear()
        self.clipboard_append(text)
        messagebox.showinfo("Skopiowano", "Transkrypcja została skopiowana do schowka.")

    def reset_app_state(self):
        if self.processing_thread and self.processing_thread.is_alive():
            messagebox.showerror("Błąd", "Nie można zresetować aplikacji podczas przetwarzania.")
            return
        if not messagebox.askokcancel("Potwierdzenie", "Czy na pewno chcesz zresetować aplikację?"):
            return

        for f in [config.SELECTED_AUDIO_FILES_LIST, config.AUDIO_LIST_TO_ENCODE_FILE, config.AUDIO_LIST_TO_TRANSCRIBE_FILE, config.PROCESSING_LIST_FILE, config.PROCESSED_LIST_FILE, config.TRANSCRIPTIONS_FILE]:
            if os.path.exists(f): os.remove(f)

        self.cleanup_temp_directory()
        os.makedirs(config.OUTPUT_DIR, exist_ok=True)

        self._update_ui_from_file_state()
        messagebox.showinfo("Reset", "Aplikacja została zresetowana.")

    def cleanup_temp_directory(self):
        try:
            if os.path.exists(config.TMP_DIR):
                shutil.rmtree(config.TMP_DIR)
        except OSError as e:
            print(f"Błąd podczas czyszczenia folderu tymczasowego: {e.strerror}")

    def on_closing(self):
        if self.processing_thread and self.processing_thread.is_alive():
            if messagebox.askokcancel("Przetwarzanie w toku", "Proces jest aktywny. Czy na pewno chcesz wyjść?"):
                self.destroy()
        else:
            self.destroy()

def main():
    app = App()
    app.mainloop()