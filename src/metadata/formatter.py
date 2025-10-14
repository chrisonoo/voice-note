# Metadata formatting module

from datetime import datetime, timedelta

def _format_timedelta_to_hms(td: timedelta):
    """Formatuje obiekt timedelta do czytelnego formatu HH:MM:SS."""
    if not isinstance(td, timedelta):
        return "00:00:00"
    total_seconds = int(td.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02}:{minutes:02}:{seconds:02}"

def _format_timedelta_to_mss(td: timedelta):
    """Formatuje obiekt timedelta do czytelnego formatu MM:SS.ms."""
    if not isinstance(td, timedelta):
        return "00:00.000"
    total_seconds = td.total_seconds()
    minutes, seconds = divmod(total_seconds, 60)
    milliseconds = td.microseconds // 1000
    return f"{int(minutes):02}:{int(seconds):02}.{milliseconds:03}"

def _create_file_tag(start_dt: datetime, end_dt: datetime, duration_ms: int, previous_ms: int):
    """
    Tworzy tag dla pliku na podstawie jego metadanych czasowych.
    Tag jest tworzony podczas przetwarzania metadanych, przed transkrypcją.
    """
    try:
        # Formatowanie dat i czasów
        start_str = start_dt.strftime('%Y-%m-%d %H:%M:%S')
        end_str = end_dt.strftime('%H:%M:%S.%f')[:-3]  # Bez daty, tylko czas

        # Czas trwania
        duration_td = timedelta(milliseconds=duration_ms)
        duration_str = _format_timedelta_to_mss(duration_td)

        # Czas od poprzedniego nagrania
        if previous_ms > 0:
            previous_td = timedelta(milliseconds=previous_ms)
            previous_str = _format_timedelta_to_hms(previous_td)
        else:
            previous_str = "00:00:00"

        return f"[START: {start_str} | END: {end_str} | DURATION: {duration_str} | PREVIOUS: {previous_str}]"

    except Exception as e:
        print(f"Błąd podczas tworzenia tagu: {e}")
        return "[TAG_ERROR]"

def format_transcription_header(file_metadata):
    """
    Tworzy sformatowany nagłówek tekstowy na podstawie metadanych z bazy.
    Funkcja jest odporna na brakujące dane (NULL w bazie).
    Obsługuje zarówno słowniki jak i obiekty sqlite3.Row.
    """
    if not file_metadata:
        return ""

    # Definiujemy domyślne wartości na wypadek błędów lub braku danych.
    start_str = "N/A"
    end_str = "N/A"
    duration_str = "N/A"
    previous_str = "N/A"

    try:
        # Próbujemy sformatować datę rozpoczęcia.
        # Używamy bezpośredniego dostępu [] zamiast .get(), bo sqlite3.Row nie ma metody .get()
        try:
            start_dt_str = file_metadata['start_datetime']
        except (KeyError, IndexError):
            start_dt_str = None

        if start_dt_str:
            start_dt = datetime.strptime(start_dt_str, '%Y-%m-%d %H:%M:%S')
            start_str = start_dt.strftime('%Y-%m-%d %H:%M:%S')

        # Próbujemy sformatować datę zakończenia.
        try:
            end_dt_str = file_metadata['end_datetime']
        except (KeyError, IndexError):
            end_dt_str = None

        if end_dt_str:
            end_dt = datetime.strptime(end_dt_str, '%Y-%m-%d %H:%M:%S.%f')
            end_str = end_dt.strftime('%H:%M:%S.%f')[:-3]

        # Próbujemy sformatować czas trwania.
        try:
            duration_ms = file_metadata['duration_ms']
        except (KeyError, IndexError):
            duration_ms = None

        if duration_ms is not None:
            duration_td = timedelta(milliseconds=duration_ms)
            duration_str = _format_timedelta_to_mss(duration_td)

        # Próbujemy sformatować przerwę od poprzedniego.
        try:
            previous_ms = file_metadata['previous_ms']
        except (KeyError, IndexError):
            previous_ms = None

        if previous_ms is not None:
            previous_td = timedelta(milliseconds=previous_ms)
            previous_str = _format_timedelta_to_hms(previous_td)

    except (TypeError, ValueError) as e:
        # W przypadku błędu parsowania, logujemy go, ale nie przerywamy działania.
        print(f"    OSTRZEŻENIE: Błąd podczas formatowania nagłówka transkrypcji: {e}")
        # Wartości pozostaną jako "N/A".

    # Zwracamy pusty string tylko jeśli brakuje kluczowej informacji o starcie.
    if start_str == "N/A":
        return ""

    return f"[START: {start_str} | END: {end_str} | DURATION: {duration_str} | PREVIOUS: {previous_str}]"
