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


@click.command()
@click.argument("source", nargs=1)
@click.argument("loc", nargs=1)
@click.option(
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
    help="Options for transcription model",
)
@click.option(
    "-t",
    "--title",
    type=str,
    help="Supply transcribed file title in 'quotes', title is mandatory in case"
    " of audio files",
)
@click.option(
    "-d",
    "--date",
    type=str,
    help="Supply the event date in format 'yyyy-mm-dd'",
)
@click.option(
    "-T",
    "--tags",
    type=str,
    help="Supply the tags for the transcript in 'quotes' and separated by "
    "commas",
)
@click.option(
    "-s",
    "--speakers",
    type=str,
    help="Supply the speakers for the transcript in 'quotes' and separated by "
    "commas",
)
@click.option(
    "-c",
    "--category",
    type=str,
    help="Supply the category for the transcript in 'quotes' and separated by "
    "commas",
)
@click.option(
    "-v",
    "--version",
    is_flag=True,
    callback=print_version,
    expose_value=False,
    is_eager=True,
    help="Show the application's version and exit.",
)
@click.option(
    "-C",
    "--chapters",
    is_flag=True,
    default=False,
    help="Supply this flag if you want to generate chapters for the transcript",
)
@click.option(
    "-p",
    "--PR",
    is_flag=True,
    default=False,
    help="Supply this flag if you want to open a PR at the bitcointranscripts repo",
)
@click.option(
    "-D",
    "--deepgram",
    is_flag=True,
    default=False,
    help="Supply this flag if you want to use deepgram",
)
@click.option(
    "-S",
    "--summarize",
    is_flag=True,
    default=False,
    help="Supply this flag if you want to summarize the content",
)
@click.option(
    "-M",
    "--diarize",
    is_flag=True,
    default=False,
    help="Supply this flag if you have multiple speakers AKA "
    "want to diarize the content",
)
@click.option(
    "-V",
    "--verbose",
    is_flag=True,
    default=False,
    help="Supply this flag to enable verbose logging",
)
@click.option(
    "-o",
    "--model_output_dir",
    type=str,
    default="local_models/",
    help="Supply this flag if you want to change the directory for saving "
    "model outputs",
)
@click.option(
    "-u",
    "--upload",
    is_flag=True,
    default=False,
    help="Supply this flag if you want to upload processed model files to AWS "
    "S3",
)
@click.option(
    "--nocleanup",
    is_flag=True,
    default=False,
    help="Do not remove temp files on exit",
)
@click.option(
    "--noqueue",
    is_flag=True,
    default=False,
    help="Do not push the resulting transcript to the Queuer backend",
)
@click.option(
    "--markdown",
    is_flag=True,
    default=False,
    help="Create a markdown file for the resulting transcript",
)
def add(
    source: str,
    loc: str,
    model: str,
    title: str,
    date: str,
    tags: str,
    speakers: str,
    category: str,
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
    """Supply a YouTube video id and directory for transcription. \n
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
