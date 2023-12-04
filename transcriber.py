import json
import logging
import tempfile
import traceback

import click

from app import __app_name__, __version__, application
from app.transcript import Transcript
from app.transcription import Transcription
from app.logging import configure_logger, get_logger
from app.utils import check_if_valid_file_path, write_to_json, configure_metadata_given_from_JSON

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

add_loc = click.option(
    "--loc",
    default="misc",
    help="Add the location in the bitcointranscripts hierarchy that you want to associate the transcript with",
)
add_title = click.option(
    "-t",
    "--title",
    type=str,
    help="Add the title for the resulting transcript (required for audio files)",
)
add_date = click.option(
    "-d",
    "--date",
    type=str,
    help="Add the event date to transcript's metadata in format 'yyyy-mm-dd'",
)
add_tags = click.option(
    "-T",
    "--tags",
    multiple=True,
    help="Add a tag to transcript's metadata (can be used multiple times)",
)
add_speakers = click.option(
    "-s",
    "--speakers",
    multiple=True,
    help="Add a speaker to the transcript's metadata (can be used multiple times)",
)
add_category = click.option(
    "-c",
    "--category",
    multiple=True,
    help="Add a category to the transcript's metadata (can be used multiple times)",
)


@cli.command()
@click.argument("source", nargs=1)
# Available transcription models and services
@whisper
@deepgram
# Options for adding metadata
@add_title
@add_date
@add_tags
@add_speakers
@add_category
@add_loc
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
    """Transcribe the provided sources. Suported sources include: \n
    - YouTube videos and playlists\n
    - Local and remote audio files\n
    - JSON files containing individual sources\n

    Notes:\n
    - The https links need to be wrapped in quotes when running the command
    on zsh\n
    - The JSON can be generated by `preprocess-sources` or created manually
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
        if source.endswith(".json"):
            transcription.add_transcription_source_JSON(source)
        else:
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
            metadata = configure_metadata_given_from_JSON(source)
            excluded_media = source.get(
                "existing_entries_not_covered_by_btctranscripts/status.json", [])
            excluded_media = [entry["media"] for entry in excluded_media]
            transcription_source = transcription.add_transcription_source(
                metadata['source_file'], loc=metadata['loc'],
                tags=metadata['tags'], category=metadata['category'],
                speakers=metadata['speakers'], nocheck=nocheck,
                preprocess=True, excluded_media=excluded_media
            )
            for transcription_source in transcription_source["added"]:
                transcription_sources.append(transcription_source)
        # Write all preprocessed sources to JSON
        write_to_json([source.to_json() for source in transcription_sources],
                      transcription.model_output_dir, "preprocessed_sources")
    except Exception as e:
        logger.error(e)
        logger.info(f"Exited with error")


@cli.command()
@click.argument("deepgram_json_file", nargs=1)
@click.argument("preprocess_json_file", nargs=1)
@diarize
def postprocess_deepgram_transcript(
    deepgram_json_file,
    preprocess_json_file,
    diarize
):
    """Supply required metadata to postprocess a transcript.
    """
    try:
        configure_logger(log_level=logging.INFO)
        check_if_valid_file_path(deepgram_json_file)
        check_if_valid_file_path(preprocess_json_file)
        logger.info(f"Processing deepgram output from {deepgram_json_file}")
        transcription = Transcription(queue=False)
        with open(deepgram_json_file, "r") as outfile:
            deepgram_output = json.load(outfile)
            outfile.close()
        with open(preprocess_json_file, "r") as outfile:
            preprocess_output = json.load(outfile)
            outfile.close()
        metadata = configure_metadata_given_from_JSON(preprocess_output)
        transcription.add_transcription_source(
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
            preprocess=False
        )
        # Postprocess deepgram transcript
        has_chapters = len(metadata["chapters"]) > 0
        transcript_from_deepgram = transcription.transcripts[0]
        transcript_from_deepgram.title = metadata["title"]
        transcript_from_deepgram.result = application.get_deepgram_transcript(
            deepgram_output, diarize)
        if has_chapters:
            if diarize:
                transcript_from_deepgram.result = application.combine_deepgram_chapters_with_diarization(
                    deepgram_data=deepgram_output, chapters=metadata["chapters"])
            else:
                transcript_from_deepgram.result = application.combine_deepgram_with_chapters(
                    deepgram_data=deepgram_output, chapters=metadata["chapters"])

        transcription.postprocess(transcript_from_deepgram)
    except Exception as e:
        logger.error(e)
        traceback.print_exc()


if __name__ == '__main__':
    cli()
