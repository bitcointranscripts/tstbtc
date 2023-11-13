import logging
import tempfile

import click

from app import __app_name__, __version__, application
from app.transcript import Transcript
from app.transcription import Transcription
from app.logging import configure_logger, get_logger

logger = get_logger()


@click.group()
def cli():
    pass


def print_version(ctx, param, value):
    if not value or ctx.resilient_parsing:
        return
    click.echo(f"{__app_name__} v{__version__}")
    ctx.exit()


def print_help(ctx, param, value):
    if not value or ctx.resilient_parsing:
        return
    logging.info(ctx.get_help())
    ctx.exit()


whisper = click.option(
    "-m",
    "--model",
    type=click.Choice(
        [
            "tiny",
            "tiny.en",
            "base",
            "base.en",
            "small",
            "small.en",
            "medium",
            "medium.en",
            "large-v2",
        ]
    ),
    default="tiny.en",
    show_default=True,
    help="Select which whisper model to use for the transcription",
)
deepgram = click.option(
    "-D",
    "--deepgram",
    is_flag=True,
    default=False,
    help="Use deepgram for transcription",
)
diarize = click.option(
    "-M",
    "--diarize",
    is_flag=True,
    default=False,
    help="Supply this flag if you have multiple speakers AKA "
    "want to diarize the content",
)
summarize = click.option(
    "-S",
    "--summarize",
    is_flag=True,
    default=False,
    help="Summarize the transcript [only available with deepgram]",
)
use_youtube_chapters = click.option(
    "-C",
    "--chapters",
    is_flag=True,
    default=False,
    help="For YouTube videos, include the YouTube chapters and timestamps in the resulting transcript.",
)
open_pr = click.option(
    "-p",
    "--PR",
    is_flag=True,
    default=False,
    help="Open a PR on the bitcointranscripts repo",
)
upload_to_s3 = click.option(
    "-u",
    "--upload",
    is_flag=True,
    default=False,
    help="Upload processed model files to AWS S3",
)
save_to_markdown = click.option(
    "--markdown",
    is_flag=True,
    default=False,
    help="Save the resulting transcript to a markdown format supported by bitcointranscripts",
)
noqueue = click.option(
    "--noqueue",
    is_flag=True,
    default=False,
    help="Do not push the resulting transcript to the Queuer backend",
)
model_output_dir = click.option(
    "-o",
    "--model_output_dir",
    type=str,
    default="local_models/",
    show_default=True,
    help="Set the directory for saving model outputs",
)
nocleanup = click.option(
    "--nocleanup",
    is_flag=True,
    default=False,
    help="Do not remove temp files on exit",
)
verbose_logging = click.option(
    "-V",
    "--verbose",
    is_flag=True,
    default=False,
    help="Supply this flag to enable verbose logging",
)


@cli.command()
@click.argument("source", nargs=1)
@click.argument("loc", nargs=1)
# Available transcription models and services
@whisper
@deepgram
# Options for adding metadata
@click.option(
    "-t",
    "--title",
    type=str,
    help="Add the title for the resulting transcript (required for audio files)",
)
@click.option(
    "-d",
    "--date",
    type=str,
    help="Add the event date to transcript's metadata in format 'yyyy-mm-dd'",
)
@click.option(
    "-T",
    "--tags",
    multiple=True,
    help="Add a tag to transcript's metadata (can be used multiple times)",
)
@click.option(
    "-s",
    "--speakers",
    multiple=True,
    help="Add a speaker to the transcript's metadata (can be used multiple times)",
)
@click.option(
    "-c",
    "--category",
    multiple=True,
    help="Add a category to the transcript's metadata (can be used multiple times)",
)
# Options for configuring the transcription process
@diarize
@summarize
@use_youtube_chapters
@open_pr
@upload_to_s3
@save_to_markdown
@noqueue
@model_output_dir
@nocleanup
@verbose_logging
@click.option(
    "-v",
    "--version",
    is_flag=True,
    callback=print_version,
    expose_value=False,
    is_eager=True,
    help="Show the application's version and exit.",
)
def add(
    source: str,
    loc: str,
    model: str,
    title: str,
    date: str,
    tags: list,
    speakers: list,
    category: list,
    chapters: bool,
    pr: bool,
    deepgram: bool,
    summarize: bool,
    diarize: bool,
    upload: bool,
    verbose: bool,
    model_output_dir: str,
    nocleanup: bool,
    noqueue: bool,
    markdown: bool
) -> None:
    """Transcribe the given source. Suported sources:
    YouTube videos, YouTube playlists, Local and remote audio files

    Note: The https links need to be wrapped in quotes when running the command
    on zsh
    """
    tmp_dir = tempfile.mkdtemp()
    configure_logger(logging.DEBUG if verbose else logging.INFO, tmp_dir)

    logger.info(
        "This tool will convert Youtube videos to mp3 files and then "
        "transcribe them to text using Whisper. "
    )
    try:
        transcription = Transcription(
            loc=loc,
            model=model,
            chapters=chapters,
            pr=pr,
            summarize=summarize,
            deepgram=deepgram,
            diarize=diarize,
            upload=upload,
            model_output_dir=model_output_dir,
            nocleanup=nocleanup,
            queue=not noqueue,
            markdown=markdown,
            working_dir=tmp_dir
        )
        transcription.add_transcription_source(
            source_file=source, title=title, date=date, tags=tags, category=category, speakers=speakers,
        )
        transcription.start()
        if nocleanup:
            logger.info("Not cleaning up temp files...")
        else:
            transcription.clean_up()
    except Exception as e:
        logger.error(e)
        logger.info(f"Exited with error, not cleaning up temp files: {tmp_dir}")
