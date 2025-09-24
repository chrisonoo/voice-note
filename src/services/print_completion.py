import json
from .datetime_logger import logger


def print_completion(
        completion,
        format_type="no",
        new_line=False,
        datetime=False,
        first_empty_line=False):

    serialize_completion = completion.model_dump_json()
    end_character = "\n\n" if new_line else ""
    datetime_logger = logger() if datetime else ""
    first_empty_line = "\n" if first_empty_line else ""

    if format_type == 'json':
        json_completion = json.loads(serialize_completion)
        print(f'{first_empty_line}{datetime_logger}{json.dumps(json_completion, indent=4)}',
              end=end_character)

    elif format_type == 'message_chat':
        message = completion.choices[0].message.content
        print(f'{first_empty_line}{datetime_logger}{message}', end=end_character)

    elif format_type == 'message_whisper':
        text = completion.text
        print(f'{first_empty_line}{datetime_logger}{text}', end=end_character)

    else:
        print(f'{first_empty_line}{datetime_logger}{completion}', end=end_character)
