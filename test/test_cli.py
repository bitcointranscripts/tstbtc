import os
import shutil

import pytest

from app import application


@pytest.mark.main
def test_initialize_repo():
    try:
        shutil.rmtree("bitcointranscripts", ignore_errors=True)
    except OSError as e:
        print(f"Error occurred while removing directory: {e}")
        assert False


@pytest.mark.feature
def test_find_source_type():
    video = application.check_source_type("B0HW_sJ503Y") == "video"
    video1 = (
        application.check_source_type(
            "https://www.youtube.com/watch?v=B0HW_sJ503Y"
        )
        == "video"
    )
    video2 = (
        application.check_source_type("https://youtu.be/B0HW_sJ503Y") == "video"
    )
    video3 = (
        application.check_source_type("https://youtube.com/embed/B0HW_sJ503Y")
        == "video"
    )
    video4 = (
        application.check_source_type("youtube.com/watch?v=B0HW_sJ503Y")
        == "video"
    )
    video5 = (
        application.check_source_type(
            "www.youtube.com/watch?v=B0HW_sJ503Y&list"
        )
        == "video"
    )
    video6 = (
        application.check_source_type("https://youtube.com/watch?v=B0HW_sJ503Y")
        == "video"
    )

    playlist = (
        application.check_source_type("PLPQwGV1aLnTuN6kdNWlElfr2tzigB9Nnj")
        == "playlist"
    )
    playlist1 = (
        application.check_source_type(
            "https://www.youtube.com/playlist?"
            "list=PLPQwGV1aLnTuN6kdNWlElfr2tzigB9Nnj"
        )
        == "playlist"
    )
    playlist2 = (
        application.check_source_type(
            "www.youtube.com/playlist?list=PLPQwGV1aLnTuN6kdNWlElfr2tzigB9Nnj"
        )
        == "playlist"
    )
    playlist3 = (
        application.check_source_type(
            "https://youtube.com/playlist?list=PLPQwGV1aLnTuN6kdNWlElfr2tzigB9N"
            "nj"
        )
        == "playlist"
    )
    playlist4 = (
        application.check_source_type(
            "https://www.youtube.com/watch?v=B0HW_sJ503Y&list"
            "=PLPQwGV1aLnTuN6kdNWlElfr2tzigB9Nnj"
        )
        == "playlist"
    )
    audio = (
        application.check_source_type(
            "https://anchor.fm/s/12fe0620/podcast/play/32260353/https%3A%2F%2Fd"
            "3ctxlq1ktw2nl.cloudfront.net%2Fstaging%2F2021-3-26%2Fdc6f12e7-a547"
            "-d872-6ef6-7acfe755a692.mp3"
        )
        == "audio"
    )
    assert (
        audio
        and playlist
        and video
        and video1
        and video2
        and video3
        and video4
        and video5
        and video6
        and playlist1
        and playlist2
        and playlist3
        and playlist4
    )


def test_download_audio_file():
    if not os.path.isdir("tmp"):
        os.mkdir("tmp")
    audio = application.get_audio_file(
        "https://dcs.megaphone.fm/FPMN6776580946.mp3", "test"
    )
    print("audio", audio)
    assert os.path.isfile("tmp/" + audio)
    os.remove("tmp/" + audio)


def test_download_video_file():
    if not os.path.isdir("tmp"):
        os.mkdir("tmp")
    url = "https://www.youtube.com/watch?v=B0HW_sJ503Y"
    video = application.download_video(url)
    assert os.path.isfile(video) and os.path.isfile("tmp/videoFile.info.json")
    print()
    os.remove(video)
    os.remove("tmp/videoFile.info.json")
    shutil.rmtree("tmp")


@pytest.mark.main
def test_convert_video_to_audio():
    application.convert_video_to_mp3("test/testAssets/test_video.mp4")
    assert os.path.isfile("test/testAssets/test_video.mp3")
    os.remove("test/testAssets/test_video.mp3")
