import pygame
import threading
from pydub import AudioSegment
import io
import os

class AudioPlayer:
    """
    Zarządza odtwarzaniem plików audio przy użyciu pygame.mixer.
    Zapewnia, że w danym momencie odtwarzany jest tylko jeden plik.
    Zaimplementowany jako Singleton, aby zagwarantować jedną instancję.
    Konwertuje pliki do formatu WAV w pamięci przed odtworzeniem.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        # Inicjalizator jest wywoływany przy każdym "tworzeniu" instancji,
        # ale stan jest inicjowany tylko raz.
        if not hasattr(self, 'initialized'):
            pygame.mixer.init()
            self.current_file = None
            self.is_playing = False
            self.is_paused = False
            self.initialized = True

    def toggle_play_pause(self, file_path):
        """
        Przełącza stan odtwarzania dla danego pliku.
        - Jeśli plik jest odtwarzany -> pauza.
        - Jeśli plik jest wstrzymany -> wznowienie.
        - Jeśli odtwarzany jest inny plik -> zatrzymanie go i odtworzenie nowego.
        - Jeśli nic nie jest odtwarzane -> odtworzenie pliku.
        """
        # Scenariusz 1: Kliknięto przycisk "pauza" dla aktualnie odtwarzanego pliku
        if self.is_playing and self.current_file == file_path:
            pygame.mixer.music.pause()
            self.is_playing = False
            self.is_paused = True
        # Scenariusz 2: Kliknięto przycisk "play" dla wstrzymanego pliku
        elif self.is_paused and self.current_file == file_path:
            pygame.mixer.music.unpause()
            self.is_playing = True
            self.is_paused = False
        # Scenariusz 3: Kliknięto przycisk "play" dla nowego pliku (lub gdy nic nie gra)
        else:
            try:
                # Zatrzymujemy cokolwiek, co mogło grać wcześniej
                pygame.mixer.music.stop()

                # --- Konwersja w locie do WAV w pamięci ---
                # 1. Załaduj plik dowolnego formatu za pomocą pydub
                audio_segment = AudioSegment.from_file(file_path)

                # 2. Utwórz bufor w pamięci
                wav_io = io.BytesIO()

                # 3. Wyeksportuj audio jako WAV do bufora
                audio_segment.export(wav_io, format="wav")

                # 4. Przewiń bufor na początek, aby pygame mógł go odczytać
                wav_io.seek(0)

                # 5. Załaduj dane WAV z pamięci do pygame
                pygame.mixer.music.load(wav_io)
                pygame.mixer.music.play()

                # Aktualizujemy stan
                self.current_file = file_path
                self.is_playing = True
                self.is_paused = False
            except Exception as e:
                print(f"Nie można odtworzyć pliku: {file_path}. Błąd: {e}")
                self.stop()

    def stop(self):
        """Zatrzymuje odtwarzanie i resetuje stan."""
        pygame.mixer.music.stop()
        try:
            # Unload może rzucić błąd, jeśli nic nie jest załadowane
            pygame.mixer.music.unload()
        except pygame.error:
            pass
        self.current_file = None
        self.is_playing = False
        self.is_paused = False

    def get_state(self, file_path):
        """
        Zwraca stan odtwarzania dla konkretnego pliku.
        Możliwe stany: 'playing', 'paused', 'stopped'.
        """
        if self.current_file != file_path:
            return 'stopped'
        if self.is_playing:
            return 'playing'
        if self.is_paused:
            return 'paused'
        return 'stopped'