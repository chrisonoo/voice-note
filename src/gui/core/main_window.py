# Ten moduł definiuje główną klasę aplikacji `App`, która dziedziczy po `ctk.CTk`.
# Jest to centralny punkt trybu graficznego (GUI), który inicjalizuje i zarządza
# wszystkimi elementami interfejsu, kontrolerami logiki oraz stanem aplikacji.

import customtkinter as ctk  # Biblioteka do tworzenia nowoczesnego interfejsu graficznego.
from tkinter import messagebox  # Standardowy moduł Tkinter do wyświetlania okien dialogowych (np. z potwierdzeniem).
import threading  # Moduł do pracy z wątkami, kluczowy do wykonywania długich operacji (jak transkrypcja) w tle.
import time  # Dodane dla cachowania danych
from src import config, database  # Importujemy nasze własne moduły: konfigurację i bazę danych.

# Importujemy wszystkie komponenty i kontrolery, które będą używane w głównym oknie.
# Taka struktura (podobna do wzorca MVC - Model-View-Controller) porządkuje kod:
# - `InterfaceBuilder`: Buduje i układa wszystkie widżety (przyciski, panele).
# - `ButtonStateController`: Zarządza stanem przycisków (włączone/wyłączone).
# - `FileHandler`: Obsługuje logikę dodawania i ładowania plików.
# - `TranscriptionController`: Zarządza procesem transkrypcji w tle.
# - `PanelManager`: Odświeża zawartość paneli z listami plików.
# - `AudioPlayer`: Kontroluje odtwarzanie próbek audio.
# - `TerminalRedirector`: Przekierowuje stdout/stderr do GUI.
from .interface_builder import InterfaceBuilder
from ..controllers.button_state_controller import ButtonStateController
from ..controllers.file_handler import FileHandler
from ..controllers.transcription_controller import TranscriptionController
from ..controllers.panel_manager import PanelManager
from ..utils.audio_player import AudioPlayer
from ..utils.terminal_redirector import TerminalRedirector

