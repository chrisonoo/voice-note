# Ten moduł zawiera wszechstronną funkcję do formatowania i drukowania
# odpowiedzi z API OpenAI.
# UWAGA: Po refaktoryzacji, ten moduł nie jest aktywnie używany w głównym
# przepływie aplikacji (`main.py`), ponieważ logikę drukowania uproszczono
# i zintegrowano bezpośrednio w innych modułach. Pozostaje on jednak jako
# świetny przykład bardziej zaawansowanej funkcji pomocniczej.

import json
from .datetime_logger import logger


def print_completion(
        completion,
        format_type="no",
        new_line=False,
        datetime=False,
        first_empty_line=False):
    """
    Drukuje odpowiedź z API OpenAI w różnych formatach.

    :param completion: Obiekt odpowiedzi zwrócony przez API OpenAI.
    :param format_type: Określa, jak sformatować odpowiedź ('json', 'message_chat', 'message_whisper').
    :param new_line: Czy dodać dwie nowe linie na końcu.
    :param datetime: Czy dodać znacznik czasowy na początku.
    :param first_empty_line: Czy dodać pustą linię na początku.
    """

    # `completion.model_dump_json()` to metoda obiektów Pydantic (używanych przez bibliotekę OpenAI),
    # która konwertuje obiekt odpowiedzi na string w formacie JSON.
    serialize_completion = completion.model_dump_json()

    # Operatory warunkowe (ternary operators) do ustawiania dodatkowych elementów formatowania.
    end_character = "\n\n" if new_line else ""
    datetime_logger = logger() if datetime else ""
    first_empty_line = "\n" if first_empty_line else ""

    # Sprawdzamy, jaki format wydruku został wybrany.
    if format_type == 'json':
        # `json.loads` konwertuje string JSON na obiekt Pythona.
        json_completion = json.loads(serialize_completion)
        # `json.dumps` konwertuje obiekt Pythona z powrotem na string JSON,
        # ale tym razem z wcięciami (`indent=4`) dla lepszej czytelności.
        print(f'{first_empty_line}{datetime_logger}{json.dumps(json_completion, indent=4)}',
              end=end_character)

    elif format_type == 'message_chat':
        # Dla odpowiedzi z czatu, interesuje nas treść wiadomości,
        # która znajduje się w `completion.choices[0].message.content`.
        message = completion.choices[0].message.content
        print(f'{first_empty_line}{datetime_logger}{message}', end=end_character)

    elif format_type == 'message_whisper':
        # Dla odpowiedzi z Whisper, interesuje nas tekst transkrypcji,
        # który znajduje się bezpośrednio w `completion.text`.
        text = completion.text
        print(f'{first_empty_line}{datetime_logger}{text}', end=end_character)

    else:
        # Jeśli nie podano specjalnego formatu, drukujemy surowy obiekt.
        print(f'{first_empty_line}{datetime_logger}{completion}', end=end_character)