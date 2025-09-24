import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


class Whisper:
    def __init__(self, audio, response_format, prompt, temperature):
        self.audio = open(audio, "rb")
        self.model = "whisper-1"
        self.response_format = response_format
        self.language = "pl"
        self.prompt = prompt
        self.temperature = temperature
        self.api_key = os.getenv("API_KEY_WHISPER")
        self.client = OpenAI(api_key=self.api_key)

    def __get_transcription(self):
        transcript = self.client.audio.transcriptions.create(
            model=self.model,
            file=self.audio,
            language=self.language,
            prompt=self.prompt,
            temperature=self.temperature,
            response_format=self.response_format
        )
        # return transcript.replace("\n", "")
        return transcript

    def transcribe(self):
        return self.__get_transcription()
