import json
import logging
import tempfile

import click

from app import __app_name__, __version__, application
from app.transcript import Transcript
from app.transcription import Transcription
from app.logging import configure_logger, get_logger
from app.utils import check_if_valid_file_path, write_to_json

logger = get_logger()


def print_version(ctx, param, value):
    if not value or ctx.resilient_parsing:
        return
    click.echo(f"{__app_name__} v{__version__}")
    ctx.exit()


@click.option(
    "-v",
    "--version",
    is_flag=True,
    callback=print_version,
    expose_value=False,
    is_eager=True,
    help="Show the application's version and exit.",
)
@click.group()
def cli():
    pass


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
@click.argument("loc", nargs=1)  # location in the bitcointranscripts hierarchy
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
def transcribe(
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
            source_file=source, loc=loc, title=title, date=date, tags=tags, category=category, speakers=speakers,
        )
        transcription.start()
        if nocleanup:
            logger.info("Not cleaning up temp files...")
        else:
            transcription.clean_up()
    except Exception as e:
        logger.error(e)
        logger.info(f"Exited with error, not cleaning up temp files: {tmp_dir}")


@cli.command()
@click.argument("json_file", nargs=1)
@whisper
@deepgram
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
def transcribe_from_json(
    json_file: str,
    model: str,
    chapters: bool,
    deepgram: bool,
    diarize: bool,
    summarize: bool,
    pr: bool,
    upload: bool,
    markdown: bool,
    noqueue: bool,
    model_output_dir: str,
    nocleanup: bool,
    verbose: bool,
):
    """Supply sources in a JSON file for transcription.
    The JSON can be generated by `preprocess-sources` or created manually.
    """
    try:
        check_if_valid_file_path(json_file)
        tmp_dir = tempfile.mkdtemp()
        configure_logger(logging.DEBUG if verbose else logging.INFO, tmp_dir)
        logger.info(f"Adding transcripts from {json_file}")
        transcription = Transcription(
            model=model,
            deepgram=deepgram,
            chapters=chapters,
            diarize=diarize,
            summarize=summarize,
            upload=upload,
            markdown=markdown,
            queue=not noqueue,
            model_output_dir=model_output_dir,
            nocleanup=nocleanup,
            working_dir=tmp_dir
        )

        with open(json_file, 'r') as file:
            sources = json.load(file)

        for source in sources:
            # Configure metadata given from JSON
            speakers = source.get("speakers", [])
            category = source.get("categories", [])
            tags = source.get("tags", [])
            loc = source.get("loc", "")
            youtube_metadata = source.get("youtube", None)
            transcription.add_transcription_source(
                source_file=source["source_file"], loc=loc,
                title=source["title"], category=category, tags=tags,
                speakers=speakers, date=source["date"],
                youtube_metadata=youtube_metadata,
                chapters=source["chapters"], link=source["media"]
            )

        transcription.start()
        if nocleanup:
            logger.info("Not cleaning up temp files...")
        else:
            transcription.clean_up()

    except Exception as e:
        logger.error(e)


@cli.command()
@click.argument("json_file", nargs=1)
@click.option(
    "--nocheck",
    is_flag=True,
    default=False,
    help="Do not check for existing sources using btctranscripts.com/status.json",
)
def preprocess_sources(json_file, nocheck):
    """Supply sources in a JSON file for preprocess. Preprocessing will fetch
    all the given sources, and output them in a JSON alongside the available
    metadata. The JSON can then be edited and piped to `transcribe-from-json`
    """
    try:
        configure_logger(log_level=logging.INFO)
        check_if_valid_file_path(json_file)
        transcription = Transcription()
        with open(json_file, "r") as outfile:
            sources = json.load(outfile)
            outfile.close()
        logger.info(f"Sources detected: {len(sources)}")
        transcription_sources = []
        for source in sources:
            logger.info(f"Preprocessing {source['title']}: {source['source']}")
            # Configure metadata given from source
            speakers = source.get("speakers", [])
            category = source.get("categories", [])
            tags = source.get("tags", [])
            loc = source.get("loc", "")
            excluded_media = source.get(
                "existing_entries_not_covered_by_btctranscripts/status.json", [])
            excluded_media = [entry["media"] for entry in excluded_media]
            transcription_source = transcription.add_transcription_source(
                source['source'], loc=loc, tags=tags, category=category,
                speakers=speakers, nocheck=nocheck, preprocess=True,
                excluded_media=excluded_media
            )
            for transcription_source in transcription_source["added"]:
                transcription_sources.append(transcription_source)
        # Write all preprocessed sources to JSON
        write_to_json([source.to_json() for source in transcription_sources],
                      transcription.model_output_dir, "preprocessed_sources")
    except Exception as e:
        logger.error(e)
        logger.info(f"Exited with error")


if __name__ == '__main__':
    cli()
