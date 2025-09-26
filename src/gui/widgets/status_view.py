# Ten moduł definiuje `StatusView`, generyczny komponent GUI (widżet)
# używany do wyświetlania list plików w różnych panelach statusu,
# np. "Wczytane", "Do przetworzenia", "Przetworzone".

import customtkinter as ctk
import os

class StatusView(ctk.CTkFrame):
    """
    Komponent GUI, który wyświetla listę nazw plików w określonym stanie
    (np. oczekujących na przetworzenie) wewnątrz pola tekstowego.
    """
    def __init__(self, parent, text, **kwargs):
        """
        Inicjalizuje ramkę statusu.

        Argumenty:
            parent: Widżet nadrzędny (główne okno aplikacji).
            text (str): Etykieta do wyświetlenia nad listą (np. "Wczytane").
        """
        # Wywołujemy konstruktor klasy nadrzędnej `ctk.CTkFrame`.
        super().__init__(parent, **kwargs)

        # Konfigurujemy siatkę (grid) wewnątrz tej ramki.
        # Wiersz 1 (z polem tekstowym) i kolumna 0 będą się rozciągać,
        # aby wypełnić dostępną przestrzeń.
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Etykieta tytułowa dla panelu.
        self.label = ctk.CTkLabel(self, text=text, anchor="center")
        self.label.grid(row=0, column=0, sticky="ew", pady=(0, 5))

        # Pole tekstowe do wyświetlania listy plików.
        # Używamy `CTkTextbox`, ponieważ `CTkLabel` nie obsługuje łatwo
        # wieloliniowego tekstu z możliwością przewijania.
        self.text = ctk.CTkTextbox(
            self,
            wrap="word",  # Zawijanie wierszy, jeśli nazwa pliku jest za długa.
            state="disabled",  # Domyślnie wyłączone, aby użytkownik nie mógł edytować tekstu.
            width=150,  # Stała szerokość.
            padx=8,  # Wewnętrzne marginesy.
            pady=8
        )
        self.text.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

    def update_from_list(self, file_paths):
        """Wypełnia pole tekstowe listą nazw plików."""
        # Musimy tymczasowo włączyć pole tekstowe, aby móc je modyfikować.
        self.text.configure(state="normal")
        # Usuwamy całą poprzednią zawartość. '1.0' to początek, "end" to koniec.
        self.text.delete('1.0', "end")
        try:
            # Konwertujemy pełne ścieżki na same nazwy plików za pomocą `os.path.basename`.
            # Sprawdzamy `if path`, aby uniknąć błędów dla pustych wpisów.
            file_names = [os.path.basename(path) for path in file_paths if path]
            # Łączymy nazwy plików w jeden ciąg znaków, oddzielając je znakiem nowej linii.
            # `insert("end", ...)` wstawia tekst na końcu pola tekstowego.
            self.text.insert("end", '\n'.join(file_names))
        except Exception as e:
            print(f"Błąd podczas aktualizacji widoku statusu: {e}")
        # Po zakończeniu modyfikacji ponownie wyłączamy pole tekstowe.
        self.text.configure(state="disabled")