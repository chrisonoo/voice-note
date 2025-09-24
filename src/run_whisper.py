from whisper import Whisper
from services import print_completion

audio = "rec.mp3"
response_format = "json"
prompt = ""
temperature = 0


def run():
    whisper = Whisper(audio, response_format, prompt, temperature)
    transcription = whisper.transcribe()

    print_completion(
        transcription,
        "message_whisper",
        datetime=True,
        new_line=True,
        first_empty_line=True,
    )
    print_completion(transcription, datetime=True, new_line=True)


if __name__ == "__main__":
    run()
