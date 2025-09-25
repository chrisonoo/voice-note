# Ten plik zawiera generyczny komponent dla list "Do przetworzenia" i "Przetworzone".
# Składa się z etykiety, listy oraz panelu z licznikiem.

import tkinter as tk
from tkinter import ttk
import os

class StatusView(ttk.Frame):
    """
    Komponent GUI wyświetlający listę plików w określonym stanie (np. do przetworzenia)
    wraz z dynamicznym licznikiem.
    """
    def __init__(self, parent, text, **kwargs):
        """
        Inicjalizuje ramkę.

        Args:
            parent: Rodzic widgetu (główne okno aplikacji).
            text (str): Etykieta do wyświetlenia nad listą (np. "Do przetworzenia").
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
        text_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        text_frame.grid_rowconfigure(0, weight=1)
        text_frame.grid_columnconfigure(0, weight=1)

        # Pole tekstowe
        self.text = tk.Text(text_frame, wrap="word", state="disabled", width=30, padx=8, pady=8, relief="sunken", borderwidth=1)
        self.text.grid(row=0, column=0, sticky="nsew")

        # --- Pasek przewijania ---
        scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=self.text.yview)
        self.text.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=0, column=1, sticky="ns")

        # Counter elements will be moved to main window level - removing from here

    def update_from_file(self, file_path):
        """Odczytuje plik tekstowy i wstawia jego zawartość do pola tekstowego, wyświetlając tylko nazwy plików."""
        self.text.config(state="normal")
        self.text.delete('1.0', tk.END)
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Przekształcenie pełnych ścieżek na nazwy plików
                    lines = content.strip().split('\n')
                    file_names = []
                    for line in lines:
                        line = line.strip()
                        if line:  # pomijamy puste linie
                            file_name = os.path.basename(line)
                            file_names.append(file_name)
                    
                    # Wstawienie nazw plików do pola tekstowego
                    self.text.insert(tk.END, '\n'.join(file_names))
        except Exception as e:
            print(f"Błąd odczytu pliku {file_path}: {e}")
        self.text.config(state="disabled")

    def clear_view(self):
        """Czyści pole tekstowe."""
        self.text.config(state="normal")
        self.text.delete('1.0', tk.END)
        self.text.config(state="disabled")