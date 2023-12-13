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
from app import (
    __app_name__,
    __version__,
    application,
    services,
    utils
)
from app.logging import get_logger
from app.queuer import Queuer


class Transcription:
    def __init__(
        self,
        model="tiny",
        pr=False,
        summarize=False,
        deepgram=False,
        diarize=False,
        upload=False,
        model_output_dir="local_models/",
        nocleanup=False,
        queue=True,
        markdown=False,
        username=None,
        test_mode=False,
        working_dir=None,
        batch_preprocessing_output=False,
        needs_review=False,
    ):
        self.test_mode = test_mode
        self.logger = get_logger()
        self.tmp_dir = working_dir if working_dir is not None else tempfile.mkdtemp()

        self.transcript_by = "username" if test_mode else self.__get_username()
        # during testing we need to create the markdown for validation purposes
        self.markdown = markdown or test_mode
        self.review_flag = self.__configure_review_flag(needs_review)
        self.open_pr = pr
        if deepgram:
            self.service = services.Deepgram(
                summarize, diarize, upload, model_output_dir)
        else:
            self.service = services.Whisper(model, upload, model_output_dir)
        self.model_output_dir = model_output_dir
        self.transcripts = []
        self.nocleanup = nocleanup
        # during testing we do not have/need a queuer backend
        self.queuer = Queuer(test_mode=test_mode) if queue is True else None
        self.existing_media = None
        self.preprocessing_output = [] if batch_preprocessing_output else None

        self.logger.info(f"Temp directory: {self.tmp_dir}")

    def _create_subdirectory(self, subdir_name):
        """Helper method to create subdirectories within the central temp director"""
        subdir_path = os.path.join(self.tmp_dir, subdir_name)
        os.makedirs(subdir_path)
        return subdir_path

    def __configure_review_flag(self, needs_review):
        # sanity check
        if needs_review and not self.markdown:
            raise Exception(
                "The `--needs-review` flag is only applicable when creating a markdown")

        if needs_review:
            return " --needs-review"
        else:
            return ""

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
            if source.source_file.endswith((".mp3", ".wav", ".m4a")):
                return Audio(source=source, chapters=chapters)
            if source.source_file.endswith(("rss", ".xml")):
                return RSS(source=source)

            if youtube_metadata is not None:
                # we have youtube metadata, this can only be true for videos
                source.preprocess = False
                return Video(source=source, youtube_metadata=youtube_metadata, chapters=chapters)
            if source.source_file.endswith((".mp4", ".webm")):
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
        metadata_file = None
        if source.preprocess:
            if self.preprocessing_output is None:
                # Save preprocessing output for each individual source
                metadata_file = utils.write_to_json(
                    source.to_json(),
                    f"{self.model_output_dir}/{source.loc}",
                    f"{source.title}_metadata", is_metadata=True
                )
            else:
                # Keep preprocessing outputs for later use
                self.preprocessing_output.append(source.to_json())
        # Initialize new transcript from source
        self.transcripts.append(Transcript(
            source=source, test_mode=self.test_mode, metadata_file=metadata_file))

    def add_transcription_source(
        self,
        source_file,
        loc="misc",
        title=None,
        date=None,
        tags=[],
        category=[],
        speakers=[],
        preprocess=True,
        youtube_metadata=None,
        link=None,
        chapters=None,
        nocheck=False,
        excluded_media=[]
    ):
        """Add a source for transcription"""
        preprocess = False if self.test_mode else preprocess
        transcription_sources = {"added": [], "exist": []}
        # check if source is a local file
        local = False
        if os.path.isfile(source_file):
            local = True
        if not nocheck and not local and self.existing_media is None and not self.test_mode:
            self.existing_media = utils.get_existing_media()
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

    def add_transcription_source_JSON(self, json_file, nocheck=False):
        # validation checks
        utils.check_if_valid_file_path(json_file)
        sources = utils.check_if_valid_json(json_file)

        # Check if JSON contains multiple sources
        if not isinstance(sources, list):
            # Initialize an array with 'sources' as the only element
            sources = [sources]

        self.logger.info(f"Adding transcripts from {json_file}")
        for source in sources:
            metadata = utils.configure_metadata_given_from_JSON(source)

            self.add_transcription_source(
                source_file=metadata["source_file"],
                loc=metadata["loc"],
                title=metadata["title"],
                category=metadata["category"],
                tags=metadata["tags"],
                speakers=metadata["speakers"],
                date=metadata["date"],
                youtube_metadata=metadata["youtube_metadata"],
                chapters=metadata["chapters"],
                link=metadata["media"],
                excluded_media=metadata["excluded_media"],
                nocheck=nocheck
            )

    def start(self, test_transcript=None):
        self.result = []
        try:
            for transcript in self.transcripts:
                output_dir = f"{self.model_output_dir}/{transcript.source.loc}"
                self.logger.info(
                    f"Processing source: {transcript.source.source_file}")
                transcript.tmp_dir = self._create_subdirectory(
                    f"transcript{len(self.result) + 1}")
                transcript.process_source(transcript.tmp_dir)
                if self.test_mode:
                    transcript.result = test_transcript if test_transcript is not None else "test-mode"
                else:
                    transcript = self.service.transcribe(transcript)
                postprocessed_transcript = self.postprocess(transcript)
                self.result.append(postprocessed_transcript)

            return self.result
        except Exception as e:
            raise Exception(f"Error with the transcription: {e}") from e

    def write_to_markdown_file(self, transcript: Transcript, output_dir):
        """Writes transcript to a markdown file and returns its absolute path
        This file is the one submitted as part of the Pull Request to the
        bitcointranscripts repo
        """
        self.logger.info("Creating markdown file with transcription...")
        try:
            # Add metadata prefix
            meta_data = (
                "---\n"
                f'title: "{transcript.title}"\n'
                f"transcript_by: {self.transcript_by} via tstbtc v{__version__}{self.review_flag}\n"
            )
            if not transcript.source.local:
                meta_data += f"media: {transcript.source.media}\n"
            meta_data += f"tags: {str(transcript.source.tags)}\n"
            meta_data += f"speakers: {str(transcript.source.speakers)}\n"
            meta_data += f"categories: {str(transcript.source.category)}\n"
            if transcript.summary:
                meta_data += f"summary: {transcript.summary}\n"
            if transcript.source.event_date:
                meta_data += f"date: {transcript.source.event_date}\n"
            meta_data += "---\n"
            # Write to file
            markdown_file = f"{utils.configure_output_file_path(output_dir, transcript.title, add_timestamp=False)}.md"
            with open(markdown_file, "w") as opf:
                opf.write(meta_data + "\n")
                opf.write(transcript.result + "\n")
            self.logger.info(f"Markdown file stored at: {markdown_file}")
            return os.path.abspath(markdown_file)
        except Exception as e:
            raise Exception(f"Error writing to file: {e}")

    def write_to_json_file(self, transcript: Transcript):
        self.logger.info("Creating JSON file with transcription...")
        output_dir = f"{self.model_output_dir}/{transcript.source.loc}"
        transcript_json = transcript.to_json()
        transcript_json["transcript_by"] = f"{self.transcript_by} via tstbtc v{__version__}"
        json_file = utils.write_to_json(
            transcript_json,
            output_dir,
            f"{transcript.title}_payload"
        )
        self.logger.info(f"Transcription stored at {json_file}")
        return json_file

    def postprocess(self, transcript: Transcript):
        try:
            result = transcript.result
            output_dir = f"{self.model_output_dir}/{transcript.source.loc}"
            if self.markdown:
                transcription_md_file = self.write_to_markdown_file(
                    transcript,
                    output_dir if not self.test_mode else transcript.tmp_dir)
                result = transcription_md_file
            if self.open_pr:
                application.create_pr(
                    absolute_path=transcription_md_file,
                    loc=transcript.source.source_file,
                    username=self.transcript_by,
                    curr_time=str(round(time.time() * 1000)),
                    title=transcript.title,
                )
            elif not self.test_mode:
                transcript_json = transcript.to_json()
                transcript_json["transcript_by"] = f"{self.transcript_by} via tstbtc v{__version__}"
                if self.queuer:
                    return self.queuer.push_to_queue(transcript_json)
                else:
                    # store payload for the user to manually send it to the queuer
                    payload_json_file = self.write_to_json_file(transcript)
                    result = payload_json_file
            return result
        except Exception as e:
            raise Exception(f"Error with postprocessing: {e}") from e

    def clean_up(self):
        self.logger.info("Cleaning up...")
        application.clean_up(self.tmp_dir)
