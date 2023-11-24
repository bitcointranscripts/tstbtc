import json
import logging
import os
import re
import tempfile
import time
from datetime import datetime

from dotenv import dotenv_values
import pytube
from pytube.exceptions import PytubeError
import requests
import yt_dlp

from app.transcript import Transcript, Source, Audio, Video, Playlist
from app import __app_name__, __version__, application
from app.utils import write_to_json
from app.logging import get_logger


class Transcription:
    def __init__(self, model="tiny", chapters=False, pr=False, summarize=False, deepgram=False, diarize=False, upload=False, model_output_dir="local_models/", nocleanup=False, queue=True, markdown=False, username=None, test_mode=False,  working_dir=None):
        self.model = model
        self.transcript_by = "username" if test_mode else self.__get_username()
        self.generate_chapters = chapters
        self.open_pr = pr
        self.summarize_transcript = summarize
        self.service = "deepgram" if deepgram else model
        self.diarize = diarize
        self.upload = upload
        self.model_output_dir = model_output_dir
        self.transcripts = []
        self.nocleanup = nocleanup
        # during testing we do not have/need a queuer backend
        self.queue = queue if not test_mode else False
        # during testing we need to create the markdown for validation purposes
        self.markdown = markdown or test_mode
        self.test_mode = test_mode
        self.logger = get_logger()
        self.tmp_dir = working_dir if working_dir is not None else tempfile.mkdtemp()

        self.logger.info(f"Temp directory: {self.tmp_dir}")

    def _create_subdirectory(self, subdir_name):
        """Helper method to create subdirectories within the central temp director"""
        subdir_path = os.path.join(self.tmp_dir, subdir_name)
        os.makedirs(subdir_path)
        return subdir_path

    def __get_username(self):
        try:
            if os.path.isfile(".username"):
                with open(".username", "r") as f:
                    username = f.read()
                    f.close()
            else:
                print("What is your github username?")
                username = input()
                with open(".username", "w") as f:
                    f.write(username)
                    f.close()
            return username
        except Exception as e:
            raise Exception("Error getting username")

    def _initialize_source(self, source: Source, youtube_metadata, chapters):
        """Initialize transcription source based on metadata
        Returns the initialized source (Audio, Video, Playlist)"""

        def check_if_youtube(source: Source):
            """Helper method to check and assign a valid source for
            a YouTube playlist or YouTube video by requesting its metadata
            Does not support video-ids, only urls"""
            try:
                ydl_opts = {
                    'quiet': False,  # Suppress console output
                    'extract_flat': True,  # Extract only metadata without downloading
                }
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info_dict = ydl.extract_info(
                        source.source_file, download=False)
                    if 'entries' in info_dict:
                        # Playlist URL, not a single video
                        # source.title = info_dict["title"]
                        return Playlist(source=source, entries=info_dict["entries"])
                    elif 'title' in info_dict:
                        # Single video URL
                        return Video(source=source)
                    else:
                        raise Exception(source.source_file)

            except Exception as e:
                # Invalid URL or video not found
                raise Exception(f"Invalid source: {e}")
        try:
            if source.source_file.endswith(".mp3") or source.source_file.endswith(".wav"):
                return Audio(source=source)

            if youtube_metadata is not None:
                # we have youtube metadata, this can only be true for videos
                source.preprocess = False
                return Video(source=source, youtube_metadata=youtube_metadata, chapters=chapters)
            if source.source_file.endswith(".mp4"):
                # regular remote video, not youtube
                source.preprocess = False
                return Video(source=source)
            youtube_source = check_if_youtube(source)
            if youtube_source == "unknown":
                raise Exception(f"Invalid source: {source}")
            return youtube_source
        except Exception as e:
            raise Exception(f"Error from assigning source: {e}")

    def add_transcription_source(self, source_file, loc="misc", title=None, date=None, tags=[], category=[], speakers=[], preprocess=True, youtube_metadata=None, link=None, chapters=None, nocheck=False):
        """Add a source for transcription"""
        transcription_sources = {"added": [], "exist": []}
        # check if source is a local file
        local = False
        if os.path.isfile(source_file):
            local = True
        # initialize source
        source = self._initialize_source(
            source=Source(source_file, loc, local, title, date,
                          tags, category, speakers, preprocess, link),
            youtube_metadata=youtube_metadata,
            chapters=chapters)
        self.logger.info(f"Detected source: {source}")
        if source.type == "playlist":
            # add a transcript for each source/video in the playlist
            for video in source.videos:
                transcription_sources['added'].append(video)
                self.transcripts.append(Transcript(video, self.test_mode))
        elif source.type in ['audio', 'video']:
            transcription_sources['added'].append(source)
            self.transcripts.append(Transcript(source, self.test_mode))
        else:
            raise Exception(f"Invalid source: {source_file}")
        return transcription_sources

    def push_to_queue(self, transcript: Transcript, payload=None):
        """Push the resulting transcript to a Queuer backend"""
        def construct_payload():
            """Helper method to construct the payload for the request to the Queuer backend"""
            payload = {
                "content": {
                    "title": transcript.title,
                    "transcript_by": f"{self.transcript_by} via TBTBTC v{__version__}",
                    "categories": transcript.source.category,
                    "tags": transcript.source.tags,
                    "speakers": transcript.source.speakers,
                    "loc": transcript.source.loc,
                    "body": transcript.result,
                }
            }
            # Handle optional metadata fields
            if transcript.source.event_date:
                payload["content"]["date"] = transcript.source.event_date if type(
                    transcript.source.event_date) is str else transcript.source.event_date.strftime("%Y-%m-%d")
            if not transcript.source.local:
                payload["content"]["media"] = transcript.source.media
            return payload

        try:
            if payload is None:
                # No payload has been given directly
                payload = construct_payload()
                # Check if the user opt-out from sending the payload to the Queuer
                if not self.queue:
                    # payload will not be send to the Queuer backend
                    if self.test_mode:
                        # queuer is disabled by default when testing but we still
                        # return the payload to be used for testing purposes
                        return payload
                    else:
                        # store payload in case the user wants to manually send it to the queuer
                        payload_json_file = write_to_json(
                            payload, f"{self.model_output_dir}/{transcript.source.loc}", f"{transcript.title}_payload")
                        self.logger.info(
                            f"Transcript not added to the queue, payload stored at: {payload_json_file}")
                        return payload_json_file
            # Push the payload with the resulting transcript to the Queuer backend
            config = dotenv_values(".env")
            if "QUEUE_ENDPOINT" not in config:
                raise Exception(
                    "To push to a queue you need to define a 'QUEUE_ENDPOINT' in your .env file")
            if "BEARER_TOKEN" not in config:
                raise Exception(
                    "To push to a queue you need to define a 'BEARER_TOKEN' in your .env file")
            url = config["QUEUE_ENDPOINT"] + "/api/transcripts"
            headers = {
                'Authorization': f'Bearer {config["BEARER_TOKEN"]}',
                'Content-Type': 'application/json'
            }
            response = requests.post(url, json=payload, headers=headers)
            if response.status_code == 200:
                self.logger.info(
                    f"Transcript added to queue with id={response.json()['id']}")
            else:
                self.logger.error(
                    f"Transcript not added to queue: ({response.status_code}) {response.text}")
            return response
        except Exception as e:
            self.logger.error(f"Transcript not added to queue: {e}")

    def start(self, test_transcript=None):
        self.result = []
        try:
            for transcript in self.transcripts:
                output_dir = f"{self.model_output_dir}/{transcript.source.loc}"
                self.logger.info(
                    f"Processing source: {transcript.source.source_file}")
                tmp_dir = self._create_subdirectory(
                    f"transcript{len(self.result) + 1}")
                transcript.process_source(tmp_dir)
                result = transcript.transcribe(
                    tmp_dir,
                    self.generate_chapters,
                    self.summarize_transcript,
                    self.service,
                    self.diarize,
                    self.upload,
                    output_dir,
                    test_transcript=test_transcript
                )
                if self.markdown:
                    transcription_md_file = transcript.write_to_file(
                        output_dir if not self.test_mode else tmp_dir,
                        self.transcript_by)
                    self.result.append(transcription_md_file)
                else:
                    self.result.append(result)
                if self.open_pr:
                    application.create_pr(
                        absolute_path=transcription_md_file,
                        loc=transcript.source.source_file,
                        username=self.transcript_by,
                        curr_time=str(round(time.time() * 1000)),
                        title=transcript.title,
                    )
                else:
                    self.push_to_queue(transcript)
            return self.result
        except Exception as e:
            raise Exception(f"Error with the transcription: {e}") from e

    def clean_up(self):
        self.logger.info("Cleaning up...")
        application.clean_up(self.tmp_dir)
