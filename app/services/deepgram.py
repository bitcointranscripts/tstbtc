import json
import mimetypes
import re

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

    def process_segments(self, transcription_service_output, diarization):
        try:
            words = transcription_service_output["results"]["channels"][0]["alternatives"][0]["words"]
            segments = []
            current_segment = None

            for word in words:
                speaker_id = word["speaker"] if diarization else "single_speaker"
                speaker_text = word["punctuated_word"]
                if speaker_id != current_segment:
                    # change of speaker
                    current_segment = speaker_id
                    segments.append({
                        "speaker": speaker_id,
                        "start": word["start"],
                        "end": word["end"],
                        "transcript": "",
                        "words": []
                    })

                segments[-1]["transcript"] += f"{speaker_text} "
                segments[-1]["words"].append(word)
                segments[-1]["end"] = word["end"]

            for segment in segments:
                segment["transcript"] = segment["transcript"].strip()

            return segments
        except Exception as e:
            raise Exception(
                f"(deepgram) Error constructing speaker segments: {e}")

    def break_segments_into_sentences(self, segments):
        result = []
        # Define the sentence splitting pattern
        abbreviation_pattern = r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)'
        sentence_end_pattern = r'(?<=\.|\?)\s'
        sentence_split_pattern = f'{abbreviation_pattern}{sentence_end_pattern}'

        for segment in segments:
            # Split the segment into sentences
            sentences = re.split(sentence_split_pattern, segment["transcript"])

            segment_data = {
                "speaker": segment["speaker"],
                "transcript": segment["transcript"],
                "start": segment["start"],
                "end": segment["end"],
                "sentences": []
            }

            word_index = 0

            for sentence in sentences:
                sentence_words = sentence.split()
                sentence_data = {
                    "transcript": sentence,
                    "start": segment["words"][word_index]["start"],
                    "end": segment["words"][word_index + len(sentence_words) - 1]["end"],
                    "words": segment["words"][word_index:word_index+len(sentence_words)]
                }

                word_index += len(sentence_words)
                segment_data["sentences"].append(sentence_data)

            result.append(segment_data)

        return result

    def adjust_chapter_timestamps(self, transformed_json, chapters):
        """Adjust the given chapter timestamps to prevent mid-sentence line break"""
        def find_sentence_for_timestamp(transformed_json, timestamp):
            for speaker_data in transformed_json:
                for sentence_data in speaker_data["sentences"]:
                    if sentence_data["start"] <= timestamp <= sentence_data["end"]:
                        return sentence_data
            return None

        def adjust_timestamp(original_timestamp, sentence_start, sentence_end):
            midpoint = (sentence_start + sentence_end) / 2
            return sentence_end if original_timestamp >= midpoint else sentence_start

        adjusted_chapters = []

        for chapter in chapters:
            chapter_start_time = chapter[1]
            chapter_sentence = find_sentence_for_timestamp(
                transformed_json, chapter_start_time)

            if chapter_sentence:
                adjusted_start_time = adjust_timestamp(
                    chapter_start_time, chapter_sentence["start"], chapter_sentence["end"])
                adjusted_chapter = [chapter[0],
                                    adjusted_start_time] + chapter[2:]
                adjusted_chapters.append(adjusted_chapter)
            else:
                adjusted_chapters.append(chapter)

        return adjusted_chapters

    def construct_transcript(self, speaker_segments, chapters):
        try:
            formatted_transcript = ""
            chapter_index = 0 if chapters else None

            for speaker_data in speaker_segments:
                speaker_id = speaker_data["speaker"]
                single_speaker = speaker_id == "single_speaker"

                for i, sentence_data in enumerate(speaker_data["sentences"]):
                    sentence_start = sentence_data["start"]
                    first_sentence = i == 0

                    if chapter_index is not None and chapter_index < len(chapters):
                        chapter_id, chapter_start_time, chapter_title = chapters[chapter_index]

                        if chapter_start_time <= sentence_start:
                            # Chapter starts at this sentence
                            formatted_transcript += "\n" if not first_sentence else ""
                            formatted_transcript += f"## {chapter_title}\n\n"
                            if not single_speaker and not first_sentence:
                                formatted_transcript += f"Speaker {speaker_id}: {utils.decimal_to_sexagesimal(chapter_start_time)}\n\n"
                            chapter_index += 1

                    if not single_speaker and first_sentence:
                        formatted_transcript += f"Speaker {speaker_id}: {utils.decimal_to_sexagesimal(sentence_start)}\n\n"

                    formatted_transcript += f'{sentence_data["transcript"]}\n'

                formatted_transcript += "\n"

            return formatted_transcript.strip()
        except Exception as e:
            raise Exception(f"Error creating output format: {e}")

    def finalize_transcript(self, transcript: Transcript):
        try:
            with open(transcript.transcription_service_output_file, "r") as outfile:
                transcription_service_output = json.load(outfile)

            has_diarization = any(
                'speaker' in word for word in transcription_service_output['results']['channels'][0]['alternatives'][0]['words'])

            logger.info(
                f"(deepgram) Finalizing transcript [diarization={has_diarization}, chapters={len(transcript.source.chapters)> 0}]...")
            speaker_segments = self.process_segments(
                transcription_service_output, has_diarization)
            speaker_segements_with_sentences = self.break_segments_into_sentences(
                speaker_segments)
            with open("test.json", "w") as json_file:
                json.dump(speaker_segements_with_sentences, json_file, indent=4)
            adjusted_chapters = self.adjust_chapter_timestamps(
                speaker_segements_with_sentences, transcript.source.chapters)
            result = self.construct_transcript(
                speaker_segements_with_sentences, adjusted_chapters)

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
