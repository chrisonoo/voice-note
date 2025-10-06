# Ten moduł definiuje `FilesView`, niestandardowy widżet (komponent GUI),
# który jest odpowiedzialny za wyświetlanie listy plików audio z interaktywnymi elementami.

import customtkinter as ctk
import os
from src import config, database
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
        super().__init__(parent, width=400, **kwargs)
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
        self.scrollable_frame = ctk.CTkScrollableFrame(self, width=384)
        self.scrollable_frame.grid(row=1, column=0, sticky="nsew", padx=8, pady=8)

        # Tworzymy nagłówki kolumn, aby użytkownik wiedział, co oznaczają dane kolumny.
        header_checkbox = ctk.CTkLabel(self.scrollable_frame, text="", width=35)
        header_checkbox.grid(row=0, column=0, padx=(5,0), pady=2)
        header_filename = ctk.CTkLabel(self.scrollable_frame, text="Nazwa", width=150, anchor="w")
        header_filename.grid(row=0, column=1, padx=5, pady=2)
        header_duration = ctk.CTkLabel(self.scrollable_frame, text="Czas", width=50, anchor="center")
        header_duration.grid(row=0, column=2, padx=5, pady=2)

        # Lista do przechowywania referencji do widżetów dla każdego pliku.
        # Jest to potrzebne, aby móc później np. aktualizować ikony przycisków play/pauza.
        self.file_widgets = []

        # Paginacja - lazy loading
        self.all_files = []  # Wszystkie pliki
        self.page_size = 20  # Liczba plików na stronę (zmniejszona dla lepszej wydajności)
        self.current_page = 0
        self.total_pages = 0

        # Przyciski nawigacji
        self.nav_frame = None
        self.prev_button = None
        self.next_button = None
        self.page_label = None

    def _create_navigation(self):
        """Tworzy przyciski nawigacji dla paginacji."""
        if self.nav_frame:
            return  # Już utworzone

        # Ramka na przyciski nawigacji
        self.nav_frame = ctk.CTkFrame(self, height=40)
        self.nav_frame.grid(row=3, column=0, sticky="ew", padx=5, pady=(5, 10))
        self.nav_frame.grid_columnconfigure(1, weight=1)

        # Przyciski nawigacji
        self.prev_button = ctk.CTkButton(
            self.nav_frame, text="◀ Poprzednie", width=100,
            command=self._prev_page
        )
        self.prev_button.grid(row=0, column=0, padx=(5, 2), pady=5)

        self.page_label = ctk.CTkLabel(self.nav_frame, text="Strona 1 z 1")
        self.page_label.grid(row=0, column=1, pady=5)

        self.next_button = ctk.CTkButton(
            self.nav_frame, text="Następne ▶", width=100,
            command=self._next_page
        )
        self.next_button.grid(row=0, column=2, padx=(2, 5), pady=5)

        # Ukryj nawigację jeśli niepotrzebna
        self.nav_frame.grid_remove()

    def _update_navigation(self):
        """Aktualizuje stan przycisków nawigacji."""
        if not self.nav_frame:
            return

        if self.total_pages <= 1:
            self.nav_frame.grid_remove()
            return

        self.nav_frame.grid()
        self.page_label.configure(text=f"Strona {self.current_page + 1} z {self.total_pages}")
        self.prev_button.configure(state="normal" if self.current_page > 0 else "disabled")
        self.next_button.configure(state="normal" if self.current_page < self.total_pages - 1 else "disabled")

    def _prev_page(self):
        """Przechodzi do poprzedniej strony."""
        if self.current_page > 0:
            self.current_page -= 1
            self._display_current_page()

    def _next_page(self):
        """Przechodzi do następnej strony."""
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self._display_current_page()

    def populate_files(self, files_data):
        """
        Wypełnia przewijalną ramkę listą plików na podstawie danych z bazy.
        Używa paginacji dla lepszej wydajności przy dużej liczbie plików.

        Argumenty:
            files_data (list): Lista obiektów wierszy z bazy danych.
        """
        # Zapisz wszystkie dane i oblicz paginację
        self.all_files = files_data
        self.total_pages = max(1, (len(files_data) + self.page_size - 1) // self.page_size)
        self.current_page = 0

        # Utwórz nawigację jeśli jeszcze nie istnieje
        self._create_navigation()

        # Wyświetl pierwszą stronę
        self._display_current_page()

    def _display_current_page(self):
        """
        Wyświetla pliki z bieżącej strony paginacji.
        """
        # Najpierw czyścimy stary widok
        self.clear_view()

        if not self.all_files:
            self._update_navigation()
            return

        # Oblicz zakres plików dla bieżącej strony
        start_idx = self.current_page * self.page_size
        end_idx = min(start_idx + self.page_size, len(self.all_files))
        page_files = self.all_files[start_idx:end_idx]

        # Wyświetl pliki z bieżącej strony
        for i, file_row in enumerate(page_files, start=1):
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

            # Tworzymy widżety dla każdego pliku.
            checkbox_var = ctk.BooleanVar(value=is_selected)
            checkbox = ctk.CTkCheckBox(
                self.scrollable_frame, text="", width=35, variable=checkbox_var,
                command=lambda fp=file_path, var=checkbox_var: self.on_checkbox_toggle(fp, var)
            )
            checkbox.grid(row=i, column=0, padx=(5,0), pady=2)

            filename_label = ctk.CTkLabel(self.scrollable_frame, text=filename, width=150, anchor="w")
            filename_label.grid(row=i, column=1, padx=5, pady=2)

            duration_label = ctk.CTkLabel(self.scrollable_frame, text=duration_str, width=50, anchor="center")
            duration_label.grid(row=i, column=2, padx=5, pady=2)

            play_button = ctk.CTkButton(self.scrollable_frame, text="▶", width=30, command=lambda fp=file_path: self.on_play_button_click(fp))
            play_button.grid(row=i, column=3, padx=5, pady=2)

            delete_button = ctk.CTkButton(self.scrollable_frame, text="X", width=30, command=lambda fp=file_path: self.on_delete_button_click(fp))
            delete_button.grid(row=i, column=4, padx=5, pady=2)

            # Jeśli plik jest za długi, kolorujemy jego etykiety na czerwono.
            if is_long:
                filename_label.configure(text_color="red")
                duration_label.configure(text_color="red")

            # Zapisujemy referencje do stworzonych widżetów.
            self.file_widgets.append((checkbox, file_path, duration_ms, play_button, delete_button))

        # Po dodaniu plików, aktualizujemy stan przycisków play/pauza i nawigacji.
        self.update_play_buttons()
        self._update_navigation()

    def on_checkbox_toggle(self, file_path, var):
        """
        Funkcja zwrotna (callback) wywoływana po przełączeniu checkboxa.
        Aktualizuje stan zaznaczenia w bazie danych.
        """
        database.set_file_selected(file_path, var.get())
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
        for _, file_path, _, button, _ in self.file_widgets:
            state = self.audio_player.get_state(file_path)
            # Ustawiamy odpowiednią ikonę (w formie tekstu) w zależności od stanu.
            button.configure(text="⏸" if state == 'playing' else "▶")

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