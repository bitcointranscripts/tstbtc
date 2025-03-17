import logging as syslogging

import click

from app import logging
from app.media_processor import MediaProcessor

logger = logging.get_logger()


@click.group()
def media():
    """Media processing commands"""
    logging.configure_logger(log_level=syslogging.INFO)
    pass


@media.command()
@click.argument("audio_path", type=click.Path(exists=True))
@click.argument("output_dir", type=click.Path(), default=None)
@click.option("--chunk_length", default=1200.0, show_default=True, help="Maximum length of each chunk (in seconds)")
def split_audio(audio_path, output_dir, chunk_length):
    """Split audio file based on silence"""
    try:
        processor = MediaProcessor(chunk_length)
        processor.split_audio(audio_path, output_dir)
        logger.info(f"Audio split successfully and saved in {output_dir}")
    except Exception as e:
        logger.error(f"Error splitting audio: {e}")


@media.command()
@click.argument("input_path", type=click.Path(exists=True))
@click.option("--output_path", type=click.Path(), default=None, help="Path to save the converted MP3 file")
def convert_to_mp3(input_path, output_path):
    """Convert any media file to MP3 format"""
    try:
        processor = MediaProcessor()
        processor.convert_to_mp3(input_path, output_path)
        logger.info(
            f"Media file converted successfully to MP3 and saved as {output_path}")
    except Exception as e:
        logger.error(f"Error converting media file: {e}")


@media.command()
@click.argument("youtube_url")
def get_video_url(youtube_url):
    """Extract the direct video URL from a YouTube link"""
    try:
        processor = MediaProcessor()
        video_url = processor.get_youtube_video_url(youtube_url)
        if video_url:
            logger.info(f"Direct video URL: {video_url}")
        else:
            logger.error("Failed to extract the video URL.")
    except Exception as e:
        logger.error(f"Error extracting video URL: {e}")


commands = media
