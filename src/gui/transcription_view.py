# Ten plik zawiera komponent dla pola "Transkrypcja".
# Składa się z etykiety, pola tekstowego i paska przewijania.

import tkinter as tk
from tkinter import ttk
import os

class TranscriptionView(ttk.Frame):
    """
    Komponent GUI wyświetlający wynikową transkrypcję.
    """
    def __init__(self, parent, text, **kwargs):
        """
        Inicjalizuje ramkę.

        Args:
            parent: Rodzic widgetu (główne okno aplikacji).
            text (str): Etykieta do wyświetlenia nad polem tekstowym.
        """
        super().__init__(parent, **kwargs)

        # Konfiguracja siatki wewnątrz komponentu
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Etykieta
        self.label = ttk.Label(self, text=text, anchor="center")
        self.label.grid(row=0, column=0, sticky="ew", pady=(0, 5))

        # --- Ramka dla pola tekstowego i paska przewijania ---
        text_frame = ttk.Frame(self)
        text_frame.grid(row=1, column=0, sticky="nsew")
        text_frame.grid_rowconfigure(0, weight=1)
        text_frame.grid_columnconfigure(0, weight=1)

        # Pole tekstowe
        self.text = tk.Text(text_frame, wrap="word", state="disabled")
        self.text.grid(row=0, column=0, sticky="nsew")

        # --- Pasek przewijania ---
        scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=self.text.yview)
        self.text.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=0, column=1, sticky="ns")

    def update_from_file(self, file_path):
        """Odczytuje plik tekstowy i wstawia jego zawartość do pola tekstowego."""
        self.text.config(state="normal")
        self.text.delete('1.0', tk.END)
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    self.text.insert(tk.END, f.read())
        except Exception as e:
            print(f"Błąd odczytu pliku {file_path}: {e}")
        self.text.config(state="disabled")

    def get_text(self):
        """Zwraca całą zawartość pola tekstowego."""
        return self.text.get("1.0", tk.END)

    def clear_view(self):
        """Czyści pole tekstowe."""
        self.text.config(state="normal")
        self.text.delete('1.0', tk.END)
        self.text.config(state="disabled")