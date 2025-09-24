import os


def get_audio_file_list(dir_path, output_file):
    # Lista rozszerzeń plików, które będą przetwarzane
    extensions = ['.mp3', '.wav', '.m4a', '.mp4', '.wma']

    with open(output_file, 'w', encoding='utf-8') as f:

        # os.walk() przejdzie przez wszystkie podkatalogi
        for root, _, files in os.walk(dir_path):
            for file in files:

                # Sprawdź rozszerzenie pliku i przekształć na małe litery
                extension = os.path.splitext(file)[1].lower()

                # Jeśli lista rozszerzeń nie jest pusta i rozszerzenie pliku jest na liście
                if extensions is None or extension in extensions:

                    # Dołącz pełną ścieżkę do pliku i zapisz do pliku
                    full_path = os.path.abspath(os.path.join(root, file))
                    f.write(full_path + '\n')
