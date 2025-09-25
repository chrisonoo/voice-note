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
from src.audio import get_file_duration, create_audio_file_list, encode_audio_files
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
        self.source_file_paths = [] # Lista ścieżek do plików wybranych przez użytkownika

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

    def create_widgets(self):
        """Tworzy i umieszcza w oknie wszystkie komponenty interfejsu."""

        # --- Wiersz 0: Panel Sterowania ---
        self.control_panel = ControlPanel(
            self,
            reset_command=self.reset_app_state,
            select_command=self.select_source_folder,
            load_command=self.load_files_to_view
        )
        self.control_panel.grid(row=0, column=0, columnspan=4, sticky="ew", padx=10, pady=(10, 0))

        # --- Wiersz 1: Główne widoki ---
        self.files_view = FilesView(self)
        self.files_view.grid(row=1, column=0, sticky="nsew", padx=(10, 5), pady=5)

        self.processing_view = StatusView(self, text="Do przetworzenia")
        self.processing_view.grid(row=1, column=1, sticky="nsew", padx=5, pady=5)

        self.processed_view = StatusView(self, text="Przetworzone")
        self.processed_view.grid(row=1, column=2, sticky="nsew", padx=5, pady=5)

        self.transcription_view = TranscriptionView(self, text="Transkrypcja")
        self.transcription_view.grid(row=1, column=3, sticky="nsew", padx=(5, 10), pady=5)

        # --- Wiersz 2: Panel Akcji ---
        # Umieszczamy go w drugim wierszu, aby był bezpośrednio pod listami.
        # `columnspan=4` sprawia, że rozciąga się na wszystkie kolumny.
        self.action_panel = ActionPanel(
            self,
            start_command=self.start_transcription_process,
            copy_command=self.copy_transcription_to_clipboard
        )
        self.action_panel.grid(row=2, column=0, columnspan=4, sticky="ew", padx=10, pady=(5, 10))

    # --- Metody związane z Panelem Sterowania ---

    def select_source_folder(self):
        """Otwiera okno dialogowe, zlicza pliki i przygotowuje do wczytania."""
        folder_path = filedialog.askdirectory(title="Wybierz folder z plikami audio")
        if not folder_path:
            return

        try:
            # Zlicz pliki pasujące do rozszerzeń, ale ich nie wczytuj
            self.source_file_paths = [
                os.path.join(folder_path, f)
                for f in os.listdir(folder_path)
                if os.path.isfile(os.path.join(folder_path, f)) and \
                   os.path.splitext(f)[1].lower() in config.AUDIO_EXTENSIONS
            ]

            if not self.source_file_paths:
                messagebox.showwarning("Brak plików", "Wybrany folder nie zawiera żadnych obsługiwanych plików audio.")
                self.control_panel.set_info_label("Nie znaleziono plików.")
                self.control_panel.set_button_state("load", "disabled")
                return

            # Zaktualizuj etykietę i aktywuj przycisk "Wczytaj Pliki"
            self.control_panel.set_info_label(f"Znaleziono {len(self.source_file_paths)} plików. Kliknij 'Wczytaj'.")
            self.control_panel.set_button_state("load", "normal")
            # Wyczyść listę "Wczytane", jeśli były na niej jakieś pliki z poprzedniej sesji
            self.files_view.clear_view()

        except Exception as e:
            messagebox.showerror("Błąd odczytu folderu", f"Wystąpił błąd: {e}")
            self.control_panel.set_button_state("load", "disabled")

    def load_files_to_view(self):
        """
        Kopiuje wybrane pliki do folderu tymczasowego, standaryzuje ich nazwy,
        pobiera metadane i wyświetla je na liście "Wczytane".
        """
        self.control_panel.set_button_state("select", "disabled")
        self.control_panel.set_button_state("load", "disabled")
        self.control_panel.set_info_label("Wczytywanie plików...")

        files_with_durations = []
        try:
            for source_path in self.source_file_paths:
                filename = os.path.basename(source_path)
                standardized_name = self._standardize_filename(filename)
                dest_path = os.path.join(config.SESSION_TEMP_DIR, standardized_name)

                # Kopiowanie pliku do folderu tymczasowego
                shutil.copy(source_path, dest_path)

                # Pobieranie czasu trwania ze skopiowanego pliku
                duration = get_file_duration(dest_path)
                files_with_durations.append((dest_path, duration))

            # Wypełnienie listy "Wczytane" danymi z plików w folderze tymczasowym
            self.files_view.populate_files(files_with_durations)
            self.control_panel.set_info_label("Pliki gotowe do przetworzenia.")
            self.update_status_lists()

        except Exception as e:
            messagebox.showerror("Błąd podczas wczytywania plików", f"Wystąpił błąd: {e}")
            self.reset_app_state()

    def _standardize_filename(self, filename):
        """Konwertuje nazwę pliku na małe litery i zamienia spacje na podkreślenia."""
        name, ext = os.path.splitext(filename)
        return f"{name.lower().replace(' ', '_')}{ext}"

    # --- Metody związane z Panelem Akcji ---

    def start_transcription_process(self):
        approved_files = self.files_view.get_checked_files()
        if not approved_files:
            messagebox.showwarning("Brak plików", "Nie wybrano żadnych plików do transkrypcji.")
            return

        self.action_panel.set_button_state("start", "disabled")
        self.control_panel.set_button_state("reset", "disabled")

        processing_thread = threading.Thread(
            target=self._transcription_thread_worker,
            args=(approved_files,),
            daemon=True
        )
        processing_thread.start()
        self.monitor_processing(processing_thread)

    def _transcription_thread_worker(self, files_to_process):
        try:
            create_audio_file_list(files_to_process)
            encode_audio_files()

            processor = TranscriptionProcessor()
            # Ten krok jest kluczowy: tworzymy listę plików .wav do transkrypcji
            # i kopiujemy ją do pliku `processing_list`, który jest monitorowany przez GUI.
            processor._prepare_transcription_list()

            # Teraz uruchamiamy właściwą pętlę transkrypcji
            processor.process_transcriptions()
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Błąd krytyczny", f"Wystąpił błąd w procesie transkrypcji: {e}"))
        finally:
            self.after(0, self.on_processing_finished)

    def monitor_processing(self, thread):
        if thread.is_alive():
            self.update_status_lists()
            self.transcription_view.update_from_file(config.TRANSCRIPTIONS_FILE)
            self.after(1000, lambda: self.monitor_processing(thread))

    def on_processing_finished(self):
        self.update_status_lists(processing_done=True)
        self.transcription_view.update_from_file(config.TRANSCRIPTIONS_FILE)
        messagebox.showinfo("Koniec", "Przetwarzanie zakończone!")
        self.action_panel.set_button_state("start", "normal")
        self.control_panel.set_button_state("reset", "normal")

    def copy_transcription_to_clipboard(self):
        text_to_copy = self.transcription_view.get_text()
        if not text_to_copy.strip():
            messagebox.showinfo("Informacja", "Brak tekstu do skopiowania.")
            return
        self.clipboard_clear()
        self.clipboard_append(text_to_copy)
        messagebox.showinfo("Skopiowano", "Transkrypcja została skopiowana do schowka.")

    # --- Metody Pomocnicze i Zarządzania Stanem ---

    def update_status_lists(self, processing_done=False):
        if not processing_done:
            approved_files = self.files_view.get_checked_files()
            with open(config.PROCESSING_LIST_FILE, 'w', encoding='utf-8') as f:
                for path in approved_files: f.write(path + '\n')

        self.processing_view.update_from_file(config.PROCESSING_LIST_FILE)
        self.processed_view.update_from_file(config.PROCESSED_LIST_FILE)

    def reset_app_state(self):
        print("Resetowanie stanu aplikacji...")
        self.source_file_paths = []

        self.files_view.clear_view()
        self.processing_view.clear_view()
        self.processed_view.clear_view()
        self.transcription_view.clear_view()

        self.control_panel.set_button_state("select", "normal")
        self.control_panel.set_button_state("load", "disabled")
        self.control_panel.set_info_label("Wybierz folder z plikami audio")
        self.action_panel.set_button_state("start", "normal")

        self.cleanup_temp_directory()
        os.makedirs(config.OUTPUT_DIR, exist_ok=True)
        messagebox.showinfo("Reset", "Aplikacja została zresetowana.")

    def cleanup_temp_directory(self):
        try:
            if os.path.exists(config.SESSION_TEMP_DIR):
                shutil.rmtree(config.SESSION_TEMP_DIR)
                print(f"Usunięto folder tymczasowy: {config.SESSION_TEMP_DIR}")
        except OSError as e:
            print(f"Błąd podczas usuwania folderu tymczasowego: {e.strerror}")

    def on_closing(self):
        if messagebox.askokcancel("Zamknij", "Czy na pewno chcesz zamknąć aplikację?"):
            self.cleanup_temp_directory()
            self.destroy()

def main():
    """Główna funkcja uruchamiająca aplikację GUI."""
    app = App()
    app.mainloop()