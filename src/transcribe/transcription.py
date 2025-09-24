# # Plik skopiowany ze starego projektu i nie analizowany
#
#
# import json
# import os
# from natsort import natsorted
# from pydub import AudioSegment
# from pydub.silence import split_on_silence
# from dotenv import load_dotenv
# from transcribe import Whisper
# from utils import logger, convert_path, save_file, read_file, sentence_to_paragraf, sentence_to_paragraf_with_number
#
# load_dotenv()
#
#
# class Transcription:
#
#     def __init__(self):
#         self.video = None
#         self.path = None
#         self.audio = None
#         self.response_format = None
#         self.prompt = None
#         self.temperature = 0
#         self.whisper = Whisper()
#
#     def transcribe(self, path_to_video, response_format="text", prompt=""):
#         self.__configure_transcription__(path_to_video, response_format, prompt)
#         return self.__transcribe_chunk__()
#
#     def load_and_transcribe(self, path_to_video, response_format="text", prompt=""):
#         self.__configure_transcription__(path_to_video, response_format, prompt)
#         self.__prepare_chunks__()
#         return self.__transcribe_chunk__()
#
#     def test(self, path_to_video, response_format="text", prompt=""):
#         self.__configure_transcription__(path_to_video, response_format, prompt)
#         transcriptions = read_file(self.path, "transcriptions")
#         splitted_transcriptions = sentence_to_paragraf_with_number(transcriptions)
#         save_file(splitted_transcriptions, self.path, "splitted_transcriptions_with_number")
#
#     def __configure_transcription__(self, path_to_video, response_format, prompt):
#         logger("Start __configure_transcription__()")
#         self.video = convert_path(path_to_video)
#         self.path = os.path.splitext(self.video)[0]
#         self.response_format = response_format
#         self.prompt = prompt
#
#     def __transcribe_chunk__(self):
#         logger("Start __transcribe_chunk__()")
#         chunk_list = self.__collect_chunk__()
#         chunk_list_to_process = chunk_list[:]
#         transcriptions = []
#         for chunk in chunk_list:
#             answer = self.whisper.transcribe(chunk, self.response_format, self.prompt, self.temperature)
#             transcriptions.append(answer)
#             self.__pop_from_chunk_list__(chunk_list_to_process, chunk)
#             save_file(transcriptions, self.path, "transcriptions")
#             logger(answer)
#         if transcriptions and transcriptions[-1] == "":
#             transcriptions.pop()
#             save_file(transcriptions, self.path, "transcriptions")
#         logger("Finish __transcribe_chunk__()")
#         return transcriptions
#
#     def __collect_chunk__(self):
#         logger("Start __collect_chunk__()")
#         chunk_list = []
#         for root, dirs, files in os.walk(self.path):
#             for file in files:
#                 if file.lower().endswith(".mp3"):
#                     chunk_list.append(os.path.join(root, file))
#         chunk_list = natsorted(chunk_list)
#         save_file(chunk_list, self.path, "chunk_list_backup")
#         return chunk_list
#
#     def __pop_from_chunk_list__(self, chunk_list_to_process, chunk):
#         if chunk in chunk_list_to_process:
#             index = chunk_list_to_process.index(chunk)
#             chunk_list_to_process.pop(index)
#             save_file(chunk_list_to_process, self.path, "chunk_list_to_process")
#
#     def __prepare_chunks__(self):
#         logger("Start AudioSegment")
#         self.audio = AudioSegment.from_file(self.video, "mp4")
#
#         logger("Start __split_audio__()")
#         self.__split_audio__()
#
#     def __split_audio__(self):
#         os.makedirs(self.path, exist_ok=True)
#         logger("Start split chunks")
#         chunks = split_on_silence(self.audio, min_silence_len=3000, silence_thresh=-40)
#         for i, chunk in enumerate(chunks):
#             chunk.export(f"{self.path}/chunk{i}.mp3", format="mp3")
