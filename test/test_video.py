from app import application
import os
import pytest
import re
from datetime import datetime
import json


def check_md_file(path, transcript_by, media, title=None, date=None, tags=None, category=None, speakers=None,
                  chapters=None, local=False):
    is_correct = True
    if not path:
        return False
    with open(path, 'r') as file:
        contents = file.read()
        file.close()

    data = contents.split('---\n')[1].strip().split('\n')

    body = contents.split('---\n')[2].strip()

    fields = {}

    for x in data:
        key = x.split(": ")[0]
        value = x.split(": ")[1]
        fields[key] = value

    detected_chapters = []

    for x in body.split('\n'):
        if x.startswith('##'):
            detected_chapters.append(x[3:].strip())

    is_correct &= fields["transcript_by"] == f'{transcript_by} via TBTBTC v{application.__version__}'
    if not is_correct:
        print("Error:", fields["transcript_by"])
    if not local:
        is_correct &= fields['media'] == media
    if not is_correct:
        print("Error:", fields['media'])
    is_correct &= fields['title'] == title
    if not is_correct:
        print("Error:", fields['title'])

    if date:
        is_correct &= fields["date"] == date
        if not is_correct:
            print("Error:", fields["date"])
    if tags:
        is_correct &= fields['tags'] == str(tags)
        if not is_correct:
            print("Error:", fields['tags'], tags)
    if speakers:
        is_correct &= fields['speakers'] == str(speakers)
        if not is_correct:
            print("Error:", fields['speakers'], speakers)
    if category:
        is_correct &= fields['categories'] == str(category)
        if not is_correct:
            print("Error:", fields['categories'], category)
    if chapters:
        is_correct &= detected_chapters == chapters
        if not is_correct:
            print("Error:", detected_chapters, detected_chapters)

    return is_correct


@pytest.mark.feature
def test_video_with_title():
    with open("test/testAssets/transcript.txt", "r") as file:
        result = file.read()
        file.close()
    source = 'test/testAssets/test_video.mp4'
    username = "username"
    title = "test_video"
    speakers = None
    tags = None
    category = None
    date = None
    created_files = []
    filename = application.process_source(source=source, title=title, event_date=date, tags=tags, category=category,
                                          speakers=speakers, loc="yada/yada", model="tiny", username=username,
                                          source_type="video", local=True,
                                          created_files=created_files, test=result, chapters=False)
    assert os.path.isfile(filename)
    assert check_md_file(path=filename, transcript_by=username, media=source, title=title,
                         date=date, tags=tags,
                         category=category, speakers=speakers, local=True)
    created_files.append('test_video.md')
    application.clean_up(created_files)


@pytest.mark.feature
def test_video_with_all_options():
    with open("test/testAssets/transcript.txt", "r") as file:
        result = file.read()
        file.close()
    source = 'test/testAssets/test_video.mp4'
    username = "username"
    title = "test_video"
    speakers = "speaker1,speaker2"
    tags = "tag1, tag2"
    category = "category"
    date = "2020-01-31"
    date = datetime.strptime(date, '%Y-%m-%d').date()
    created_files = []
    filename = application.process_source(source=source, title=title, event_date=date, tags=tags, category=category,
                                          speakers=speakers, loc="yada/yada", model="tiny", username=username,
                                          source_type="video", local=True,
                                          created_files=created_files, test=True, chapters=False)
    assert os.path.isfile(filename)
    category = [cat.strip() for cat in category.split(",")]
    tags = [tag.strip() for tag in tags.split(",")]
    speakers = [speaker.strip() for speaker in speakers.split(",")]
    date = date.strftime('%Y-%m-%d')

    assert check_md_file(path=filename, transcript_by=username, media=source, title=title, date=date, tags=tags,
                         category=category, speakers=speakers, local=True)
    created_files.append('test_video.md')
    application.clean_up(created_files)


@pytest.mark.feature
def test_video_with_chapters():
    with open("test/testAssets/transcript.txt", "r") as file:
        result = file.read()
        file.close()
    source = 'test/testAssets/test_video.mp4'
    username = "username"
    title = "test_video"
    speakers = "speaker1,speaker2"
    tags = "tag1, tag2"
    category = "category"
    date = "2020-01-31"
    date = datetime.strptime(date, '%Y-%m-%d').date()
    created_files = []
    filename = application.process_source(source=source, title=title, event_date=date, tags=tags, category=category,
                                          speakers=speakers, loc="yada/yada", model="tiny", username=username,
                                          source_type="video", local=True,
                                          created_files=created_files, test=result, chapters=True, pr=True)
    chapter_names = []
    with open("test/testAssets/test_video_chapters.chapters", "r") as file:
        result = file.read()
        for x in result.split('\n'):
            if re.search("CHAPTER\d\dNAME", x):
                chapter_names.append(x.split("= ")[1].strip())
        file.close()

    print(filename)
    assert os.path.isfile(filename)
    category = [cat.strip() for cat in category.split(",")]
    tags = [tag.strip() for tag in tags.split(",")]
    speakers = [speaker.strip() for speaker in speakers.split(",")]
    date = date.strftime('%Y-%m-%d')
    assert check_md_file(path=filename, transcript_by=username, media=source, title=title, date=date, tags=tags,
                         category=category, speakers=speakers, chapters=chapter_names, local=True)
    created_files.append('test_video.md')
    created_files.append("test/testAssets/test_video.chapters")
    application.clean_up(created_files)


@pytest.mark.feature
def test_generate_payload():
    date = "2020-01-31"
    date = datetime.strptime(date, '%Y-%m-%d').date()
    with open("test/testAssets/transcript.txt", "r") as file:
        transcript = file.read()
        file.close()
    payload = application.generate_payload(title="test_title", event_date=date, tags="tag1, tag2", test=True,
                                           category="category1, category2", speakers="speaker1, speaker2",
                                           username="username", media="test/testAssets/test_video.mp4",
                                           transcript=transcript)
    with open('test/testAssets/payload.json', 'r') as outfile:
        content = json.load(outfile)
        outfile.close()
    assert payload == content

