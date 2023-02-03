"""This module provides the transcript cli."""
import subprocess
from clint.textui import progress
import pytube
from moviepy.editor import VideoFileClip
import pywhisper
import os
import static_ffmpeg
from app import __version__
import requests
import re
import datetime
from pytube.cli import on_progress
from urllib.parse import urlparse, parse_qs


def download_video(url):
    name = None
    try:
        print("URL: " + url)
        print("Downloading video... Please wait.")
        video = pytube.YouTube(url, on_progress_callback=on_progress)
        name = video.title.replace("/", "-")
        print("Video title: " + name)

        with open(name + '.description', 'w') as f:
            f.write(video.description)
        stream = video.streams.get_by_itag(18)
        stream.download()
        os.rename(stream.default_filename, name + '.mp4')
        return os.path.abspath(name + '.mp4')
    except Exception as e:
        print("Error downloading video")
        if name and os.path.exists(name + '.description'):
            os.remove(name + '.description')
        print(e)
        return


def read_description(description_file):
    list_of_chapters = []
    print("Reading description file: " + description_file)
    if not os.path.exists(description_file):
        print("Description file not found")
        return list_of_chapters
    with open(description_file, 'r') as f:
        # only increment chapter number on a chapter line
        # chapter lines start with timecode
        line_counter = 1
        for line in f:
            result = re.search(r"\(?(\d?:?\d+:\d+)\)?", line)
            try:
                time_count = datetime.datetime.strptime(result.group(1), '%H:%M:%S')
            except:
                try:
                    time_count = datetime.datetime.strptime(result.group(1), '%M:%S')
                except:
                    continue
            chap_name = line.replace(result.group(0), "").rstrip(' :\n').strip("-")
            chap_pos = datetime.datetime.strftime(time_count, '%H:%M:%S')
            list_of_chapters.append((str(line_counter).zfill(2), chap_pos, chap_name))
            line_counter += 1
    return list_of_chapters


def write_chapters_file(chapter_file: str, chapter_list: list) -> None:
    # Write out the chapter file based on simple MP4 format (OGM)
    with open(chapter_file, 'w') as fo:
        for current_chapter in chapter_list:
            fo.write(f'CHAPTER{current_chapter[0]}='
                     f'{current_chapter[1]}\n'
                     f'CHAPTER{current_chapter[0]}NAME='
                     f'{current_chapter[2]}\n')


def split_mp4(chapters: list, download_filename: str, download_name: str) -> None:
    current_duration_pretext = subprocess.run(['ffprobe', '-i', download_filename,
                                               '-show_entries', 'format=duration',
                                               '-v', 'quiet'],
                                              capture_output=True, encoding='UTF8')
    current_duration = float(current_duration_pretext.stdout[18:-13])
    m, s = divmod(current_duration, 60)
    h, m = divmod(m, 60)
    current_dur = ':'.join([str(int(h)), str(int(m)), str(s)])
    for current_index, current_chapter in enumerate(chapters):
        # current_chapter will be a tuple: position, timecode, name
        next_index = current_index + 1
        start_time = current_chapter[1]
        try:
            end_time = chapters[next_index][1]
        except:
            end_time = current_dur
        output_name = f'{download_name} - ({current_index}).mp4'
        subprocess.run(["ffmpeg", "-ss", start_time, "-to", end_time,
                        "-i", download_filename, "-acodec", "copy",
                        "-vcodec", "copy", output_name, "-loglevel", "quiet"])


def convert_video_to_mp3(filename):
    try:
        clip = VideoFileClip(filename)
        print("Converting video to mp3... Please wait.")
        print(filename[:-4] + ".mp3")
        clip.audio.write_audiofile(filename[:-4] + ".mp3")
        clip.close()
        print("Converted video to mp3")
    except:
        print("Error converting video to mp3")
        return None
    return filename


def convert_wav_to_mp3(abs_path, filename):
    subprocess.call(['ffmpeg', '-i', abs_path, abs_path[:-4] + ".mp3"])
    return filename[:-4] + ".mp3"


def check_if_playlist(media):
    try:
        if media.startswith("PL") \
                or media.startswith("UU") \
                or media.startswith("FL") \
                or media.startswith("RD"):
            return True
        pytube.Playlist(media)
        return True
    except:
        return False


def check_if_video(media):
    if re.search(r'^([\dA-Za-z_-]{11})$', media):
        return True
    try:
        pytube.YouTube(media)
        return True
    except:
        return False


def get_playlist_videos(url):
    try:
        videos = pytube.Playlist(url)
        return videos
    except Exception as e:
        print("Error getting playlist videos")
        print(e)
        return


def audio_to_text(filename):
    model = pywhisper.load_model("base")
    result = model.transcribe(filename)
    sonuc = result["text"]
    return sonuc


