# Ten plik __init__.py w folderze `whisper` pełni dwie kluczowe funkcje:
# 1. Informuje Pythona, że ten folder powinien być traktowany jako pakiet (moduł).
#    Dzięki temu kod związany bezpośrednio z obsługą API Whisper jest logicznie oddzielony.
# 2. Upraszcza importowanie klas i funkcji z tego modułu w innych częściach aplikacji.

# Poniższa linia importuje klasę `Whisper` z pliku `whisper.py` w tym samym folderze.
# Pozwala to na używanie krótszego, bardziej intuicyjnego importu w innych miejscach,
# np. `from src.whisper import Whisper` zamiast `from src.whisper.whisper import Whisper`.
from .whisper import Whisper