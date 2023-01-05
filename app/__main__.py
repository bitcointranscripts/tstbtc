"""RP To-Do entry point script."""
# yttbtc/__main__.py

from yttbtc import application, __app_name__

def main():
    application.app(prog_name=__app_name__)

if __name__ == "__main__":
    main()
