import os
import click

from app.config import settings
from app.commands.cli_utils import (
    start_server,
    stop_server,
    get_running_server_info,
    is_server_running,
    get_transcription_url
)

@click.group()
def server():
    """Manage the transcription server."""
    pass

@server.command()
@click.option(
    "--mode",
    type=click.Choice(["dev", "prod"]),
    default=settings.config.get("server_mode", "prod"),
    help="Server mode to start",
    show_default=True,
)
@click.option(
    "--host",
    default="0.0.0.0",
    help="The host to bind to",
    show_default=True,
)
@click.option(
    "--port",
    default=8000,
    help="The port to bind to",
    show_default=True,
)
@click.option(
    "--verbose", "-v",
    is_flag=True,
    default=False,
    help="Show server output directly in the console",
)
def start(mode, host, port, verbose):
    """Start the transcription server."""
    start_server(host=host, port=port, mode=mode, verbose=verbose)

@server.command()
@click.option(
    "--mode",
    type=click.Choice(["dev", "prod"]),
    default=settings.config.get("server_mode", "prod"),
    help="Server mode to stop",
    show_default=True,
)
def stop(mode):
    """Stop the transcription server."""
    stop_server(mode=mode)

@server.command()
@click.option(
    "--mode",
    type=click.Choice(["dev", "prod"]),
    default=settings.config.get("server_mode", "prod"),
    help="Server mode to check",
    show_default=True,
)
def status(mode):
    """Check the status of the transcription server."""
    server_info = get_running_server_info(mode)
    url = get_transcription_url()
    
    if server_info:
        click.echo(f"Server is running with PID {server_info['pid']}.")
        click.echo(f"Started at: {server_info['start_time']}")
        click.echo(f"Mode: {server_info['mode']}")
        click.echo(f"Host: {server_info['host']}")
        click.echo(f"Port: {server_info['port']}")
        click.echo(f"Log file: {server_info['log_file']}")
        
        if is_server_running(url):
            click.echo("Server is responding to health checks.")
        else:
            click.echo("Warning: Server process is running but not responding to health checks.")
    else:
        click.echo(f"No {mode} server is currently running.")
        
        if is_server_running(url):
            click.echo(f"However, a server is responding at {url}.")
            click.echo("This might be a server started outside of this CLI.")

@server.command()
@click.option(
    "--mode",
    type=click.Choice(["dev", "prod"]),
    default=settings.config.get("server_mode", "prod"),
    help="Server mode to check logs",
    show_default=True,
)
@click.option(
    "--follow", "-f",
    is_flag=True,
    default=False,
    help="Follow the log output (similar to tail -f)",
)
@click.option(
    "--lines", "-n",
    type=int,
    default=50,
    help="Number of lines to show",
    show_default=True,
)
def logs(mode, follow, lines):
    """View the server logs.
    
    This command allows you to view the logs of the server.
    """
    # Get the path to the log file
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    logs_dir = os.path.join(base_dir, 'logs')
    log_file = os.path.join(logs_dir, f'server_{mode}.log')
    
    if not os.path.exists(log_file):
        click.echo(f"Log file not found: {log_file}")
        click.echo(f"The server may not have been started in {mode} mode yet.")
        return
    
    if follow:
        # Use the 'tail' command with -f option to follow the log file
        click.echo(f"Following logs from {log_file}. Press Ctrl+C to stop.")
        os.system(f"tail -n {lines} -f {log_file}")
    else:
        # Use the 'tail' command to show the last N lines
        os.system(f"tail -n {lines} {log_file}") 