import json
import logging
import os
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
from app.utils import slugify

logger = get_logger()


class Transcript:
    def __init__(self, source, test_mode=False):
        self.source = source
        self.test_mode = test_mode
        self.logger = get_logger()

    def create_transcript(self):
        result = ""
        for x in self.result:
            result = result + x[2] + " "

        return result

    def process_source(self, tmp_dir=None):
        tmp_dir = tmp_dir if tmp_dir is not None else tempfile.mkdtemp()
        self.audio_file = self.source.process(tmp_dir)
        self.title = self.source.title if self.source.title else os.path.basename(
            self.audio_file)[:-4]
        return self.audio_file, tmp_dir

    def transcribe(self, working_dir, generate_chapters, summarize_transcript, service, diarize, upload, model_output_dir, test_transcript=None):

        def process_mp3():
            """using whisper"""
            self.logger.info("Transcribing audio to text using whisper ...")
            try:
                my_model = whisper.load_model(service)
                result = my_model.transcribe(self.audio_file)
                data = []
                for x in result["segments"]:
                    data.append(tuple((x["start"], x["end"], x["text"])))
                data_path = application.generate_srt(
                    data, self.title, model_output_dir)
                if upload:
                    application.upload_file_to_s3(data_path)
                return data
            except Exception as e:
                self.logger.error(
                    f"(wisper,{service}) Error transcribing audio to text: {e}")
                return

        def write_chapters_file():
            """Write out the chapter file based on simple MP4 format (OGM)"""
            try:
                if generate_chapters and len(self.source.chapters) > 0:
                    self.logger.info("Chapters detected")
                    chapters_file = os.path.join(working_dir, os.path.basename(
                        self.audio_file)[:-4] + ".chapters")

                    with open(chapters_file, "w") as fo:
                        for current_chapter in self.source.chapters:
                            fo.write(
                                f"CHAPTER{current_chapter[0]}="
                                f"{current_chapter[1]}\n"
                                f"CHAPTER{current_chapter[0]}NAME="
                                f"{current_chapter[2]}\n"
                            )
                        fo.close()
                    return True
                else:
                    return False
            except Exception as e:
                raise Exception(f"Error writing chapters file: {e}")

        try:
            self.summary = None
            if self.test_mode:
                self.result = test_transcript if test_transcript is not None else "test-mode"
                return self.result
            if not self.audio_file:
                # TODO give audio file path as argument
                raise Exception(
                    "audio file is missing, you need to process_source() first")

            has_chapters = len(self.source.chapters) > 0
            self.result = None
            if service == "deepgram" or summarize_transcript:
                deepgram_resp = application.process_mp3_deepgram(
                    self.audio_file, summarize_transcript, diarize)
                self.result = application.get_deepgram_transcript(
                    deepgram_resp, diarize, self.title, upload, model_output_dir)

                if summarize_transcript:
                    self.summary = application.get_deepgram_summary(
                        deepgram_resp)

                if service == "deepgram" and has_chapters:
                    if diarize:
                        self.result = application.combine_deepgram_chapters_with_diarization(
                            deepgram_data=deepgram_resp, chapters=self.source.chapters
                        )
                    else:
                        self.result = application.combine_deepgram_with_chapters(
                            deepgram_data=deepgram_resp, chapters=self.source.chapters
                        )

            if not service == "deepgram":
                # whisper
                self.result = process_mp3()
                if has_chapters:
                    # this is only available for videos, for now
                    self.result = application.combine_chapter(
                        chapters=self.source.chapters,
                        transcript=self.result,
                        working_dir=working_dir
                    )
                else:
                    # finalize transcript
                    self.result = self.create_transcript()

            return self.result

        except Exception as e:
            raise Exception(f"Error while transcribing audio source: {e}")

    def write_to_file(self, working_dir, transcript_by):
        """Writes transcript to a markdown file and returns its absolute path
        This file is submitted as part of the Pull Request to the 
        bitcointranscripts repo
        """

        def process_metadata(key, value):
            if value:
                value = value.strip()
                value = [item.strip() for item in value.split(",")]
                return f"{key}: {value}\n"
            return ""

        self.logger.info("Creating markdown file with transcription...")
        try:
            # Add metadata prefix
            meta_data = (
                "---\n"
                f"title: {self.title}\n"
                f"transcript_by: {transcript_by} via TBTBTC v{__version__}\n"
            )
            if not self.source.local:
                meta_data += f"media: {self.source.source_file}\n"
            meta_data += process_metadata("tags", self.source.tags)
            meta_data += process_metadata("speakers", self.source.speakers)
            meta_data += process_metadata("categories",
                                          self.source.category)
            if self.summary:
                meta_data += f"summary: {self.summary}\n"
            if self.source.event_date:
                meta_data += f"date: {self.source.event_date}\n"
            meta_data += "---\n"
            # Write to file
            output_file = os.path.join(
                working_dir, f"{slugify(self.title)}.md")
            with open(output_file, "a") as opf:
                opf.write(meta_data + "\n")
                opf.write(self.result + "\n")
                opf.close()
            self.logger.info(f"Markdown file stored at: {output_file}")
            return os.path.abspath(output_file)
        except Exception as e:
            self.logger.error(f"Error writing to file: {e}")

    def __str__(self):
        excluded_fields = ['test_mode', 'logger']
        fields = {key: value for key, value in self.__dict__.items()
                  if key not in excluded_fields}
        fields['source'] = str(self.source)
        return f"Transcript:{str(fields)}"


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
    def __init__(self, source):
        try:
            # initialize source using a base Source
            super().__init__(source_file=source.source_file, link=source.link, loc=source.loc, local=source.local, title=source.title,
                             date=source.event_date, tags=source.tags, category=source.category, speakers=source.speakers, preprocess=source.preprocess)
            self.type = "audio"
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
                               self.category, self.speakers, self.preprocess, link=entry.link))
                self.entries.append(source)
            else:
                self.logger.warning(
                    f"Invalid source for '{entry.title}'. '{enclosure.type}' not supported for RSS feeds, source skipped.")
