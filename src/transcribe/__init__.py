# Plik __init__.py w folderze `transcribe` pełni dwie kluczowe funkcje:
# 1. Informuje Pythona, że ten folder powinien być traktowany jako pakiet (moduł),
#    co pozwala na organizowanie kodu w logiczne, oddzielne jednostki.
# 2. Upraszcza importowanie klas i funkcji z tego modułu w innych częściach aplikacji.

# Poniższa linia importuje klasę `TranscriptionProcessor` z pliku `transcription_processor.py`.
# Dzięki temu, zamiast pisać `from src.transcribe.transcription_processor import TranscriptionProcessor`,
# możemy użyć krótszej i bardziej czytelnej formy: `from src.transcribe import TranscriptionProcessor`.
from .transcription_processor import TranscriptionProcessor