import subprocess
import os
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
@click.argument('media', nargs=1)
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
        media: str,
        loc: str,
        model: str,
        title: str,
        date: str,
        tags: str,
        speakers: str,
        category: str,
) -> None:
    """Supply a YouTube video id and directory for transcription"""

    url = "https://www.youtube.com/watch?v=" + media
    videos = [url]
    if media.startswith("PL") or media.startswith("UU") or media.startswith("FL") or media.startswith("RD"):
        url = "https://www.youtube.com/playlist?list=" + media
        videos = application.get_playlist_videos(url)
        print("Playlist detected")

    selected_model = model + '.en'

    event_date = str()
    if date:
        try:
            event_date = datetime.strptime(date, '%Y-%m-%d').date()
        except:
            print("Supplied date is invalid")
            return
    print("What is your github username?")
    username = input()
    curr_time = str(round(time.time() * 1000))
    for video in videos:
        print("Transcribing video: " + video)
        result = application.convert(video, selected_model)
        # print(result)
        file_name_with_ext = application.write_to_file(result, video, title, event_date, tags, category, speakers)

        absolute_path = os.path.abspath(file_name_with_ext)
        branch_name = loc.replace("/", "-")
        subprocess.call(['bash', 'initializeRepo.sh', absolute_path, loc, branch_name, username, curr_time])
    """ INITIALIZE GIT AND OPEN A PR"""
    branch_name = loc.replace("/", "-")
    subprocess.call(['bash', 'github.sh', branch_name, username, curr_time])
