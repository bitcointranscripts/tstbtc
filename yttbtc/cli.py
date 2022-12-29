"""This module provides the transcript cli."""
# yttbtc/cli.py

import urllib.request
import json
import urllib
from typing import Optional
import typer
from requests_html import HTMLSession
from youtube_transcript_api import YouTubeTranscriptApi

from yttbtc import __app_name__, __version__
import subprocess

app = typer.Typer()

session = HTMLSession()


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"{__app_name__} v{__version__}")
        raise typer.Exit()

@app.callback()
def main(
        version: Optional[bool] = typer.Option(
            None,
            "--version",
            "-v",
            help="Show the application's version and exit.",
            callback=_version_callback,
            is_eager=True,
        )
) -> None:
    return


@app.command()
def yt2btc(
        video_id: str,
        file_name: str
) -> None:
    """Add a transcription"""
    file_name = file_name.replace("/", "-")
    file_name_with_ext = file_name + '.md'
    outls = []

    tx = YouTubeTranscriptApi.get_transcript(video_id)

    url = "https://www.youtube.com/watch?v=" + video_id

    query_string = urllib.parse.urlencode({"format": "json", "url": url})
    full_url = "https://www.youtube.com/oembed" + "?" + query_string

    with urllib.request.urlopen(full_url) as response:
        response_text = response.read()
        data = json.loads(response_text.decode())
        title = data['title']

    meta_data = '---\n' \
                f'title: {title} ' + '\n' \
                'transcript_by: youtube_transcript_api\n' \
                f'media: {url}\n' \
                '---\n'
    with open(file_name_with_ext, 'a') as opf:
        opf.write(meta_data + '\n')

        for i in tx:
            output_text = (i['text'])
            outls.append(output_text)

            opf.write(output_text + '\n')


    """ INITIALIZE AND OPEN A PR"""
    print("Initializing git and creating a repo \n")
    subprocess.call(['bash', 'github.sh', file_name_with_ext, file_name])


