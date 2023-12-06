import mimetypes

import deepgram
from dotenv import dotenv_values

from app import (
    application,
    utils
)
from app.logging import get_logger
from app.transcript import Transcript

logger = get_logger()


class Deepgram:
    def __init__(self, summarize, diarize, upload, output_dir):
        self.summarize = summarize
        self.diarize = diarize
        self.upload = upload
        self.output_dir = output_dir

    def audio_to_text(self, audio_file):
        logger.info("Transcribing audio to text using deepgram...")
        try:
            config = dotenv_values(".env")
            dg_client = deepgram.Deepgram(config["DEEPGRAM_API_KEY"])

            with open(audio_file, "rb") as audio:
                mimeType = mimetypes.MimeTypes().guess_type(audio_file)[0]
                source = {"buffer": audio, "mimetype": mimeType}
                response = dg_client.transcription.sync_prerecorded(
                    source,
                    {
                        "punctuate": True,
                        "speaker_labels": True,
                        "diarize": self.diarize,
                        "smart_formatting": True,
                        "summarize": self.summarize,
                        "model": "whisper-large",
                    },
                )
                audio.close()
            return response
        except Exception as e:
            raise Exception(f"(deepgram) Error transcribing audio to text: {e}")

    def process_with_diarization_and_chapters(self, raw_transcript, chapters):
        logger.info(
            "(deepgram) Processing diarization with detected chapters...")
        try:
            para = ""
            string = ""
            curr_speaker = None
            words = raw_transcript["results"]["channels"][0]["alternatives"][0][
                "words"
            ]
            words_pointer = 0
            chapters_pointer = 0
            while chapters_pointer < len(chapters) and words_pointer < len(words):
                if chapters[chapters_pointer][1] <= words[words_pointer]["start"]:
                    if para != "":
                        para = para.strip(" ")
                        string = string + para + "\n\n"
                    para = ""
                    string = string + f"## {chapters[chapters_pointer][2]}\n\n"
                    chapters_pointer += 1
                else:
                    if words[words_pointer]["speaker"] != curr_speaker:
                        if para != "":
                            para = para.strip(" ")
                            string = string + para + "\n\n"
                        para = ""
                        string = (
                            string
                            + f'Speaker {words[words_pointer]["speaker"]}: '
                            + utils.decimal_to_sexagesimal(words[words_pointer]["start"])
                        )
                        curr_speaker = words[words_pointer]["speaker"]
                        string = string + "\n\n"

                    para = para + " " + words[words_pointer]["punctuated_word"]
                    words_pointer += 1
            while words_pointer < len(words):
                if words[words_pointer]["speaker"] != curr_speaker:
                    if para != "":
                        para = para.strip(" ")
                        string = string + para + "\n\n"
                    para = ""
                    string = (
                        string + f'Speaker {words[words_pointer]["speaker"]}:'
                        f' {utils.decimal_to_sexagesimal(words[words_pointer]["start"])}'
                    )
                    curr_speaker = words[words_pointer]["speaker"]
                    string = string + "\n\n"

                para = para + " " + words[words_pointer]["punctuated_word"]
                words_pointer += 1
            para = para.strip(" ")
            string = string + para
            return string
        except Exception as e:
            raise Exception(f"Error combining deepgram chapters: {e}")

    def process_with_diarization(self, raw_transcript):
        logger.info(f"(deepgram) Processing diarization...")
        para = ""
        string = ""
        curr_speaker = None
        for word in raw_transcript["results"]["channels"][0]["alternatives"][0][
            "words"
        ]:
            if word["speaker"] != curr_speaker:
                if para != "":
                    para = para.strip(" ")
                    string = string + para + "\n\n"
                para = ""
                string = (
                    string + f'Speaker {word["speaker"]}: '
                    f'{utils.decimal_to_sexagesimal(word["start"])}'
                )
                curr_speaker = word["speaker"]
                string = string + "\n\n"

            para = para + " " + word["punctuated_word"]
        para = para.strip(" ")
        string = string + para
        return string

    def process_with_chapters(self, raw_transcript, chapters):
        logger.info("(deepgram) Combining transcript with detected chapters...")
        try:
            chapters_pointer = 0
            words_pointer = 0
            result = ""
            words = raw_transcript["results"]["channels"][0]["alternatives"][0][
                "words"
            ]
            # chapters index, start time, name
            # transcript start time, end time, text
            while chapters_pointer < len(chapters) and words_pointer < len(words):
                if chapters[chapters_pointer][1] <= words[words_pointer]["end"]:
                    result = (
                        result + "\n\n## " +
                        chapters[chapters_pointer][2] + "\n\n"
                    )
                    chapters_pointer += 1
                else:
                    result = result + \
                        words[words_pointer]["punctuated_word"] + " "
                    words_pointer += 1

            # Append the final chapter heading and remaining content
            while chapters_pointer < len(chapters):
                result = result + "\n\n## " + \
                    chapters[chapters_pointer][2] + "\n\n"
                chapters_pointer += 1
            while words_pointer < len(words):
                result = result + words[words_pointer]["punctuated_word"] + " "
                words_pointer += 1

            return result
        except Exception as e:
            raise Exception(f"Error combining deepgram with chapters: {e}")

    def process_summary(self, raw_transcript):
        try:
            summaries = raw_transcript["results"]["channels"][0]["alternatives"][0][
                "summaries"
            ]
            summary = ""
            for x in summaries:
                summary = summary + " " + x["summary"]
            return summary.strip(" ")
        except Exception as e:
            logger.error(f"Error getting summary: {e}")

    def construct_transcript(self, raw_transcript, chapters):
        if len(chapters) > 0:
            # With chapters
            if self.diarize:
                # With diarization
                return self.process_with_diarization_and_chapters(raw_transcript, chapters)
            else:
                # Without diarization
                return self.process_with_chapters(raw_transcript, chapters)
        else:
            # Without chapters
            if self.diarize:
                # With diarization
                return self.process_with_diarization(raw_transcript)
            else:
                # Without diarization
                return raw_transcript["results"]["channels"][0]["alternatives"][0]["transcript"]

        return result

    def transcribe(self, transcript: Transcript):
        try:
            raw_transcript = self.audio_to_text(transcript.audio_file)
            raw_transcript_file = utils.write_to_json(
                raw_transcript, f"{self.output_dir}/{transcript.source.loc}", transcript.title, is_metadata=True)
            logger.info(
                f"(deepgram) Model stored at: {raw_transcript_file}")
            if self.upload:
                application.upload_file_to_s3(raw_transcript_file)
            if self.summarize:
                transcript.summary = self.process_summary(raw_transcript)
            transcript.result = self.construct_transcript(
                raw_transcript, transcript.source.chapters)

            return transcript
        except Exception as e:
            raise Exception(f"(deepgram) Error while transcribing: {e}")
