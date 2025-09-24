# Ten moduł zawiera klasę `Whisper`, która jest "opakowaniem" (wrapperem)
# dla API Audio Transcriptions od OpenAI. Jej zadaniem jest uproszczenie
# procesu wysyłania pliku audio i otrzymywania transkrypcji.

import os
from dotenv import load_dotenv
from openai import OpenAI
from src import config

# `load_dotenv()` wczytuje zmienne środowiskowe z pliku .env.
# Dzięki temu możemy bezpiecznie przechowywać nasz klucz API poza kodem źródłowym.
load_dotenv()


class Whisper:
    """
    Klasa do interakcji z API OpenAI Whisper.
    """
    def __init__(self, audio_path):
        """
        Inicjalizuje klienta Whisper.

        :param audio_path: Ścieżka do pliku audio, który ma być transkrybowany.
        """
        # Przechowujemy ścieżkę do pliku audio.
        self.audio_path = audio_path
        # Definiujemy, jakiego modelu chcemy użyć. "whisper-1" to główny model transkrypcji.
        self.model = "whisper-1"
        # Ustawiamy język na polski, co pomaga modelowi w uzyskaniu lepszych wyników.
        self.language = "pl"
        # Pobieramy klucz API ze zmiennych środowiskowych.
        # Ważne jest, aby nazwa "API_KEY_WHISPER" w pliku .env była taka sama.
        self.api_key = os.getenv("API_KEY_WHISPER")
        # Tworzymy instancję klienta OpenAI, przekazując mu nasz klucz API.
        # Ten obiekt będzie używany do komunikacji z serwerami OpenAI.
        self.client = OpenAI(api_key=self.api_key)

    def transcribe(self):
        """
        Wysyła plik audio do API OpenAI Whisper w celu transkrypcji.
        Ta metoda prawidłowo zarządza otwieraniem i zamykaniem pliku,
        co zapobiega błędom i wyciekom zasobów.
        """
        try:
            # Używamy `with open(...)`, aby otworzyć plik audio.
            # 'rb' oznacza tryb odczytu binarnego (read binary), co jest wymagane dla plików audio.
            # `as audio_file` przypisuje otwarty plik do zmiennej `audio_file`.
            # Po wyjściu z bloku `with`, plik zostanie automatycznie zamknięty.
            with open(self.audio_path, "rb") as audio_file:
                # Wywołujemy metodę `transcriptions.create` na naszym kliencie OpenAI.
                transcript = self.client.audio.transcriptions.create(
                    model=self.model,
                    file=audio_file,  # Przekazujemy otwarty plik
                    language=self.language,
                    prompt=config.WHISPER_API_PROMPT,
                    temperature=config.WHISPER_API_TEMPERATURE,
                    response_format=config.WHISPER_API_RESPONSE_FORMAT
                )
            # Jeśli wszystko poszło dobrze, zwracamy otrzymaną transkrypcję.
            return transcript
        except FileNotFoundError:
            # Jeśli plik pod podaną ścieżką nie istnieje, przechwytujemy błąd
            # i informujemy o tym użytkownika. Zwracamy `None`, aby funkcja,
            # która wywołała tę metodę, wiedziała, że coś poszło nie tak.
            print(f"    BŁĄD: Nie znaleziono pliku audio: {self.audio_path}")
            return None
        except Exception as e:
            # Przechwytujemy wszystkie inne, nieoczekiwane błędy (np. problemy z siecią,
            # błędy po stronie API) i wyświetlamy je. To również zwraca `None`.
            print(f"    BŁĄD: Wystąpił nieoczekiwany błąd podczas transkrypcji pliku {self.audio_path}: {e}")
            return None