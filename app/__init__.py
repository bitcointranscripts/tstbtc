"""Top-level package for tstbtc."""
# yttbtc/__init__.py

__app_name__ = "tstbtc"
__version__ = "1.0.0"

(
    SUCCESS,
    DIR_ERROR,
    FILE_ERROR,
    DB_READ_ERROR,
    DB_WRITE_ERROR,
    JSON_ERROR,
    ID_ERROR,
) = range(7)

ERRORS = {
    DIR_ERROR: "config directory error",
    FILE_ERROR: "config file error",
}
