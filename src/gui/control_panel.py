# Ten plik zawiera komponent dla górnego panelu sterowania.
# Odpowiada za przyciski: Resetuj, Wybierz Foldery, Wczytaj Pliki.

import tkinter as tk
from tkinter import ttk

class ControlPanel(ttk.Frame):
    """
    Komponent GUI zawierający główne przyciski do sterowania aplikacją.
    """
    def __init__(self, parent, reset_command, select_command, load_command, **kwargs):
        """
        Inicjalizuje ramkę z przyciskami.

        Args:
            parent: Rodzic widgetu (główne okno aplikacji).
            reset_command (callable): Funkcja do wywołania po kliknięciu "Resetuj".
            select_command (callable): Funkcja do wywołania po kliknięciu "Wybierz Foldery".
            load_command (callable): Funkcja do wywołania po kliknięciu "Wczytaj Pliki".
        """
        super().__init__(parent, **kwargs)

        # Konfiguracja siatki wewnątrz komponentu - 4 równe kolumny
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=1)
        self.grid_columnconfigure(3, weight=1)

        # --- Przyciski ---
        self.reset_button = ttk.Button(self, text="Resetuj", command=reset_command)
        self.reset_button.grid(row=0, column=0, padx=5, sticky="ew")

        self.select_button = ttk.Button(self, text="Wybierz Foldery", command=select_command)
        self.select_button.grid(row=0, column=1, padx=5, sticky="ew")

        # Etykieta na informację o wybranym folderze lub liczbie plików
        self.info_label = ttk.Label(self, text="Wybierz folder z plikami audio")
        self.info_label.grid(row=0, column=2, padx=5)

        self.load_button = ttk.Button(self, text="Wczytaj Pliki", command=load_command, state="disabled")
        self.load_button.grid(row=0, column=3, padx=5, sticky="ew")

    def set_button_state(self, button_name, state):
        """
        Ustawia stan (aktywny/nieaktywny) wybranego przycisku.

        Args:
            button_name (str): Nazwa przycisku ("select", "load").
            state (str): "normal" lub "disabled".
        """
        if button_name == "select":
            self.select_button.config(state=state)
        elif button_name == "load":
            self.load_button.config(state=state)

    def set_info_label(self, text):
        """Ustawia tekst etykiety informacyjnej."""
        self.info_label.config(text=text)