# Ten moduł definiuje `FilesView`, niestandardowy widżet (komponent GUI),
# który jest odpowiedzialny za wyświetlanie listy plików audio z interaktywnymi elementami.

import customtkinter as ctk
import os
from src import config, database
from src.utils.file_type_helper import get_file_type
from ..utils.audio_player import AudioPlayer
from tkinter.messagebox import askyesno

class FilesView(ctk.CTkFrame):
    """
    Komponent GUI, który wyświetla listę wybranych przez użytkownika plików.
    Zastępuje standardowy widok drzewa (Treeview) ramką przewijalną (CTkScrollableFrame)
    z polami wyboru (checkbox), etykietami i przyciskami, co nadaje nowoczesny wygląd.
    Zawiera również kontrolki do odtwarzania plików audio.
    """
    def __init__(self, parent, audio_player: AudioPlayer, title="Wybrane", **kwargs):
        # Wywołujemy konstruktor klasy nadrzędnej `ctk.CTkFrame`.
        super().__init__(parent, width=config.PANEL_SELECTED_WIDTH, **kwargs)
        # `grid_propagate(False)` zapobiega automatycznemu dopasowywaniu się rozmiaru ramki
        # do jej zawartości, co pozwala nam utrzymać stałą szerokość.
        self.grid_propagate(False)

        # Przechowujemy referencję do odtwarzacza audio.
        self.audio_player = audio_player

        # Konfigurujemy siatkę (grid) wewnątrz tej ramki.
        self.grid_rowconfigure(1, weight=1)  # Wiersz 1 (z przewijalną listą) będzie się rozciągał.
        self.grid_columnconfigure(0, weight=1) # Kolumna 0 będzie się rozciągać.

        # Etykieta tytułowa dla panelu.
        self.label = ctk.CTkLabel(self, text=title, anchor="center")
        self.label.grid(row=0, column=0, sticky="ew", pady=(0, 5))

        # Tworzymy przewijalną ramkę, w której będą umieszczane wpisy plików.
        self.scrollable_frame = ctk.CTkScrollableFrame(self, width=config.SCROLLABLE_FRAME_WIDTH)
        self.scrollable_frame.grid(row=1, column=0, sticky="nsew", padx=8, pady=8)

        # Tworzymy nagłówki kolumn, aby użytkownik wiedział, co oznaczają dane kolumny.
        header_checkbox = ctk.CTkLabel(self.scrollable_frame, text="", width=config.COLUMN_CHECKBOX_WIDTH)
        header_checkbox.grid(row=0, column=0, padx=(5,0), pady=2)
        header_type = ctk.CTkLabel(self.scrollable_frame, text="", width=config.COLUMN_TYPE_WIDTH, anchor="center")
        header_type.grid(row=0, column=1, padx=5, pady=2)
        header_filename = ctk.CTkLabel(self.scrollable_frame, text="Nazwa", width=config.COLUMN_FILENAME_WIDTH, anchor="w")
        header_filename.grid(row=0, column=2, padx=5, pady=2)
        header_duration = ctk.CTkLabel(self.scrollable_frame, text="Czas", width=config.COLUMN_DURATION_WIDTH, anchor="center")
        header_duration.grid(row=0, column=3, padx=5, pady=2)

        # Lista do przechowywania referencji do widżetów dla każdego pliku.
        # Jest to potrzebne, aby móc później np. aktualizować ikony przycisków play/pauza.
        self.file_widgets = []

    def _truncate_filename(self, filename, max_length=None):
        """
        Skraca nazwę pliku do określonej długości i dodaje '...' jeśli jest za długa.
        
        Argumenty:
            filename (str): Oryginalna nazwa pliku
            max_length (int): Maksymalna długość nazwy (domyślnie z config)
            
        Zwraca:
            str: Skrócona nazwa pliku z '...' jeśli potrzeba
        """
        if max_length is None:
            max_length = config.MAX_FILENAME_LENGTH_SELECTED
        if len(filename) <= max_length:
            return filename
        return filename[:max_length-3] + "..."

    def populate_files(self, files_data):
        """
        Wypełnia przewijalną ramkę listą plików na podstawie danych z bazy.
        Wyświetla wszystkie pliki jednocześnie.

        Argumenty:
            files_data (list): Lista obiektów wierszy z bazy danych.
        """
        # Najpierw czyścimy stary widok
        self.clear_view()

        if not files_data:
            return

        # Wyświetl wszystkie pliki
        for i, file_row in enumerate(files_data, start=1):
            # Wyciągamy potrzebne dane z obiektu wiersza.
            file_path = file_row['source_file_path']
            duration_ms = file_row['duration_ms'] or 0
            is_selected = file_row['is_selected']

            duration_sec = duration_ms / 1000
            filename = os.path.basename(file_path)
            # Formatujemy czas trwania na czytelny format MM:SS.
            duration_str = f"{int(duration_sec // 60):02d}:{int(duration_sec % 60):02d}"
            # Sprawdzamy, czy plik jest dłuższy niż limit z konfiguracji.
            is_long = duration_sec > config.MAX_FILE_DURATION_SECONDS
            
            # Określamy typ pliku i ikonkę
            file_type = get_file_type(file_path)
            type_icon = "🎵" if file_type == 'audio' else "🎬"

            # Tworzymy widżety dla każdego pliku.
            checkbox_var = ctk.BooleanVar(value=is_selected)
            checkbox = ctk.CTkCheckBox(
                self.scrollable_frame, text="", width=config.COLUMN_CHECKBOX_WIDTH, variable=checkbox_var,
                command=lambda fp=file_path, var=checkbox_var: self.on_checkbox_toggle(fp, var)
            )
            checkbox.grid(row=i, column=0, padx=(5,0), pady=2)

            type_label = ctk.CTkLabel(self.scrollable_frame, text=type_icon, width=config.COLUMN_TYPE_WIDTH, anchor="center")
            type_label.grid(row=i, column=1, padx=5, pady=2)

            filename_label = ctk.CTkLabel(self.scrollable_frame, text=self._truncate_filename(filename), width=config.COLUMN_FILENAME_WIDTH, anchor="w")
            filename_label.grid(row=i, column=2, padx=5, pady=2)

            duration_label = ctk.CTkLabel(self.scrollable_frame, text=duration_str, width=config.COLUMN_DURATION_WIDTH, anchor="center")
            duration_label.grid(row=i, column=3, padx=5, pady=2)

            play_button = ctk.CTkButton(self.scrollable_frame, text="▶", width=config.COLUMN_PLAY_WIDTH, height=25, command=lambda fp=file_path: self.on_play_button_click(fp))
            play_button.grid(row=i, column=4, padx=5, pady=2)

            delete_button = ctk.CTkButton(self.scrollable_frame, text="X", width=config.COLUMN_DELETE_WIDTH, command=lambda fp=file_path: self.on_delete_button_click(fp))
            delete_button.grid(row=i, column=5, padx=5, pady=2)

            # Jeśli plik jest za długi, kolorujemy jego etykiety na czerwono.
            if is_long:
                filename_label.configure(text_color="red")
                duration_label.configure(text_color="red")

            # Zapisujemy referencje do stworzonych widżetów.
            self.file_widgets.append((checkbox, file_path, duration_ms, play_button, delete_button, type_label))

        # Po dodaniu plików, aktualizujemy stan przycisków play/pauza.
        self.update_play_buttons()


    def on_checkbox_toggle(self, file_path, var):
        """
        Funkcja zwrotna (callback) wywoływana po przełączeniu checkboxa.
        Aktualizuje stan zaznaczenia w bazie danych.
        """
        database.set_file_selected(file_path, var.get())
        # Unieważniamy cache ponieważ dane zostały zmienione
        self.master.invalidate_cache()
        # `self.master` odnosi się do rodzica tego widżetu, czyli głównego okna aplikacji `App`.
        # Wywołujemy metodę z głównego okna, aby zaktualizować liczniki.
        self.master.update_all_counters()

    def on_delete_button_click(self, file_path):
        """Obsługuje kliknięcie przycisku usuwania."""
        filename = os.path.basename(file_path)
        # Wyświetlamy okno dialogowe z prośbą o potwierdzenie.
        answer = askyesno(title='Potwierdzenie usunięcia', message=f'Czy na pewno chcesz usunąć plik?\n\n{filename}')
        if answer:
            # Jeśli użytkownik się zgodził, usuwamy plik z bazy (i z dysku).
            database.delete_file(file_path)
            # Unieważniamy cache ponieważ dane zostały zmienione
            self.master.invalidate_cache()
            # Odświeżamy wszystkie widoki, aby usunięty plik zniknął z interfejsu.
            self.master.refresh_all_views()

    def on_play_button_click(self, file_path):
        """Obsługuje kliknięcie przycisku play/pauza."""
        # Delegujemy logikę do odtwarzacza audio.
        self.audio_player.toggle_play_pause(file_path)
        # Aktualizujemy ikony na przyciskach.
        self.update_play_buttons()

    def update_play_buttons(self):
        """Aktualizuje tekst wszystkich przycisków play/pauza na podstawie stanu odtwarzacza."""
        if not self.file_widgets:
            return
        # Iterujemy przez zapisane referencje do widżetów.
        for _, file_path, _, button, _, _ in self.file_widgets:
            state = self.audio_player.get_state(file_path)
            # Ustawiamy odpowiednią ikonę (w formie tekstu) w zależności od stanu.
            if state == 'playing':
                button.configure(text="⏸")
            elif state == 'paused':
                button.configure(text="▶")
            else:
                button.configure(text="▶")

    def clear_view(self):
        """
        Czyści widok, niszcząc wszystkie widżety-dzieci w przewijalnej ramce
        i resetując listę referencji do widżetów.
        Jest to kluczowe, aby zapobiec wyciekom pamięci i duplikowaniu wpisów.
        """
        if self.audio_player:
            self.audio_player.stop()

        # Iterujemy po wszystkich widżetach wewnątrz `scrollable_frame`.
        for widget in self.scrollable_frame.winfo_children():
            # Usuwamy tylko wiersze z danymi (zaczynające się od 1), zostawiając nagłówki (wiersz 0).
            if widget.grid_info()["row"] > 0:
                widget.destroy()
        # Czyścimy naszą listę referencji.
        self.file_widgets.clear()