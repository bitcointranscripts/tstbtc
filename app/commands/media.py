import logging as syslogging
from datetime import datetime
import os

import click

from app import (
    logging,
    utils
)
from app.media_processor import MediaProcessor

logger = logging.get_logger()


def _display_youtube_video_info(info, for_download=False, quality=None, output_dir=None):
    """Displays metadata for a YouTube video."""
    click.echo("-" * 70)
    if for_download:
        click.echo("Starting download:")
        click.echo(f"  Title: {info.get('title')}")
    else:
        click.echo(f"Title: {info.get('title')}")
        click.echo(f"Uploader: {info.get('uploader')}")

    upload_date = info.get('upload_date')
    if upload_date:
        date_obj = datetime.strptime(upload_date, '%Y%m%d')
        date_str = date_obj.strftime('%Y-%m-%d')
        if for_download:
            click.echo(f"  Published on: {date_str}")
        else:
            click.echo(f"Published on: {date_str}")

    duration = info.get('duration')
    if not for_download and duration:
        mins, secs = divmod(duration, 60)
        hours, mins = divmod(mins, 60)
        duration_str = f"{hours}h {mins}m {secs}s" if hours > 0 else f"{mins}m {secs}s"
        click.echo(f"Duration: {duration_str}")

    if for_download:
        click.echo(f"  Quality selection: '{quality}'")
        click.echo(f"  Saving to: '{output_dir or os.getcwd()}'")

    click.echo("-" * 70)


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


@media.command()
@click.argument("youtube_url", required=False)
@click.option("--output_dir", type=click.Path(), default=None, help="Path to save the downloaded video")
@click.option("--quality", default='best', help="Video quality to download (e.g., '360p' or 'best'). Use '--list-formats' to see options.")
@click.option("--list-formats", is_flag=True, help="List available formats for the video instead of downloading.")
def download_youtube_video(youtube_url, output_dir, quality, list_formats):
    """Download a video from YouTube or list available formats."""
    if not youtube_url:
        click.echo("Please provide a YouTube URL or use the --help flag for more options.")
        return

    try:
        processor = MediaProcessor()
        info = processor.get_youtube_video_info(youtube_url)

        if list_formats:
            _display_youtube_video_info(info)
            formats = info.get('formats')
            duration = info.get('duration')  # duration is in seconds

            if formats:
                click.echo("\nAvailable formats:")
                header = f"{'ID':<10} {'EXT':<5} {'RESOLUTION':<15} {'FPS':>5} {'BITRATE':>9} {'VCODEC':<20} {'ACODEC':<15} {'FILESIZE':>10} {'NOTE'}"
                click.echo(header)
                click.echo("-" * 105)
                for f in formats:
                    if f.get('ext') == 'mhtml':
                        continue  # Skip storyboards

                    filesize = f.get('filesize') or f.get('filesize_approx')
                    bitrate = f.get('tbr') or f.get('vbr') or f.get('abr')

                    if filesize:
                        filesize_str = f"{filesize / (1024*1024):.2f}MB"
                    elif bitrate and duration:
                        # Estimate size from bitrate and duration
                        size_in_mb = (bitrate * 1000 / 8 * duration) / (1024 * 1024)
                        filesize_str = f"~{size_in_mb:.2f}MB"
                    else:
                        filesize_str = "N/A"

                    vcodec = f.get('vcodec', 'none')
                    acodec = f.get('acodec', 'none')

                    # Determine resolution and codec display based on stream type
                    if vcodec != 'none' and acodec == 'none':
                        resolution_display = f.get('resolution', 'video only')
                        acodec_display = 'N/A'
                        vcodec_display = vcodec
                    elif vcodec == 'none' and acodec != 'none':
                        resolution_display = 'audio only'
                        vcodec_display = 'N/A'
                        acodec_display = acodec
                    else:
                        resolution_display = f.get('resolution', 'N/A')
                        vcodec_display = vcodec
                        acodec_display = acodec

                    fps = f.get('fps', '')
                    bitrate_str = f"{bitrate}k" if bitrate else "N/A"

                    click.echo(
                        f"{f['format_id']:<10} {f['ext']:<5} {resolution_display:<15} {str(fps):>5} "
                        f"{bitrate_str:>9} {vcodec_display:<20} {acodec_display:<15} {filesize_str:>10} "
                        f"{f.get('format_note', '')}"
                    )

                click.echo("\n" + "-" * 105)
                click.echo("You can use the 'ID' or RESOLUTION (e.g., '360p') with the 'download-youtube-video' command.")
                click.echo("\nExamples:")
                click.echo("  `tstbtc media download-youtube-video <url> --quality 360p`")
                click.echo("  `tstbtc media download-youtube-video <url> --quality 232`")
            else:
                logger.error("Could not retrieve formats.")
        else:
            _display_youtube_video_info(info, for_download=True, quality=quality, output_dir=output_dir)

            title = info.get('title', 'video')
            slugified_title = utils.slugify(title)
            filename_template = f"{slugified_title}.%(ext)s"

            format_selector = quality
            if quality.endswith('p'):
                height = quality[:-1]
                # Prioritize H.264 (avc1) video and AAC (m4a) audio for broad compatibility
                format_selector = f"bestvideo[height<={height}][vcodec^=avc1][ext=mp4]+bestaudio[ext=m4a]/best[height<={height}]"
            elif quality.isdigit():
                format_selector = f"{quality}+bestaudio/{quality}"

            processor.download_youtube_video(
                youtube_url,
                output_dir,
                format_selector=format_selector,
                filename_template=filename_template
            )
            click.echo("Download complete.")
    except Exception as e:
        logger.error(f"Error processing YouTube URL: {e}")


commands = media
