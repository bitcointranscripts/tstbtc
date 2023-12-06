"""This module provides the transcript cli."""
import errno
import logging
import os
import shutil
import subprocess

import boto3
from dotenv import dotenv_values

from app import __app_name__, __version__
from app.logging import get_logger

logger = get_logger()


def convert_wav_to_mp3(abs_path, filename, working_dir="tmp/"):
    logger = logging.getLogger(__app_name__)
    logger.info(f"Converting {abs_path} to mp3...")
    op = subprocess.run(
        ["ffmpeg", "-i", abs_path, filename[:-4] + ".mp3"],
        cwd=working_dir,
        capture_output=True,
        text=True,
    )
    logger.info(op.stdout)
    logger.error(op.stderr)
    return os.path.abspath(os.path.join(working_dir, filename[:-4] + ".mp3"))


def create_pr(absolute_path, loc, username, curr_time, title):
    logger = logging.getLogger(__app_name__)
    branch_name = loc.replace("/", "-")
    subprocess.call(
        [
            "bash",
            "initializeRepo.sh",
            absolute_path,
            loc,
            branch_name,
            username,
            curr_time,
        ]
    )
    subprocess.call(
        ["bash", "github.sh", branch_name, username, curr_time, title]
    )
    logger.info("Please check the PR for the transcription.")


def clean_up(tmp_dir):
    try:
        shutil.rmtree(tmp_dir)
    except OSError as exc:
        if exc.errno != errno.ENOENT:
            raise



def upload_file_to_s3(file_path):
    logger = logging.getLogger(__app_name__)
    s3 = boto3.client("s3")
    config = dotenv_values(".env")
    bucket = config["S3_BUCKET"]
    base_filename = file_path.split("/")[-1]
    dir = "model outputs/" + base_filename
    try:
        s3.upload_file(file_path, bucket, dir)
        logger.info(f"File uploaded to S3 bucket : {bucket}")
    except Exception as e:
        logger.error(f"Error uploading file to S3 bucket: {e}")
