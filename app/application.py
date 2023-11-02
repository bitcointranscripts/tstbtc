"""This module provides the transcript cli."""
import errno
import json
import logging
import mimetypes
import os
import re
import shutil
import subprocess
import tempfile
import time
from datetime import datetime
from urllib.parse import parse_qs, urlparse

import boto3
import pytube
import requests
import static_ffmpeg
import whisper
import yt_dlp
from clint.textui import progress
from deepgram import Deepgram
from dotenv import dotenv_values
from moviepy.editor import VideoFileClip
from pytube.exceptions import PytubeError

from app import __app_name__, __version__
from app.utils import write_to_json


def convert_wav_to_mp3(abs_path, filename, working_dir="tmp/"):
    logger = logging.getLogger(__app_name__)
    logger.info(f"Converting {abs_path} to mp3...")
    op = subprocess.run(
        ["ffmpeg", "-i", abs_path, filename[:-4] + ".mp3"],
        cwd=working_dir,
        capture_output=True,
        text=True,
    )
    logger.info(op.stdout)
    logger.error(op.stderr)
    return os.path.abspath(os.path.join(working_dir, filename[:-4] + ".mp3"))


def decimal_to_sexagesimal(dec):
    sec = int(dec % 60)
    minu = int((dec // 60) % 60)
    hrs = int((dec // 60) // 60)

    return f"{hrs:02d}:{minu:02d}:{sec:02d}"


def combine_chapter(chapters, transcript, working_dir="tmp/"):
    logger = logging.getLogger(__app_name__)
    try:
        chapters_pointer = 0
        transcript_pointer = 0
        result = ""
        # chapters index, start time, name
        # transcript start time, end time, text

        while chapters_pointer < len(chapters) and transcript_pointer < len(
            transcript
        ):
            if (
                chapters[chapters_pointer][1]
                <= transcript[transcript_pointer][0]
            ):
                result = (
                    result + "\n\n## " + chapters[chapters_pointer][2] + "\n\n"
                )
                chapters_pointer += 1
            else:
                result = result + transcript[transcript_pointer][2]
                transcript_pointer += 1

        while transcript_pointer < len(transcript):
            result = result + transcript[transcript_pointer][2]
            transcript_pointer += 1

        return result
    except Exception as e:
        logger.error("Error combining chapters")
        logger.error(e)


def combine_deepgram_chapters_with_diarization(deepgram_data, chapters):
    logger = logging.getLogger(__app_name__)
    try:
        para = ""
        string = ""
        curr_speaker = None
        words = deepgram_data["results"]["channels"][0]["alternatives"][0][
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
                        + decimal_to_sexagesimal(words[words_pointer]["start"])
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
                    f' {decimal_to_sexagesimal(words[words_pointer]["start"])}'
                )
                curr_speaker = words[words_pointer]["speaker"]
                string = string + "\n\n"

            para = para + " " + words[words_pointer]["punctuated_word"]
            words_pointer += 1
        para = para.strip(" ")
        string = string + para
        return string
    except Exception as e:
        logger.error("Error combining deepgram chapters")
        logger.error(e)


def get_deepgram_transcript(deepgram_data, diarize, title, upload, model_output_dir):
    logger = logging.getLogger(__app_name__)

    def save_local_json(json_data, title, model_output_dir):
        logger.info(f"Saving Locally...")
        time_in_str = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        if not os.path.isdir(model_output_dir):
            os.makedirs(model_output_dir)
        file_path = os.path.join(
            model_output_dir, title + "_" + time_in_str + ".json"
        )
        with open(file_path, "w") as json_file:
            json.dump(json_data, json_file, indent=4)
        logger.info(f"Model stored at path {file_path}")
        return file_path
    try:
        data_path = write_to_json(
            deepgram_data, model_output_dir, title)
        logger.info(f"(deepgram) Model stored at: {data_path}")
        if upload:
            upload_file_to_s3(data_path)
        if diarize:
            para = ""
            string = ""
            curr_speaker = None
            for word in deepgram_data["results"]["channels"][0]["alternatives"][0][
                "words"
            ]:
                if word["speaker"] != curr_speaker:
                    if para != "":
                        para = para.strip(" ")
                        string = string + para + "\n\n"
                    para = ""
                    string = (
                        string + f'Speaker {word["speaker"]}: '
                        f'{decimal_to_sexagesimal(word["start"])}'
                    )
                    curr_speaker = word["speaker"]
                    string = string + "\n\n"

                para = para + " " + word["punctuated_word"]
            para = para.strip(" ")
            string = string + para
            return string
        else:
            return deepgram_data["results"]["channels"][0]["alternatives"][0][
                "transcript"
            ]
    except Exception as e:
        raise Exception(f"Error while getting deepgram transcript: {e}")


def get_deepgram_summary(deepgram_data):
    logger = logging.getLogger(__app_name__)
    try:
        summaries = deepgram_data["results"]["channels"][0]["alternatives"][0][
            "summaries"
        ]
        summary = ""
        for x in summaries:
            summary = summary + " " + x["summary"]
        return summary.strip(" ")
    except Exception as e:
        logger.error("Error getting summary")
        logger.error(e)


def process_mp3_deepgram(filename, summarize, diarize):
    """using deepgram"""
    logger = logging.getLogger(__app_name__)
    logger.info("Transcribing audio to text using deepgram...")
    try:
        config = dotenv_values(".env")
        dg_client = Deepgram(config["DEEPGRAM_API_KEY"])

        with open(filename, "rb") as audio:
            mimeType = mimetypes.MimeTypes().guess_type(filename)[0]
            source = {"buffer": audio, "mimetype": mimeType}
            response = dg_client.transcription.sync_prerecorded(
                source,
                {
                    "punctuate": True,
                    "speaker_labels": True,
                    "diarize": diarize,
                    "smart_formatting": True,
                    "summarize": summarize,
                    "model": "whisper-large",
                },
            )
            audio.close()
        return response
    except Exception as e:
        raise Exception(f"(deepgram) Error transcribing audio to text: {e}")


def create_pr(absolute_path, loc, username, curr_time, title):
    logger = logging.getLogger(__app_name__)
    branch_name = loc.replace("/", "-")
    subprocess.call(
        [
            "bash",
            "initializeRepo.sh",
            absolute_path,
            loc,
            branch_name,
            username,
            curr_time,
        ]
    )
    subprocess.call(
        ["bash", "github.sh", branch_name, username, curr_time, title]
    )
    logger.info("Please check the PR for the transcription.")


def combine_deepgram_with_chapters(deepgram_data, chapters):
    logger = logging.getLogger(__app_name__)
    try:
        chapters_pointer = 0
        words_pointer = 0
        result = ""
        words = deepgram_data["results"]["channels"][0]["alternatives"][0][
            "words"
        ]
        # chapters index, start time, name
        # transcript start time, end time, text
        while chapters_pointer < len(chapters) and words_pointer < len(words):
            if chapters[chapters_pointer][1] <= words[words_pointer]["end"]:
                result = (
                    result + "\n\n## " + chapters[chapters_pointer][2] + "\n\n"
                )
                chapters_pointer += 1
            else:
                result = result + words[words_pointer]["punctuated_word"] + " "
                words_pointer += 1

        # Append the final chapter heading and remaining content
        while chapters_pointer < len(chapters):
            result = result + "\n\n## " + chapters[chapters_pointer][2] + "\n\n"
            chapters_pointer += 1
        while words_pointer < len(words):
            result = result + words[words_pointer]["punctuated_word"] + " "
            words_pointer += 1

        return result
    except Exception as e:
        logger.error("Error combining deepgram with chapters")
        logger.error(e)


def clean_up(tmp_dir):
    try:
        shutil.rmtree(tmp_dir)
    except OSError as exc:
        if exc.errno != errno.ENOENT:
            raise


def generate_srt(data, filename, model_output_dir):
    logger = logging.getLogger(__app_name__)
    logger.info("Saving Locally...")
    time_in_str = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    if not os.path.isdir(model_output_dir):
        os.makedirs(model_output_dir)
    output_file = os.path.join(
        model_output_dir, filename + "_" + time_in_str + ".srt"
    )
    logger.debug(f"Writing srt to {output_file}")
    with open(output_file, "w") as f:
        for index, segment in enumerate(data):
            start_time, end_time, text = segment
            f.write(f"{index+1}\n")
            f.write(f"{format_time(start_time)} --> {format_time(end_time)}\n")
            f.write(f"{text.strip()}\n\n")
    logger.info("File saved")
    return output_file


def format_time(time):
    hours = int(time / 3600)
    minutes = int((time % 3600) / 60)
    seconds = int(time % 60)
    milliseconds = int((time % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"


def upload_file_to_s3(file_path):
    logger = logging.getLogger(__app_name__)
    s3 = boto3.client("s3")
    config = dotenv_values(".env")
    bucket = config["S3_BUCKET"]
    base_filename = file_path.split("/")[-1]
    dir = "model outputs/" + base_filename
    try:
        s3.upload_file(file_path, bucket, dir)
        logger.info(f"File uploaded to S3 bucket : {bucket}")
    except Exception as e:
        logger.error(f"Error uploading file to S3 bucket: {e}")
