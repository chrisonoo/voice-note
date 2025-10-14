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
    Odtwarzacz audio używający PyAV do dekodowania i sounddevice do odtwarzania.
    Wspiera wszystkie formaty obsługiwane przez FFmpeg.
    Ma pełną funkcjonalność pauzy i wznowienia poprzez kontrolę wątku odtwarzania.
    """

    def __init__(self):
        self.container = None
        self.sample_rate = None  # Częstotliwość próbkowania
        self.current_file = None
        self.is_playing = False
        self.is_paused = False
        self.play_thread = None  # Wątek odtwarzania
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()

    def _decode_audio(self, file_path):
        """Otwiera plik audio/wideo i przygotowuje do streamingu."""
        try:
            container = av.open(file_path)
            if not container.streams.audio:
                container.close()
                return None, None
            stream = container.streams.audio[0]
            return container, stream
        except av.AVError as e:
            print(f"Błąd PyAV podczas otwierania pliku {file_path}: {e}")
            return None, None
        except Exception as e:
            print(f"Nieoczekiwany błąd podczas otwierania pliku {file_path}: {e}")
            return None, None

    def _play_audio_thread(self, container, stream):
        """Wątek odtwarzający audio bezpośrednio ze streamu PyAV."""
        try:
            self.sample_rate = stream.rate
            for frame in container.decode(stream):
                if self.stop_event.is_set():
                    break

                self.pause_event.wait()

                audio_array = frame.to_ndarray()
                if audio_array.ndim > 1:
                    audio_array = np.mean(audio_array, axis=0)

                audio_data = audio_array.astype(np.float32)

                if audio_data.size > 0:
                    sd.play(audio_data, self.sample_rate, blocking=True)
        except (av.AVError, sd.PortAudioError) as e:
            print(f"Błąd biblioteki audio podczas odtwarzania: {e}")
        except Exception as e:
            print(f"Nieoczekiwany błąd podczas odtwarzania audio: {e}")
        finally:
            self.stop()
            if container:
                container.close()

    def play_file(self, file_path, stop_first=True):
        """Rozpoczyna odtwarzanie pliku."""
        if not os.path.exists(file_path):
            print(f"Plik nie istnieje: {file_path}")
            return

        if is_video_file(file_path):
            print(f"Plik wideo {os.path.basename(file_path)} - odtwarzanie ścieżki audio...")

        if stop_first:
            self.stop()

        container, stream = self._decode_audio(file_path)
        if not container or not stream:
            print(f"Nie można zdekodować pliku: {file_path}")
            return

        self.container = container
        self.current_file = file_path
        self.is_playing = True
        self.is_paused = False

        self.stop_event.clear()
        self.pause_event.set()

        self.play_thread = threading.Thread(target=self._play_audio_thread, args=(container, stream), daemon=True)
        self.play_thread.start()

    def pause(self):
        """Wstrzymuje odtwarzanie."""
        if self.is_playing and not self.is_paused:
            self.pause_event.clear()
            self.is_paused = True

    def unpause(self, file_path=None):
        """Wznawia odtwarzanie."""
        if self.is_paused:
            self.pause_event.set()
            self.is_paused = False

    def stop(self):
        """Zatrzymuje odtwarzanie."""
        self.stop_event.set()
        self.pause_event.set()

        try:
            sd.stop()
        except Exception as e:
            print(f"Błąd przy zatrzymywaniu sounddevice: {e}")

        if self.play_thread and self.play_thread.is_alive():
            self.play_thread.join(timeout=0.5)

        if self.container:
            self.container.close()
            self.container = None

        self.current_file = None
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