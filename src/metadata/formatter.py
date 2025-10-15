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

