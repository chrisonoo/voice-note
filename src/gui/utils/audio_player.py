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
        self.audio_data = None  # Numpy array z dekodowanym audio
        self.sample_rate = None  # Częstotliwość próbkowania
        self.current_file = None
        self.is_playing = False
        self.is_paused = False
        self.play_thread = None  # Wątek odtwarzania
        self.stop_event = None  # Event do zatrzymania odtwarzania
        self.pause_event = None  # Event do pauzy

    def _decode_audio(self, file_path):
        """Dekoduje plik audio do numpy array używając PyAV."""
        try:
            container = av.open(file_path)
            stream = container.streams.audio[0]

            # Zbieramy wszystkie próbki audio
            audio_frames = []
            for frame in container.decode(stream):
                # Konwertujemy do numpy array
                audio_array = frame.to_ndarray()
                # Jeśli stereo, konwertujemy do mono poprzez uśrednienie kanałów
                if audio_array.ndim > 1:
                    audio_array = np.mean(audio_array, axis=0)
                audio_frames.append(audio_array)

            # Łączymy wszystkie ramki w jedną tablicę
            if audio_frames:
                audio_data = np.concatenate(audio_frames)
                sample_rate = stream.rate
                container.close()
                return audio_data, sample_rate
            else:
                container.close()
                return None, None

        except Exception as e:
            print(f"Błąd podczas dekodowania pliku {file_path}: {e}")
            return None, None

    def _play_audio_thread(self):
        """Wątek odtwarzający audio z obsługą pauzy."""
        try:
            # Znajdź domyślne urządzenie wyjściowe
            device = sd.default.device[1]  # Output device
            sd.default.device = (None, device)  # Ustaw domyślne urządzenie wyjściowe

            # Odtwarzaj audio z obsługą pauzy
            start_idx = 0
            chunk_size = self.sample_rate // 10  # 100ms chunks

            while start_idx < len(self.audio_data) and not self.stop_event.is_set():
                if self.pause_event.is_set():
                    # Pauza - czekaj aż zostanie wznowione
                    self.pause_event.wait()
                    continue

                end_idx = min(start_idx + chunk_size, len(self.audio_data))
                chunk = self.audio_data[start_idx:end_idx]

                # Odtwarzaj chunk
                sd.play(chunk, self.sample_rate, blocking=True)

                start_idx = end_idx

        except Exception as e:
            print(f"Błąd podczas odtwarzania audio: {e}")
        finally:
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
            # Dekoduj plik audio
            audio_data, sample_rate = self._decode_audio(file_path)
            if audio_data is None:
                print(f"Nie można zdekodować pliku: {file_path}")
                return

            self.audio_data = audio_data
            self.sample_rate = sample_rate
            self.current_file = file_path

            # Przygotuj events dla kontroli odtwarzania
            self.stop_event = threading.Event()
            self.pause_event = threading.Event()
            self.pause_event.set()  # Rozpocznij bez pauzy

            # Uruchom wątek odtwarzania
            self.play_thread = threading.Thread(target=self._play_audio_thread, daemon=True)
            self.play_thread.start()

            self.is_playing = True
            self.is_paused = False

        except Exception as e:
            print(f"Nie można odtworzyć pliku: {file_path}. Błąd: {e}")
            self.stop()

    def pause(self):
        """Wstrzymuje odtwarzanie."""
        if self.is_playing and not self.is_paused and self.pause_event:
            self.pause_event.clear()  # Wyczyść event - pauza
            self.is_paused = True

    def unpause(self, file_path=None):
        """Wznawia odtwarzanie."""
        if self.is_paused and self.pause_event:
            self.pause_event.set()  # Ustaw event - wznowienie
            self.is_paused = False

    def stop(self):
        """Zatrzymuje odtwarzanie."""
        if self.stop_event:
            self.stop_event.set()  # Ustaw event stop

        if self.pause_event:
            self.pause_event.set()  # Upewnij się że pauza jest zdjęta

        # Zatrzymaj sounddevice jeśli coś gra
        try:
            sd.stop()
        except:
            pass  # Ignoruj błędy

        # Poczekaj na zakończenie wątku
        if self.play_thread and self.play_thread.is_alive():
            self.play_thread.join(timeout=1.0)

        # Wyczyść stan
        self.audio_data = None
        self.sample_rate = None
        self.current_file = None
        self.is_playing = False
        self.is_paused = False
        self.play_thread = None
        self.stop_event = None
        self.pause_event = None

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

                # Używamy PyAV + sounddevice dla wszystkich formatów
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