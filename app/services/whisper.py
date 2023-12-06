import whisper

from app import (
    application,
    utils
)
from app.logging import get_logger
from app.transcript import Transcript

logger = get_logger()


class Whisper:
    def __init__(self, model, upload, output_dir):
        self.model = model
        self.upload = upload
        self.output_dir = output_dir

    def audio_to_text(self, audio_file):
        logger.info(
            f"Transcribing audio to text using whisper ({self.model}) ...")
        try:
            my_model = whisper.load_model(self.model)
            result = my_model.transcribe(audio_file)
            data = []
            for x in result["segments"]:
                data.append(tuple((x["start"], x["end"], x["text"])))
            return data
        except Exception as e:
            logger.error(
                f"(wisper,{service}) Error transcribing audio to text: {e}")
            return

    def generate_srt(self, data, filename, loc):
        def format_time(time):
            hours = int(time / 3600)
            minutes = int((time % 3600) / 60)
            seconds = int(time % 60)
            milliseconds = int((time % 1) * 1000)
            return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"

        output_file = f"{utils.configure_output_file_path(f'{self.output_dir}/{loc}', filename, is_metadata=True)}.srt"
        logger.info(f"(whisper) Writing srt to {output_file}...")
        with open(output_file, "w") as f:
            for index, segment in enumerate(data):
                start_time, end_time, text = segment
                f.write(f"{index+1}\n")
                f.write(
                    f"{format_time(start_time)} --> {format_time(end_time)}\n")
                f.write(f"{text.strip()}\n\n")
        return output_file

    def process_with_chapters(self, raw_transcript, chapters):
        try:
            chapters_pointer = 0
            transcript_pointer = 0
            result = ""
            # chapters index, start time, name
            # transcript start time, end time, text

            while chapters_pointer < len(chapters) and transcript_pointer < len(
                raw_transcript
            ):
                if (
                    chapters[chapters_pointer][1]
                    <= raw_transcript[transcript_pointer][0]
                ):
                    result = (
                        result + "\n\n## " +
                        chapters[chapters_pointer][2] + "\n\n"
                    )
                    chapters_pointer += 1
                else:
                    result = result + raw_transcript[transcript_pointer][2]
                    transcript_pointer += 1

            while transcript_pointer < len(raw_transcript):
                result = result + raw_transcript[transcript_pointer][2]
                transcript_pointer += 1

            return result
        except Exception as e:
            logger.error("Error combining chapters")
            logger.error(e)

    def process_default(self):
        result = ""
        for x in self.result:
            result = result + x[2] + " "

        return result

    def construct_transcript(self, raw_transcript, chapters):
        if len(chapters) > 0:
            # Source has chapters, add them to transcript
            return self.process_with_chapters(raw_transcript, chapters)
        else:
            return self.process_default(raw_transcript)

    def transcribe(self, transcript: Transcript):
        try:
            raw_transcript = self.audio_to_text(transcript.audio_file)
            raw_transcript_file = self.generate_srt(
                raw_transcript, transcript.title, transcript.source.loc)
            if self.upload:
                application.upload_file_to_s3(raw_transcript_file)

            transcript.result = construct_transcript(
                raw_transcript, transcript.source.chapters)

            return transcript
        except Exception as e:
            raise Exception(f"(whisper) Error while transcribing: {e}")
