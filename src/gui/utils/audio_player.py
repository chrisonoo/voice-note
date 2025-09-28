# Ten moduł zawiera klasę `AudioPlayer`, która jest klasą pomocniczą
# odpowiedzialną za odtwarzanie próbek audio bezpośrednio w interfejsie.

import pygame  # Główna biblioteka do obsługi multimediów, w tym dźwięku.
import threading  # Używany do zapewnienia bezpieczeństwa wątkowego przy tworzeniu Singletonu.
from pydub import AudioSegment  # Potężna biblioteka do manipulacji plikami audio.
import io  # Moduł do obsługi operacji I/O w pamięci (traktowania danych binarnych jak pliku).

class AudioPlayer:
    """
    Zarządza odtwarzaniem plików audio przy użyciu `pygame.mixer`.
    Zapewnia, że w danym momencie odtwarzany jest tylko jeden plik.
    Została zaimplementowana jako Singleton, aby zagwarantować istnienie
    tylko jednej, globalnej instancji odtwarzacza w całej aplikacji.
    Konwertuje pliki do formatu WAV w pamięci RAM przed odtworzeniem,
    dzięki czemu nie trzeba tworzyć tymczasowych plików na dysku.
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
            pygame.mixer.init()  # Inicjalizujemy mikser pygame.
            self.current_file = None  # Ścieżka do aktualnie odtwarzanego pliku.
            self.is_playing = False  # Flaga, czy coś jest aktywnie odtwarzane.
            self.is_paused = False  # Flaga, czy odtwarzanie jest wstrzymane.
            self.initialized = True  # Ustawiamy flagę, aby uniknąć ponownej inicjalizacji.

    def toggle_play_pause(self, file_path):
        """
        Przełącza stan odtwarzania dla danego pliku (play/pauza/wznów).

        Logika działania:
        - Jeśli kliknięto na plik, który jest już odtwarzany -> pauzuje go.
        - Jeśli kliknięto na plik, który jest spauzowany -> wznawia go.
        - Jeśli kliknięto na nowy plik (a inny jest odtwarzany) -> zatrzymuje stary i odtwarza nowy.
        - Jeśli nic nie jest odtwarzane -> odtwarza kliknięty plik.
        """
        # Scenariusz 1: Kliknięto przycisk "pauza" dla aktualnie odtwarzanego pliku.
        if self.is_playing and self.current_file == file_path:
            pygame.mixer.music.pause()
            self.is_playing = False
            self.is_paused = True
        # Scenariusz 2: Kliknięto przycisk "play" dla wstrzymanego pliku.
        elif self.is_paused and self.current_file == file_path:
            pygame.mixer.music.unpause()
            self.is_playing = True
            self.is_paused = False
        # Scenariusz 3: Kliknięto "play" na nowym pliku (lub gdy nic nie gra).
        else:
            try:
                # Zatrzymujemy cokolwiek, co mogło być odtwarzane wcześniej.
                pygame.mixer.music.stop()

                # --- Konwersja w locie (on-the-fly) do formatu WAV w pamięci RAM ---
                # 1. Ładujemy plik w dowolnym formacie (np. mp3, m4a) za pomocą biblioteki pydub.
                audio_segment = AudioSegment.from_file(file_path)

                # 2. Tworzymy w pamięci obiekt, który zachowuje się jak plik binarny (bufor).
                wav_io = io.BytesIO()

                # 3. Eksportujemy załadowany segment audio do formatu WAV, ale zamiast zapisywać go
                #    na dysku, zapisujemy go do naszego bufora w pamięci.
                audio_segment.export(wav_io, format="wav")

                # 4. Po zapisie, "wskaźnik" w buforze jest na końcu. Musimy go przewinąć na początek,
                #    aby pygame mógł odczytać dane od początku.
                wav_io.seek(0)

                # 5. Ładujemy dane audio w formacie WAV bezpośrednio z bufora w pamięci do pygame.
                pygame.mixer.music.load(wav_io)
                pygame.mixer.music.play()

                # Aktualizujemy stan odtwarzacza.
                self.current_file = file_path
                self.is_playing = True
                self.is_paused = False
            except Exception as e:
                print(f"Nie można odtworzyć pliku: {file_path}. Błąd: {e}")
                self.stop()

    def stop(self):
        """Zatrzymuje odtwarzanie i całkowicie resetuje stan odtwarzacza."""
        pygame.mixer.music.stop()
        try:
            # `unload` zwalnia zasoby załadowanego pliku. Może rzucić błąd, jeśli nic nie jest załadowane.
            pygame.mixer.music.unload()
        except pygame.error:
            pass
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