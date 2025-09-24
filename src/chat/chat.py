import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


class Chat:
    def __init__(self, system, user, model, temperature, max_tokens):
        self.system = system
        self.user = user
        self.model = self.__choose_gpt_version(model)
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=self.api_key)

    @staticmethod
    def __choose_gpt_version(model):
        return "gpt-4-0125-preview" if model == 4 else "gpt-3.5-turbo-0125"

    def __form_messages(self):
        return [
            {
                "role": "system",
                "content": self.system
            },
            {
                "role": "user",
                "content": self.user
            }
        ]

    def __get_chat_completion(self):
        completion = self.client.chat.completions.create(
            model=self.model,
            messages=self.__form_messages(),
            temperature=self.temperature,
            max_tokens=self.max_tokens
        )
        return completion

    def ask(self):
        return self.__get_chat_completion()
