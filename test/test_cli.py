import shutil
import pytest
import os
from app import application


@pytest.mark.main
def test_initialize_repo():
    try:
        shutil.rmtree("bitcointranscripts", ignore_errors=True)
    except Exception as e:
        assert False


@pytest.mark.main
def test_find_source_type():
    video = application.check_source_type("B0HW_sJ503Y") == "video"

    playlist = application.check_source_type("PLPQwGV1aLnTuN6kdNWlElfr2tzigB9Nnj") == "playlist"

    audio = application.check_source_type(
        "https://anchor.fm/s/12fe0620/podcast/play/32260353/https%3A%2F%2Fd3ctxlq1ktw2nl.cloudfront.net%2Fstaging"
        "%2F2021-3-26%2Fdc6f12e7-a547-d872-6ef6-7acfe755a692.mp3") == "audio"
    assert audio and playlist and video


def test_download_audio_file():
    audio = application.get_audio_file("https://dcs.megaphone.fm/FPMN6776580946.mp3", "test")
    assert os.path.isfile(audio)
    os.remove(audio)


def test_download_video_file():
    url = "https://www.youtube.com/watch?v=B0HW_sJ503Y"
    video = application.download_video(url)
    assert os.path.isfile(video) and os.path.isfile(video[:-3] + "description")
    print()
    os.remove(video)
    os.remove(video[:-3] + "description")


@pytest.mark.main
def test_chapter_creation():
    chapters = application.read_description("testAssets/test_video.description")
    with open("testAssets/test_video_1.chapters", "w") as file:
        file.write(str(chapters))
    with open("testAssets/test_video_1.chapters", "r") as file:
        data = str(file.read().strip("\n"))
        with open("testAssets/test_video_chapters.chapters", "r") as file:
            chapters = str(file.read().strip("\n"))
            assert data == chapters
    os.remove("testAssets/test_video_1.chapters")


@pytest.mark.main
def test_split_video():
    chapters = application.read_description("testAssets/test_video.description")
    application.split_mp4(chapters, "testAssets/test_video.mp4", "testAssets/test_video")
    is_pass = True
    for i in range(3):
        is_pass = is_pass and os.path.isfile("testAssets/test_video - (" + str(i) + ").mp4")
        os.remove("testAssets/test_video - (" + str(i) + ").mp4")
    assert is_pass


@pytest.mark.main
def test_convert_video_to_audio():
    application.convert_video_to_mp3("testAssets/test_video.mp4")
    assert os.path.isfile("testAssets/test_video.mp3")
    os.remove("testAssets/test_video.mp3")
