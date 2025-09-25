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

        # --- Ramka dla Listbox i paska przewijania ---
        list_frame = ttk.Frame(self)
        list_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        list_frame.grid_rowconfigure(0, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)

        # Lista
        self.listbox = tk.Listbox(list_frame, width=30, relief="sunken", borderwidth=1)
        self.listbox.grid(row=0, column=0, sticky="nsew")

        # --- Pasek przewijania ---
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=0, column=1, sticky="ns")

        # Counter elements will be moved to main window level - removing from here

    def update_from_file(self, file_path):
        """
        Odczytuje plik tekstowy i aktualizuje listę, wyświetlając tylko nazwy plików.
        """
        self.listbox.delete(0, tk.END)
        count = 0
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        self.listbox.insert(tk.END, os.path.basename(line.strip()))
                        count += 1
        except Exception as e:
            print(f"Błąd odczytu pliku {file_path}: {e}")

        # Counter label moved to main window - accessing through parent
        if hasattr(self.master, 'update_status_counter'):
            self.master.update_status_counter(self, count)

    def clear_view(self):
        """Czyści listę i resetuje licznik."""
        self.listbox.delete(0, tk.END)
        # Counter label moved to main window - accessing through parent
        if hasattr(self.master, 'update_status_counter'):
            self.master.update_status_counter(self, 0)