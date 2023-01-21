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


def download_video(url):
    try:
        print("URL: " + url)
        print("Downloading video... Please wait.")
        video = pytube.YouTube(url)
        stream = video.streams.get_by_itag(18)
        stream.download()
        return stream.default_filename
    except Exception as e:
        print("Error downloading video")
        print(e)
        return


def convert_video_to_mp3(filename):
    clip = VideoFileClip(filename)
    clip.audio.write_audiofile(filename[:-4] + ".mp3")
    clip.close()
    os.remove(filename)


def convert_wav_to_mp3(filename):
    subprocess.call(['ffmpeg', '-i', filename, filename[:-4] + ".mp3"])
    os.remove(filename)
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


def AudiotoText(filename):
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
        os.remove(filename[:-4] + ".mp3")
        print("Removed video and audio files")
        return result
    except Exception as e:
        print("Error transcribing audio to text")
        print(e)
        return


def convert(filename):
    print('''
    This tool will convert Youtube videos to mp3 files and then transcribe them to text using Whisper.
    ''')
    # FFMPEG installed on first use.
    print("Initializing FFMPEG...")
    static_ffmpeg.add_paths()

    try:
        convert_video_to_mp3(filename)
        print("Converted video to mp3")
    except:
        print("Error converting video to mp3")
        return
    return filename


def write_to_file(result, url, title, date, tags, category, speakers, video_title):
    transcribed_text = result
    if title:
        file_title = title
    else:
        file_title = video_title[:-4]
    if tags is None:
        tags = ""
    if speakers is None:
        speakers = ""
    if category is None:
        category = ""
    tags = tags.strip()
    tags = tags.split(",")
    for i in range(len(tags)):
        tags[i] = tags[i].strip()
    speakers = speakers.strip()
    speakers = speakers.split(",")
    for i in range(len(speakers)):
        speakers[i] = speakers[i].strip()
    category = category.strip()
    category = category.split(",")
    for i in range(len(category)):
        category[i] = category[i].strip()
    file_name = video_title.replace(' ', '-')
    file_name_with_ext = file_name + '.md'
    meta_data = '---\n' \
                f'title: {file_title}\n' \
                f'transcript_by: youtube_to_bitcoin_transcript_v_{__version__}\n' \
                f'tags: {tags}\n' \
                f'categories: {category}\n' \
                f'speakers: {speakers}\n' \
                f'media: {url}\n'
    if date:
        meta_data = meta_data + f'date: {date}\n'

    meta_data = meta_data + '---\n'

    with open(file_name_with_ext, 'a') as opf:
        opf.write(meta_data + '\n')
        opf.write(transcribed_text + '\n')
    return file_name_with_ext


def create_pr(result, video, title, event_date, tags, category, speakers, loc, username, curr_time, video_title):
    file_name_with_ext = write_to_file(result, video, title, event_date, tags, category, speakers, video_title)

    absolute_path = os.path.abspath(file_name_with_ext)
    branch_name = loc.replace("/", "-")
    subprocess.call(['bash', 'initializeRepo.sh', absolute_path, loc, branch_name, username, curr_time])
