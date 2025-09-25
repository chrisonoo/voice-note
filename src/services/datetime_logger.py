# Ten moduł zawiera prostą funkcję pomocniczą do generowania znaczników czasowych.
# UWAGA: Po refaktoryzacji, ten moduł nie jest aktywnie używany w głównym
# przepływie aplikacji (`main.py`), ale pozostaje jako dobry przykład
# tworzenia małych, użytecznych narzędzi.

from datetime import datetime


def logger():
    """
    Zwraca sformatowany znacznik czasowy.
    Przykład: `[2023.10.27 10:30:00.123:]`
    """
    # Wywołuje prywatną funkcję `__current_time`, aby uzyskać czas,
    # a następnie formatuje go w czytelny sposób.
    return f'[{__current_time()}:]\n'


def __current_time():
    """
    Prywatna funkcja pomocnicza (oznaczona `__` na początku) do pobierania
    i formatowania aktualnego czasu.
    """
    # `datetime.now()` pobiera aktualny czas.
    # `strftime(...)` formatuje go do postaci "Rok.Miesiąc.Dzień Godzina:Minuta:Sekunda.Milisekundy".
    # `[:-3]` na końcu obcina trzy ostatnie znaki (mikrosekundy), zostawiając tylko milisekundy,
    # co jest bardziej czytelne.
    return datetime.now().strftime("%Y.%m.%d %H:%M:%S.%f")[:-3]