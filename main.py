from src.audio import get_audio_file_list, encode_audio_files
from src.transcribe import TranscriptionProcessor


def main():
    """
    Główna funkcja orkiestrująca procesem transkrypcji.
    """
    print("--- Rozpoczynam proces transkrypcji ---")

    # Krok 1: Znajdź pliki audio do przetworzenia
    get_audio_file_list()

    # Krok 2: Przekonwertuj pliki audio do formatu WAV
    encode_audio_files()

    # Krok 3 & 4: Przetwórz (transkrybuj) przekonwertowane pliki
    processor = TranscriptionProcessor()
    processor.process_transcriptions()

    print("\n--- Proces transkrypcji zakończony pomyślnie! ---")


if __name__ == "__main__":
    main()