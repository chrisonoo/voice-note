# Ten moduł definiuje `TranscriptionView`, niestandardowy widżet (komponent GUI)
# przeznaczony do wyświetlania finalnego tekstu transkrypcji.

import customtkinter as ctk
from src import config

class TranscriptionView(ctk.CTkFrame):
    """
    Komponent GUI do wyświetlania ostatecznego, połączonego tekstu transkrypcji.
    """
    def __init__(self, parent, text, **kwargs):
        """
        Inicjalizuje ramkę z polem tekstowym na transkrypcję.

        Argumenty:
            parent: Widżet nadrzędny (główne okno aplikacji).
            text (str): Etykieta do wyświetlenia nad polem tekstowym.
        """
        # Wywołujemy konstruktor klasy nadrzędnej `ctk.CTkFrame`.
        super().__init__(parent, **kwargs)

        # Przechowujemy referencję do głównego okna aplikacji
        self.app = parent

        # Konfigurujemy siatkę (grid) wewnątrz tej ramki.
        # Wiersz 1 (z polem tekstowym) i kolumna 0 będą się rozciągać,
        # aby wypełnić dostępną przestrzeń.
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Ramka dla nagłówka z etykietą i checkboxem
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 5))

        # Konfigurujemy siatkę w header_frame
        self.header_frame.grid_columnconfigure(0, weight=1)
        self.header_frame.grid_columnconfigure(1, weight=0)  # Kolumna dla checkboxa "Numeracja"
        self.header_frame.grid_columnconfigure(2, weight=0)  # Kolumna dla checkboxa "Tagi"

        # Etykieta tytułowa dla panelu.
        self.label = ctk.CTkLabel(self.header_frame, text=text, anchor="center")
        self.label.grid(row=0, column=0, sticky="ew")

        # Checkbox do pokazywania/ukrywania numeracji
        self.show_numbering_checkbox = ctk.CTkCheckBox(
            self.header_frame,
            text="Numeracja",
            command=self._on_checkbox_toggle
        )
        self.show_numbering_checkbox.grid(row=0, column=1, sticky="e", padx=(10, 5))

        # Checkbox do pokazywania/ukrywania tagów
        self.show_tags_checkbox = ctk.CTkCheckBox(
            self.header_frame,
            text="Tagi",
            command=self._on_checkbox_toggle
        )
        self.show_tags_checkbox.grid(row=0, column=2, sticky="e", padx=(0, 0))

        # Pole tekstowe do wyświetlania wyniku transkrypcji.
        self.text = ctk.CTkTextbox(
            self,
            wrap="word",  # Włącza zawijanie wierszy.
            state="disabled",  # Domyślnie wyłączone, aby użytkownik nie mógł edytować tekstu.
            width=config.PANEL_TRANSCRIPTION_WIDTH,  # Szerokość z konfiguracji.
            padx=8,  # Wewnętrzne marginesy.
            pady=8
        )
        self.text.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

    def update_text(self, content):
        """
        Wypełnia pole tekstowe podaną treścią.
        Tekst jest nieedytowalny dla użytkownika.
        """
        # Krok 1: Tymczasowo włącz pole tekstowe, aby umożliwić modyfikację programową.
        self.text.configure(state="normal")
        # Krok 2: Usuń całą poprzednią zawartość.
        self.text.delete('1.0', "end")
        try:
            # Krok 3: Wstaw nową treść na końcu pola tekstowego.
            self.text.insert("end", content)
        except Exception as e:
            print(f"Błąd podczas aktualizacji widoku transkrypcji: {e}")
        # Krok 4: Ponownie wyłącz pole tekstowe, aby uczynić je tylko do odczytu dla użytkownika.
        self.text.configure(state="disabled")

    def get_text(self):
        """Zwraca całą zawartość pola tekstowego jako ciąg znaków."""
        # '1.0' oznacza pierwszy wiersz, zerowy znak. "end" oznacza koniec tekstu.
        return self.text.get("1.0", "end")

    def _on_checkbox_toggle(self):
        """Obsługuje zmianę stanu checkboxa - przeładowuje transkrypcje."""
        # Wywołujemy metodę przeładowania transkrypcji w głównym oknie
        if hasattr(self.app, 'refresh_transcription_display'):
            self.app.refresh_transcription_display()

    def should_show_tags(self):
        """Zwraca True jeśli checkbox jest zaznaczony (pokazuj tagi)."""
        return self.show_tags_checkbox.get() == 1

    def should_show_numbering(self):
        """Zwraca True jeśli checkbox 'Numeracja' jest zaznaczony."""
        return self.show_numbering_checkbox.get() == 1