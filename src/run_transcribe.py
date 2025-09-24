from audio import encode_audio_file
from audio import get_audio_file_list
from transcribe import TranscriptionProcessor


def run():
    dir_input_path = '../../rec/input'
    output_file = '../../rec/1_audio_file_list_to_encode.txt'

    get_audio_file_list(dir_input_path, output_file)

    file_list = output_file
    input_dir_template = r'D:\_data\__code\solution\speech_to_text\rec\input'
    output_dir_template = r'D:\_data\__code\solution\speech_to_text\rec\output'

    encode_audio_file(file_list, input_dir_template, output_dir_template)

    dir_output_path = '../../rec/output'
    output_file = '../../rec/2_audio_file_list_to_transcribe.txt'
    response_format = "json"
    prompt = ""
    temperature = 0
    source_file_list = output_file
    processing_file_list = '../../rec/3_processing_file_list.txt'
    processed_file_list = '../../rec/4_processed_file_list.txt'

    get_audio_file_list(dir_output_path, output_file)

    processor = TranscriptionProcessor(
        source_file_list,
        processing_file_list,
        processed_file_list,
        response_format,
        prompt,
        temperature)

    processor.process_transcriptions()


if __name__ == '__main__':
    run()