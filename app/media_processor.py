import librosa
import soundfile as sf
import os
import ffmpeg

from app.logging import get_logger

logger = get_logger()


class MediaProcessor:
    def __init__(self, chunk_length=1200.0):
        self.chunk_length = chunk_length

    def split_audio(self, audio_path, output_dir=None, overlap=0):
        # Set default output directory if not provided
        if output_dir is None:
            output_dir = os.path.splitext(audio_path)[0] + "_chunks"

        # Load the audio file
        audio, sr = librosa.load(audio_path, sr=None)
        duration = librosa.get_duration(y=audio, sr=sr)

        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # Array to store paths of chunks
        chunk_paths = []

        # Split the audio into chunks
        chunk_start = 0
        chunk_counter = 1

        while chunk_start < duration:
            chunk_end = min(chunk_start + self.chunk_length, duration)
            chunk_audio = audio[int(chunk_start * sr):int(chunk_end * sr)]
            chunk_path = os.path.join(output_dir, f"chunk_{chunk_counter}.mp3")
            sf.write(chunk_path, chunk_audio, sr)
            logger.debug(
                f"Saved chunk {chunk_counter} to {chunk_path} (start={chunk_start:.2f}s, end={chunk_end:.2f}s, duration={chunk_end - chunk_start:.2f}s)")
            chunk_paths.append(chunk_path)
            chunk_counter += 1

            if chunk_end == duration:
                break

            chunk_start = chunk_end - overlap  # Move start point back by overlap duration

        return chunk_paths

    def convert_to_mp3(self, input_path, output_path=None):
        if output_path is None:
            output_path = os.path.splitext(input_path)[0] + ".mp3"

        print(f"Converting {input_path} to {output_path}")
        try:
            ffmpeg.input(input_path).output(output_path, format='mp3').run()
            print(f"Successfully converted to {output_path}")
        except ffmpeg.Error as e:
            print(f"Error converting file: {e}")
