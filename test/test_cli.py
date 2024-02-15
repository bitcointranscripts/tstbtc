import os
import shutil

import pytest

from app import application
from app.transcription import Transcription


def rel_path(path):
    return os.path.relpath(
        os.path.abspath(os.path.join(os.path.dirname(__file__), path))
    )


# @pytest.mark.main
# def test_find_source_type():
# @TODO rewwrite


@pytest.mark.feature
def test_download_audio_file():
    transcription = Transcription(
        test_mode=True,
    )
    transcription.add_transcription_source(
        source_file="https://dcs.megaphone.fm/FPMN6776580946.mp3", title="test")
    audio_file, tmp_dir = transcription.transcripts[0].process_source(
        transcription.tmp_dir)
    assert os.path.isfile(audio_file)
    application.clean_up(tmp_dir)


@pytest.mark.feature
def test_download_video_file():
    transcription = Transcription(
        test_mode=True,
    )
    transcription.add_transcription_source(
        source_file="https://www.youtube.com/watch?v=B0HW_sJ503Y", title="test")
    audio_file, tmp_dir = transcription.transcripts[0].process_source(
        transcription.tmp_dir)
    assert os.path.isfile(f"{tmp_dir}/videoFile.mp4")  # video download
    assert os.path.isfile(audio_file)  # mp3 convert
    application.clean_up(tmp_dir)
