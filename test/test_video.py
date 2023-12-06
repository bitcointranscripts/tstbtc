import json
import os
import re
from datetime import datetime

import pytest

from app import application, __version__
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
    chapters=None,
    local=False,
):
    is_correct = True
    if not path:
        return False
    with open(path, "r") as file:
        contents = file.read()
        file.close()

    data = contents.split("---\n")[1].strip().split("\n")

    body = contents.split("---\n")[2].strip()

    fields = {}

    for x in data:
        key = x.split(": ")[0]
        value = x.split(": ")[1]
        fields[key] = value

    detected_chapters = []

    for x in body.split("\n"):
        if x.startswith("##"):
            detected_chapters.append(x[3:].strip())

    is_correct &= (
        fields["transcript_by"]
        == f"{transcript_by} via TBTBTC v{application.__version__}"
    )
    if not is_correct:
        print("Error:", fields["transcript_by"])
    if not local:
        is_correct &= fields["media"] == media
    if not is_correct:
        print("Error:", fields["media"])
    is_correct &= fields["title"] == title
    if not is_correct:
        print("Error:", fields["title"])

    if date:
        is_correct &= fields["date"] == date
        if not is_correct:
            print("Error:", fields["date"])
    if tags:
        is_correct &= fields["tags"] == str(tags)
        if not is_correct:
            print("Error:", fields["tags"], tags)
    if speakers:
        is_correct &= fields["speakers"] == str(speakers)
        if not is_correct:
            print("Error:", fields["speakers"], speakers)
    if category:
        is_correct &= fields["categories"] == str(category)
        if not is_correct:
            print("Error:", fields["categories"], category)
    if chapters:
        is_correct &= detected_chapters == chapters
        if not is_correct:
            print("Error:", detected_chapters, detected_chapters)

    return is_correct


@pytest.mark.feature
def test_video_with_title():
    source = os.path.abspath(rel_path("testAssets/test_video.mp4"))
    username = "username"
    title = "test_video"
    speakers = None
    tags = None
    category = None
    date = None
    transcription = Transcription(
        username=username,
        test_mode=True,
    )
    transcription.add_transcription_source(
        source, title, date, tags, category, speakers)
    transcripts = transcription.start()

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


@pytest.mark.feature
def test_video_with_all_options():
    source = rel_path("testAssets/test_video.mp4")
    username = "username"
    title = "test_video"
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
    assert os.path.isfile(transcripts[0])
    category = [cat.strip() for cat in category.split(",")]
    tags = [tag.strip() for tag in tags.split(",")]
    speakers = [speaker.strip() for speaker in speakers.split(",")]

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


@pytest.mark.feature
def test_video_with_chapters():
    with open(rel_path("testAssets/transcript.txt"), "r") as file:
        result = file.read()
        file.close()
    source = rel_path("testAssets/test_video.mp4")
    username = "username"
    title = "test_video"
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
    transcripts = transcription.start(result)

    chapter_names = []
    with open(rel_path("testAssets/test_video_chapters.chapters"), "r") as file:
        result = file.read()
        for x in result.split("\n"):
            if re.search(r"CHAPTER\d\dNAME", x):
                chapter_names.append(x.split("= ")[1].strip())
        file.close()

    assert os.path.isfile(transcripts[0])
    category = [cat.strip() for cat in category.split(",")]
    tags = [tag.strip() for tag in tags.split(",")]
    speakers = [speaker.strip() for speaker in speakers.split(",")]
    assert check_md_file(
        path=transcripts[0],
        transcript_by=username,
        media=source,
        title=title,
        date=date,
        tags=tags,
        category=category,
        speakers=speakers,
        chapters=chapter_names,
        local=True,
    )
    transcription.clean_up()


@pytest.mark.feature
def test_generate_payload():
    with open(rel_path("testAssets/transcript.txt"), "r") as file:
        transcript = file.read()
        file.close()

    source = rel_path("testAssets/test_video.mp4")
    username = "username"
    title = "test_title"
    speakers = ["speaker1", "speaker2"]
    tags = []
    category = ["category1", "category2"]
    date = "2020-01-31"
    loc = "yada/yada"

    transcription = Transcription(
        test_mode=True,
    )
    transcription.add_transcription_source(
        source_file=source, loc=loc, title=title, date=date, tags=tags, category=category, speakers=speakers)
    transcription.start(test_transcript=transcript)
    transcript_json = transcription.transcripts[0].to_json()
    transcript_json["transcript_by"] = f"{username} via TBTBTC v{__version__}"
    payload = {
        "content": transcript_json
    }
    transcription.clean_up()
    with open(rel_path("testAssets/payload.json"), "r") as outfile:
        content = json.load(outfile)
        outfile.close()

    # assert payload == content
    assert list(content.keys()) == list(payload.keys())
    for k in content.keys():
        if k == "content":
            for key in content[k].keys():
                if key == "loc":
                    assert payload[k][key][-9:] == content[k][key][-9:]
                elif key == "media":
                    assert payload[k][key][-25:] == content[k][key][-25:]
                else:
                    assert payload[k][key] == content[k][key]
        else:
            assert payload[k] == content[k]
