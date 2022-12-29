"""RP To-Do entry point script."""
# yttbtc/__main__.py

from yttbtc import cli, __app_name__

def main():
    cli.app(prog_name=__app_name__)

if __name__ == "__main__":
    main()
