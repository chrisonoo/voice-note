import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import threading
import shutil
from src.audio import get_audio_file_list, encode_audio_files
from src.transcribe import TranscriptionProcessor
from src import config

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Transkrypcja Audio")
        self.geometry("1200x600")
        self.selected_folder = ""

        # Konfiguracja siatki
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=1)
        self.grid_columnconfigure(3, weight=1)
        self.grid_rowconfigure(2, weight=1) # Główny wiersz z listami

        self.create_widgets()
        self.update_lists() # Odśwież listy na starcie

    def create_widgets(self):
        # --- Wiersz 1: Panel Sterowania ---
        control_frame = ttk.Frame(self)
        control_frame.grid(row=0, column=0, columnspan=4, sticky="ew", padx=10, pady=10)
        for i in range(4):
            control_frame.grid_columnconfigure(i, weight=1)

        self.reset_button = ttk.Button(control_frame, text="Resetuj", command=self.reset_data)
        self.reset_button.grid(row=0, column=0, padx=5, sticky="ew")

        self.select_folders_button = ttk.Button(control_frame, text="Wybierz Foldery", command=self.select_folder)
        self.select_folders_button.grid(row=0, column=1, padx=5, sticky="ew")

        self.files_to_load_label = ttk.Label(control_frame, text="Pliki do wczytania: 0")
        self.files_to_load_label.grid(row=0, column=2, padx=5)

        self.load_files_button = ttk.Button(control_frame, text="Wczytaj Pliki", command=self.load_files)
        self.load_files_button.grid(row=0, column=3, padx=5, sticky="ew")

        # --- Wiersz 2: Panel Monitorowania ---
        # Etykiety dla list
        ttk.Label(self, text="Wczytane").grid(row=1, column=0, sticky="n", pady=(0,5))
        ttk.Label(self, text="Do przetworzenia").grid(row=1, column=1, sticky="n", pady=(0,5))
        ttk.Label(self, text="Przetworzone").grid(row=1, column=2, sticky="n", pady=(0,5))
        ttk.Label(self, text="Podgląd").grid(row=1, column=3, sticky="n", pady=(0,5))

        self.loaded_list = tk.Listbox(self)
        self.loaded_list.grid(row=2, column=0, sticky="nsew", padx=5, pady=5)

        self.processing_list = tk.Listbox(self)
        self.processing_list.grid(row=2, column=1, sticky="nsew", padx=5, pady=5)

        self.processed_list = tk.Listbox(self)
        self.processed_list.grid(row=2, column=2, sticky="nsew", padx=5, pady=5)

        self.preview_text = tk.Text(self, wrap="word")
        self.preview_text.grid(row=2, column=3, sticky="nsew", padx=5, pady=5)

        # --- Wiersz 3: Panel Akcji ---
        action_frame = ttk.Frame(self)
        action_frame.grid(row=3, column=0, columnspan=4, sticky="ew", padx=10, pady=10)
        action_frame.grid_columnconfigure(0, weight=1)
        action_frame.grid_columnconfigure(3, weight=1)

        self.start_button = ttk.Button(action_frame, text="Start", command=self.start_processing)
        self.start_button.grid(row=0, column=0, padx=5, sticky="ew")

        self.copy_text_button = ttk.Button(action_frame, text="Kopiuj Tekst", command=self.copy_to_clipboard)
        self.copy_text_button.grid(row=0, column=3, padx=5, sticky="ew")

    def select_folder(self):
        folder_path = filedialog.askdirectory()
        if folder_path:
            self.selected_folder = folder_path
            # Zlicz pliki i zaktualizuj etykietę
            try:
                files = [f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))]
                self.files_to_load_label.config(text=f"Pliki do wczytania: {len(files)}")
            except Exception as e:
                messagebox.showerror("Błąd", f"Nie można odczytać folderu: {e}")

    def load_files(self):
        if not self.selected_folder:
            messagebox.showwarning("Brak folderu", "Najpierw wybierz folder z plikami audio.")
            return

        try:
            get_audio_file_list(self.selected_folder)
            encode_audio_files()
            processor = TranscriptionProcessor()
            processor._prepare_transcription_list()
            self.update_lists()
            messagebox.showinfo("Sukces", "Pliki zostały wczytane i przygotowane do transkrypcji.")
        except Exception as e:
            messagebox.showerror("Błąd podczas ładowania", f"Wystąpił błąd: {e}")

    def reset_data(self):
        if messagebox.askokcancel("Potwierdzenie", "Czy na pewno chcesz zresetować wszystkie dane i usunąć przetworzone pliki?"):
            try:
                # Czyszczenie plików stanu
                open(config.AUDIO_LIST_TO_ENCODE_FILE, 'w').close()
                open(config.AUDIO_LIST_TO_TRANSCRIBE_FILE, 'w').close()
                open(config.PROCESSING_LIST_FILE, 'w').close()
                open(config.PROCESSED_LIST_FILE, 'w').close()
                open(config.TRANSCRIPTIONS_FILE, 'w').close()

                # Czyszczenie folderu output
                if os.path.exists(config.OUTPUT_DIR):
                    shutil.rmtree(config.OUTPUT_DIR)
                os.makedirs(config.OUTPUT_DIR)

                self.update_lists()
                self.files_to_load_label.config(text="Pliki do wczytania: 0")
                messagebox.showinfo("Reset", "Dane zostały zresetowane.")
            except Exception as e:
                messagebox.showerror("Błąd resetowania", f"Nie można zresetować danych: {e}")

    def start_processing(self):
        # Uruchomienie przetwarzania w osobnym wątku, aby nie blokować GUI
        processing_thread = threading.Thread(target=self._process_transcriptions_thread, daemon=True)
        processing_thread.start()
        self.monitor_processing(processing_thread)

    def _process_transcriptions_thread(self):
        try:
            processor = TranscriptionProcessor()
            processor.process_transcriptions()
        except Exception as e:
            messagebox.showerror("Błąd transkrypcji", f"Wystąpił krytyczny błąd: {e}", parent=self)

    def monitor_processing(self, thread):
        if thread.is_alive():
            self.update_lists()
            self.after(1000, lambda: self.monitor_processing(thread))
        else:
            self.update_lists()
            messagebox.showinfo("Koniec", "Przetwarzanie zakończone!")

    def update_lists(self):
        self._update_listbox(self.loaded_list, config.AUDIO_LIST_TO_TRANSCRIBE_FILE)
        self._update_listbox(self.processing_list, config.PROCESSING_LIST_FILE)
        self._update_listbox(self.processed_list, config.PROCESSED_LIST_FILE)
        self._update_textbox(self.preview_text, config.TRANSCRIPTIONS_FILE)

    def _update_listbox(self, listbox, file_path):
        listbox.delete(0, tk.END)
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        listbox.insert(tk.END, os.path.basename(line.strip()))
        except Exception as e:
            print(f"Błąd odczytu pliku {file_path}: {e}") # Log do konsoli

    def _update_textbox(self, textbox, file_path):
        textbox.delete('1.0', tk.END)
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    textbox.insert(tk.END, f.read())
        except Exception as e:
            print(f"Błąd odczytu pliku {file_path}: {e}") # Log do konsoli

    def copy_to_clipboard(self):
        self.clipboard_clear()
        self.clipboard_append(self.preview_text.get('1.0', tk.END))
        messagebox.showinfo("Skopiowano", "Zawartość podglądu została skopiowana do schowka.")

def main():
    app = App()
    app.mainloop()

if __name__ == "__main__":
    main()