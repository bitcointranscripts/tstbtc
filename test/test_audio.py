import os.path
from datetime import datetime

import pytest

from app import application
from app.transcription import Transcription


def rel_path(path):
    return os.path.relpath(
        os.path.abspath(os.path.join(os.path.dirname(__file__), path))
    )


def check_md_file(
    path,
    transcript_by,
    media,
    title=None,
    date=None,
    tags=None,
    category=None,
    speakers=None,
    local=False,
):
    is_correct = True
    if not path:
        return False
    with open(path, "r") as file:
        contents = file.read()
        file.close()

    data = contents.split("---\n")[1].strip().split("\n")

    fields = {}

    for x in data:
        key = x.split(": ")[0]
        value = x.split(": ")[1]
        fields[key] = value

    is_correct &= (
        fields["transcript_by"]
        == f"{transcript_by} via TBTBTC v{application.__version__}"
    )
    if not local:
        is_correct &= fields["media"] == media
    is_correct &= fields["title"] == title

    if date:
        is_correct &= fields["date"] == date
    if tags:
        is_correct &= fields["tags"] == str(tags)
    if speakers:
        is_correct &= fields["speakers"] == str(speakers)
    if category:
        is_correct &= fields["categories"] == str(category)

    return is_correct


@pytest.mark.feature
def test_audio_with_title():
    with open(rel_path("testAssets/transcript.txt"), "r") as file:
        result = file.read()
        file.close()
    source = rel_path("testAssets/audio.mp3")
    title = "title"
    username = "username"
    transcription = Transcription(
        username=username,
        test_mode=True,
    )
    transcription.add_transcription_source(source_file=source, title=title)
    transcripts = transcription.start()
    assert os.path.isfile(transcripts[0])
    assert check_md_file(
        path=transcripts[0],
        transcript_by=username,
        media=source,
        title=title,
        local=True,
    )
    transcription.clean_up()


@pytest.mark.feature
def test_audio_without_title():
    with open(rel_path("testAssets/transcript.txt"), "r") as file:
        result = file.read()
        file.close()

    source = rel_path("test/testAssets/audio.mp3")
    title = None
    transcription = Transcription(
        test_mode=True
    )
    with pytest.raises(Exception) as error:
        transcription.add_transcription_source(source_file=source, title=title)
    assert "Please supply a title for the audio file" in str(error)
    transcription.clean_up()


@pytest.mark.feature
def test_audio_with_all_data():
    with open(rel_path("testAssets/transcript.txt"), "r") as file:
        result = file.read()
        file.close()
    source = rel_path("testAssets/audio.mp3")
    username = "username"
    title = "title"
    speakers = "speaker1,speaker2"
    tags = "tag1, tag2"
    category = "category"
    date = "2020-01-31"
    transcription = Transcription(
        username=username,
        test_mode=True,
    )
    transcription.add_transcription_source(
        source_file=source, title=title, date=date, tags=tags, category=category, speakers=speakers)
    transcripts = transcription.start()

    category = [cat.strip() for cat in category.split(",")]
    tags = [tag.strip() for tag in tags.split(",")]
    speakers = [speaker.strip() for speaker in speakers.split(",")]
    assert os.path.isfile(transcripts[0])
    assert check_md_file(
        path=transcripts[0],
        transcript_by=username,
        media=source,
        title=title,
        date=date,
        tags=tags,
        category=category,
        speakers=speakers,
        local=True,
    )
    transcription.clean_up()
