import tkinter as tk
from tkinter import ttk

class ActionPanel(ttk.Frame):
    """
    Komponent GUI zawierający przyciski do uruchamiania głównych akcji,
    takich jak start transkrypcji, pauza i kopiowanie wyników.
    """
    def __init__(self, parent, process_command, start_command, pause_resume_command, copy_command, **kwargs):
        """
        Inicjalizuje ramkę z przyciskami.
        """
        super().__init__(parent, **kwargs)

        # Konfiguracja siatki wewnątrz komponentu
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=1)
        self.grid_columnconfigure(3, weight=1)
        self.grid_columnconfigure(4, weight=1)

        # --- Przyciski ---
        self.process_button = ttk.Button(self, text="Przetwórz", command=process_command)
        self.process_button.grid(row=0, column=0, padx=5, sticky="ew")

        self.start_button = ttk.Button(self, text="Start", command=start_command)
        self.start_button.grid(row=0, column=1, padx=5, sticky="ew")

        # Przycisk "Pauza/Wznów" - jego tekst i komenda będą zarządzane z zewnątrz
        self.pause_resume_button = ttk.Button(self, text="Pauza", command=pause_resume_command)
        self.pause_resume_button.grid(row=0, column=2, padx=5, sticky="ew")

        self.copy_button = ttk.Button(self, text="Kopiuj Transkrypcję", command=copy_command)
        self.copy_button.grid(row=0, column=4, padx=5, sticky="ew")

        # Kolekcja przycisków do łatwego zarządzania stanem
        self.buttons = {
            "process": self.process_button,
            "start": self.start_button,
            "pause_resume": self.pause_resume_button,
            "copy": self.copy_button
        }

    def set_button_state(self, button_name, state):
        """
        Ustawia stan (aktywny/nieaktywny) wybranego przycisku.
        """
        if button_name in self.buttons:
            self.buttons[button_name].config(state=state)

    def set_pause_resume_button_config(self, text, command):
        """
        Ustawia tekst i komendę dla przycisku pauzy/wznowienia.
        """
        self.pause_resume_button.config(text=text, command=command)

    def show_button(self, button_name, show=True):
        """
        Pokazuje lub ukrywa przycisk, usuwając go z siatki.
        """
        if button_name in self.buttons:
            if show:
                self.buttons[button_name].grid()
            else:
                self.buttons[button_name].grid_remove()