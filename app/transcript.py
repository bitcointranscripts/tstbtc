import logging
import os
import tempfile
from datetime import (
    datetime,
    date
)
from typing import (
    Optional,
    TypedDict
)

import feedparser
import requests
import static_ffmpeg
import yt_dlp
from clint.textui import progress

from app import (
    __app_name__,
    __version__,
    logging,
    utils
)
from app.media_processor import MediaProcessor

logger = logging.get_logger()


class Output(TypedDict):
    raw: Optional[str]
    markdown: Optional[str]
    json: Optional[str]
    # The output generated by the transcription service
    transcription_service_output_file: Optional[str]
    srt_file: Optional[str]
    dpe_file: Optional[str]


class Transcript:
    def __init__(self, source, test_mode=False, metadata_file=None):
        self.status = "queued" # Can be "queued", "in_progress", "completed", or "failed"
        self.source: Source = source
        self.metadata_file = metadata_file
        self.test_mode = test_mode
        self.logger = logging.get_logger()
        self.outputs: Output = {
            "markdown": None,
            "json": None,
            "raw": None,
            "transcription_service_output_file": None,
            "srt_file": None,
            "dpe_file": None
        }

    def process_source(self, tmp_dir=None):
        tmp_dir = tmp_dir if tmp_dir is not None else tempfile.mkdtemp()
        self.audio_file = self.source.process(tmp_dir)
        return self.audio_file, tmp_dir

    @property
    def output_path_with_title(self):
        return self.source.output_path_with_title

    @property
    def title(self):
        return self.source.title

    @property
    def summary(self):
        return self.source.summary

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
        }
        if "raw" in self.outputs:
            json_data["body"] = self.outputs["raw"]
        if not self.source.local:
            json_data["media"] = self.source.media
        if self.source.date:
            json_data['date'] = self.source.date.isoformat()

        return json_data


class Source:
    def __init__(self, source_file, loc, local, title, date, tags, category, speakers, preprocess, summary=None, episode=None, link=None):
        # initialize source with arguments
        self.save_source(source_file=source_file, loc=loc, local=local, title=title, summary=summary,
                         episode=episode, tags=tags, category=category, speakers=speakers, preprocess=preprocess, link=link)
        self.__config_event_date(date)
        self.logger = logging.get_logger()

    def save_source(self, source_file, loc, local, title, summary, episode, tags, category, speakers, preprocess, link):
        self.source_file = source_file
        self.link = link  # the url that will be used as `media` for the transcript. It contains more metadata than just the audio download link
        self.loc = loc.strip("/")
        self.local = local
        self.title = title
        self.summary = summary
        self.episode = episode
        self.tags = tags
        self.category = category
        self.speakers = speakers
        self.preprocess = preprocess
        self.additional_resources: list[dict[str, str]] = []

    @property
    def output_path_with_title(self):
        return os.path.join(self.loc.strip("/"), utils.slugify(self.title))

    @property
    def media(self):
        return self.link if self.link is not None else self.source_file

    @property
    def date(self) -> date:
        if self.event_date is None:
            return None
        # If event_date is already a datetime.date object, return it directly
        elif isinstance(self.event_date, date):
            return self.event_date
        # TODO: This conversion from string to datetime.date is temporary.
        # Once all date handling in the codebase is updated to use datetime.date objects,
        # this conversion logic should be removed.
        elif isinstance(self.event_date, str):
            # Utilizing the validate_and_parse_date function to ensure the date string
            # is valid and to convert it into a datetime.date object.
            return utils.validate_and_parse_date(self.event_date)

    def __config_event_date(self, event_date):
        self.event_date = None
        if event_date:
            if isinstance(event_date, str):
                self.event_date = utils.validate_and_parse_date(event_date)
            elif isinstance(event_date, date):
                # If date_input is already a datetime.date, assign it directly
                self.event_date = event_date
            else:
                # Raise an error if date_input is neither a string nor a datetime.date
                raise TypeError(
                    "The date must be a string or datetime.date object.")

    def initialize(self):
        try:
            # FFMPEG installed on first use.
            self.logger.debug("Initializing FFMPEG...")
            static_ffmpeg.add_paths()
            self.logger.debug("Initialized FFMPEG")
        except Exception as e:
            raise Exception("Error initializing")

    def __str__(self):
        default_print_keys = ["tags", "speakers", "category"]
        excluded_fields = ["logger"]
        fields = {}
        for key, value in self.__dict__.items():
            if key not in excluded_fields:
                if key in default_print_keys or not isinstance(value, list):
                    fields[key] = value
                else:
                    fields[key] = f"{len(value)} {type(value[0]).__name__ if value else 'unknown'}"
        return f"Source:{str(fields)}"

    def to_json(self):
        json_data = {
            'title': self.title,
            'speakers': self.speakers,
            'tags': self.tags,
            'type': self.type,
            'loc': self.loc,
            "source_file": self.source_file,
            "media": self.media,
            'categories': self.category,
            'chapters': self.chapters,
        }
        if self.description:
            json_data['description'] = self.description
        if self.date:
            json_data['date'] = self.date.isoformat()
        if self.summary:
            json_data['summary'] = self.summary
        if self.additional_resources:
            json_data['additional_resources'] = self.additional_resources
        if self.episode:
            json_data['episode'] = self.episode
        return json_data


