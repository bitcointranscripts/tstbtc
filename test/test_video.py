from app import application
import time
import os
import pytest
import re


def check_md_file(path, transcript_by, media, title=None, date=None, tags=None, category=None, speakers=None,
                  chapters=None):
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
    with open("testAssets/transcript.txt", "r") as file:
        result = file.read()
        file.close()
    source = 'testAssets/test_video.mp4'
    username = "username"
    title = "test_video"
    speakers = None
    tags = None
    category = None
    date = None
    curr_time = str(round(time.time() * 1000))
    created_files = []
    filename = application.process_source(source=source, title=title, event_date=date, tags=tags, category=category,
                                          speakers=speakers, loc="yada/yada", model="tiny", username=username,
                                          curr_time=curr_time, source_type="video", local=True,
                                          created_files=created_files, test=result, chapters=False)
    assert os.path.isfile(filename)
    assert check_md_file(path=filename, transcript_by=username, media=source, title=title,
                         date=date, tags=tags,
                         category=category, speakers=speakers)
    created_files.append('test_video.md')
    application.clean_up(created_files)


@pytest.mark.feature
def test_video_with_all_options():
    with open("testAssets/transcript.txt", "r") as file:
        result = file.read()
        file.close()
    source = 'testAssets/test_video.mp4'
    username = "username"
    title = "test_video"
    speakers = "speaker1,speaker2"
    tags = "tag1, tag2"
    category = "category"
    date = "2020-01-01"
    curr_time = str(round(time.time() * 1000))
    created_files = []
    filename = application.process_source(source=source, title=title, event_date=date, tags=tags, category=category,
                                          speakers=speakers, loc="yada/yada", model="tiny", username=username,
                                          curr_time=curr_time, source_type="video", local=True,
                                          created_files=created_files, test=True, chapters=False)
    assert os.path.isfile(filename)
    category = [cat.strip() for cat in category.split(",")]
    tags = [tag.strip() for tag in tags.split(",")]
    speakers = [speaker.strip() for speaker in speakers.split(",")]
    assert check_md_file(path=filename, transcript_by=username, media=source, title=title,
                         date=date, tags=tags,
                         category=category, speakers=speakers)
    created_files.append('test_video.md')
    application.clean_up(created_files)


@pytest.mark.feature
def test_video_with_chapters():
    with open("testAssets/transcript.txt", "r") as file:
        result = file.read()
        file.close()
    source = 'testAssets/test_video.mp4'
    username = "username"
    title = "test_video"
    speakers = "speaker1,speaker2"
    tags = "tag1, tag2"
    category = "category"
    date = "2020-01-01"
    curr_time = str(round(time.time() * 1000))
    created_files = []
    filename = application.process_source(source=source, title=title, event_date=date, tags=tags, category=category,
                                          speakers=speakers, loc="yada/yada", model="tiny", username=username,
                                          curr_time=curr_time, source_type="video", local=True,
                                          created_files=created_files, test=result, chapters=True)
    chapter_names = []
    with open("testAssets/test_video.chapters", "r") as file:
        result = file.read()
        for x in result.split('\n'):
            if re.search("CHAPTER\d\dNAME", x):
                chapter_names.append(x.split("= ")[1].strip())
        file.close()

    assert os.path.isfile(filename)
    category = [cat.strip() for cat in category.split(",")]
    tags = [tag.strip() for tag in tags.split(",")]
    speakers = [speaker.strip() for speaker in speakers.split(",")]
    assert check_md_file(path=filename, transcript_by=username, media=source, title=title, date=date, tags=tags,
                         category=category, speakers=speakers, chapters=chapter_names)
    created_files.append('test_video.md')
    created_files.append("testAssets/test_video.chapters")
    application.clean_up(created_files)
    # print(chapter_names)
