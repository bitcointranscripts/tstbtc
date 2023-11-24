import json
import os
import re
from datetime import datetime

import requests

from app.logging import get_logger

logger = get_logger()


def slugify(text):
    return re.sub(r'\W+', '-', text).strip('-').lower()


def write_to_json(json_data, output_dir, filename, add_timestamp=True):
    if not os.path.isdir(output_dir):
        os.makedirs(output_dir)
    time_in_str = f'_{datetime.now().strftime("%Y-%m-%d-%H-%M-%S")}' if add_timestamp else ""
    file_path = os.path.join(
        output_dir, f"{slugify(filename)}{time_in_str}.json"
    )
    with open(file_path, "w") as json_file:
        json.dump(json_data, json_file, indent=4)
    return file_path


def check_if_valid_file_path(file_path):
    if not isinstance(file_path, str) or not os.path.isfile(file_path):
        raise Exception(f"Not a valid file: {file_path}")


def get_status():
    """Helper method to fetch and store status.json locally"""
    STATUS_FILE_PATH = "status.json"  # the file path for storing the status locally
    try:
        source = STATUS_FILE_PATH
        if os.path.exists(STATUS_FILE_PATH):
            # If the file exists locally, load the data from the file
            with open(STATUS_FILE_PATH, "r") as file:
                data = json.load(file)
        else:
            # If the file doesn't exist locally, fetch it from the remote URL
            url = "http://btctranscripts.com/status.json"
            source = url
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                # Store the fetched data locally
                with open(STATUS_FILE_PATH, "w") as file:
                    json.dump(data, file)
            else:
                raise Exception(f"Status code: {response.status_code}")

        return data, source
    except Exception as e:
        logger.error(f"Error fetching status data: {e}")
        return None


def get_existing_media():
    """Helper method to create a dictionary with all the existing media from btctranscripts.com
        It can be used to quickly check if a source is already transcribed"""
    try:
        data, source = get_status()  # Fetch status data
        if data:
            logger.info(
                f"Fetched {len(data['existing']['media'])} existing media sources from {source}")
            return {value: True for value in data["existing"]["media"]}
        else:
            return {}
    except Exception as e:
        logger.error(f"Error fetching media data: {e}")
        return {}