class Audio(Source):
    def __init__(self, source, description=None, chapters=[]):
        try:
            # initialize source using a base Source
            super().__init__(source_file=source.source_file, link=source.link, loc=source.loc, local=source.local, title=source.title, summary=source.summary,
                             episode=source.episode, date=source.event_date, tags=source.tags, category=source.category, speakers=source.speakers, preprocess=source.preprocess)
            self.type = "audio"
            self.description = description
            self.chapters = chapters
            if self.title is None:
                self.title = os.path.splitext(
                    os.path.basename(self.source_file))[0]
        except Exception as e:
            raise Exception(f"Error during Audio creation: {e}")

    def process(self, working_dir):
        """Process audio"""

        def download_audio():
            """Helper method to download an audio file and return its absolute path"""
            # sanity checks
            if self.local:
                raise Exception(f"{self.source_file} is a local file")
            self.logger.debug(f"Downloading audio file: {self.source_file}")
            try:
                audio = requests.get(self.source_file, stream=True)
                output_file = os.path.join(
                    working_dir, f"{utils.slugify(self.title)}.mp3")
                with open(output_file, "wb") as f:
                    chunked_audio = audio.iter_content(chunk_size=1024)
                    total_length = audio.headers.get("content-length")
                    if total_length is None:
                        self.logger.warning(
                            "Content length not available. Unable to display progress bar.")
                    else:
                        chunked_audio = progress.bar(
                            chunked_audio, expected_size=(int(total_length) / 1024) + 1)
                    for chunk in chunked_audio:
                        if chunk:
                            f.write(chunk)
                            f.flush()
                return os.path.abspath(output_file)
            except Exception as e:
                raise Exception(f"Error downloading audio file: {e}")

        try:
            self.logger.debug(f"Audio processing: '{self.source_file}'")
            if not self.local:
                # download audio file from the internet
                audio_file_path = download_audio()
                self.logger.debug(f"Audio file stored in: {audio_file_path}")
            else:
                # calculate the absolute path of the local audio file
                audio_file_path = os.path.abspath(self.source_file)
            if not audio_file_path.endswith(".mp3"):
                media_processor = MediaProcessor()
                audio_file_path = media_processor.convert_to_mp3(
                    audio_file_path, working_dir)
            # return the audio file that is now ready for transcription
            return audio_file_path

        except Exception as e:
            raise Exception(f"Error processing audio file: {e}")

    def __str__(self):
        excluded_fields = ['logger']
        fields = {key: value for key, value in self.__dict__.items()
                  if key not in excluded_fields}
        return f"Audio:{str(fields)}"

    def to_json(self):
        json_data = super().to_json()

        return json_data


