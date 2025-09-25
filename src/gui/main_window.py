import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import shutil
import os
import threading
from src import config

# Importowanie naszych niestandardowych komponentów GUI
from .files_view import FilesView
from .status_view import StatusView
from .transcription_view import TranscriptionView

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
        self.grid_columnconfigure(0, weight=4)
        self.grid_columnconfigure(1, weight=0)
        self.grid_columnconfigure(2, weight=0)
        self.grid_columnconfigure(3, weight=0)
        self.grid_columnconfigure(4, weight=3)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=0) # Row for the reset button

        # --- Button instances ---
        self.select_button = None
        self.load_button = None
        self.start_button = None
        self.pause_resume_button = None
        self.copy_button = None
        self.reset_button = None

        self.create_widgets()
        self._update_ui_from_file_state()

    def create_widgets(self):
        """Tworzy i umieszcza w oknie wszystkie komponenty interfejsu."""
        # --- Column 0: Selected Files ---
        select_frame = ttk.Frame(self)
        select_frame.grid(row=0, column=0, sticky="ew", padx=(10, 5), pady=(10, 0))
        select_frame.grid_columnconfigure(0, weight=1)
        self.select_button = ttk.Button(select_frame, text="Wybierz pliki", command=self.select_source_files)
        self.select_button.grid(row=0, column=0, sticky="ew")
        self.selected_files_view = FilesView(self, "Wybrane")
        self.selected_files_view.grid(row=1, column=0, sticky="nsew", padx=(10, 5), pady=5)

        # --- Column 1: Loaded Files ---
        load_frame = ttk.Frame(self)
        load_frame.grid(row=0, column=1, sticky="ew", padx=(10, 5), pady=(10, 0))
        load_frame.grid_columnconfigure(0, weight=1)
        self.load_button = ttk.Button(load_frame, text="Wczytaj Pliki", command=self.load_selected_files)
        self.load_button.grid(row=0, column=0, sticky="ew")
        self.loaded_files_view = StatusView(self, text="Wczytane")
        self.loaded_files_view.grid(row=1, column=1, sticky="nsew", padx=(10, 5), pady=5)

        # --- Column 2: To Process ---
        start_frame = ttk.Frame(self)
        start_frame.grid(row=0, column=2, sticky="ew", padx=5, pady=(10, 0))
        start_frame.grid_columnconfigure(0, weight=1)
        self.start_button = ttk.Button(start_frame, text="Start", command=self.start_transcription_process)
        self.start_button.grid(row=0, column=0, sticky="ew")
        self.processing_view = StatusView(self, text="Do przetworzenia")
        self.processing_view.grid(row=1, column=2, sticky="nsew", padx=5, pady=5)

        # --- Column 3: Processed ---
        pause_frame = ttk.Frame(self)
        pause_frame.grid(row=0, column=3, sticky="ew", padx=5, pady=(10, 0))
        pause_frame.grid_columnconfigure(0, weight=1)
        self.pause_resume_button = ttk.Button(pause_frame, text="Pauza", command=self.pause_transcription)
        self.pause_resume_button.grid(row=0, column=0, sticky="ew")
        self.processed_view = StatusView(self, text="Przetworzone")
        self.processed_view.grid(row=1, column=3, sticky="nsew", padx=5, pady=5)

        # --- Column 4: Transcription ---
        copy_frame = ttk.Frame(self)
        copy_frame.grid(row=0, column=4, sticky="ew", padx=(5, 10), pady=(10, 0))
        copy_frame.grid_columnconfigure(0, weight=1)
        self.copy_button = ttk.Button(copy_frame, text="Kopiuj Transkrypcję", command=self.copy_transcription_to_clipboard)
        self.copy_button.grid(row=0, column=0, sticky="ew")
        self.transcription_view = TranscriptionView(self, text="Transkrypcja")
        self.transcription_view.grid(row=1, column=4, sticky="nsew", padx=(5, 10), pady=5)

        # --- Row 2: Reset Button ---
        reset_frame = ttk.Frame(self)
        reset_frame.grid(row=2, column=0, columnspan=5, sticky="ew", padx=10, pady=(5, 10))
        reset_frame.grid_columnconfigure(0, weight=1)
        style = ttk.Style(self)
        style.configure("Red.TButton", foreground="white", background="red", borderwidth=0, relief="flat")
        style.map("Red.TButton",
            background=[('active', '#C00000'), ('pressed', '!disabled', '#C00000')]
        )
        self.reset_button = ttk.Button(reset_frame, text="Resetuj", command=self.reset_app_state, style="Red.TButton")
        self.reset_button.grid(row=0, column=1, sticky="e", ipady=5)

    def _get_list_content(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return [line.strip() for line in f.readlines() if line.strip()]
        except FileNotFoundError:
            return []

    def _refresh_all_views(self):
        # --- Selected Files (Wybrane) ---
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

        self.selected_files_view.populate_files(files_data)
        if error_files:
            messagebox.showwarning(
                "Błąd odczytu plików",
                "Nie udało się odczytać metadanych dla następujących plików (zostały pominięte):\n\n" + "\n".join(error_files)
            )

        # --- Pozostałe widoki ---
        self.loaded_files_view.update_from_file(config.LOADED_LIST)
        self.processing_view.update_from_file(config.PROCESSING_LIST)
        self.processed_view.update_from_file(config.PROCESSED_LIST)
        self.transcription_view.update_from_file(config.TRANSCRIPTIONS)

    def _update_ui_from_file_state(self):
        self._refresh_all_views()
        is_processing = self.processing_thread and self.processing_thread.is_alive()

        selected_list = self._get_list_content(config.SELECTED_LIST)
        to_transcribe_list = self._get_list_content(config.LOADED_LIST)
        processing_list = self._get_list_content(config.PROCESSING_LIST)
        processed_list = self._get_list_content(config.PROCESSED_LIST)

        self.select_button.config(state="disabled" if is_processing else "normal")
        self.load_button.config(state="normal" if selected_list and not to_transcribe_list and not is_processing else "disabled")
        self.reset_button.config(state="disabled" if is_processing else "normal")

        # Start button is enabled if there are loaded files and we are not already processing
        self.start_button.config(state="normal" if to_transcribe_list and not is_processing else "disabled")

        # Pause/Resume button logic
        is_paused = self.pause_request_event.is_set()

        self.pause_resume_button.config(state="disabled")
        self.pause_resume_button.config(text="Pauza")
        self.pause_resume_button.config(command=self.pause_transcription)

        if is_processing:
            self.pause_resume_button.config(state="normal")
            if is_paused:
                self.pause_resume_button.config(text="Wznów", command=self.resume_transcription)

        self.copy_button.config(state="normal")

    def select_source_files(self):
        if self.processing_thread and self.processing_thread.is_alive(): return
        paths = filedialog.askopenfilenames(title="Wybierz pliki audio", filetypes=[("Pliki audio", " ".join(config.AUDIO_EXTENSIONS))])
        if not paths: return

        with open(config.SELECTED_LIST, 'w', encoding='utf-8') as f:
            for p in paths: f.write(p + '\n')

        for f_path in [config.LOADED_LIST, config.PROCESSING_LIST, config.PROCESSED_LIST, config.TRANSCRIPTIONS]:
            if os.path.exists(f_path): os.remove(f_path)

        self._update_ui_from_file_state()

    def load_selected_files(self):
        self.load_button.config(state="disabled")
        self.update_idletasks()

        files_to_load = self.selected_files_view.get_checked_files()
        if not files_to_load:
            messagebox.showwarning("Brak plików", "Nie zaznaczono żadnych plików na liście 'Wybrane'.")
            self._update_ui_from_file_state()
            return

        # Save only checked files to a separate list for processing, 
        # but keep the original SELECTED_LIST intact
        files_to_process_list = os.path.join(config.TMP_DIR, 'files_to_process.txt')
        with open(files_to_process_list, 'w', encoding='utf-8') as f:
            for file_path in files_to_load:
                f.write(file_path + '\n')

        threading.Thread(target=self._load_files_worker, args=(files_to_process_list,), daemon=True).start()

    def _load_files_worker(self, files_to_process_list):
        try:
            # Temporarily use the files_to_process list for encoding
            original_selected = config.SELECTED_LIST
            config.SELECTED_LIST = files_to_process_list
            
            encode_audio_files()
            wav_files = sorted([os.path.join(config.OUTPUT_DIR, f) for f in os.listdir(config.OUTPUT_DIR) if f.endswith('.wav')])
            with open(config.LOADED_LIST, 'w', encoding='utf-8') as f:
                for path in wav_files: f.write(path + '\n')

            # Restore original selected list
            config.SELECTED_LIST = original_selected

            # Po załadowaniu, nie czyścimy już listy wybranych (SELECTED_LIST) – to źródło prawdy

            self.after(0, self._update_ui_from_file_state)
        except Exception as e:
            # Restore original selected list in case of error
            config.SELECTED_LIST = original_selected
            self.after(0, lambda: messagebox.showerror("Błąd konwersji", f"Wystąpił błąd: {e}"))
            self.after(0, self.reset_app_state)

    def start_transcription_process(self):
        # Merge "prepare_for_processing" logic into this method
        files = self._get_list_content(config.LOADED_LIST)
        if not files:
            messagebox.showwarning("Brak plików", "Brak plików do przetworzenia.")
            return
        with open(config.PROCESSING_LIST, 'w', encoding='utf-8') as f:
            for file in files: f.write(file + '\n')

        self._update_ui_from_file_state() # Refresh UI to show files in "Do przetworzenia"
        self.update_idletasks() # Ensure UI updates before starting the thread

        self.pause_request_event.clear()
        self.processing_thread = threading.Thread(target=self._transcription_thread_worker, daemon=True)
        self.processing_thread.start()
        self.monitor_processing()
        self._update_ui_from_file_state()

    def pause_transcription(self):
        self.pause_request_event.set()
        self._update_ui_from_file_state()

    def resume_transcription(self):
        self.pause_request_event.clear()
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
        if not messagebox.askokcancel("Potwierdzenie", "Czy na pewno chcesz zresetować aplikację? Cały stan zostanie usunięty."):
            return

        # Zatrzymaj monitorowanie, jeśli jest aktywne
        # (chociaż przycisk resetu jest wyłączony podczas przetwarzania, to jest to dodatkowe zabezpieczenie)
        if self.processing_thread:
            self.on_processing_finished()

        try:
            # Usuń cały folder tymczasowy, jeśli istnieje
            if os.path.exists(config.TMP_DIR):
                shutil.rmtree(config.TMP_DIR)

            # Utwórz ponownie wymagane foldery
            os.makedirs(config.OUTPUT_DIR, exist_ok=True)

            self._update_ui_from_file_state()
            messagebox.showinfo("Reset", "Aplikacja została zresetowana.")
        except Exception as e:
            messagebox.showerror("Błąd resetowania", f"Nie udało się zresetować aplikacji: {e}")
            # Spróbuj odtworzyć podstawową strukturę, aby aplikacja mogła kontynuować
            os.makedirs(config.OUTPUT_DIR, exist_ok=True)
            self._update_ui_from_file_state()

    def on_closing(self):
        if self.processing_thread and self.processing_thread.is_alive():
            if messagebox.askokcancel("Przetwarzanie w toku", "Proces jest aktywny. Czy na pewno chcesz wyjść?"):
                self.destroy()
        else:
            self.destroy()

def main():
    app = App()
    app.mainloop()