import json
import logging
import os
import re
import shutil
import tempfile
from datetime import datetime, date
from urllib.parse import parse_qs, urlparse

import feedparser
import pytube
import requests
import static_ffmpeg
import whisper
import yt_dlp
from clint.textui import progress
from moviepy.editor import VideoFileClip

from app import __app_name__, __version__, application
from app.logging import get_logger
from app.utils import slugify, write_to_json

logger = get_logger()


class Transcript:
    def __init__(self, source, test_mode=False):
        self.source = source
        self.summary = None
        self.test_mode = test_mode
        self.logger = get_logger()

    def process_source(self, tmp_dir=None):
        tmp_dir = tmp_dir if tmp_dir is not None else tempfile.mkdtemp()
        self.audio_file = self.source.process(tmp_dir)
        self.title = self.source.title if self.source.title else os.path.basename(
            self.audio_file)[:-4]
        return self.audio_file, tmp_dir

    def __str__(self):
        excluded_fields = ['test_mode', 'logger']
        fields = {key: value for key, value in self.__dict__.items()
                  if key not in excluded_fields}
        fields['source'] = str(self.source)
        return f"Transcript:{str(fields)}"

    def to_json(self):
        json_data = {
            "title": self.title,
            "categories": self.source.category,
            "tags": self.source.tags,
            "speakers": self.source.speakers,
            "loc": self.source.loc,
            "body": self.result,
            "media": self.source.media
        }
        if self.source.date:
            json_data['date'] = self.source.date

        return json_data


class Source:
    def __init__(self, source_file, loc, local, title, date, tags, category, speakers, preprocess, link=None):
        # initialize source with arguments
        self.save_source(source_file=source_file, loc=loc, local=local, title=title, tags=tags,
                         category=category, speakers=speakers, preprocess=preprocess, link=link)
        self.__config_event_date(date)
        self.logger = get_logger()

    def save_source(self, source_file, loc, local, title, tags, category, speakers, preprocess, link):
        self.source_file = source_file
        self.link = link  # the url that will be used as `media` for the transcript. It contains more metadata than just the audio download link
        self.loc = loc.strip("/")
        self.local = local
        self.title = title
        self.tags = tags
        self.category = category
        self.speakers = speakers
        self.preprocess = preprocess

    @property
    def media(self):
        return self.link if self.link is not None else self.source_file

    @property
    def date(self):
        if self.event_date is None:
            return None
        if type(self.event_date) is str:
            return self.event_date
        else:
            return self.event_date.strftime("%Y-%m-%d")

    def __config_event_date(self, date):
        self.event_date = None
        if date:
            try:
                if type(date) is str:
                    self.event_date = datetime.strptime(date, "%Y-%m-%d").date()
                else:
                    self.event_date = date
            except ValueError as e:
                raise ValueError(f"Supplied date is invalid: {e}")
                return

    def initialize(self):
        try:
            # FFMPEG installed on first use.
            self.logger.debug("Initializing FFMPEG...")
            static_ffmpeg.add_paths()
            self.logger.debug("Initialized FFMPEG")
        except Exception as e:
            raise Exception("Error initializing")


