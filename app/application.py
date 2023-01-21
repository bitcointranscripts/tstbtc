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
        return name + ".mp4"
    except Exception as e:
        print("Error downloading video")
        if name and os.path.exists(name + '.description'):
            os.remove(name + '.description')
        print(e)
        return


def read_description(description_file):
    list_of_chapters = []
    print("Reading description file: " + description_file)
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
    clip = VideoFileClip(filename)
    print("Converting video to mp3... Please wait.")
    print(filename[:-4] + ".mp3")
    clip.audio.write_audiofile(filename[:-4] + ".mp3")
    clip.close()


def convert_wav_to_mp3(filename):
    subprocess.call(['ffmpeg', '-i', filename, filename[:-4] + ".mp3"])
    return filename[:-4] + ".mp3"


def check_if_playlist(media):
    return media.startswith("PL") \
        or media.startswith("UU") \
        or media.startswith("FL") \
        or media.startswith("RD")


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


def convert(filename):
    try:
        convert_video_to_mp3(filename)
        print("Converted video to mp3")
    except:
        print("Error converting video to mp3")
        return
    return filename


def write_to_file(result, url, title, date, tags, category, speakers, video_title, username):
    transcribed_text = result
    if title:
        file_title = title
    else:
        file_title = video_title
    meta_data = '---\n' \
                f'title: {file_title}\n' \
                f'transcript_by: {username} via TBTBTC v{__version__}\n' \
                f'media: {url}\n'
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


def get_md_file_path(result, video, title, event_date, tags, category, speakers, loc, username, curr_time,
                     video_title):  # todo rename function
    file_name_with_ext = write_to_file(result, video, title, event_date, tags, category, speakers, video_title,
                                       username)

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
    if source.startswith("https://www.youtube.com"):
        if source.find("list=") != -1:
            return "playlist"
        else:
            return "video"
    elif source.endswith(".mp3") or source.endswith(".wav"):
        return "audio"
    elif check_if_playlist(source):
        return "playlist"
    else:
        return "video"


def process_audio(source, title, event_date, tags, category, speakers, loc, model, username, curr_time):
    print("audio file detected")
    if title is None:
        print("Error: Please supply a title for the audio file")
        return None
    # process audio file
    filename = get_audio_file(source, title)
    print("processing audio file", filename)
    if filename is None:
        print("File not found")
        return
    if filename.endswith('wav'):
        filename = convert_wav_to_mp3(filename)
        os.remove(filename[:-4] + '.wav')
    result = process_mp3(filename, model)
    os.remove(filename[:-4] + ".mp3")
    absolute_path = get_md_file_path(result, source, title, event_date, tags, category, speakers, loc, username,
                                     curr_time,
                                     filename[:-4])
    initialize_repo(absolute_path, loc, username, curr_time)
    return filename


def process_videos(source, title, event_date, tags, category, speakers, loc, model, username, curr_time):
    print("Playlist detected")
    url = "https://www.youtube.com/playlist?list=" + source
    videos = get_playlist_videos(url)
    if videos is None:
        print("Playlist is empty")
        return

    selected_model = model + '.en'
    filename = ""

    for video in videos:
        filename = process_video(video, title, event_date, tags, category, speakers, loc, selected_model, username,
                                 curr_time)
    return filename


def process_video(video, title, event_date, tags, category, speakers, loc, model, username, curr_time):
    result = ""
    print("Transcribing video: " + video)
    filename = download_video(video)
    print()
    print()
    if filename is None:  # todo add creation check
        print("File not found")
        return None
    chapters = read_description(filename[:-4] + '.description')
    if len(chapters) > 0:
        print("Chapters detected")
        write_chapters_file(filename[:-4] + '.chapters', chapters)
        split_mp4(chapters, filename, filename[:-4])
        initialize()
        for current_index, chapter in enumerate(chapters):
            print(f"Processing chapter {chapter[2]} {current_index + 1} of {len(chapters)}")
            convert(f'{filename[:-4]} - ({current_index}).mp4')
            os.remove(f'{filename[:-4]} - ({current_index}).mp4')
            temp_filename = f'{filename[:-4]} - ({current_index}).mp4'
            temp_res = process_mp3(temp_filename, model)
            os.remove(temp_filename[:-4] + ".mp3")
            result = result + "## " + chapter[2] + "\n\n" + temp_res + "\n\n"
            print()
        os.remove(filename)
        os.remove(filename[:-4] + '.chapters')
    else:
        convert(filename)
        os.remove(filename)
        result = process_mp3(filename, model)
        os.remove(filename[:-4] + ".mp3")
    absolute_path = get_md_file_path(result, video, title, event_date, tags, category, speakers, loc, username,
                                     curr_time,
                                     filename[:-4])
    initialize_repo(absolute_path, loc, username, curr_time)
    os.remove(filename[:-4] + '.description')
    return filename


def process_source(source, title, event_date, tags, category, speakers, loc, model, username, curr_time, source_type):
    if source_type == 'audio':
        filename = process_audio(source, title, event_date, tags, category, speakers, loc, model, username,
                                 curr_time)
    elif source_type == 'playlist':
        filename = process_videos(source, title, event_date, tags, category, speakers, loc, model, username,
                                  curr_time)
    else:
        filename = process_video(source, title, event_date, tags, category, speakers, loc, model, username,
                                 curr_time)
    return filename
