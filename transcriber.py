import logging
from datetime import datetime

import click

from app import __app_name__, __version__, application


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
    "-h",
    "--help",
    is_flag=True,
    callback=print_help,
    expose_value=False,
    is_eager=True,
    help="Show the application's help and exit.",
)
@click.option(
    "-p",
    "--PR",
    is_flag=True,
    default=False,
    help="Supply this flag if you want to generate a payload",
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
    verbose: bool,
) -> None:
    """Supply a YouTube video id and directory for transcription. \n
    Note: The https links need to be wrapped in quotes when running the command
    on zsh
    """
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    else:
        logging.getLogger().setLevel(logging.WARNING)

    logging.info(
        " This tool will convert Youtube videos to mp3 files and then "
        "transcribe them to text using Whisper. "
    )
    try:
        username = application.get_username()
        loc = loc.strip("/")
        event_date = None
        if date:
            try:
                event_date = datetime.strptime(date, "%Y-%m-%d").date()
            except ValueError as e:
                logging.error("Supplied date is invalid: ", e)
                return

        source_type = application.check_source_type(source=source)
        if source_type is None:
            logging.error("Invalid source")
            return
        filename, tmp_dir = application.process_source(
            source=source,
            title=title,
            event_date=event_date,
            tags=tags,
            category=category,
            speakers=speakers,
            loc=loc,
            model=model,
            username=username,
            chapters=chapters,
            pr=pr,
            summarize=summarize,
            source_type=source_type,
            deepgram=deepgram,
            diarize=diarize,
            verbose=verbose,
        )
        if filename:
            """INITIALIZE GIT AND OPEN A PR"""
            logging.info("Transcription complete")
        logging.info("Cleaning up...")
        application.clean_up(tmp_dir)
    except Exception as e:
        logging.error(e)
        logging.error("Cleaning up...")
