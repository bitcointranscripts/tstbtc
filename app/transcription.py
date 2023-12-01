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

from app.transcript import Transcript, Source, Audio, Video, Playlist, RSS
from app import __app_name__, __version__, application
from app.utils import write_to_json, get_existing_media
from app.logging import get_logger
from app.queuer import Queuer


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
        self.queuer = Queuer(test_mode=test_mode) if queue is True else None
        # during testing we need to create the markdown for validation purposes
        self.markdown = markdown or test_mode
        self.existing_media = None
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
            if source.source_file.endswith(".mp3") or source.source_file.endswith(".wav") or source.source_file.endswith(".m4a"):
                return Audio(source=source)
            if source.source_file.endswith("rss") or source.source_file.endswith(".xml"):
                return RSS(source=source)

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

    def _new_transcript_from_source(self, source: Source):
        """Helper method to initialize a new Transcript from source"""
        self.transcripts.append(Transcript(source, self.test_mode))
        # Save preprocessed source
        if source.preprocess:
            write_to_json(
                source.to_json(),
                f"{self.model_output_dir}/{source.loc}",
                f"{source.title}_preprocess", is_metadata=True
            )

    def add_transcription_source(self, source_file, loc="misc", title=None, date=None, tags=[], category=[], speakers=[], preprocess=True, youtube_metadata=None, link=None, chapters=None, nocheck=False, excluded_media=[]):
        """Add a source for transcription"""
        preprocess = False if self.test_mode else preprocess
        transcription_sources = {"added": [], "exist": []}
        # check if source is a local file
        local = False
        if os.path.isfile(source_file):
            local = True
        if not nocheck and not local and self.existing_media is None and not self.test_mode:
            self.existing_media = get_existing_media()
        # combine existing media from btctranscripts.com with excluded media given from source
        excluded_media = {value: True for value in excluded_media}
        if self.existing_media is not None:
            excluded_media.update(self.existing_media)
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
                if video.media not in excluded_media:
                    transcription_sources['added'].append(video)
                    self._new_transcript_from_source(video)
                else:
                    transcription_sources['exist'].append(video)
        elif source.type == 'rss':
            # add a transcript for each source/audio in the rss feed
            for entry in source.entries:
                if entry.media not in excluded_media:
                    transcription_sources['added'].append(entry)
                    self._new_transcript_from_source(entry)
                else:
                    transcription_sources['exist'].append(entry)
        elif source.type in ['audio', 'video']:
            if source.media not in excluded_media:
                transcription_sources['added'].append(source)
                self._new_transcript_from_source(source)
                self.logger.info(
                    f"Source added for transcription: {source.title}")
            else:
                transcription_sources['exist'].append(source)
                self.logger.info(f"Source already exists: {source.title}")
        else:
            raise Exception(f"Invalid source: {source_file}")
        if source.type in ['playlist', 'rss']:
            self.logger.info(
                f"{source.title}: sources added for transcription: {len(transcription_sources['added'])} (Ignored: {len(transcription_sources['exist'])} sources)")
        return transcription_sources

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
                    transcript_json = transcript.to_json()
                    transcript_json["transcript_by"] = f"{self.transcript_by} via TBTBTC v{__version__}"
                    if self.queuer:
                        self.queuer.push_to_queue(transcript_json)
                    else:
                        # store payload for the user to manually send it to the queuer
                        payload_json_file = write_to_json(
                            transcript_json,
                            f"{self.model_output_dir}/{transcript.source.loc}",
                            f"{transcript.title}_payload"
                        )
                        self.logger.info(
                            f"Transcript not added to the queue, payload stored at: {payload_json_file}")
            return self.result
        except Exception as e:
            raise Exception(f"Error with the transcription: {e}") from e

    def clean_up(self):
        self.logger.info("Cleaning up...")
        application.clean_up(self.tmp_dir)
