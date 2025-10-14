# Ten moduł zawiera klasę `AudioPlayer`, która jest klasą pomocniczą
# odpowiedzialną za odtwarzanie próbek audio bezpośrednio w interfejsie.

import threading  # Używany do zapewnienia bezpieczeństwa wątkowego przy tworzeniu Singletonu.
import os  # Do sprawdzania istnienia plików
import av  # PyAV do dekodowania audio
import sounddevice as sd  # Do odtwarzania audio przez głośniki
import numpy as np  # Do przetwarzania tablic audio
from src.utils.file_type_helper import is_video_file  # Do sprawdzania typu pliku

class AudioPlayerWrapper:
    """
    Prosty odtwarzacz audio używający PyAV do dekodowania i sounddevice do odtwarzania.
    Wspiera wszystkie formaty obsługiwane przez FFmpeg.
    """

    def __init__(self):
        self.current_file = None
        self.audio_data = None  # Zdekodowane dane audio
        self.sample_rate = None
        self.is_playing = False
        self.is_paused = False

    def _decode_audio(self, file_path):
        """Dekoduje cały plik audio do numpy array."""
        try:
            container = av.open(file_path)
            if not container.streams.audio:
                container.close()
                return None, None

            stream = container.streams.audio[0]
            audio_frames = []

            # Dekoduj wszystkie ramki
            for frame in container.decode(stream):
                audio_array = frame.to_ndarray()
                if audio_array.ndim > 1:
                    audio_array = np.mean(audio_array, axis=0)  # Konwertuj na mono
                audio_frames.append(audio_array.astype(np.float32))

            container.close()

            if audio_frames:
                # Połącz wszystkie ramki w jedną tablicę
                audio_data = np.concatenate(audio_frames)
                return audio_data, stream.rate

            return None, None

        except av.AVError as e:
            print(f"Błąd PyAV podczas otwierania pliku {file_path}: {e}")
            return None, None
        except Exception as e:
            print(f"Nieoczekiwany błąd podczas otwierania pliku {file_path}: {e}")
            return None, None

    def play_file(self, file_path, stop_first=True):
        """Rozpoczyna odtwarzanie pliku."""
        if not os.path.exists(file_path):
            print(f"Plik nie istnieje: {file_path}")
            return

        if is_video_file(file_path):
            print(f"Plik wideo {os.path.basename(file_path)} - odtwarzanie ścieżki audio...")

        if stop_first:
            self.stop()

        # Dekoduj plik jeśli to nowy plik lub jeszcze nie zdekodowany
        if self.current_file != file_path or self.audio_data is None:
            audio_data, sample_rate = self._decode_audio(file_path)
            if audio_data is None or sample_rate is None:
                print(f"Nie można zdekodować pliku: {file_path}")
                return

            self.audio_data = audio_data
            self.sample_rate = sample_rate
            self.current_file = file_path

        # Rozpocznij odtwarzanie
        try:
            sd.play(self.audio_data, self.sample_rate)
            self.is_playing = True
            self.is_paused = False
        except Exception as e:
            print(f"Błąd podczas odtwarzania: {e}")
            self.is_playing = False

    def pause(self):
        """Wstrzymuje odtwarzanie."""
        if self.is_playing and not self.is_paused:
            sd.stop()
            self.is_paused = True
            self.is_playing = False

    def unpause(self, file_path=None):
        """Wznawia odtwarzanie od początku."""
        if self.is_paused and self.audio_data is not None:
            try:
                sd.play(self.audio_data, self.sample_rate)
                self.is_playing = True
                self.is_paused = False
            except Exception as e:
                print(f"Błąd podczas wznawiania: {e}")

    def stop(self):
        """Zatrzymuje odtwarzanie."""
        try:
            sd.stop()
        except Exception as e:
            print(f"Błąd przy zatrzymywaniu sounddevice: {e}")

        self.current_file = None
        self.audio_data = None
        self.sample_rate = None
        self.is_playing = False
        self.is_paused = False

    def is_busy(self):
        """Sprawdza czy odtwarzacz jeszcze odtwarza."""
        return self.is_playing and not self.is_paused

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
    Zarządza odtwarzaniem plików audio przy użyciu PyAV i sounddevice.
    Zapewnia, że w danym momencie odtwarzany jest tylko jeden plik.
    Została zaimplementowana jako Singleton, aby zagwarantować istnienie
    tylko jednej, globalnej instancji odtwarzacza w całej aplikacji.

    Używa PyAV do dekodowania wszystkich formatów audio i sounddevice do odtwarzania.
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

    def toggle_play_pause(self, file_path, playback_path=None):
        """
        Przełącza stan odtwarzania dla danego pliku (play/pauza/wznów).

        Logika działania:
        - Jeśli kliknięto na plik, który jest już odtwarzany -> pauzuje go (stop).
        - Jeśli kliknięto na plik, który jest spauzowany -> wznawia go (play od nowa).
        - Jeśli kliknięto na nowy plik -> zatrzymuje stary i odtwarza nowy.
        - Jeśli nic nie jest odtwarzane -> odtwarza kliknięty plik.
        """
        # Jeśli nie podano playback_path, użyj file_path
        if playback_path is None:
            playback_path = file_path

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

                # Używamy PyAV + sounddevice dla wszystkich formatów
                self.audio_player.play_file(playback_path)

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