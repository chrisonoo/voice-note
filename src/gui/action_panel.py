# Ten plik zawiera komponent dla dolnego panelu akcji.
# Odpowiada za przyciski: Start, Kopiuj Tekst.

import tkinter as tk
from tkinter import ttk

class ActionPanel(ttk.Frame):
    """
    Komponent GUI zawierający przyciski do uruchamiania głównych akcji,
    takich jak start transkrypcji.
    """
    def __init__(self, parent, start_command, copy_command, **kwargs):
        """
        Inicjalizuje ramkę z przyciskami.

        Args:
            parent: Rodzic widgetu (główne okno aplikacji).
            start_command (callable): Funkcja do wywołania po kliknięciu "Start".
            copy_command (callable): Funkcja do wywołania po kliknięciu "Kopiuj Tekst".
        """
        super().__init__(parent, **kwargs)

        # Konfiguracja siatki wewnątrz komponentu
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1) # Pusty rozpychacz

        # --- Przyciski ---
        self.start_button = ttk.Button(self, text="Start", command=start_command)
        self.start_button.grid(row=0, column=0, padx=5, sticky="ew")

        self.copy_button = ttk.Button(self, text="Kopiuj Transkrypcję", command=copy_command)
        self.copy_button.grid(row=0, column=2, padx=5, sticky="ew")

    def set_button_state(self, button_name, state):
        """
        Ustawia stan (aktywny/nieaktywny) wybranego przycisku.

        Args:
            button_name (str): Nazwa przycisku ("start", "copy").
            state (str): "normal" lub "disabled".
        """
        if button_name == "start":
            self.start_button.config(state=state)
        elif button_name == "copy":
            self.copy_button.config(state=state)