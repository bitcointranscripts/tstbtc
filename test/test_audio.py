import os.path
import pytest
from app import application
from datetime import datetime


def check_md_file(path, transcript_by, media, title=None, date=None, tags=None, category=None, speakers=None,
                  local=False):
    is_correct = True
    if not path:
        return False
    with open(path, 'r') as file:
        contents = file.read()
        file.close()

    data = contents.split('---\n')[1].strip().split('\n')

    fields = {}

    for x in data:
        key = x.split(": ")[0]
        value = x.split(": ")[1]
        fields[key] = value

    is_correct &= fields["transcript_by"] == f'{transcript_by} via TBTBTC v{application.__version__}'
    if not local:
        is_correct &= fields['media'] == media
    is_correct &= fields['title'] == title

    if date:
        is_correct &= fields["date"] == date
    if tags:
        is_correct &= fields['tags'] == str(tags)
    if speakers:
        is_correct &= fields['speakers'] == str(speakers)
    if category:
        is_correct &= fields['categories'] == str(category)

    return is_correct


@pytest.mark.feature
def test_audio_with_title():
    with open("test/testAssets/transcript.txt", "r") as file:
        result = file.read()
        file.close()
    source = 'test/testAssets/audio.mp3'
    title = "title"
    username = "username"
    created_files = []
    filename = application.process_source(source=source, title=title, event_date=None, tags=None, category=None,
                                          speakers=None, loc="yada/yada", model="tiny", username=username,
                                          source_type="audio", local=True, test=result, chapters=False, pr=False,
                                          created_files=created_files)
    assert os.path.isfile(filename)
    assert check_md_file(path=filename, transcript_by=username, media=source, title=title, local=True)
    application.clean_up(created_files)


@pytest.mark.feature
def test_audio_without_title():
    with open("test/testAssets/transcript.txt", "r") as file:
        result = file.read()
        file.close()

    source = 'test/testAssets/audio.mp3'
    username = "username"
    created_files = []
    title = None
    filename = application.process_source(source=source, title=title, event_date=None, tags=None, category=None,
                                          speakers=None, loc="yada/yada", model="tiny", username=username, pr=False,
                                          source_type="audio", local=True, created_files=created_files, test=result,
                                          chapters=False)
    assert filename is None
    assert not check_md_file(path=filename, transcript_by=username, media=source, title=title)
    application.clean_up(created_files)


@pytest.mark.feature
def test_audio_with_all_data():
    with open("test/testAssets/transcript.txt", "r") as file:
        result = file.read()
        file.close()
    source = 'test/testAssets/audio.mp3'
    username = "username"
    title = "title"
    speakers = "speaker1,speaker2"
    tags = "tag1, tag2"
    category = "category"
    date = "2020-01-31"
    date = datetime.strptime(date, '%Y-%m-%d').date()
    created_files = []
    filename = application.process_source(source=source, title=title, event_date=date, tags=tags, category=category,
                                          speakers=speakers, loc="yada/yada", model="tiny", username=username,
                                          source_type="audio", local=True, test=result, chapters=False,
                                          created_files=created_files, pr=False)
    category = [cat.strip() for cat in category.split(",")]
    tags = [tag.strip() for tag in tags.split(",")]
    speakers = [speaker.strip() for speaker in speakers.split(",")]
    date = date.strftime('%Y-%m-%d')
    assert os.path.isfile(filename)
    assert check_md_file(path=filename, transcript_by=username, media=source, title=title, date=date, tags=tags,
                         category=category, speakers=speakers, local=True)
    application.clean_up(created_files)
