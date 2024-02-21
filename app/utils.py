import json
import os
import re
from datetime import datetime

import requests

from app.logging import get_logger

logger = get_logger()


def slugify(text):
    return re.sub(r'\W+', '-', text).strip('-').lower()


def configure_output_file_path(output_dir, filename, add_timestamp=True, is_metadata=False):
    if is_metadata:
        # subdirectory for metadata
        output_dir = os.path.join(output_dir, "metadata")
    if not os.path.isdir(output_dir):
        os.makedirs(output_dir)
    time_in_str = f'_{datetime.now().strftime("%Y-%m-%d-%H-%M-%S")}' if add_timestamp else ""
    file_path = os.path.join(
        output_dir, f"{slugify(filename)}{time_in_str}"
    )
    return file_path


def write_to_json(json_data, output_dir, filename, add_timestamp=True, is_metadata=False):
    file_path = f"{configure_output_file_path(output_dir, filename, add_timestamp, is_metadata)}.json"
    with open(file_path, "w") as json_file:
        json.dump(json_data, json_file, indent=4)
    return file_path


def decimal_to_sexagesimal(dec):
    sec = int(dec % 60)
    minu = int((dec // 60) % 60)
    hrs = int((dec // 60) // 60)

    return f"{hrs:02d}:{minu:02d}:{sec:02d}"


def check_if_valid_json(file_path):
    try:
        with open(file_path) as file:
            json_content = json.load(file)
        return json_content
    except Exception as e:
        raise Exception(f"Not a valid JSON file: {file_path}")


def check_if_valid_file_path(file_path):
    if not isinstance(file_path, str) or not os.path.isfile(file_path):
        raise Exception(f"Not a valid file: {file_path}")


def configure_metadata_given_from_JSON(source, from_json=None):
    """Helper method that deals with missings fields from JSON
    by assigning default values"""
    try:
        metadata = {}
        # required in the JSON
        metadata["source_file"] = source["source_file"]
        # not required in the JSON
        metadata["title"] = source.get("title", "no-title")
        metadata["speakers"] = source.get("speakers", [])
        metadata["category"] = source.get("categories", [])
        metadata["tags"] = source.get("tags", [])
        metadata["chapters"] = source.get("chapters", [])
        metadata["loc"] = source.get("loc", "")
        metadata["date"] = source.get("date", None)
        metadata["youtube_metadata"] = source.get("youtube", None)
        metadata["media"] = source.get("media", None)
        excluded_media = source.get(
            "existing_entries_not_covered_by_btctranscripts/status.json", [])
        metadata["excluded_media"] = [entry["media"]
                                      for entry in excluded_media]
        # transcription service output
        services = ["whisper", "deepgram"]
        for service in services:
            key = f"{service}_output"
            metadata[key] = source.get(key, None)
            if metadata[key] is not None and from_json is not None:
                base_directory = os.path.dirname(from_json)
                metadata[key] = os.path.join(base_directory, metadata[key])
                check_if_valid_file_path(metadata[key])

        return metadata
    except KeyError as e:
        raise Exception(f"Parsing JSON: {e} is required")


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
