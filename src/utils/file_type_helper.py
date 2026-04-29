# Ten moduł zawiera funkcje pomocnicze do określania typów plików.
# Zapewnia czyste rozdzielenie logiki biznesowej od konfiguracji.

import json
import os
import subprocess

from src import config


def get_file_type(file_path: str):
    """
    Określa typ pliku na podstawie rozszerzenia.

    Argumenty:
        file_path (str): Ścieżka do pliku

    Zwraca:
        str: 'audio' dla plików audio, 'video' dla plików wideo
    """
    extension = os.path.splitext(file_path)[1].lower()

    if extension in config.AUDIO_EXTENSIONS:
        return "audio"
    elif extension in config.VIDEO_EXTENSIONS:
        return "video"
    else:
        return "audio"  # domyślnie traktuj jako audio


def is_audio_file(file_path: str):
    """
    Sprawdza czy plik to plik audio.

    Argumenty:
        file_path (str): Ścieżka do pliku

    Zwraca:
        bool: True jeśli plik to audio, False w przeciwnym razie
    """
    return get_file_type(file_path) == "audio"


def is_video_file(file_path: str):
    """
    Sprawdza czy plik to plik wideo.

    Argumenty:
        file_path (str): Ścieżka do pliku

    Zwraca:
        bool: True jeśli plik to wideo, False w przeciwnym razie
    """
    return get_file_type(file_path) == "video"


def is_aac_audio_file(file_path: str):
    """
    Sprawdza czy plik audio jest już w formacie AAC.

    Argumenty:
        file_path (str): Ścieżka do pliku audio/wideo

    Zwraca:
        bool: True jeśli plik zawiera strumień audio w formacie AAC, False w przeciwnym razie
    """
    try:
        # Używamy ffprobe do sprawdzenia kodeka audio
        command = [
            "ffprobe",
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_streams",
            "-select_streams",
            "a:0",  # Wybieramy tylko pierwszy strumień audio
            file_path,
        ]

        result = subprocess.run(command, capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            # Parsujemy wyjście JSON
            probe_data = json.loads(result.stdout)
            streams = probe_data.get("streams", [])

            if streams:
                codec_name = streams[0].get("codec_name", "").lower()
                # Sprawdzamy czy kodek to AAC
                return codec_name == "aac"
        else:
            print(f"    Błąd ffprobe dla pliku {os.path.basename(file_path)}: {result.stderr}")

    except subprocess.TimeoutExpired:
        print(f"    Timeout podczas sprawdzania kodeka dla {os.path.basename(file_path)}")
    except json.JSONDecodeError:
        print(f"    Błąd parsowania JSON z ffprobe dla {os.path.basename(file_path)}")
    except Exception as e:
        print(f"    Błąd podczas sprawdzania kodeka AAC dla {os.path.basename(file_path)}: {e}")

    return False