class Audio(Source):
    def __init__(self, source, description=None, chapters=[]):
        try:
            # initialize source using a base Source
            super().__init__(source_file=source.source_file, link=source.link, loc=source.loc, local=source.local, title=source.title,
                             date=source.event_date, tags=source.tags, category=source.category, speakers=source.speakers, preprocess=source.preprocess)
            self.type = "audio"
            self.description = description
            self.chapters = chapters
            self.__config_source()
        except Exception as e:
            raise Exception(f"Error during Audio creation: {e}")

    def __config_source(self):
        if self.title is None:
            raise Exception("Please supply a title for the audio file")

    def process(self, working_dir):
        """Process audio"""

        def download_audio():
            """Helper method to download an audio file and return its absolute path"""
            # sanity checks
            if self.local:
                raise Exception(f"{self.source_file} is a local file")
            if self.title is None:
                raise Exception("Please supply a title for the audio file")
            self.logger.info(f"Downloading audio file: {self.source_file}")
            try:
                audio = requests.get(self.source_file, stream=True)
                output_file = os.path.join(
                    working_dir, f"{slugify(self.title)}.mp3")
                with open(output_file, "wb") as f:
                    total_length = int(audio.headers.get("content-length"))
                    for chunk in progress.bar(
                        audio.iter_content(chunk_size=1024),
                        expected_size=(total_length / 1024) + 1,
                    ):
                        if chunk:
                            f.write(chunk)
                            f.flush()
                return os.path.abspath(output_file)
            except Exception as e:
                raise Exception(f"Error downloading audio file: {e}")

        try:
            self.logger.info(f"Audio processing: '{self.source_file}'")
            if not self.local:
                # download audio file from the internet
                abs_path = download_audio()
                self.logger.info(f"Audio file stored in: {abs_path}")
            else:
                # calculate the absolute path of the local audio file
                filename = self.source_file.split("/")[-1]
                abs_path = os.path.abspath(self.source_file)
            filename = os.path.basename(abs_path)
            if filename.endswith("wav"):
                self.initialize()
                abs_path = application.convert_wav_to_mp3(
                    abs_path=abs_path, filename=filename, working_dir=working_dir
                )
            # return the audio file that is now ready for transcription
            return abs_path

        except Exception as e:
            raise Exception(f"Error processing audio file: {e}")

    def to_json(self):
        json_data = {
            'type': self.type,
            'loc': self.loc,
            "source_file": self.source_file,
            "media": self.media,
            'title': self.title,
            'categories': self.category,
            'tags': self.tags,
            'speakers': self.speakers,
            'date': self.date,
            'description': self.description,
            'chapters': self.chapters,
        }
        if self.date:
            json_data['date'] = self.date

        return json_data