class App(ctk.CTk):
    """
    Główna klasa aplikacji, która dziedziczy po `customtkinter.CTk`,
    tworząc główne okno i zarządzając całym cyklem życia aplikacji w trybie GUI.
    """
    def __init__(self):
        # `super().__init__()` wywołuje konstruktor klasy nadrzędnej (`ctk.CTk`), co jest niezbędne do inicjalizacji okna.
        super().__init__()

        # Ustawiamy wygląd aplikacji (System - jasny/ciemny jak w systemie, "blue" - kolor akcentu).
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        # Inicjalizujemy atrybuty związane z przetwarzaniem w tle.
        self.processing_thread = None  # Będzie przechowywać referencję do wątku roboczego.
        # `threading.Event` to prosty mechanizm do komunikacji między wątkami. Używamy go do sygnalizowania pauzy.
        self.pause_request_event = threading.Event()

        # Inicjalizujemy cache dla danych z bazy
        self._cached_files_data = None
        self._cache_timestamp = 0
        self._cache_timeout = 2.0  # sekundy

        # Inicjalizujemy stan terminala (domyślnie rozwinięty)
        self.terminal_expanded = True

        # Ustawiamy tytuł okna, pobierając go z pliku konfiguracyjnego.
        self.title(config.APP_NAME)
        # Ustawiamy minimalny rozmiar okna.
        self.minsize(1110, 850)
        # `protocol` pozwala przechwycić zdarzenia systemowe okna. "WM_DELETE_WINDOW" to kliknięcie przycisku "X".
        # Zamiast domyślnego zamknięcia, wywołujemy naszą własną metodę `on_closing`.
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Konfigurujemy siatkę (grid) głównego okna. `weight` decyduje o tym, jak kolumny/wiersze rozciągają się przy zmianie rozmiaru okna.
        # Kolumna 4 (z panelem transkrypcji) ma `weight=3`, więc będzie się rozciągać najbardziej.
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=0)
        self.grid_columnconfigure(2, weight=0)
        self.grid_columnconfigure(3, weight=0)
        self.grid_columnconfigure(4, weight=3)
        # Wiersz 1 (z głównymi panelami) ma `weight=1`, więc będzie się rozciągał w pionie.
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=0)
        self.grid_rowconfigure(3, weight=0)

        # Tworzymy instancje naszych klas pomocniczych (kontrolerów i menedżerów).
        # Przekazujemy `self` (czyli instancję `App`), aby miały one dostęp do głównego okna i jego komponentów.
        self.audio_player = AudioPlayer()
        self.interface_builder = InterfaceBuilder(self, self.audio_player)
        self.button_state_controller = ButtonStateController(self)
        self.file_handler = FileHandler(self)
        self.transcription_controller = TranscriptionController(self)
        self.panel_manager = PanelManager(self)

        # Wywołujemy metodę, która fizycznie tworzy i umieszcza wszystkie widżety w oknie.
        self.interface_builder.create_widgets()

        # Inicjalizujemy przekierowanie terminala
        self.terminal_redirector = TerminalRedirector(self.append_to_terminal)
        self.terminal_redirector.start_redirect()

        # Ustawiamy początkowy stan przycisków i odświeżamy widoki.
        self.button_state_controller.update_ui_state()
        self.refresh_all_views()

        # Inicjalizujemy wyświetlanie transkrypcji zgodnie z domyślnym stanem checkboxa
        self.refresh_transcription_display()

        # Uruchamiamy cykliczne sprawdzanie statusu odtwarzania audio.
        self._check_playback_status()

    def get_cached_files_data(self):
        """Zwraca dane z cache'a lub odświeża jeśli cache jest przestarzały."""
        current_time = time.time()
        if self._cached_files_data is None or (current_time - self._cache_timestamp) > self._cache_timeout:
            self._cached_files_data = database.get_all_files()
            self._cache_timestamp = current_time
        return self._cached_files_data

    def invalidate_cache(self):
        """Unieważnia cache gdy dane mogły się zmienić."""
        self._cached_files_data = None

    def update_all_counters(self, all_files=None):
        """
        Aktualizuje wszystkie etykiety z licznikami plików.
        Jeśli dane nie są dostarczone (`all_files` jest None), pobiera je z cache'a.
        W przeciwnym razie, używa istniejących danych, aby uniknąć zbędnych zapytań do bazy.
        """
        try:
            # Używamy cache'a zamiast bezpośredniego zapytania do bazy
            if all_files is None:
                all_files = self.get_cached_files_data()

            # Jedna pętla dla wszystkich obliczeń - optymalizacja wydajności
            stats = {
                'total': len(all_files),
                'selected': 0,
                'long': 0,
                'loaded': 0,
                'processing': 0,
                'processed': 0
            }

            max_duration_ms = config.MAX_FILE_DURATION_SECONDS * 1000

            for row in all_files:
                if row['is_selected']:
                    stats['selected'] += 1
                if row['duration_ms'] and row['duration_ms'] > max_duration_ms:
                    stats['long'] += 1
                if row['is_loaded']:
                    stats['loaded'] += 1
                    if not row['is_processed']:
                        stats['processing'] += 1
                if row['is_processed']:
                    stats['processed'] += 1

            # Aktualizuj etykiety
            self.files_counter_label.configure(text=f"Razem: {stats['total']} | Zaznaczone: {stats['selected']} | Długie: {stats['long']}")
            self.loaded_counter_label.configure(text=f"Wczytane: {stats['loaded']}")
            self.processing_counter_label.configure(text=f"Kolejka: {stats['processing']}")
            self.processed_counter_label.configure(text=f"Gotowe: {stats['processed']}")

        except Exception as e:
            print(f"Błąd podczas aktualizacji liczników: {e}")

    def refresh_all_views(self):
        """
        Odświeża wszystkie główne widoki (panele z plikami), pobierając dane z cache'a
        i przekazując je do poszczególnych metod, co jest wydajniejsze.
        """
        try:
            all_files = self.get_cached_files_data()
            # Przekazujemy pobrane dane do menedżera paneli, liczników i kontrolera przycisków.
            self.panel_manager.refresh_all_views(data=all_files)
            self.update_all_counters(all_files=all_files)
            self.button_state_controller.update_ui_state(all_files=all_files)
        except Exception as e:
            print(f"Błąd podczas pełnego odświeżania: {e}")

    def pause_transcription(self):
        """Deleguje zadanie pauzy do kontrolera transkrypcji."""
        self.transcription_controller.pause_transcription()

    def resume_transcription(self):
        """Deleguje zadanie wznowienia do kontrolera transkrypcji."""
        self.transcription_controller.resume_transcription()

    def on_processing_finished(self):
        """
        Obsługuje zakończenie procesu transkrypcji.
        Ta metoda jest wywoływana z kontrolera transkrypcji, gdy pętla przetwarzania się zakończy.
        """
        # Finalizuje stan w kontrolerze (np. zmienia stan przycisków).
        self.transcription_controller.on_processing_finished()

        # Sprawdzamy, czy wszystkie zaznaczone pliki zostały przetworzone.
        all_files = database.get_all_files()
        is_fully_processed = all_files and all(f['is_processed'] for f in all_files if f['is_selected'])

        if is_fully_processed:
            # Wyświetlamy transkrypcje z uwzględnieniem ustawień checkboxa
            self.refresh_transcription_display()

    def refresh_transcription_display(self):
        """
        Odświeża wyświetlanie transkrypcji z uwzględnieniem ustawień checkboxów
        (czy pokazywać numerację i/lub tagi).
        """
        try:
            # Pobieramy wszystkie pliki z bazy danych
            all_files = database.get_all_files()

            # Filtrujemy tylko przetworzone pliki z zaznaczonymi plikami, które mają transkrypcję
            processed_files = [
                f for f in all_files
                if f['is_processed'] and f['is_selected'] and f['transcription']
            ]

            if not processed_files:
                self.transcription_output_panel.update_text("")
                return

            # Sprawdzamy ustawienia checkboxów
            show_numbering = self.transcription_output_panel.should_show_numbering()
            show_tags = self.transcription_output_panel.should_show_tags()

            processed_transcriptions = []
            # Użyj enumerate do dynamicznego generowania numeracji
            for i, f in enumerate(processed_files, 1):
                parts = []
                transcription = f['transcription'] or ''

                # Dodaj numerację, jeśli zaznaczone
                if show_numbering:
                    parts.append(f"**{i}:**")

                # Dodaj tag, jeśli zaznaczone i istnieje
                if show_tags:
                    tag = f['tag'] or ''
                    if tag:
                        parts.append(tag)

                # Dodaj właściwą transkrypcję
                parts.append(transcription)

                # Połącz wszystkie części w jeden tekst
                full_text = " ".join(parts)
                processed_transcriptions.append(full_text)

            # Łączymy transkrypcje w jeden tekst
            final_text = "\n\n".join(processed_transcriptions)
            # Aktualizujemy główny panel wyjściowy
            self.transcription_output_panel.update_text(final_text)

        except Exception as e:
            print(f"Błąd podczas odświeżania wyświetlania transkrypcji: {e}")

    def start_transcription_process(self):
        """Deleguje zadanie rozpoczęcia procesu transkrypcji do kontrolera."""
        self.transcription_controller.start_transcription_process()

    def reset_application(self):
        """
        Resetuje aplikację do stanu początkowego, czyszcząc tabelę files i pliki audio.
        Prosi użytkownika o potwierdzenie tej operacji.
        """
        answer = messagebox.askyesno(
            "Potwierdzenie resetowania",
            "Czy na pewno chcesz zresetować aplikację?\n\n"
            "Spowoduje to usunięcie wszystkich wczytanych plików i transkrypcji."
        )
        if answer:
            try:
                # Zatrzymujemy aktywne procesy (np. odtwarzanie audio) przed czyszczeniem.
                if self.audio_player:
                    self.audio_player.stop()

                # Resetujemy tabelę files i czyścimy pliki audio.
                database.reset_files_table()
                # Optymalizujemy bazę danych po wyczyszczeniu
                database.optimize_database()
                # Unieważniamy cache ponieważ dane zostały wyczyszczone
                self.invalidate_cache()
                # Odświeżamy wszystkie widoki, aby odzwierciedliły pusty stan.
                self.refresh_all_views()
                # Czyścimy również główny panel z transkrypcją.
                self.refresh_transcription_display()

                messagebox.showinfo("Reset zakończony", "Aplikacja została zresetowana.")
            except Exception as e:
                messagebox.showerror("Błąd", f"Wystąpił błąd podczas resetowania: {e}")

    def on_transcription_progress(self):
        """
        Funkcja zwrotna (callback) wywoływana z wątku roboczego po przetworzeniu każdego pliku.
        Ta metoda bezpiecznie aktualizuje GUI z głównego wątku.
        """
        try:
            # Pobieramy świeże dane i aktualizujemy tylko te widoki, które pokazują postęp.
            all_files = database.get_all_files()
            self.panel_manager.refresh_transcription_progress_views(data=all_files)
            self.update_all_counters(all_files=all_files)
            self.button_state_controller.update_ui_state(all_files=all_files)

            # Odświeżamy również panel transkrypcji z uwzględnieniem ustawień checkboxa
            self.refresh_transcription_display()
        except Exception as e:
            print(f"Błąd w trakcie aktualizacji postępu: {e}")

    def copy_transcription_to_clipboard(self):
        """Kopiuje zawartość panelu wyjściowego do schowka systemowego."""
        text = self.transcription_output_panel.get_text()
        # Sprawdzamy, czy jest co kopiować (ignorujemy białe znaki).
        if not text.strip():
            messagebox.showinfo("Informacja", "Brak tekstu do skopiowania.")
            return
        self.clipboard_clear()  # Czyścimy schowek.
        self.clipboard_append(text)  # Dodajemy tekst do schowka.
        messagebox.showinfo("Skopiowano", "Transkrypcja została skopiowana do schowka.")

    def _check_playback_status(self):
        """Cyklicznie sprawdza, czy odtwarzanie audio się zakończyło, aby zaktualizować UI."""
        # Sprawdzamy czy ffplay jeszcze odtwarza plik
        if self.audio_player.is_playing and not self.audio_player.is_busy():
            self.audio_player.stop()  # Aktualizujemy stan naszego odtwarzacza.
            # `hasattr` sprawdza, czy widżet został już utworzony.
            if hasattr(self, 'file_selection_panel'):
                # Aktualizujemy wygląd przycisków play/stop w panelu.
                self.file_selection_panel.update_play_buttons()
        # `self.after(ms, func)` to metoda Tkinter, która planuje wykonanie funkcji `func` po `ms` milisekundach.
        # Wywołując samą siebie, tworzymy pętlę, która działa w tle bez blokowania GUI.
        self.after(100, self._check_playback_status)

    def toggle_terminal(self):
        """Zwijanie/rozwijanie panelu terminala."""
        if self.terminal_expanded:
            # Zwijamy terminal
            self.terminal_frame.grid_remove()
            self.terminal_toggle_button.configure(text="▼ Terminal")
            self.terminal_expanded = False
            # Dostosuj rozmiar okna po zwinięciu
            current_width = self.winfo_width()
            self.geometry(f"{current_width}x600")
        else:
            # Rozwijamy terminal
            self.terminal_frame.grid()
            self.terminal_toggle_button.configure(text="▲ Terminal")
            self.terminal_expanded = True
            # Dostosuj rozmiar okna po rozwinięciu
            current_width = self.winfo_width()
            self.geometry(f"{current_width}x850")

    def append_to_terminal(self, text):
        """Dodaje tekst do terminala GUI."""
        if hasattr(self, 'terminal_text'):
            self.terminal_text.configure(state="normal")
            self.terminal_text.insert("end", text)
            self.terminal_text.configure(state="disabled")
            # Przewiń na dół
            self.terminal_text.see("end")

    def on_closing(self):
        """Obsługuje zdarzenie zamknięcia okna."""
        self.audio_player.stop()

        # Zatrzymaj przekierowanie terminala
        if hasattr(self, 'terminal_redirector'):
            self.terminal_redirector.stop_redirect()

        # Sprawdzamy, czy wątek przetwarzający wciąż działa.
        if self.processing_thread and self.processing_thread.is_alive():
            # Jeśli tak, pytamy użytkownika, czy na pewno chce zamknąć aplikację.
            if messagebox.askokcancel("Przetwarzanie w toku", "Proces jest aktywny. Czy na pewno chcesz wyjść?"):
                self.destroy()  # `destroy()` zamyka okno.
        else:
            # Jeśli nic nie jest przetwarzane, zamykamy od razu.
            self.destroy()

def main():
    """Główna funkcja uruchamiająca aplikację w trybie GUI."""
    # Komentarz: Inicjalizacja bazy danych została przeniesiona do głównego pliku main.py,
    # aby uniknąć podwójnego wywołania przy starcie w trybie GUI. To dobra praktyka.
    app = App()
    app.mainloop()  # `mainloop()` uruchamia główną pętlę zdarzeń Tkinter, która czeka na akcje użytkownika.