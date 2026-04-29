# Moduł zawierający dekoratory do obsługi błędów i monitoringu wydajności

import contextlib
import functools
import logging
import os
import time
from collections.abc import Callable
from typing import Any, TypeVar, cast

F = TypeVar("F", bound=Callable[..., Any])

# Skonfiguruj logging dla błędów
logging.basicConfig(
    filename="voice_note_errors.log",
    level=logging.ERROR,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


def with_error_handling(operation_name: str) -> Callable[[F], F]:
    """
    Dekorator do bezpiecznego wykonywania operacji z obsługą błędów.

    Argumenty:
        operation_name (str): Nazwa operacji dla logowania błędów.
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_msg = f"[{operation_name}] Krytyczny błąd: {e}"
                print(error_msg)
                logging.error(f"{operation_name}: {e}", exc_info=True)

                # Jeśli mamy dostęp do GUI, pokaż błąd użytkownikowi
                if hasattr(args[0] if args else None, "show_error"):
                    with contextlib.suppress(BaseException):
                        args[0].show_error(f"Błąd w {operation_name}: {str(e)}")

                return None

        return cast(F, wrapper)

    return decorator


def measure_performance(func: F) -> F:
    """
    Dekorator do mierzenia czasu wykonania funkcji.
    Loguje tylko operacje dłuższe niż 1 sekundę.
    """

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()

        execution_time = end_time - start_time
        if execution_time > 1.0:  # Loguj tylko wolne operacje
            print(f"[PERF] {func.__name__} wykonał się w {execution_time:.2f}s")

        return result

    return cast(F, wrapper)


def validate_file_access(func: F) -> F:
    """
    Dekorator sprawdzający dostępność plików przed przetworzeniem.
    """

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        from src import database

        # Znajdź argumenty zawierające ścieżki plików
        file_paths: list[str] = []
        for arg in args:
            if isinstance(arg, str) and (
                arg.endswith((".mp3", ".wav", ".m4a", ".mp4", ".wma")) or os.path.isfile(arg)
            ):
                file_paths.append(arg)

        # Sprawdź dostępność plików
        invalid_files: list[tuple[str, str]] = []
        for path in file_paths:
            is_valid, error_msg = database.validate_file_access(path)
            if not is_valid:
                invalid_files.append((path, error_msg))

        if invalid_files:
            error_details = "\n".join(
                [f"{os.path.basename(path)}: {msg}" for path, msg in invalid_files]
            )
            raise FileNotFoundError(f"Następujące pliki są niedostępne:\n{error_details}")

        return func(*args, **kwargs)

    return cast(F, wrapper)
