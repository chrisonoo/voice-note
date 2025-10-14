# Ten moduł zawiera klasę `AudioPlayer`, która jest klasą pomocniczą
# odpowiedzialną za odtwarzanie próbek audio bezpośrednio w interfejsie.

import threading  # Używany do zapewnienia bezpieczeństwa wątkowego przy tworzeniu Singletonu.
import os  # Do sprawdzania istnienia plików
from audioplayer import AudioPlayer as AudioPlayerLib  # Nowa biblioteka do odtwarzania audio
from src.utils.file_type_helper import is_video_file  # Do sprawdzania typu pliku

class AudioPlayerWrapper:
    """
    Odtwarzacz audio używający biblioteki audioplayer do obsługi wszystkich formatów audio.
    Wspiera WMA, M4A, MP4, MP3 i inne formaty bez konwersji.
    Ma pełną funkcjonalność pauzy i wznowienia.
    """

    def __init__(self):
        self.player = None
        self.current_file = None
        self.is_playing = False
        self.is_paused = False

    def play_file(self, file_path, stop_first=True):
        """Rozpoczyna odtwarzanie pliku."""
        if not os.path.exists(file_path):
            print(f"Plik nie istnieje: {file_path}")
            return

        # Sprawdzamy czy to plik wideo - nie odtwarzamy filmów (tylko audio)
        if is_video_file(file_path):
            print(f"Plik wideo {os.path.basename(file_path)} nie może być odtwarzany bezpośrednio.")
            print("Skonwertuj plik wideo do formatu audio najpierw.")
            return

        if stop_first:
            self.stop()  # Zatrzymaj ewentualne poprzednie odtwarzanie

        try:
            # Tworzymy nowego playera z plikiem
            self.player = AudioPlayerLib(file_path)
            self.player.play()

            self.current_file = file_path
            self.is_playing = True
            self.is_paused = False

        except Exception as e:
            print(f"Nie można odtworzyć pliku przez audioplayer: {file_path}. Błąd: {e}")
            self.stop()

    def pause(self):
        """Wstrzymuje odtwarzanie."""
        if self.player and self.is_playing and not self.is_paused:
            self.player.pause()
            self.is_paused = True

    def unpause(self, file_path=None):
        """Wznawia odtwarzanie."""
        if self.player and self.is_paused:
            self.player.resume()  # Używamy resume() do wznowienia pauzy
            self.is_paused = False

    def stop(self):
        """Zatrzymuje odtwarzanie."""
        if self.player:
            try:
                self.player.stop()
            except:
                pass  # Ignoruj błędy przy zatrzymywaniu

        self.player = None
        self.current_file = None
        self.is_playing = False
        self.is_paused = False

    def is_busy(self):
        """Sprawdza czy odtwarzacz jeszcze odtwarza."""
        # W audioplayer nie ma prostej właściwości is_playing,
        # więc sprawdzamy czy player istnieje i nie jest w stanie stopped
        return self.player is not None and self.is_playing

    def get_state(self, file_path):
        """Zwraca stan odtwarzania dla danego pliku."""
        if self.current_file == file_path:
            if self.is_playing and not self.is_paused:
                return 'playing'
            elif self.is_paused:
                return 'paused'
        return 'stopped'

class AudioPlayer:
    """
    Zarządza odtwarzaniem plików audio przy użyciu biblioteki `audioplayer`.
    Zapewnia, że w danym momencie odtwarzany jest tylko jeden plik.
    Została zaimplementowana jako Singleton, aby zagwarantować istnienie
    tylko jednej, globalnej instancji odtwarzacza w całej aplikacji.

    Używa audioplayer dla wszystkich formatów audio bez konwersji.
    """
    # Wzorzec Singleton - implementacja
    # `_instance` przechowuje jedyną instancję klasy.
    _instance = None
    # `_lock` zapewnia, że tylko jeden wątek na raz może tworzyć instancję (bezpieczeństwo wątkowe).
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        # `__new__` jest wywoływane przed `__init__`. To tutaj kontrolujemy tworzenie obiektu.
        if not cls._instance:
            with cls._lock:
                # Podwójne sprawdzenie (double-checked locking) na wypadek, gdyby wiele wątków czekało na blokadę.
                if not cls._instance:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        # Inicjalizator jest wywoływany za każdym razem, gdy próbujemy "stworzyć" instancję
        # (np. `AudioPlayer()`), ale właściwa inicjalizacja stanu (zmienne)
        # odbywa się tylko raz, dzięki fladze `self.initialized`.
        if not hasattr(self, 'initialized'):
            self.audio_player = AudioPlayerWrapper()  # Player dla wszystkich formatów
            self.current_file = None  # Ścieżka do aktualnie odtwarzanego pliku.
            self.is_playing = False  # Flaga, czy coś jest aktywnie odtwarzane.
            self.is_paused = False  # Flaga, czy odtwarzanie jest wstrzymane.
            self.initialized = True  # Ustawiamy flagę, aby uniknąć ponownej inicjalizacji.

    def toggle_play_pause(self, file_path):
        """
        Przełącza stan odtwarzania dla danego pliku (play/pauza/wznów).

        Logika działania:
        - Jeśli kliknięto na plik, który jest już odtwarzany -> pauzuje go (stop).
        - Jeśli kliknięto na plik, który jest spauzowany -> wznawia go (play od nowa).
        - Jeśli kliknięto na nowy plik -> zatrzymuje stary i odtwarza nowy.
        - Jeśli nic nie jest odtwarzane -> odtwarza kliknięty plik.
        """
        # Scenariusz 1: Kliknięto przycisk "pauza" dla aktualnie odtwarzanego pliku.
        if self.is_playing and self.current_file == file_path:
            self.audio_player.pause()
            self.is_playing = False
            self.is_paused = True
        # Scenariusz 2: Kliknięto przycisk "play" dla wstrzymanego pliku.
        elif self.is_paused and self.current_file == file_path:
            self.audio_player.unpause(file_path)
            self.is_playing = True
            self.is_paused = False
        # Scenariusz 3: Kliknięto "play" na nowym pliku (lub gdy nic nie gra).
        else:
            try:
                # Zatrzymujemy cokolwiek, co mogło być odtwarzane wcześniej.
                self.stop()

                # Używamy audioplayer dla wszystkich formatów
                self.audio_player.play_file(file_path)

                # Aktualizujemy stan odtwarzacza.
                self.current_file = file_path
                self.is_playing = True
                self.is_paused = False
            except Exception as e:
                print(f"Nie można odtworzyć pliku: {file_path}. Błąd: {e}")
                self.stop()

    def stop(self):
        """Zatrzymuje odtwarzanie i całkowicie resetuje stan odtwarzacza."""
        self.audio_player.stop()

        self.current_file = None
        self.is_playing = False
        self.is_paused = False

    def is_busy(self):
        """Sprawdza czy audioplayer jeszcze odtwarza."""
        return self.audio_player.is_busy()

    def get_state(self, file_path):
        """
        Zwraca stan odtwarzania dla konkretnego pliku.
        Używane przez `FilesView` do narysowania odpowiedniej ikony (play/pauza/stop).

        Zwraca:
            str: 'playing', 'paused', lub 'stopped'.
        """
        if self.current_file != file_path:
            return 'stopped'

        if self.is_playing:
            return 'playing'
        if self.is_paused:
            return 'paused'
        return 'stopped'