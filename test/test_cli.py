import os
import shutil

import pytest

from app import application


def rel_path(path):
    return os.path.relpath(
        os.path.abspath(os.path.join(os.path.dirname(__file__), path))
    )


@pytest.mark.main
def test_initialize_repo():
    try:
        shutil.rmtree("bitcointranscripts", ignore_errors=True)
    except OSError as e:
        print(f"Error occurred while removing directory: {e}")
        assert False


@pytest.mark.feature
def test_find_source_type():
    assert application.check_source_type("B0HW_sJ503Y")[0] == "video"
    assert application.check_source_type("https://www.youtube.com/watch?v=B0HW_sJ503Y")[0] == "video"
    assert application.check_source_type("https://youtu.be/B0HW_sJ503Y")[0] == "video"
    assert application.check_source_type("https://youtube.com/embed/B0HW_sJ503Y")[0] == "video"
    assert application.check_source_type("youtube.com/watch?v=B0HW_sJ503Y")[0] == "video"
    assert application.check_source_type("www.youtube.com/watch?v=B0HW_sJ503Y&list")[0] == "video"
    assert application.check_source_type("https://youtube.com/watch?v=B0HW_sJ503Y")[0] == "video"

    assert application.check_source_type("PLPQwGV1aLnTuN6kdNWlElfr2tzigB9Nnj")[0] == "playlist"
    assert application.check_source_type("https://www.youtube.com/playlist?list=PLPQwGV1aLnTuN6kdNWlElfr2tzigB9Nnj")[0] == "playlist"
    assert application.check_source_type("www.youtube.com/playlist?list=PLPQwGV1aLnTuN6kdNWlElfr2tzigB9Nnj")[0] == "playlist"
    assert application.check_source_type("https://youtube.com/playlist?list=PLPQwGV1aLnTuN6kdNWlElfr2tzigB9Nnj")[0] == "playlist"
    assert application.check_source_type("https://www.youtube.com/watch?v=B0HW_sJ503Y&list=PLPQwGV1aLnTuN6kdNWlElfr2tzigB9Nnj")[0] == "playlist"

    assert application.check_source_type("https://anchor.fm/s/12fe0620/podcast/play/32260353/https%3A%2F%2Fd3ctxlq1ktw2nl.cloudfront.net%2Fstaging%2F2021-3-26%2Fdc6f12e7-a547-d872-6ef6-7acfe755a692.mp3")[0] == "audio"



def test_download_audio_file():
    if not os.path.isdir("tmp"):
        os.mkdir("tmp")
    audio = application.get_audio_file(
        "https://dcs.megaphone.fm/FPMN6776580946.mp3", "test"
    )
    print("audio", audio)
    assert os.path.isfile(audio)
    os.remove(audio)


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
    if not os.path.isdir("tmp/"):
        os.makedirs("tmp/")
    application.convert_video_to_mp3(rel_path("testAssets/test_video.mp4"))
    assert os.path.isfile("tmp/test_video.mp3")
    shutil.rmtree("tmp/")
