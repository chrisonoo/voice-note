# Metadata processing module

import os
from datetime import datetime, timedelta
from typing import Any, cast

from src import config, database
from src.utils.audio.duration_checker import get_file_duration
from src.utils.error_handlers import measure_performance, with_error_handling

from .formatter import create_file_tag


@with_error_handling("Przetwarzanie metadanych")
@measure_performance
def process_and_update_all_metadata(allow_long: bool = False) -> list[str]:
    """
    Centralna funkcja do przetwarzania metadanych.
    Wczytuje pliki bez metadanych, sortuje je w pamięci wg daty modyfikacji,
    oblicza wszystkie metadane (w tym flagę `is_selected`), zapisuje je masowo do bazy
    i zwraca listę plików, które przekraczają limit długości.
    """
    print("\n--- Rozpoczynam centralne przetwarzanie metadanych ---")

    files_to_process = database.get_files_needing_metadata()
    if not files_to_process:
        print("Brak nowych plików do przetworzenia metadanych.")
        return []

    # Rozdziel pliki zwykłe od chunków
    regular_files = [f for f in files_to_process if f["parent_file_path"] is None]
    chunk_files = [f for f in files_to_process if f["parent_file_path"] is not None]

    try:
        # Przetwórz pliki zwykłe
        regular_metadata, regular_long_files = _process_regular_files_metadata(
            regular_files, allow_long
        )

        # Przetwórz chunk'y
        chunk_metadata = _process_chunk_files_metadata(chunk_files)

        all_metadata_to_update = regular_metadata + chunk_metadata
        long_files = regular_long_files

    except OSError as e:
        print(f"BŁĄD: Nie można posortować plików, problem z dostępem do pliku: {e}")
        return []

    if all_metadata_to_update:
        database.update_all_metadata_bulk(all_metadata_to_update)
        print(
            f"Pomyślnie przetworzono i zaktualizowano metadane dla "
            f"{len(all_metadata_to_update)} plików."
        )

    print("--- Zakończono centralne przetwarzanie metadanych ---")
    return long_files


def _process_regular_files_metadata(
    files_to_process: list[dict[str, Any]], allow_long: bool
) -> tuple[list[dict[str, Any]], list[str]]:
    """
    Przetwarza metadane dla zwykłych plików (nie chunków).

    Zwraca:
        tuple: (lista_metadanych, lista_długich_plików)
    """
    if not files_to_process:
        return [], []

    try:
        files_with_mtime: list[dict[str, Any]] = []
        for file_row in files_to_process:
            mtime = os.path.getmtime(file_row["source_file_path"])
            files_with_mtime.append({**file_row, "mtime": mtime})

        sorted_files: list[dict[str, Any]] = sorted(files_with_mtime, key=lambda x: x["mtime"])
    except OSError as e:
        print(f"BŁĄD: Nie można posortować plików zwykłych, problem z dostępem do pliku: {e}")
        return [], []

    all_metadata_to_update: list[dict[str, Any]] = []
    long_files: list[str] = []
    previous_end_datetime = None

    for file_info in sorted_files:
        start_dt = datetime.fromtimestamp(file_info["mtime"])
        duration_sec = get_file_duration(file_info["source_file_path"])
        duration_ms = int(duration_sec * 1000)
        end_dt = start_dt + timedelta(milliseconds=duration_ms)

        if previous_end_datetime:
            previous_ms = int((start_dt - previous_end_datetime).total_seconds() * 1000)
        else:
            previous_ms = 0

        previous_end_datetime = end_dt

        is_long = duration_sec > config.MAX_FILE_DURATION_SECONDS
        if is_long:
            long_files.append(os.path.basename(cast(str, file_info["source_file_path"])))

        is_selected = True if allow_long else not is_long

        # Tworzymy tag na podstawie metadanych
        tag = create_file_tag(start_dt, end_dt, duration_ms, previous_ms)

        all_metadata_to_update.append(
            {
                "id": file_info["id"],
                "start_datetime": start_dt.strftime("%Y-%m-%d %H:%M:%S"),
                "duration_ms": duration_ms,
                "end_datetime": end_dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
                "previous_ms": previous_ms,
                "is_selected": is_selected,
                "tag": tag,
            }
        )

    return all_metadata_to_update, long_files


def _process_chunk_files_metadata(chunk_files: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Przetwarza metadane dla chunków na podstawie metadanych ich plików rodzicielskich.

    Zwraca:
        list: Lista metadanych do aktualizacji
    """
    if not chunk_files:
        return []

    all_metadata_to_update: list[dict[str, Any]] = []

    # Grupuj chunk'y według pliku rodzicielskiego
    chunks_by_parent: dict[str, list[dict[str, Any]]] = {}
    for chunk in chunk_files:
        parent_path = chunk["parent_file_path"]
        if parent_path:
            if parent_path not in chunks_by_parent:
                chunks_by_parent[parent_path] = []
            chunks_by_parent[parent_path].append(chunk)

    for parent_path, chunks in chunks_by_parent.items():
        # Pobierz metadane pliku rodzicielskiego
        parent_metadata = database.get_file_metadata(parent_path)
        if not parent_metadata:
            print(
                f"Ostrzeżenie: Nie można znaleźć metadanych dla pliku rodzicielskiego {parent_path}"
            )
            continue

        try:
            parent_start_dt = datetime.strptime(
                parent_metadata["start_datetime"], "%Y-%m-%d %H:%M:%S"
            )
            parent_duration_ms = parent_metadata["duration_ms"]

            # Sortuj chunk'y według indeksu
            sorted_chunks = sorted(
                chunks, key=lambda x: x["chunk_index"] if "chunk_index" in x else 0
            )

            previous_end_dt = None

            for chunk in sorted_chunks:
                chunk_index = chunk["chunk_index"] if "chunk_index" in chunk else 1

                # Oblicz rzeczywistą długość chunk'a
                duration_sec = get_file_duration(chunk["source_file_path"])
                duration_ms = int(duration_sec * 1000)

                # Szacuj pozycję czasową chunk'a w pliku rodzicielskim
                # To przybliżenie - zakładamy równomierny podział
                parent_duration_sec = parent_duration_ms / 1000
                estimated_start_sec = (chunk_index - 1) * config.MAX_FILE_DURATION_SECONDS
                estimated_start_sec = min(estimated_start_sec, parent_duration_sec - duration_sec)

                start_dt = parent_start_dt + timedelta(seconds=estimated_start_sec)
                end_dt = start_dt + timedelta(milliseconds=duration_ms)

                if previous_end_dt:
                    previous_ms = int((start_dt - previous_end_dt).total_seconds() * 1000)
                else:
                    previous_ms = 0

                previous_end_dt = end_dt

                # Tworzymy tag na podstawie metadanych chunk'a
                tag = create_file_tag(start_dt, end_dt, duration_ms, previous_ms)

                all_metadata_to_update.append(
                    {
                        "id": chunk["id"],
                        "start_datetime": start_dt.strftime("%Y-%m-%d %H:%M:%S"),
                        "duration_ms": duration_ms,
                        "end_datetime": end_dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
                        "previous_ms": previous_ms,
                        "is_selected": True,  # Chunk'y są zawsze zaznaczone
                        "tag": tag,
                    }
                )

        except Exception as e:
            print(f"Błąd podczas przetwarzania metadanych dla chunków pliku {parent_path}: {e}")
            continue

    return all_metadata_to_update
