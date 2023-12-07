import json
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

    def write_to_json_file(self, transcription_service_output, transcript: Transcript):
        transcription_service_output_file = utils.write_to_json(
            transcription_service_output, f"{self.output_dir}/{transcript.source.loc}", transcript.title, is_metadata=True)
        logger.info(
            f"(deepgram) Model stored at: {transcription_service_output_file}")
        # Add deepgram output file path to transcript's metadata file
        if transcript.metadata_file is not None:
            # Read existing content of the metadata file
            with open(transcript.metadata_file, 'r') as file:
                data = json.load(file)
            # Add deepgram output
            data['deepgram_output'] = transcription_service_output_file
            # Write the updated dictionary back to the JSON file
            with open(transcript.metadata_file, 'w') as file:
                json.dump(data, file, indent=4)

        return transcription_service_output_file

    def process_with_diarization_and_chapters(self, transcription_service_output, chapters):
        logger.info(
            "(deepgram) Processing diarization with detected chapters...")
        try:
            para = ""
            string = ""
            curr_speaker = None
            words = transcription_service_output["results"]["channels"][0]["alternatives"][0][
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

    def process_with_diarization(self, transcription_service_output):
        logger.info(f"(deepgram) Processing diarization...")
        para = ""
        string = ""
        curr_speaker = None
        for word in transcription_service_output["results"]["channels"][0]["alternatives"][0][
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

    def process_with_chapters(self, transcription_service_output, chapters):
        logger.info("(deepgram) Combining transcript with detected chapters...")
        try:
            chapters_pointer = 0
            words_pointer = 0
            result = ""
            words = transcription_service_output["results"]["channels"][0]["alternatives"][0][
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

    def process_summary(self, transcript: Transcript):
        with open(transcript.transcription_service_output_file, "r") as outfile:
            transcription_service_output = json.load(outfile)

        try:
            summaries = transcription_service_output["results"]["channels"][0]["alternatives"][0][
                "summaries"
            ]
            summary = ""
            for x in summaries:
                summary = summary + " " + x["summary"]
            return summary.strip(" ")
        except Exception as e:
            logger.error(f"Error getting summary: {e}")

    def finalize_transcript(self, transcript: Transcript):
        try:
            with open(transcript.transcription_service_output_file, "r") as outfile:
                transcription_service_output = json.load(outfile)

            has_diarization = any(
                'speaker' in word for word in transcription_service_output['results']['channels'][0]['alternatives'][0]['words'])
            has_chapters = len(transcript.source.chapters) > 0

            if has_chapters:
                # With chapters
                if has_diarization:
                    # With diarization
                    return self.process_with_diarization_and_chapters(transcription_service_output, chapters)
                else:
                    # Without diarization
                    return self.process_with_chapters(transcription_service_output, transcript.source.chapters)
            else:
                # Without chapters
                if has_diarization:
                    # With diarization
                    return self.process_with_diarization(transcription_service_output)
                else:
                    # Without diarization
                    return transcription_service_output["results"]["channels"][0]["alternatives"][0]["transcript"]

            return result
        except Exception as e:
            raise Exception(f"(deepgram) Error finalizing transcript: {e}")

    def transcribe(self, transcript: Transcript):
        try:
            transcription_service_output = self.audio_to_text(
                transcript.audio_file)
            transcript.transcription_service_output_file = self.write_to_json_file(
                transcription_service_output, transcript)
            if self.upload:
                application.upload_file_to_s3(
                    transcript.transcription_service_output_file)
            if self.summarize:
                transcript.summary = self.process_summary(transcript)
            transcript.result = self.finalize_transcript(transcript)

            return transcript
        except Exception as e:
            raise Exception(f"(deepgram) Error while transcribing: {e}")
