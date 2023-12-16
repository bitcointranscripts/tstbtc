import json

import click

from app.queuer import Queuer


@click.group()
def queue():
    """Queuer commands"""
    pass


@queue.command()
@click.argument("transcript_json", nargs=1)
def push(transcript_json):
    """Supply a transcript payload as JSON to push to the Queuer
    """
    try:
        configure_logger(log_level=logging.INFO)
        logger.info(f"Adding transcript from {transcript_json}")
        queuer = Queuer()
        with open(transcript_json, "r") as outfile:
            transcript = json.load(outfile)
        response = queuer.push_to_queue(transcript)

    except Exception as e:
        logger.error(e)
        logger.info(f"Exited with error")


@queue.command()
@click.option(
    "--total",
    is_flag=True,
    default=False,
    help="Output only the total number of transcripts in the Queue",
)
def get_queue(total):
    queuer = Queuer()
    result = queuer.get_queue()
    if total:
        print(len(result))
    else:
        print(json.dumps(result))


@queue.command()
@click.argument(
    "status",
    nargs=1,
    type=click.Choice(
        [
            "active",
            "pending",
            "expired"
        ]
    )
)
@click.option(
    "--total",
    is_flag=True,
    default=False,
    help="Output only the total number of items",
)
def get_reviews(status, total):
    queuer = Queuer()
    result = queuer.get_reviews(status)
    if total:
        print(f"{len(result)} {status} reviews")
    else:
        print(json.dumps(result))


@queue.command()
@click.argument("transcript_id", nargs=1)
def get_transcript(transcript_id):
    queuer = Queuer()
    result = queuer.get_transcript(transcript_id)
    print(json.dumps(result))


commands = queue