class Video(Source):
    def __init__(self, source, youtube_metadata=None, chapters=None):
        try:
            # initialize source using a base Source
            super().__init__(source_file=source.source_file, link=source.link, loc=source.loc, local=source.local, title=source.title,
                             date=source.event_date, tags=source.tags, category=source.category, speakers=source.speakers, preprocess=source.preprocess)
            self.type = "video"
            self.youtube_metadata = youtube_metadata
            self.chapters = chapters

            if self.youtube_metadata is None:
                # importing from json, metadata exist
                if not self.local and self.preprocess:
                    self.download_video_metadata()
        except Exception as e:
            raise Exception(f"Error during Video creation: {e}")

    def download_video_metadata(self):
        self.logger.info(f"Downloading metadata from: {self.source_file}")
        ydl_opts = {
            'quiet': True,  # Suppress console output
            'extract_flat': True,  # Extract only metadata without downloading
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                yt_info = ydl.extract_info(self.source_file, download=False)
                self.title = yt_info.get('title', 'N/A')
                self.youtube_metadata = {
                    "description": yt_info.get('description', 'N/A'),
                    "tags": yt_info.get('tags', 'N/A'),
                    "categories": yt_info.get('categories', 'N/A')
                }
                self.event_date = datetime.strptime(yt_info.get(
                    'upload_date', None), "%Y%m%d").date() if yt_info.get('upload_date', None) else None
                # Extract chapters from video's metadata
                self.chapters = []
                has_chapters = yt_info.get('chapters', None)
                if has_chapters:
                    for index, x in enumerate(yt_info["chapters"]):
                        name = x["title"]
                        start = x["start_time"]
                        self.chapters.append((str(index), start, str(name)))
        except yt_dlp.DownloadError as e:
            raise Exception(f"Error with downloading YouTube metadata: {e}")

    def process(self, working_dir):
        """Process video"""

        def download_video():
            """Helper method to download a YouTube video and return its absolute path"""
            # sanity checks
            if self.local:
                raise Exception(f"{self.source_file} is a local file")
            try:
                self.logger.info(f"Downloading video: {self.source_file}")
                ydl_opts = {
                    "format": "18",
                    "outtmpl": os.path.join(working_dir, "videoFile.%(ext)s"),
                    "nopart": True,
                }
                with yt_dlp.YoutubeDL(ydl_opts) as ytdl:
                    ytdl.download([self.source_file])

                output_file = os.path.join(working_dir, "videoFile.mp4")
                return os.path.abspath(output_file)
            except Exception as e:
                self.logger.error(e)
                raise Exception(f"Error downloading video: {e}")

        def convert_video_to_mp3(video_file):
            try:
                self.logger.info(f"Converting {video_file} to mp3...")
                clip = VideoFileClip(video_file)
                output_file = os.path.join(
                    working_dir, os.path.basename(video_file)[:-4] + ".mp3")
                clip.audio.write_audiofile(output_file)
                clip.close()
                self.logger.info("Video converted to mp3")
                return output_file
            except Exception as e:
                raise Exception(f"Error converting video to mp3: {e}")

        def extract_chapters_from_downloaded_video_metadata():
            try:
                list_of_chapters = []
                with open(f"{working_dir}/videoFile.info.json", "r") as f:
                    info = json.load(f)
                if "chapters" not in info:
                    self.logger.info("No chapters found for downloaded video")
                    return list_of_chapters
                for index, x in enumerate(info["chapters"]):
                    name = x["title"]
                    start = x["start_time"]
                    list_of_chapters.append((str(index), start, str(name)))

                return list_of_chapters
            except Exception as e:
                self.logger.error(
                    f"Error reading downloaded video's metadata: {e}")
                return []

        try:
            self.logger.info(f"Video processing: '{self.source_file}'")
            if not self.local:
                abs_path = download_video()
                if self.chapters is None:
                    self.chapters = extract_chapters_from_downloaded_video_metadata()
            else:
                abs_path = os.path.abspath(self.source_file)

            self.initialize()
            audio_file = convert_video_to_mp3(abs_path)
            return audio_file

        except Exception as e:
            raise Exception(f"Error processing video file: {e}")

    def __str__(self):
        excluded_fields = ['logger']
        fields = {key: value for key, value in self.__dict__.items()
                  if key not in excluded_fields}
        return f"Video:{str(fields)}"

    def to_json(self):
        json_data = {
            'type': self.type,
            'loc': self.loc,
            "source_file": self.source_file,
            "media": self.media,
            'title': self.title,
            'categories': self.category,
            'tags': self.tags,
            'speakers': self.speakers,
            'date': self.date,
            'chapters': self.chapters,
            'youtube': self.youtube_metadata
        }
        if self.date:
            json_data['date'] = self.date

        return json_data


class Playlist(Source):
    def __init__(self, source, entries, preprocess=False):
        try:
            # initialize source using a base Source
            super().__init__(source.source_file, source.loc, source.local, source.title, source.event_date,
                             source.tags, source.category, source.speakers, source.preprocess)
            self.__config_source(entries)
        except Exception as e:
            raise Exception(f"Error during Playlist creation: {e}")

    def __config_source(self, entries):
        self.type = "playlist"
        self.videos = []
        for entry in entries:
            if entry["title"] != '[Private video]':
                source = Video(source=Source(entry["url"], self.loc, self.local, entry["title"], self.event_date,
                                             self.tags, self.category, self.speakers, self.preprocess))
                self.videos.append(source)


class RSS(Source):
    def __init__(self, source):
        super().__init__(source.source_file, source.loc, source.local, source.title, source.event_date,
                         source.tags, source.category, source.speakers, source.preprocess)
        self.type = "rss"
        self.entries = []
        self.__config_source()

    def __config_source(self):
        try:
            rss = feedparser.parse(self.source_file)
            self.title = rss.feed.title
            self.author = rss.feed.author
            self.logger.info(
                f"RSS feed detected: {self.title} by {self.author}")
        except Exception as e:
            raise Exception(f"Invalid source: {self.source_file}")
        for entry in rss.entries:
            enclosure = next(
                (link for link in entry.links if link.get('rel') == 'enclosure'), None)
            if enclosure.type in ['audio/mpeg', 'audio/wav', 'audio/x-m4a']:
                published_date = date(*entry.published_parsed[:3])
                source = Audio(Source(enclosure.href, self.loc, self.local, entry.title, published_date, self.tags,
                               self.category, self.speakers, self.preprocess, link=entry.link), description=entry.description)
                self.entries.append(source)
            else:
                self.logger.warning(
                    f"Invalid source for '{entry.title}'. '{enclosure.type}' not supported for RSS feeds, source skipped.")
