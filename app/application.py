"""This module provides the transcript cli."""
# app/application.py

import pytube
from moviepy.editor import VideoFileClip
import pywhisper
import os
import static_ffmpeg
from app import __version__


def download_video(url):
    video = pytube.YouTube(url)
    stream = video.streams.get_by_itag(18)
    stream.download()
    return stream.default_filename


def convert_to_mp3(filename):
    clip = VideoFileClip(filename)
    clip.audio.write_audiofile(filename[:-4] + ".mp3")
    clip.close()


def AudiotoText(filename):
    model = pywhisper.load_model("base")
    result = model.transcribe(filename)
    sonuc = result["text"]
    return sonuc


def convert(link, model):
    print('''
    This tool will convert Youtube videos to mp3 files and then transcribe them to text using Whisper.
    ''')
    print("URL: " + link)
    print("MODEL: " + model)
    # FFMPEG installed on first use.
    print("Initializing FFMPEG...")
    static_ffmpeg.add_paths()

    print("Downloading video... Please wait.")
    try:
        filename = download_video(link)
        print("Downloaded video as " + filename)
    except:
        print("Not a valid link..")
        return
    try:
        convert_to_mp3(filename)
        print("Converted video to mp3")
    except:
        print("Error converting video to mp3")
        return
    try:
        mymodel = pywhisper.load_model(model)
        result = mymodel.transcribe(filename[:-4] + ".mp3")
        result = result["text"]
        os.remove(filename)
        os.remove(filename[:-4] + ".mp3")
        print("Removed video and audio files")
        return result, filename
    except Exception as e:
        print("Error transcribing audio to text")
        print(e)
        return


def write_to_file(result, url, title, date):
    transcribed_text = result[0]
    video_title = result[1][:-4]
    if title:
        file_title = title
    else:
        file_title = video_title

    file_name = video_title.replace(' ', '-')
    file_name_with_ext = file_name + '.md'
    meta_data = '---\n' \
                f'title: {file_title} ' + '\n' \
                f'transcript_by: youtube_to_bitcoin_transcript_v_{__version__}\n' \
                f'media: {url}\n' 
    if date:
        meta_data = meta_data + f'date: {date}\n' 

    meta_data = meta_data + '---\n'
    
    with open(file_name_with_ext, 'a') as opf:
        opf.write(meta_data + '\n')
        opf.write(transcribed_text + '\n')
    return file_name_with_ext