class Video(Source):
    def __init__(self, source, youtube_metadata=None, chapters=[]):
        try:
            # initialize source using a base Source
            super().__init__(source_file=source.source_file, link=source.link, loc=source.loc, local=source.local, title=source.title, summary=source.summary,
                             episode=source.episode, date=source.event_date, tags=source.tags, category=source.category, speakers=source.speakers, preprocess=source.preprocess)
            self.type = "video"
            self.youtube_metadata = youtube_metadata
            self.chapters = chapters

            if self.youtube_metadata is None:
                # importing from json, metadata exist
                if not self.local and self.preprocess:
                    self.download_video_metadata()
        except Exception as e:
            raise Exception(f"Error during Video creation: {e}")

    @property
    def description(self):
        return self.youtube_metadata.get("description", None) if self.youtube_metadata else None

    @description.setter
    def description(self, value):
        if self.youtube_metadata is None:
            self.youtube_metadata = {}
        self.youtube_metadata["description"] = value

    def download_video_metadata(self):
        self.logger.debug(f"Downloading metadata from: {self.source_file}")
        ydl_opts = {
            'quiet': True,  # Suppress console output
            'extract_flat': True,  # Extract only metadata without downloading
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                yt_info = ydl.extract_info(self.source_file, download=False)
                if self.title is None:
                    self.title = yt_info.get('title', 'N/A')
                self.youtube_metadata = {
                    "description": yt_info.get('description', 'N/A'),
                    "tags": yt_info.get('tags', 'N/A'),
                    "categories": yt_info.get('categories', 'N/A')
                }
                if self.event_date is None and yt_info.get('upload_date', None):
                    self.event_date = datetime.strptime(
                        yt_info.get('upload_date', None), "%Y%m%d").date()
                # Extract chapters from video's metadata
                self.chapters = []
                has_chapters = yt_info.get('chapters', None)
                if has_chapters:
                    # YouTube adds an extra chapter when a starting chapter is not defined
                    if yt_info["chapters"][0]["title"] == '<Untitled Chapter 1>':
                        yt_info["chapters"].pop(0)
                    for index, x in enumerate(yt_info["chapters"]):
                        name = x["title"]
                        start = x["start_time"]
                        self.chapters.append([str(index), start, str(name)])
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
                self.logger.debug(f"Downloading video: {self.source_file}")
                ydl_opts = {
                    "format": 'worstvideo[ext=mp4]+worstaudio[ext=m4a]/worst[ext=mp4]/worst',
                    "outtmpl": os.path.join(working_dir, "videoFile.%(ext)s"),
                    "nopart": True,
                }
                with yt_dlp.YoutubeDL(ydl_opts) as ytdl:
                    ytdl.download([self.source_file])

                output_file = os.path.join(working_dir, "videoFile.mp4")
                if not os.path.exists(output_file):
                    raise Exception(f"Downloaded file not found: {output_file}")

                return os.path.abspath(output_file)
            except Exception as e:
                self.logger.error(e)
                raise Exception(f"Error downloading video: {e}")

        try:
            self.logger.debug(f"Video processing: '{self.source_file}'")
            if not self.local:
                video_file_path = download_video()
            else:
                video_file_path = os.path.abspath(self.source_file)

            media_processor = MediaProcessor()
            audio_file = media_processor.convert_to_mp3(
                video_file_path, working_dir)
            return audio_file

        except Exception as e:
            raise Exception(f"Error processing video file: {e}")

    def __str__(self):
        excluded_fields = ['logger']
        fields = {key: value for key, value in self.__dict__.items()
                  if key not in excluded_fields}
        return f"Video:{str(fields)}"

    def to_json(self):
        json_data = super().to_json()
        json_data['youtube'] = self.youtube_metadata

        return json_data


class Playlist(Source):
    def __init__(self, source, entries):
        try:
            # initialize source using a base Source
            super().__init__(source_file=source.source_file, link=source.link, loc=source.loc, local=source.local, title=source.title, summary=source.summary,
                             episode=source.episode, date=source.event_date, tags=source.tags, category=source.category, speakers=source.speakers, preprocess=source.preprocess)
            self.__config_source(entries)
        except Exception as e:
            raise Exception(f"Error during Playlist creation: {e}")

    def __config_source(self, entries):
        self.type = "playlist"
        self.videos: Video = []
        for entry in entries:
            if entry["title"] != '[Private video]':
                source = Video(source=Source(source_file=entry["url"], loc=self.loc, local=self.local, title=entry["title"], date=self.event_date,
                                             tags=self.tags, category=self.category, speakers=self.speakers, preprocess=self.preprocess))
                self.videos.append(source)


class RSS(Source):
    def __init__(self, source):
        super().__init__(source_file=source.source_file, link=source.link, loc=source.loc, local=source.local, title=source.title, summary=source.summary,
                         episode=source.episode, date=source.event_date, tags=source.tags, category=source.category, speakers=source.speakers, preprocess=source.preprocess)
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
            if enclosure.type in ['audio/mpeg', 'audio/wav', 'audio/x-m4a', 'audio/mp4']:
                published_date = date(*entry.published_parsed[:3])
                # Attempt to extract episode information
                episode = int(
                    entry.itunes_episode) if 'itunes_episode' in entry else None

                source = Audio(Source(source_file=enclosure.href, loc=self.loc, local=self.local, title=entry.title, date=published_date, summary=self.summary, episode=episode, tags=self.tags,
                               category=self.category, speakers=self.speakers, preprocess=self.preprocess, link=entry.link), description=entry.description)
                self.entries.append(source)
            else:
                self.logger.warning(
                    f"Invalid source for '{entry.title}'. '{enclosure.type}' not supported for RSS feeds, source skipped.")
