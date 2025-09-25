# Ten plik jest głównym punktem wejścia dla interfejsu graficznego.
# Jego zadaniem jest stworzenie głównego okna aplikacji i złożenie w nim
# wszystkich mniejszych komponentów (paneli, list, etc.).

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
from src.transcribe import TranscriptionProcessor

class App(tk.Tk):
    """
    Główna klasa aplikacji, dziedzicząca po tk.Tk.
    Odpowiada za inicjalizację okna, składanie komponentów i zarządzanie
    głównym stanem aplikacji.
    """
    def __init__(self):
        super().__init__()

        # --- Zmienne Stanu Aplikacji ---
        # W tej architekturze nie przechowujemy stanu w zmiennych,
        # a jedynie w plikach.

        # --- Konfiguracja Głównego Okna ---
        self.title(config.APP_NAME)
        self.minsize(1024, 600)
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Konfiguracja głównej siatki
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=1)
        self.grid_columnconfigure(3, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.create_widgets()
        self._refresh_all_views() # Odśwież widok na starcie

    def create_widgets(self):
        """Tworzy i umieszcza w oknie wszystkie komponenty interfejsu."""

        self.control_panel = ControlPanel(
            self,
            reset_command=self.reset_app_state,
            select_command=self.select_source_files,
            load_command=self.load_selected_files
        )
        self.control_panel.grid(row=0, column=0, columnspan=4, sticky="ew", padx=10, pady=(10, 0))

        self.files_view = FilesView(self)
        self.files_view.grid(row=1, column=0, sticky="nsew", padx=(10, 5), pady=5)

        self.processing_view = StatusView(self, text="Do przetworzenia")
        self.processing_view.grid(row=1, column=1, sticky="nsew", padx=5, pady=5)

        self.processed_view = StatusView(self, text="Przetworzone")
        self.processed_view.grid(row=1, column=2, sticky="nsew", padx=5, pady=5)

        self.transcription_view = TranscriptionView(self, text="Transkrypcja")
        self.transcription_view.grid(row=1, column=3, sticky="nsew", padx=(5, 10), pady=5)

        self.action_panel = ActionPanel(
            self,
            process_command=self.prepare_for_processing,
            start_command=self.start_transcription_process,
            copy_command=self.copy_transcription_to_clipboard
        )
        self.action_panel.grid(row=2, column=0, columnspan=4, sticky="ew", padx=10, pady=(5, 10))

    # --- Logika przepływu pracy ---

    def select_source_files(self):
        file_types = [("Pliki audio", " ".join(config.AUDIO_EXTENSIONS)), ("Wszystkie pliki", "*.*")]
        selected_paths = filedialog.askopenfilenames(title="Wybierz pliki audio", filetypes=file_types)
        if not selected_paths: return

        try:
            with open(config.AUDIO_LIST_TO_ENCODE_FILE, 'w', encoding='utf-8') as f:
                for path in selected_paths: f.write(path + '\n')

            self.control_panel.set_info_label(f"Wybrano {len(selected_paths)} plików. Kliknij 'Wczytaj'.")
            self.control_panel.set_button_state("load", "normal")
            self.control_panel.set_button_state("select", "disabled")
        except Exception as e:
            messagebox.showerror("Błąd zapisu", f"Nie można zapisać listy plików: {e}")

    def load_selected_files(self):
        self.control_panel.set_button_state("load", "disabled")
        self.control_panel.set_info_label("Wczytywanie i konwersja...")
        self.update_idletasks()

        try:
            encode_audio_files()
            wav_files = sorted([os.path.join(config.OUTPUT_DIR, f) for f in os.listdir(config.OUTPUT_DIR) if f.endswith('.wav')])
            with open(config.AUDIO_LIST_TO_TRANSCRIBE_FILE, 'w', encoding='utf-8') as f:
                for path in wav_files: f.write(path + '\n')

            self._refresh_all_views()
            self.control_panel.set_info_label("Pliki wczytane. Wybierz i zatwierdź.")
        except Exception as e:
            messagebox.showerror("Błąd podczas konwersji plików", f"Wystąpił błąd: {e}")
            self.reset_app_state()

    def prepare_for_processing(self):
        approved_files = self.files_view.get_checked_files()
        if not approved_files:
            messagebox.showwarning("Brak plików", "Nie zaznaczono żadnych plików do przetworzenia.")
            return

        try:
            with open(config.PROCESSING_LIST_FILE, 'w', encoding='utf-8') as f:
                for path in approved_files: f.write(path + '\n')

            self._refresh_all_views()
            messagebox.showinfo("Sukces", f"Zatwierdzono {len(approved_files)} plików do przetworzenia.")
        except Exception as e:
            messagebox.showerror("Błąd", f"Nie można zapisać listy do przetworzenia: {e}")

    def start_transcription_process(self):
        try:
            with open(config.PROCESSING_LIST_FILE, 'r', encoding='utf-8') as f:
                if not f.read().strip():
                    messagebox.showwarning("Brak plików", "Lista 'Do przetworzenia' jest pusta. Użyj przycisku 'Przetwórz'.")
                    return
        except FileNotFoundError:
            messagebox.showwarning("Brak plików", "Lista 'Do przetworzenia' nie istnieje. Użyj przycisku 'Przetwórz'.")
            return

        self.action_panel.set_button_state("process", "disabled")
        self.action_panel.set_button_state("start", "disabled")
        self.control_panel.set_button_state("reset", "disabled")

        processing_thread = threading.Thread(target=self._transcription_thread_worker, daemon=True)
        processing_thread.start()
        self.monitor_processing(processing_thread)

    def _transcription_thread_worker(self):
        try:
            processor = TranscriptionProcessor()
            processor.process_transcriptions()
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Błąd krytyczny", f"Wystąpił błąd: {e}"))
        finally:
            self.after(0, self.on_processing_finished)

    def monitor_processing(self, thread):
        if thread.is_alive():
            self._refresh_all_views()
            self.after(1000, lambda: self.monitor_processing(thread))
        else:
            self._refresh_all_views()

    def on_processing_finished(self):
        self._refresh_all_views()
        messagebox.showinfo("Koniec", "Przetwarzanie zakończone!")
        self.action_panel.set_button_state("start", "normal")
        self.action_panel.set_button_state("process", "normal")
        self.control_panel.set_button_state("reset", "normal")

    def copy_transcription_to_clipboard(self):
        text = self.transcription_view.get_text()
        if not text.strip():
            messagebox.showinfo("Informacja", "Brak tekstu do skopiowania.")
            return
        self.clipboard_clear()
        self.clipboard_append(text)
        messagebox.showinfo("Skopiowano", "Transkrypcja została skopiowana do schowka.")

    def _refresh_all_views(self):
        try:
            with open(config.AUDIO_LIST_TO_TRANSCRIBE_FILE, 'r', encoding='utf-8') as f:
                wav_files = [line.strip() for line in f.readlines()]
            files_data = [(path, get_file_duration(path)) for path in wav_files]
            self.files_view.populate_files(files_data)
        except FileNotFoundError:
            self.files_view.clear_view()

        self.processing_view.update_from_file(config.PROCESSING_LIST_FILE)
        self.processed_view.update_from_file(config.PROCESSED_LIST_FILE)
        self.transcription_view.update_from_file(config.TRANSCRIPTIONS_FILE)

    def reset_app_state(self):
        if not messagebox.askokcancel("Potwierdzenie", "Czy na pewno chcesz zresetować aplikację?"):
            return

        for f in [config.AUDIO_LIST_TO_ENCODE_FILE, config.AUDIO_LIST_TO_TRANSCRIBE_FILE, config.PROCESSING_LIST_FILE, config.PROCESSED_LIST_FILE, config.TRANSCRIPTIONS_FILE]:
            if os.path.exists(f): os.remove(f)

        self._refresh_all_views()

        self.control_panel.set_button_state("select", "normal")
        self.control_panel.set_button_state("load", "disabled")
        self.control_panel.set_info_label("Wybierz pliki audio")
        self.action_panel.set_button_state("start", "normal")
        self.action_panel.set_button_state("process", "normal")

        self.cleanup_temp_directory()
        os.makedirs(config.OUTPUT_DIR, exist_ok=True)
        messagebox.showinfo("Reset", "Aplikacja została zresetowana.")

    def cleanup_temp_directory(self):
        try:
            if os.path.exists(config.SESSION_TEMP_DIR):
                shutil.rmtree(config.SESSION_TEMP_DIR)
        except OSError as e:
            print(f"Błąd: {e.strerror}")

    def on_closing(self):
        if messagebox.askokcancel("Zamknij", "Czy na pewno chcesz zamknąć aplikację?"):
            self.cleanup_temp_directory()
            self.destroy()

def main():
    app = App()
    app.mainloop()