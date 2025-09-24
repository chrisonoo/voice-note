import os
from dotenv import load_dotenv
from openai import OpenAI
from src import config

load_dotenv()


class Whisper:
    def __init__(self, audio_path):
        """
        Inicjalizuje klienta Whisper.
        :param audio_path: Ścieżka do pliku audio, który ma być transkrybowany.
        """
        self.audio_path = audio_path
        self.model = "whisper-1"
        self.language = "pl"
        self.api_key = os.getenv("API_KEY_WHISPER")
        self.client = OpenAI(api_key=self.api_key)

    def transcribe(self):
        """
        Wysyła plik audio do API OpenAI Whisper w celu transkrypcji.
        Prawidłowo zarządza otwieraniem i zamykaniem pliku.
        """
        try:
            with open(self.audio_path, "rb") as audio_file:
                transcript = self.client.audio.transcriptions.create(
                    model=self.model,
                    file=audio_file,
                    language=self.language,
                    prompt=config.WHISPER_API_PROMPT,
                    temperature=config.WHISPER_API_TEMPERATURE,
                    response_format=config.WHISPER_API_RESPONSE_FORMAT
                )
            return transcript
        except FileNotFoundError:
            print(f"    BŁĄD: Nie znaleziono pliku audio: {self.audio_path}")
            return None
        except Exception as e:
            print(f"    BŁĄD: Wystąpił nieoczekiwany błąd podczas transkrypcji pliku {self.audio_path}: {e}")
            return None