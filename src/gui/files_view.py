# Ten plik zawiera komponent dla listy "Wczytane".
# Używa zaawansowanego widżetu ttk.Treeview do wyświetlania plików
# w kolumnach, wraz z checkboxami, nazwą i czasem trwania.

import tkinter as tk
from tkinter import ttk
import os
from src import config

class FilesView(ttk.Frame):
    """
    Komponent GUI wyświetlający listę plików wybranych przez użytkownika.
    """
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)

        # Konfiguracja siatki wewnątrz komponentu
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Etykieta
        self.label = ttk.Label(self, text="Wczytane", anchor="center")
        self.label.grid(row=0, column=0, sticky="ew", pady=(0, 5))

        # --- Ramka dla Treeview i paska przewijania ---
        tree_frame = ttk.Frame(self)
        tree_frame.grid(row=1, column=0, sticky="nsew")
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        # --- Widżet Treeview do wyświetlania plików ---
        self.tree = ttk.Treeview(
            tree_frame,
            columns=("checked", "filename", "duration"),
            displaycolumns=("checked", "filename", "duration"),
            show="headings"
        )
        self.tree.grid(row=0, column=0, sticky="nsew")

        # --- Konfiguracja Kolumn ---
        self.tree.heading("checked", text="")
        self.tree.column("checked", width=40, stretch=tk.NO, anchor="center")
        self.tree.heading("filename", text="Nazwa pliku")
        self.tree.column("filename", width=250, stretch=tk.YES)
        self.tree.heading("duration", text="Czas trwania")
        self.tree.column("duration", width=100, stretch=tk.NO, anchor="center")

        # --- Pasek przewijania ---
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=0, column=1, sticky="ns")

        # --- Panel z licznikami ---
        counter_frame = ttk.Frame(self)
        counter_frame.grid(row=2, column=0, sticky="ew", pady=(5, 0))

        self.total_files_label = ttk.Label(counter_frame, text="Wszystkich: 0")
        self.total_files_label.pack(side="left", padx=5)
        self.approved_files_label = ttk.Label(counter_frame, text="Zatwierdzonych: 0")
        self.approved_files_label.pack(side="left", padx=5)
        self.long_files_label = ttk.Label(counter_frame, text="Za długich: 0")
        self.long_files_label.pack(side="left", padx=5)

        # --- Logika emulowanych checkboxów ---
        self._create_checkbox_images()
        self.tree.bind("<Button-1>", self._toggle_checkbox)
        self.tree.tag_configure("long_file", foreground="red")

        # Słownik do przechowywania pełnych ścieżek dla każdego wiersza
        self.file_paths = {}

    def _create_checkbox_images(self):
        """Tworzy proste obrazki do emulacji checkboxów."""
        self.checkbox_on = tk.PhotoImage(width=16, height=16)
        self.checkbox_off = tk.PhotoImage(width=16, height=16)

        self.checkbox_on.put(("black",), to=(2, 2, 13, 13))
        self.checkbox_on.put(("white",), to=(4, 4, 11, 11))
        self.checkbox_on.put(("#009688",), to=(5, 5, 10, 10)) # Kolor zaznaczenia

        self.checkbox_off.put(("black",), to=(2, 2, 13, 13))
        self.checkbox_off.put(("white",), to=(3, 3, 12, 12))

    def _toggle_checkbox(self, event):
        """Obsługuje kliknięcie w celu przełączenia stanu checkboxa."""
        row_id = self.tree.identify_row(event.y)
        column_id = self.tree.identify_column(event.x)

        if not row_id or column_id != "#1":
            return

        item = self.tree.item(row_id)
        current_image = item["image"][0] # Nazwa obrazka jest w krotce

        new_image = self.checkbox_on if current_image == str(self.checkbox_off) else self.checkbox_off
        self.tree.item(row_id, image=new_image)
        self.update_counters()

    def populate_files(self, files_data):
        """
        Wypełnia Treeview listą plików i ich danymi.

        Args:
            files_data (list): Lista krotek (ścieżka_pliku, czas_trwania_w_sek).
        """
        self.clear_view()
        for file_path, duration_sec in files_data:
            filename = os.path.basename(file_path)
            duration_str = f"{int(duration_sec // 60):02d}:{int(duration_sec % 60):02d}"

            is_long = duration_sec > config.MAX_FILE_DURATION_SECONDS
            image = self.checkbox_off if is_long else self.checkbox_on
            tags = ("long_file",) if is_long else ()

            row_id = self.tree.insert("", "end", values=("", filename, duration_str), image=image, tags=tags)
            self.file_paths[row_id] = file_path

        self.update_counters()

    def update_counters(self):
        """Aktualizuje etykiety z licznikami plików."""
        total = len(self.tree.get_children())
        approved = len(self.get_checked_files())
        long_files = len(self.tree.tag_has("long_file"))

        self.total_files_label.config(text=f"Wszystkich: {total}")
        self.approved_files_label.config(text=f"Zatwierdzonych: {approved}")
        self.long_files_label.config(text=f"Za długich: {long_files}")

    def get_checked_files(self):
        """Zwraca listę pełnych ścieżek do plików, które są zaznaczone."""
        checked_files = []
        for row_id in self.tree.get_children():
            if self.tree.item(row_id, "image")[0] == str(self.checkbox_on):
                checked_files.append(self.file_paths[row_id])
        return checked_files

    def clear_view(self):
        """Czyści widok Treeview i resetuje liczniki."""
        for i in self.tree.get_children():
            self.tree.delete(i)
        self.file_paths.clear()
        self.update_counters()