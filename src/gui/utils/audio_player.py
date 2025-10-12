# Ten moduł zawiera klasę `AudioPlayer`, która jest klasą pomocniczą
# odpowiedzialną za odtwarzanie próbek audio bezpośrednio w interfejsie.

import threading  # Używany do zapewnienia bezpieczeństwa wątkowego przy tworzeniu Singletonu.
import subprocess  # Do uruchamiania ffplay.
import psutil  # Do zarządzania procesami systemowymi

class FFplayAudioPlayer:
    """
    Odtwarzacz audio używający ffplay (część ffmpeg) do obsługi wszystkich formatów audio.
    Wspiera WMA, M4A, MP4 i inne formaty bez konwersji.
    Używa tylko play/stop - pauza nie jest wspierana dla uproszczenia.
    """

    def __init__(self):
        self.process = None
        self.current_file = None
        self.is_playing = False

    def play_file(self, file_path, stop_first=True):
        """Rozpoczyna odtwarzanie pliku."""
        if stop_first:
            self.stop()  # Zatrzymaj ewentualne poprzednie odtwarzanie

        try:
            # Uruchamiamy ffplay z parametrami do cichego odtwarzania
            self.process = subprocess.Popen([
                'ffplay',
                '-nodisp',  # Bez okna graficznego
                '-autoexit',  # Zamknij po zakończeniu odtwarzania
                '-loglevel', 'quiet',  # Bez logów
                file_path
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            self.current_file = file_path
            self.is_playing = True

        except Exception as e:
            print(f"Nie można odtworzyć pliku przez ffplay: {file_path}. Błąd: {e}")
            self.stop()

    def pause(self):
        """Wstrzymuje odtwarzanie - uproszczone do stop."""
        self.stop()

    def unpause(self):
        """Wznawia odtwarzanie - uproszczone do ponownego play."""
        if self.current_file:
            self.play_file(self.current_file, stop_first=False)

    def stop(self):
        """Zatrzymuje odtwarzanie."""
        # Zabijamy wszystkie procesy ffplay w systemie
        try:
            for proc in psutil.process_iter(['pid', 'name']):
                if proc.info['name'] == 'ffplay.exe':
                    proc.kill()
        except:
            pass

        self.process = None
        self.current_file = None
        self.is_playing = False

    def get_state(self, file_path):
        """Zwraca stan odtwarzania dla danego pliku."""
        if self.current_file == file_path and self.is_playing:
            return 'playing'
        return 'stopped'

class AudioPlayer:
    """
    Zarządza odtwarzaniem plików audio przy użyciu `ffplay`.
    Zapewnia, że w danym momencie odtwarzany jest tylko jeden plik.
    Została zaimplementowana jako Singleton, aby zagwarantować istnienie
    tylko jednej, globalnej instancji odtwarzacza w całej aplikacji.

    Używa ffplay dla wszystkich formatów audio bez konwersji.
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
        # (np. `AudioPlayer()`), ale właściwa inicjalizacja stanu (pygame, zmienne)
        # odbywa się tylko raz, dzięki fladze `self.initialized`.
        if not hasattr(self, 'initialized'):
            self.ffplay_player = FFplayAudioPlayer()  # Player dla wszystkich formatów
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
            self.ffplay_player.pause()
            self.is_playing = False
            self.is_paused = True
        # Scenariusz 2: Kliknięto przycisk "play" dla wstrzymanego pliku.
        elif self.is_paused and self.current_file == file_path:
            self.ffplay_player.unpause()
            self.is_playing = True
            self.is_paused = False
        # Scenariusz 3: Kliknięto "play" na nowym pliku (lub gdy nic nie gra).
        else:
            try:
                # Zatrzymujemy cokolwiek, co mogło być odtwarzane wcześniej.
                self.stop()

                # Używamy ffplay dla wszystkich formatów
                self.ffplay_player.play_file(file_path)

                # Aktualizujemy stan odtwarzacza.
                self.current_file = file_path
                self.is_playing = True
                self.is_paused = False
            except Exception as e:
                print(f"Nie można odtworzyć pliku: {file_path}. Błąd: {e}")
                self.stop()

    def stop(self):
        """Zatrzymuje odtwarzanie i całkowicie resetuje stan odtwarzacza."""
        self.ffplay_player.stop()

        self.current_file = None
        self.is_playing = False
        self.is_paused = False

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