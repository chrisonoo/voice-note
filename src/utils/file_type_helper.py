# Ten moduł zawiera funkcje pomocnicze do określania typów plików.
# Zapewnia czyste rozdzielenie logiki biznesowej od konfiguracji.

import os
from src import config

def get_file_type(file_path):
    """
    Określa typ pliku na podstawie rozszerzenia.
    
    Argumenty:
        file_path (str): Ścieżka do pliku
        
    Zwraca:
        str: 'audio' dla plików audio, 'video' dla plików wideo
    """
    extension = os.path.splitext(file_path)[1].lower()
    
    if extension in config.AUDIO_EXTENSIONS:
        return 'audio'
    elif extension in config.VIDEO_EXTENSIONS:
        return 'video'
    else:
        return 'audio'  # domyślnie traktuj jako audio

def is_audio_file(file_path):
    """
    Sprawdza czy plik to plik audio.
    
    Argumenty:
        file_path (str): Ścieżka do pliku
        
    Zwraca:
        bool: True jeśli plik to audio, False w przeciwnym razie
    """
    return get_file_type(file_path) == 'audio'

def is_video_file(file_path):
    """
    Sprawdza czy plik to plik wideo.
    
    Argumenty:
        file_path (str): Ścieżka do pliku
        
    Zwraca:
        bool: True jeśli plik to wideo, False w przeciwnym razie
    """
    return get_file_type(file_path) == 'video'
