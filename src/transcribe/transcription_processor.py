from whisper import Whisper
from services import print_completion
import shutil


class TranscriptionProcessor:
    def __init__(
            self,
            source_file_list,
            processing_file_list,
            processed_file_list,
            response_format,
            prompt,
            temperature):
        self.source_file_list = source_file_list
        self.processing_file_list = processing_file_list
        self.processed_file_list = processed_file_list
        self.response_format = response_format
        self.prompt = prompt
        self.temperature = temperature

        # Tworzenie pliku processing_file_list z nazwami plików do transkrypcji
        shutil.copyfile(self.source_file_list, self.processing_file_list)

    def process_transcriptions(self):
        with open(self.source_file_list, 'r', encoding='utf8') as source_files:
            lines = source_files.readlines()

        for line in lines:
            audio_file = line.strip()
            whisper = Whisper(audio_file, self.response_format, self.prompt, self.temperature)

            try:
                print(f"Processing file: {audio_file}")
                transcription = whisper.transcribe()  # Pobieranie transkrypcji
                print_completion(transcription, format_type="message_whisper", datetime=True, new_line=True)

                with open('../../rec/5_transcriptions.txt', 'a', encoding='utf8') as f:
                    f.write(f"{transcription.text}\n\n")

            except Exception as e:
                print(f"An error occurred while processing file: {audio_file}, Error: {str(e)}")
                continue

            # Dodawanie wpisu do processed_file_list i usuwanie z processing_file_list
            if transcription:
                with open(self.processed_file_list, 'a', encoding='utf8') as processed_files:
                    processed_files.write(audio_file + '\n')

                with open(self.processing_file_list, 'r', encoding='utf8') as proc_file:
                    processing_lines = proc_file.readlines()

                new_lines = [proc_line for proc_line in processing_lines if proc_line.strip() != audio_file]

                with open(self.processing_file_list, 'w', encoding='utf8') as file:
                    file.writelines(new_lines)
