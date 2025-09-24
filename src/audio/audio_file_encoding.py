import os
import subprocess


def encode_audio_file(file_list, input_dir, output_dir):
    with open(file_list, 'r', encoding='utf-8') as f:
        for line in f:
            original_path = line.strip()

            # Usuń bazową ścieżkę wejściową z oryginalnej ścieżki, aby pozostała tylko struktura folderów i nazwa pliku
            relative_path = os.path.relpath(original_path, start=input_dir)

            # Buduj nową ścieżkę do pliku .wav
            new_path = os.path.join(output_dir, relative_path)
            new_path = os.path.splitext(new_path)[0] + '.wav'

            os.makedirs(os.path.dirname(new_path), exist_ok=True)
            command = f'ffmpeg -y -i "{original_path}" -ac 1 -ar 44100 "{new_path}"'
            subprocess.run(command, shell=True, check=True)