def get_audio_file(url, title):
    print("URL: " + url)
    print("downloading audio file")
    try:
        audio = requests.get(url, stream=True)
        with open(title + ".mp3", "wb") as f:
            total_length = int(audio.headers.get('content-length'))
            for chunk in progress.bar(audio.iter_content(chunk_size=1024), expected_size=(total_length / 1024) + 1):
                if chunk:
                    f.write(chunk)
                    f.flush()
        return title + ".mp3"
    except Exception as e:
        print("Error downloading audio file")
        print(e)
        return


def process_mp3(filename, model):
    print("Transcribing audio to text...")
    try:
        mymodel = pywhisper.load_model(model)
        result = mymodel.transcribe(filename[:-4] + ".mp3")
        result = result["text"]
        print("Removed video and audio files")
        return result
    except Exception as e:
        print("Error transcribing audio to text")
        print(e)
        return


def initialize():
    print('''
    This tool will convert Youtube videos to mp3 files and then transcribe them to text using Whisper.
    ''')
    # FFMPEG installed on first use.
    print("Initializing FFMPEG...")
    static_ffmpeg.add_paths()


def write_to_file(result, url, title, date, tags, category, speakers, video_title, username, local):
    transcribed_text = result
    if title:
        file_title = title
    else:
        file_title = video_title
    meta_data = '---\n' \
                f'title: {file_title}\n' \
                f'transcript_by: {username} via TBTBTC v{__version__}\n'
    if not local:
        meta_data += "f'media: {url}\n"
    if tags:
        tags = tags.strip()
        tags = tags.split(",")
        for i in range(len(tags)):
            tags[i] = tags[i].strip()
        meta_data += f'tags: {tags}\n'
    if speakers:
        speakers = speakers.strip()
        speakers = speakers.split(",")
        for i in range(len(speakers)):
            speakers[i] = speakers[i].strip()
        meta_data += f'speakers: {speakers}\n'
    if category:
        category = category.strip()
        category = category.split(",")
        for i in range(len(category)):
            category[i] = category[i].strip()
        meta_data += f'categories: {category}\n'

    print(video_title)
    file_name = video_title.replace(' ', '-')
    file_name_with_ext = file_name + '.md'

    if date:
        meta_data = meta_data + f'date: {date}\n\n'

    meta_data += '---\n'

    with open(file_name_with_ext, 'a') as opf:
        opf.write(meta_data + '\n')
        opf.write(transcribed_text + '\n')
        opf.close()
    return file_name_with_ext


def get_md_file_path(result, video, title, event_date, tags, category, speakers, username, local,
                     video_title):
    file_name_with_ext = write_to_file(result, video, title, event_date, tags, category, speakers, video_title,
                                       username, local)

    absolute_path = os.path.abspath(file_name_with_ext)
    return absolute_path


def initialize_repo(absolute_path, loc, username, curr_time):
    branch_name = loc.replace("/", "-")
    subprocess.call(['bash', 'initializeRepo.sh', absolute_path, loc, branch_name, username, curr_time])


def get_username():
    if os.path.isfile(".username"):
        with open(".username", "r") as f:
            username = f.read()
            f.close()
    else:
        print("What is your github username?")
        username = input()
        with open(".username", "w") as f:
            f.write(username)
            f.close()
    return username


def check_source_type(source):
    if source.endswith(".mp3") or source.endswith(".wav"):
        if os.path.isfile(source):
            return "audio-local"
        else:
            return "audio"
    elif os.path.isfile(source):
        return "video-local"
    elif check_if_video(source):
        return "video"
    elif check_if_playlist(source):
        return "playlist"
    else:
        return None


def process_audio(source, title, event_date, tags, category, speakers, loc, model, username, curr_time, local,
                  created_files, test):
    print("audio file detected")
    # check if title is supplied if not, return None
    if title is None:
        print("Error: Please supply a title for the audio file")
        return None
    # process audio file
    if not local:
        filename = get_audio_file(url=source, title=title)
        abs_path = os.path.abspath(path=filename)
        created_files.append(abs_path)
    else:
        filename = source.split("/")[-1]
        abs_path = source
    print("processing audio file", abs_path)
    if filename is None:
        print("File not found")
        return
    if filename.endswith('wav'):
        abs_path = convert_wav_to_mp3(abs_path=abs_path, filename=filename)
        created_files.append(abs_path)
    if test:
        result = test
    else:
        result = process_mp3(abs_path, model)
    absolute_path = get_md_file_path(result=result, video=source, title=title, event_date=event_date, tags=tags,
                                     category=category, speakers=speakers, username=username, local=local,
                                     video_title=filename[:-4])
    created_files.append(absolute_path)
    initialize_repo(absolute_path=absolute_path, loc=loc, username=username, curr_time=curr_time)
    return absolute_path


