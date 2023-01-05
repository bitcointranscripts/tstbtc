import urllib.request
from requests_html import HTMLSession
import subprocess
import os
import click
from app import application
import json
from app import __version__, __app_name__

session = HTMLSession()
os.environ["IMAGEIO_FFMPEG_EXE"] = "/usr/bin/ffmpeg"


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
@click.option('--version',  is_flag=True, callback=print_version,
              expose_value=False, is_eager=True, help="Show the application's version and exit.")
def add(
        media: str,
        loc: str
) -> None:
    """Supply a YouTube video id and directory for transcription"""
    file_name = loc.replace("/", "-")
    file_name_with_ext = file_name + '.md'

    url = "https://www.youtube.com/watch?v=" + media
    result = application.convert(url, 'tiny.en')

    query_string = urllib.parse.urlencode({"format": "json", "url": url})
    full_url = "https://www.youtube.com/oembed" + "?" + query_string

    with urllib.request.urlopen(full_url) as response:
        response_text = response.read()
        data = json.loads(response_text.decode())
        title = data['title']

    meta_data = '---\n' \
                f'title: {title} ' + '\n' \
                                     f'transcript_by: youtube_to_bitcoin_transcript_v_{__version__}\n' \
                                     f'media: {url}\n' \
                                     '---\n'
    with open(file_name_with_ext, 'a') as opf:
        opf.write(meta_data + '\n')
        opf.write(result + '\n')

    absolute_path = os.path.abspath(file_name_with_ext)

    """ INITIALIZE AND OPEN A PR"""
    print("Initializing git \n")
    subprocess.call(['bash', 'github.sh', file_name_with_ext, file_name, absolute_path])
