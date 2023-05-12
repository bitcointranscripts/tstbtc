"""This module provides the transcript cli."""
import json
import shutil
import subprocess
from clint.textui import progress
import pytube
from moviepy.editor import VideoFileClip
import whisper
import os
import static_ffmpeg
from app import __version__
import requests
import re
from urllib.parse import urlparse, parse_qs
import time
from dotenv import dotenv_values
import yt_dlp
from deepgram import Deepgram
import mimetypes


def download_video(url):
    try:
        print("URL: " + url)
        print("Downloading video... Please wait.")

        ydl_opts = {
            'format': '18',
            'outtmpl': 'tmp/videoFile.%(ext)s',
            'nopart': True,
            'writeinfojson': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ytdl:
            ytdl.download([url])

        with open('tmp/videoFile.info.json') as file:
            info = ytdl.sanitize_info(json.load(file))
            name = info['title'].replace('/', '-')
            file.close()

        os.rename("tmp/videoFile.mp4", "tmp/" + name + '.mp4')

        return os.path.abspath("tmp/" + name + '.mp4')
    except Exception as e:
        print("Error downloading video")
        shutil.rmtree('tmp')
        return


def read_description(prefix):
    try:
        list_of_chapters = []
        with open(prefix + 'videoFile.info.json', 'r') as f:
            info = json.load(f)
        if 'chapters' not in info:
            print("No chapters found in description")
            return list_of_chapters
        for index, x in enumerate(info['chapters']):
            name = x['title']
            start = x['start_time']
            list_of_chapters.append((str(index), start, str(name)))

        return list_of_chapters
    except Exception as e:
        print("Error reading description")
        return []


def write_chapters_file(chapter_file: str, chapter_list: list) -> None:
    # Write out the chapter file based on simple MP4 format (OGM)
    try:
        with open(chapter_file, 'w') as fo:
            for current_chapter in chapter_list:
                fo.write(f'CHAPTER{current_chapter[0]}='
                         f'{current_chapter[1]}\n'
                         f'CHAPTER{current_chapter[0]}NAME='
                         f'{current_chapter[2]}\n')
            fo.close()
    except Exception as e:
        print("Error writing chapter file")
        print(e)


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
        playlists = list(pytube.Playlist(media).video_urls)
        if type(playlists) is not list:
            return False
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


def get_audio_file(url, title):
    print("URL: " + url)
    print("downloading audio file")
    try:
        audio = requests.get(url, stream=True)
        with open("tmp/" + title + ".mp3", "wb") as f:
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
    print("Transcribing audio to text using whisper ...")
    try:
        my_model = whisper.load_model(model)
        result = my_model.transcribe(filename)
        data = []
        for x in result["segments"]:
            data.append(tuple((x["start"], x["end"], x["text"])))
        print("Removed video and audio files")
        return data
    except Exception as e:
        print("Error transcribing audio to text")
        print(e)
        return


def decimal_to_sexagesimal(dec):
    sec = int(dec % 60)
    minu = int((dec // 60) % 60)
    hrs = int((dec // 60) // 60)

    return f'{hrs:02d}:{minu:02d}:{sec:02d}'


def get_deepgram_transcript(deepgram_data, diarize):
    if diarize:
        para = ""
        string = ""
        curr_speaker = None
        for word in deepgram_data["results"]["channels"][0]["alternatives"][0]["words"]:
            if word["speaker"] != curr_speaker:
                if para != "":
                    para = para.strip(" ")
                    string = string + para + "\n\n"
                para = ""
                string = string + f'Speaker {word["speaker"]}: {decimal_to_sexagesimal(word["start"])}'
                curr_speaker = word["speaker"]
                string = string + '\n\n'

            para = para + " " + word["punctuated_word"]
        para = para.strip(" ")
        string = string + para
        return string
    else:
        return deepgram_data["results"]["channels"][0]["alternatives"][0]["transcript"]


def get_deepgram_summary(deepgram_data):
    try:
        summaries = deepgram_data["results"]["channels"][0]["alternatives"][0]["summaries"]
        summary = ""
        for x in summaries:
            summary = summary + " " + x["summary"]
        return summary.strip(" ")
    except Exception as e:
        print("Error getting summary")
        print(e)


def process_mp3_deepgram(filename, summarize, diarize):
    print("Transcribing audio to text using deepgram...")
    try:
        config = dotenv_values(".env")
        dg_client = Deepgram(config["DEEPGRAM_API_KEY"])

        with open(filename, "rb") as audio:
            mimeType = mimetypes.MimeTypes().guess_type(filename)[0]
            source = {'buffer': audio, 'mimetype': mimeType}
            response = dg_client.transcription.sync_prerecorded(source, {'punctuate': True, 'speaker_labels': True,
                                                                         'diarize': diarize, 'smart_formatting': True,
                                                                         'summarize': summarize})
            audio.close()
        return response
    except Exception as e:
        print("Error transcribing audio to text")
        print(e)
        return


def create_transcript(data):
    result = ""
    for x in data:
        result = result + x[2] + " "

    return result


def initialize():
    try:
        print('''
        This tool will convert Youtube videos to mp3 files and then transcribe them to text using Whisper.
        ''')
        # FFMPEG installed on first use.
        print("Initializing FFMPEG...")
        static_ffmpeg.add_paths()
        print("Initialized FFMPEG")
    except Exception as e:
        print("Error initializing")
        print(e)


def write_to_file(result, loc, url, title, date, tags, category, speakers, video_title, username, local, test, pr,
                  summary):
    try:
        transcribed_text = result
        if title:
            file_title = title
        else:
            file_title = video_title
        meta_data = '---\n' \
                    f'title: {file_title}\n' \
                    f'transcript_by: {username} via TBTBTC v{__version__}\n'
        if not local:
            meta_data += f'media: {url}\n'
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
        if summary:
            meta_data += f'summary: {summary}\n'

        file_name = video_title.replace(' ', '-')
        file_name_with_ext = "tmp/" + file_name + '.md'

        if date:
            meta_data += f'date: {date}\n'

        meta_data += '---\n'
        if test is not None or pr:
            with open(file_name_with_ext, 'a') as opf:
                opf.write(meta_data + '\n')
                opf.write(transcribed_text + '\n')
                opf.close()
        if local:
            url = None
        if not pr:
            generate_payload(loc=loc, title=file_title, transcript=transcribed_text, media=url, tags=tags,
                             category=category, speakers=speakers, username=username, event_date=date, test=test)
        return file_name_with_ext
    except Exception as e:
        print("Error writing to file")
        print(e)


def get_md_file_path(result, loc, video, title, event_date, tags, category, speakers, username, local, video_title,
                     test, pr, summary=""):
    try:
        print("writing .md file")
        file_name_with_ext = write_to_file(result, loc, video, title, event_date, tags, category, speakers, video_title,
                                           username, local, test, pr, summary)
        print("wrote .md file")

        absolute_path = os.path.abspath(file_name_with_ext)
        return absolute_path
    except Exception as e:
        print("Error getting markdown file path")
        print(e)


def create_pr(absolute_path, loc, username, curr_time, title):
    branch_name = loc.replace("/", "-")
    subprocess.call(['bash', 'initializeRepo.sh', absolute_path, loc, branch_name, username, curr_time])
    subprocess.call(['bash', 'github.sh', branch_name, username, curr_time, title])
    print("Please check the PR for the transcription.")


def get_username():
    try:
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
    except Exception as e:
        print("Error getting username")
        print(e)


def check_source_type(source):
    if source.endswith(".mp3") or source.endswith(".wav"):
        if os.path.isfile(source):
            return "audio-local"
        else:
            return "audio"
    elif check_if_playlist(source):
        return "playlist"
    elif os.path.isfile(source):
        return "video-local"
    elif check_if_video(source):
        return "video"
    else:
        return None


def process_audio(source, title, event_date, tags, category, speakers, loc, model, username, local,
                  created_files, test, pr, deepgram, summarize, diarize):
    try:
        print("audio file detected")
        curr_time = str(round(time.time() * 1000))

        # check if title is supplied if not, return None
        if title is None:
            print("Error: Please supply a title for the audio file")
            return None
        # process audio file
        summary = None
        result = None
        if not local:
            filename = get_audio_file(url=source, title=title)
            abs_path = os.path.abspath(path="tmp/" + filename)
            print("filename", filename)
            print("abs_path", abs_path)
            created_files.append(abs_path)
        else:
            filename = source.split("/")[-1]
            abs_path = source
        print("processing audio file", abs_path)
        if filename is None:
            print("File not found")
            return
        if filename.endswith('wav'):
            initialize()
            abs_path = convert_wav_to_mp3(abs_path=abs_path, filename=filename)
            created_files.append(abs_path)
        if test:
            result = test
        else:
            if deepgram or summarize:
                deepgram_resp = process_mp3_deepgram(filename=abs_path, summarize=summarize, diarize=diarize)
                result = get_deepgram_transcript(deepgram_data=deepgram_resp, diarize=diarize)
                if summarize:
                    summary = get_deepgram_summary(deepgram_data=deepgram_resp)
            if not deepgram:
                result = process_mp3(abs_path, model)
                result = create_transcript(result)
        absolute_path = get_md_file_path(result=result, loc=loc, video=source, title=title, event_date=event_date,
                                         tags=tags, category=category, speakers=speakers, username=username,
                                         local=local, video_title=filename[:-4], test=test, pr=pr, summary=summary)

        created_files.append(absolute_path)
        if pr:
            create_pr(absolute_path=absolute_path, loc=loc, username=username, curr_time=curr_time, title=title)
        else:
            created_files.append(absolute_path)
        return absolute_path
    except Exception as e:
        print("Error processing audio file")
        print(e)


def process_videos(source, title, event_date, tags, category, speakers, loc, model, username, created_files,
                   chapters, pr, deepgram, summarize, diarize):
    try:
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
                                     pr=pr, created_files=created_files, chapters=chapters, test=False, diarize=diarize,
                                     deepgram=deepgram, summarize=summarize)
            if filename is None:
                return None
        return filename
    except Exception as e:
        print("Error processing playlist")
        print(e)


def combine_deepgram_with_chapters(deepgram_data, chapters):
    try:
        chapters_pointer = 0
        words_pointer = 0
        result = ""
        words = deepgram_data["results"]["channels"][0]["alternatives"][0]["words"]
        # chapters index, start time, name
        # transcript start time, end time, text
        while chapters_pointer < len(chapters) and words_pointer < len(words):
            if chapters[chapters_pointer][1] <= words[words_pointer]["end"]:
                result = result + "\n\n## " + chapters[chapters_pointer][2] + "\n\n"
                chapters_pointer += 1
            else:
                result = result + words[words_pointer]["punctuated_word"] + " "
                words_pointer += 1
        return result
    except Exception as e:
        print("Error combining deepgram with chapters")
        print(e)


def combine_chapter(chapters, transcript):
    try:
        chapters_pointer = 0
        transcript_pointer = 0
        result = ""
        # chapters index, start time, name
        # transcript start time, end time, text

        while chapters_pointer < len(chapters) and transcript_pointer < len(transcript):
            if chapters[chapters_pointer][1] <= transcript[transcript_pointer][0]:
                result = result + "\n\n## " + chapters[chapters_pointer][2] + "\n\n"
                chapters_pointer += 1
            else:
                result = result + transcript[transcript_pointer][2]
                transcript_pointer += 1

        while transcript_pointer < len(transcript):
            result = result + transcript[transcript_pointer][2]
            transcript_pointer += 1

        with open("result.md", "w") as file:
            file.write(result)

        return result
    except Exception as e:
        print("Error combining chapters")
        print(e)


def process_video(video, title, event_date, tags, category, speakers, loc, model, username, created_files,
                  chapters, test, pr, local=False, deepgram=False, summarize=False, diarize=False):
    try:
        curr_time = str(round(time.time() * 1000))
        if not local:
            if "watch?v=" in video:
                parsed_url = urlparse(video)
                video = parse_qs(parsed_url.query)["v"][0]
            elif "youtu.be" in video or "embed" in video:
                video = video.split("/")[-1]
            video = "https://www.youtube.com/watch?v=" + video
            print("Transcribing video: " + video)
            if event_date is None:
                event_date = get_date(video)
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

        initialize()
        summary = None
        result = ""
        deepgram_data = None
        if chapters and not test:
            chapters = read_description("tmp/")
        elif test:
            chapters = read_description("test/testAssets/")
        convert_video_to_mp3(abs_path[:-4] + '.mp4')
        if deepgram or summarize:
            deepgram_data = process_mp3_deepgram(abs_path[:-4] + ".mp3", summarize=summarize, diarize=diarize)
            result = get_deepgram_transcript(deepgram_data=deepgram_data, diarize=diarize)
            if summarize:
                print("Summarizing")
                summary = get_deepgram_summary(deepgram_data=deepgram_data)
        if not deepgram:
            result = process_mp3(abs_path[:-4] + ".mp3", model)
        created_files.append(abs_path[:-4] + ".mp3")
        if chapters and len(chapters) > 0:
            print("Chapters detected")
            write_chapters_file(abs_path[:-4] + '.chapters', chapters)
            created_files.append(abs_path[:-4] + '.chapters')
            if deepgram:
                result = combine_deepgram_with_chapters(deepgram_data=deepgram_data, chapters=chapters)
            else:
                result = combine_chapter(chapters=chapters, transcript=result)
            if not local:
                created_files.append(abs_path)
            created_files.append("tmp/" + filename[:-4] + '.chapters')
        else:
            if not test and not deepgram:
                result = create_transcript(result)
            elif not deepgram:
                result = ""
        if not title:
            title = filename[:-4]
        print("Creating markdown file")
        absolute_path = get_md_file_path(result=result, loc=loc, video=video, title=title, event_date=event_date,
                                         tags=tags, summary=summary, category=category, speakers=speakers,
                                         username=username, video_title=filename[:-4], local=local, pr=pr, test=test)
        created_files.append("tmp/" + filename[:-4] + '.description')
        if not test:
            if pr:
                create_pr(absolute_path=absolute_path, loc=loc, username=username, curr_time=curr_time, title=title)
            else:
                created_files.append(absolute_path)
        return absolute_path
    except Exception as e:
        print("Error processing video")
        print(e)


def process_source(source, title, event_date, tags, category, speakers, loc, model, username, source_type,
                   created_files, chapters, local=False, test=None, pr=False, deepgram=False, summarize=False,
                   diarize=False):
    try:
        if not os.path.isdir("tmp"):
            os.mkdir("tmp")
        else:
            shutil.rmtree("tmp")
            os.mkdir("tmp")

        if source_type == 'audio':
            filename = process_audio(source=source, title=title, event_date=event_date, tags=tags, category=category,
                                     speakers=speakers, loc=loc, model=model, username=username, summarize=summarize,
                                     local=local, created_files=created_files, test=test, pr=pr, deepgram=deepgram,
                                     diarize=diarize)
        elif source_type == 'audio-local':
            filename = process_audio(source=source, title=title, event_date=event_date, tags=tags, category=category,
                                     speakers=speakers, loc=loc, model=model, username=username, summarize=summarize,
                                     local=True, created_files=created_files, test=test, pr=pr, deepgram=deepgram,
                                     diarize=diarize)
        elif source_type == 'playlist':
            filename = process_videos(source=source, title=title, event_date=event_date, tags=tags, category=category,
                                      speakers=speakers, loc=loc, model=model, username=username, summarize=summarize,
                                      created_files=created_files, chapters=chapters, pr=pr, deepgram=deepgram,
                                      diarize=diarize)
        elif source_type == 'video-local':
            filename = process_video(video=source, title=title, event_date=event_date, summarize=summarize,
                                     tags=tags, category=category, speakers=speakers, loc=loc, model=model,
                                     username=username, created_files=created_files, local=True, diarize=diarize,
                                     chapters=chapters, test=test, pr=pr, deepgram=deepgram)
        else:
            filename = process_video(video=source, title=title, event_date=event_date, summarize=summarize,
                                     tags=tags, category=category, speakers=speakers, loc=loc, model=model,
                                     username=username, created_files=created_files, local=local, diarize=diarize,
                                     chapters=chapters, test=test, pr=pr, deepgram=deepgram)
        return filename
    except Exception as e:
        print("Error processing source")
        print(e)


def get_date(url):
    video = pytube.YouTube(url)
    return str(video.publish_date).split(" ")[0]


def clean_up(created_files):
    for file in created_files:
        if os.path.isfile(file):
            os.remove(file)
    shutil.rmtree("tmp")


def generate_payload(loc, title, event_date, tags, category, speakers, username, media, transcript, test):
    try:
        event_date = event_date if event_date is None else event_date if type(
            event_date) is str else event_date.strftime('%Y-%m-%d')
        data = {
            "title": title,
            "transcript_by": f'{username} via TBTBTC v{__version__}\n',
            "categories": str(category),
            "tags": str(tags),
            "speakers": str(speakers),
            "date": event_date,
            "media": media,
            "loc": loc,
            "body": transcript
        }
        content = {'content': data}
        if test:
            return content
        else:
            config = dotenv_values(".env")
            url = config['QUEUE_ENDPOINT'] + "/api/transcripts"
            resp = requests.post(url, json=content)
            if resp.status_code == 200:
                print("Transcript added to queue")
            return resp
    except Exception as e:
        print(e)
