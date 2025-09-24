from audio import encode_audio_file


def run():
    output_file = '../../rec/1_audio_file_list_to_encode.txt'
    file_list = output_file
    input_dir = r'D:\_data\__code\solution\speech_to_text\rec\input'
    output_dir = r'D:\_data\__code\solution\speech_to_text\rec\output'

    encode_audio_file(file_list, input_dir, output_dir)


if __name__ == '__main__':
    run()
