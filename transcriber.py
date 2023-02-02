import os
import subprocess
import click
from app import application
from app import __version__, __app_name__
from datetime import datetime
import time


@click.group()
def cli():
    pass


def print_version(ctx, param, value):
    if not value or ctx.resilient_parsing:
        return
    click.echo(f"{__app_name__} v{__version__}")
    ctx.exit()


@click.command()
@click.argument('source', nargs=1)
@click.argument('loc', nargs=1)
@click.option('-m', '--model', type=click.Choice(['tiny', 'base', 'small', 'medium']), default='tiny',
              help='Options for transcription model'
              )
@click.option('-t', '--title', type=str, help="Supply transcribed file title in 'quotes'")
@click.option('-d', '--date', type=str, help="Supply the event date in format 'yyyy-mm-dd'")
@click.option('-T', '--tags', type=str, help="Supply the tags for the transcript in 'quotes' and separated by commas")
@click.option('-s', '--speakers', type=str, help="Supply the speakers for the transcript in 'quotes' and separated by "
                                                 "commas")
@click.option('-c', '--category', type=str, help="Supply the category for the transcript in 'quotes' and separated by "
                                                 "commas")
@click.option('-v', '--version', is_flag=True, callback=print_version,
              expose_value=False, is_eager=True, help="Show the application's version and exit.")
def add(
        source: str,
        loc: str,
        model: str,
        title: str,
        date: str,
        tags: str,
        speakers: str,
        category: str,
) -> None:
    """Supply a YouTube video id and directory for transcription"""
    username = application.get_username()
    curr_time = str(round(time.time() * 1000))
    loc = loc.strip("/")
    event_date = None
    if date:
        try:
            event_date = datetime.strptime(date, '%Y-%m-%d').date()
        except:
            print("Supplied date is invalid")
            return

    created_files = []
    source_type = application.check_source_type(source)
    filename = application.process_source(source, title, event_date, tags, category, speakers, loc, model, username,
                                          curr_time, source_type, created_files)
    if filename:
        """ INITIALIZE GIT AND OPEN A PR"""
        branch_name = loc.replace("/", "-")
        subprocess.call(['bash', 'github.sh', branch_name, username, curr_time, filename[:-4]])
        print("Transcription complete. Please check the PR for the transcription.")
    print("Cleaning up...")
    application.clean_up(created_files)
