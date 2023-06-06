import json
import os
import re
from datetime import datetime

import pytest

from app import application


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
    with open(rel_path("testAssets/transcript.txt"), "r") as file:
        result = file.read()
        file.close()
    source = os.path.abspath(rel_path("testAssets/test_video.mp4"))
    username = "username"
    title = "test_video"
    speakers = None
    tags = None
    category = None
    date = None
    filename, tmp_dir = application.process_source(
        source=source,
        title=title,
        event_date=date,
        tags=tags,
        category=category,
        speakers=speakers,
        loc="yada/yada",
        model="tiny",
        username=username,
        source_type="video",
        local=True,
        test=result,
        chapters=False,
    )
    assert tmp_dir is not None
    filename = os.path.join(tmp_dir, filename)
    assert os.path.isfile(filename)
    assert check_md_file(
        path=filename,
        transcript_by=username,
        media=source,
        title=title,
        date=date,
        tags=tags,
        category=category,
        speakers=speakers,
        local=True,
    )
    application.clean_up(tmp_dir)


@pytest.mark.feature
def test_video_with_all_options():
    source = rel_path("testAssets/test_video.mp4")
    username = "username"
    title = "test_video"
    speakers = "speaker1,speaker2"
    tags = "tag1, tag2"
    category = "category"
    date = "2020-01-31"
    date = datetime.strptime(date, "%Y-%m-%d").date()
    filename, tmp_dir = application.process_source(
        source=source,
        title=title,
        event_date=date,
        tags=tags,
        category=category,
        speakers=speakers,
        loc="yada/yada",
        model="tiny",
        username=username,
        source_type="video",
        local=True,
        test=True,
        chapters=False,
    )
    assert tmp_dir is not None
    filename = os.path.join(tmp_dir, filename)
    assert os.path.isfile(filename)
    category = [cat.strip() for cat in category.split(",")]
    tags = [tag.strip() for tag in tags.split(",")]
    speakers = [speaker.strip() for speaker in speakers.split(",")]
    date = date.strftime("%Y-%m-%d")

    assert check_md_file(
        path=filename,
        transcript_by=username,
        media=source,
        title=title,
        date=date,
        tags=tags,
        category=category,
        speakers=speakers,
        local=True,
    )
    application.clean_up(tmp_dir)


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
    date = datetime.strptime(date, "%Y-%m-%d").date()
    filename, tmp_dir = application.process_source(
        source=source,
        title=title,
        event_date=date,
        tags=tags,
        category=category,
        speakers=speakers,
        loc="yada/yada",
        model="tiny",
        username=username,
        source_type="video",
        local=True,
        test=result,
        chapters=True,
        pr=True,
    )
    assert tmp_dir is not None
    filename = os.path.join(tmp_dir, filename)
    chapter_names = []
    with open(rel_path("testAssets/test_video_chapters.chapters"), "r") as file:
        result = file.read()
        for x in result.split("\n"):
            if re.search(r"CHAPTER\d\dNAME", x):
                chapter_names.append(x.split("= ")[1].strip())
        file.close()

    print(filename)
    assert os.path.isfile(filename)
    category = [cat.strip() for cat in category.split(",")]
    tags = [tag.strip() for tag in tags.split(",")]
    speakers = [speaker.strip() for speaker in speakers.split(",")]
    date = date.strftime("%Y-%m-%d")
    assert check_md_file(
        path=filename,
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
    application.clean_up(tmp_dir)


@pytest.mark.feature
def test_generate_payload():
    date = "2020-01-31"
    date = datetime.strptime(date, "%Y-%m-%d").date()
    with open(rel_path("testAssets/transcript.txt"), "r") as file:
        transcript = file.read()
        file.close()
    payload = application.generate_payload(
        loc=rel_path("yada/yada"),
        title="test_title",
        event_date=date,
        tags=["tag1", "tag2"],
        test=True,
        category=["category1", "category2"],
        speakers=["speaker1", "speaker2"],
        username="username",
        media=rel_path("testAssets/test_video.mp4"),
        transcript=transcript,
    )
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
