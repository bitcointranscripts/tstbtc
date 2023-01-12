import subprocess
import os
import click
from app import application
from app import __version__, __app_name__


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
@click.option('--version', is_flag=True, callback=print_version,
              expose_value=False, is_eager=True, help="Show the application's version and exit.")
def add(
        media: str,
        loc: str,
        model: str
) -> None:
    """Supply a YouTube video id and directory for transcription"""

    url = "https://www.youtube.com/watch?v=" + media
    selected_model = model + '.en'
    result = application.convert(url, selected_model)
    file_name_with_ext = application.write_to_file(result, url)

    absolute_path = os.path.abspath(file_name_with_ext)
    branch_name = loc.replace("/", "-")

    """ INITIALIZE GIT AND OPEN A PR"""
    subprocess.call(['bash', 'github.sh', absolute_path, loc, branch_name])


