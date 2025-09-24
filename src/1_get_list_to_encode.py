from audio import get_audio_file_list


def run():
    dir_path = '../../rec/input'
    output_file = '../../rec/1_audio_file_list_to_encode.txt'

    get_audio_file_list(dir_path, output_file)


if __name__ == '__main__':
    run()
