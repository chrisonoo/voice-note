# Ten moduł zawiera klasę `WhisperService`, która jest "opakowaniem" (wrapperem)
# dla API Audio Transcriptions od OpenAI. Jej zadaniem jest uproszczenie
# procesu wysyłania pliku audio i otrzymywania transkrypcji, ukrywając
# szczegóły implementacyjne komunikacji z API.

import os  # Moduł do interakcji z systemem operacyjnym, używany tutaj do odczytu zmiennych środowiskowych.
from dotenv import load_dotenv  # Funkcja do wczytywania zmiennych z pliku .env.
from openai import OpenAI  # Główna klasa z biblioteki OpenAI do komunikacji z API.
from src import config  # Importujemy nasz plik konfiguracyjny.

# `load_dotenv()` to kluczowa funkcja, która szuka w głównym folderze projektu
# pliku o nazwie `.env`. Jeśli go znajdzie, wczytuje zdefiniowane w nim zmienne
# (np. API_KEY_WHISPER="sk-...") i udostępnia je jako zmienne środowiskowe dla aplikacji.
# Dzięki temu klucz API jest bezpiecznie oddzielony od kodu źródłowego.
load_dotenv()


class WhisperService:
    """
    Serwis dedykowany do interakcji z API OpenAI Whisper.
    Każdy obiekt tej klasy jest odpowiedzialny za transkrypcję jednego pliku audio.
    """
    def __init__(self, audio_path):
        """
        Inicjalizuje klienta Whisper, przygotowując go do transkrypcji konkretnego pliku.

        Argumenty:
            audio_path (str): Ścieżka do pliku audio, który ma zostać przetworzony.
        """
        # Przechowujemy ścieżkę do pliku audio wewnątrz obiektu, aby była dostępna w innych metodach.
        self.audio_path = audio_path
        # `os.getenv` odczytuje zmienną środowiskową. W tym przypadku szuka klucza API,
        # który został wczytany z pliku .env przez `load_dotenv()`.
        self.api_key = os.getenv("API_KEY_WHISPER")
        # Tworzymy instancję klienta OpenAI, przekazując mu nasz klucz API.
        # Ten obiekt `client` będzie naszym głównym narzędziem do wysyłania zapytań do serwerów OpenAI.
        self.client = OpenAI(api_key=self.api_key)

    def transcribe(self):
        """
        Wysyła plik audio do API OpenAI Whisper w celu wykonania transkrypcji.
        Metoda ta zarządza całym procesem: otwiera plik, wysyła zapytanie,
        obsługuje potencjalne błędy i zwraca wynik.
        """
        try:
            # `try...except` to mechanizm obsługi błędów. Kod w bloku `try` jest wykonywany,
            # a jeśli wystąpi błąd określonego typu (np. `FileNotFoundError`), program nie przerywa działania,
            # lecz wykonuje kod z odpowiedniego bloku `except`.

            # Używamy konstrukcji `with open(...)`, która jest zalecanym sposobem pracy z plikami w Pythonie.
            # 'rb' oznacza tryb odczytu binarnego (read binary), który jest konieczny dla plików multimedialnych.
            # `as audio_file` przypisuje otwarty plik do zmiennej `audio_file`.
            # Najważniejszą zaletą `with` jest to, że plik zostanie automatycznie i bezpiecznie zamknięty
            # po zakończeniu bloku, nawet jeśli w środku wystąpi błąd.
            with open(self.audio_path, "rb") as audio_file:
                # Przygotowujemy parametry dla wywołania API - wszystkie ustawienia pobieramy z konfiguracji
                api_params = {
                    "model": config.WHISPER_API_MODEL,  # Wskazujemy, którego modelu użyć.
                    "file": audio_file,  # Przekazujemy otwarty plik binarny.
                    "language": config.WHISPER_API_LANGUAGE,  # Wskazujemy język nagrania.
                    "prompt": config.WHISPER_API_PROMPT,
                    "temperature": config.WHISPER_API_TEMPERATURE,
                    "response_format": config.WHISPER_API_RESPONSE_FORMAT
                }

                # Dodajemy timestamp_granularities tylko jeśli lista nie jest pusta
                if config.WHISPER_API_TIMESTAMP_GRANULARITIES:
                    api_params["timestamp_granularities"] = config.WHISPER_API_TIMESTAMP_GRANULARITIES

                # Wywołujemy metodę `transcriptions.create` na naszym kliencie OpenAI.
                # Jest to właściwe zapytanie do API o wykonanie transkrypcji.
                transcript = self.client.audio.transcriptions.create(**api_params)
            # Jeśli zapytanie do API się powiodło, zwracamy otrzymany obiekt transkrypcji.
            return transcript
        except FileNotFoundError:
            # Ten blok zostanie wykonany, jeśli plik pod ścieżką `self.audio_path` nie zostanie znaleziony.
            print(f"    BŁĄD: Nie znaleziono pliku audio: {self.audio_path}")
            # Zwracamy `None`, aby funkcja, która wywołała tę metodę, wiedziała, że operacja się nie powiodła.
            return None
        except Exception as e:
            # Ten blok `except` jest ogólny - "łapie" wszystkie inne, nieprzewidziane błędy.
            # Mogą to być problemy z połączeniem internetowym, błędy po stronie serwera OpenAI,
            # nieprawidłowy klucz API itp.
            print(f"    BŁĄD: Wystąpił nieoczekiwany błąd podczas transkrypcji pliku {self.audio_path}: {e}")
            # Również zwracamy `None` w przypadku błędu.
            return None