def process_videos(source, title, event_date, tags, category, speakers, loc, model, username, curr_time, created_files,
                   chapters):
    print("Playlist detected")
    if source.startswith("http") or source.startswith("www"):
        parsed_url = urlparse(source)
        source = parse_qs(parsed_url.query)["list"][0]
    url = "https://www.youtube.com/playlist?list=" + source
    print(url)
    videos = get_playlist_videos(url)
    if videos is None:
        print("Playlist is empty")
        return

    selected_model = model + '.en'
    filename = ""

    for video in videos:
        filename = process_video(video=video, title=title, event_date=event_date, tags=tags, category=category,
                                 speakers=speakers, loc=loc, model=selected_model, username=username,
                                 curr_time=curr_time, created_files=created_files, chapters=chapters, test=False)
        if filename is None:
            return None
    return filename


def process_video(video, title, event_date, tags, category, speakers, loc, model, username, curr_time, created_files,
                  chapters, test, local=False):
    result = ""
    if not local:
        if "watch?v=" in video:
            parsed_url = urlparse(video)
            video = parse_qs(parsed_url.query)["v"][0]
        elif "youtu.be" in video or "embed" in video:
            video = video.split("/")[-1]
        video = "https://www.youtube.com/watch?v=" + video
        print("Transcribing video: " + video)
        abs_path = download_video(url=video)
        if abs_path is None:
            print("File not found")
            return None
        created_files.append(abs_path)
        filename = abs_path.split("/")[-1]
    else:
        filename = video.split("/")[-1]
        print("Transcribing video: " + filename)
        abs_path = video
    print()
    print()

    if chapters:
        chapters = read_description(description_file=abs_path[:-4] + '.description')
    if chapters and len(chapters) > 0:
        print("Chapters detected")
        write_chapters_file(abs_path[:-4] + '.chapters', chapters)
        created_files.append(abs_path[:-4] + '.chapters')
        split_mp4(chapters=chapters, download_filename=abs_path, download_name=abs_path[:-4])
        initialize()
        for current_index, chapter in enumerate(chapters):
            print(f"Processing chapter {chapter[2]} {current_index + 1} of {len(chapters)}")
            temp_filename = f'{abs_path[:-4]} - ({current_index}).mp4'
            if not test:
                file = convert_video_to_mp3(filename=temp_filename)
                if file is None:
                    print("File not found")
                    return None
                temp_res = process_mp3(filename=temp_filename, model=model)
                created_files.append(temp_filename[:-4] + ".mp3")
            else:
                temp_res = ""
            created_files.append(temp_filename)
            result = result + "## " + chapter[2] + "\n\n" + temp_res + "\n\n"
            print()
        if not local:
            created_files.append(abs_path)
        created_files.append(filename[:-4] + '.chapters')
    else:
        if not test:
            convert_video_to_mp3(abs_path)
            created_files.append(abs_path[:-4] + '.mp3')
            result = process_mp3(abs_path[:-4] + '.mp3', model)
            created_files.append(abs_path[:-4] + ".mp3")
        else:
            result = ""
    absolute_path = get_md_file_path(result, video, title, event_date, tags, category, speakers, username, local,
                                     filename[:-4])
    initialize_repo(absolute_path, loc, username, curr_time)
    created_files.append(filename[:-4] + '.description')
    return absolute_path


def process_source(source, title, event_date, tags, category, speakers, loc, model, username, curr_time, source_type,
                   created_files, chapters, local=False, test=None):
    if source_type == 'audio':
        filename = process_audio(source=source, title=title, event_date=event_date, tags=tags, category=category,
                                 speakers=speakers, loc=loc, model=model, username=username,
                                 curr_time=curr_time, local=local, created_files=created_files, test=test)
    elif source_type == 'audio-local':
        filename = process_audio(source=source, title=title, event_date=event_date, tags=tags, category=category,
                                 speakers=speakers, loc=loc, model=model, username=username,
                                 curr_time=curr_time, local=True, created_files=created_files, test=test)
    elif source_type == 'playlist':
        filename = process_videos(source=source, title=title, event_date=event_date, tags=tags, category=category,
                                  speakers=speakers, loc=loc, model=model, username=username,
                                  curr_time=curr_time, created_files=created_files, chapters=chapters)
    elif source_type == 'video-local':
        filename = process_video(video=source, title=title, event_date=event_date,
                                 tags=tags, category=category, speakers=speakers, loc=loc, model=model,
                                 username=username, curr_time=curr_time, created_files=created_files, local=True,
                                 chapters=chapters, test=test)
    else:
        filename = process_video(video=source, title=title, event_date=event_date,
                                 tags=tags, category=category, speakers=speakers, loc=loc, model=model,
                                 username=username, curr_time=curr_time, created_files=created_files, local=local,
                                 chapters=chapters, test=test)
    return filename


def clean_up(created_files):
    for file in created_files:
        if os.path.isfile(file):
            os.remove(file)
