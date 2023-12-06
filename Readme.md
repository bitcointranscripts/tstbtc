# TRANSCRIBER TO BITCOIN TRANSCRIPT

This cli app transcribes audio and video for submission to the [bitcointranscripts](https://github.com/bitcointranscripts/bitcointranscripts) repo. 

**Available transcription models and services**

- (local) Whisper `--model xxx [default: tiny.en]`
- (remote) Deepgram (whisper-large) `--deepgram [default: False]`
  - summarization `--summarize`
  - diarization `--diarize`

**Transcription Workflow**

This transcription tool operates through a structured four-stage process:

1. Preprocess: Gathers all the available metadata for each source (supports YouTube videos&playlists, and RSS feeds)
2. Process: Downloads and converts sources for transcription preparation
3. Transcription: Utilizes [`openai-whisper`](https://github.com/openai/whisper) or [Deepgram](https://deepgram.com/) to generate transcripts.
    1. Converts audio to text.
        - Preserves raw wisper transcript in SRT
        - Preserves raw deepgram output in JSON
    2. Summarize: Generates a summary of the transcript. [only available with deepgram]
    3. Upload: Saves raw transcript files in an AWS S3 Bucket [optional]
    4. Constructs the resulting transcript.
        - Process diarization. [deepgram only]
        - Process chapters.
4. Postprocess: Offers multiple options for further actions:
    - **Pull Request**: Opens a PR on the [bitcointranscripts](https://github.com/bitcointranscripts/bitcointranscripts) repo for the resulting transcript.
    - **Markdown**: Saves transcripts in a markdown format supported by bitcointranscripts.
    - **Upload**: Saves transcripts in an AWS S3 Bucket.
    - **Push to Queuer backend**: Sends transcripts to [a Queuer backend](https://github.com/bitcointranscripts/transcription-review-backend).
    - **Save as JSON**: Preserves transcripts for future use.


## Prerequisites

- To use [deepgram](https://deepgram.com/) as a transcription service,
  you must have a valid `DEEPGRAM_API_KEY` in the `.env` file.

- To push the resulting transcript to a Queuer backend, you must have a 
  valid `QUEUE_ENDPOINT` in the `.env` file. If not, you can instead save
  the payload in a json file using the `--noqueue` flag.

- To enable us fork bitcointranscript repo and open a PR, we require you to
  login into your GitHub account. Kindly install `GITHUB CLI` using the
  instructions on their repo [here](https://github.com/cli/cli#installation).
  Following the prompt, please select the below options from the prompt to
  login:

    - what account do you want to log into? `Github.com`

    - what is your preferred protocol for Git operations? `SSH`

    - Upload your SSH public key to your GitHub account? `skip`

    - How would you like to authenticate GitHub CLI? `Login with a web browser`

    - copy the generated one-time pass-code and paste in the browser to
      authenticate if you have enabled 2FA

- To enable pushing the models to a S3 bucket,
    - [Install](https://aws.amazon.com/cli/) aws-cli to your system.
    - [Configure](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html)
      aws-cli by first generating IAM credentials (if not already present) and
      using `aws configure` to set them.
    - To verify proper configuration, run `aws s3 ls` to show the list of S3
      buckets. Don't forget to set a valid `S3_BUCKET` in the `.env` file.

- To be able to convert the intermediary media files to mp3, install `FFmpeg`

    - for Mac Os users, run `brew install ffmpeg`

    - for other users, follow the instruction on
      their [site](https://ffmpeg.org/) to install

## Install/Uninstall

Navigate to the application directory and run the below commands:

`python3 -m venv venv` creates a virtual environment

`source venv/bin/activate` activates the virtual environment

`pip3 install . --use-pep517` to install the application

To check the version:
`tstbtc --version` view the application version

`tstbtc --help` view the application help

`pip3 uninstall tstbtc` to uninstall the application

## Usage

`tstbtc transcribe {source_file/url}` transcribe the given source

Suported sources:
  - YouTube videos and playlists
  - Local and remote audio files
  - JSON files containing individual sources

Note:
- The https links need to be wrapped in quotes when running the command on zsh

To include optional metadata in your transcript, you can add the following
parameters:

- `--loc`: Add the location in the bitcointranscripts hierarchy that you want to associate the transcript [default: "misc"]
- `-t` or `--title`: Add the title for the resulting transcript (required for audio files)
- `-d` or `--date`: Add the event date to transcript's metadata in format 'yyyy-mm-dd'
- can be used multiple times:
  - `-T` or `--tags`: Add a tag to transcript's metadata
  - `-s` or `--speakers`: Add a speaker to the transcript's metadata
  - `-c` or `--category`: Add a category to the transcript's metadata

To configure the transcription process, you can use the following flags:

- `-m` or `--model`: Select which whisper model to use for the transcription [default: tiny.en]
- `-D` or `--deepgram`: Use deepgram for transcription, instead of using the whisper model [default: False]
- `-M` or `--diarize`: Supply this flag if you have multiple speakers AKA want to diarize the content [only available with deepgram]
- `-S` or `--summarize`: Summarize the transcript [only available with deepgram]
- `-C` or `--chapters`: For YouTube videos, include the YouTube chapters and timestamps in the resulting transcript.
- `-p` or `--pr`: Open a PR on the bitcointranscripts repo
- `-u` or `--upload`: Upload processed model files to AWS S3
- `--markdown`: Save the resulting transcript to a markdown format supported by bitcointranscripts
- `--noqueue`: Do not push the resulting transcript to the Queuer, instead store the payload in a json file
- `--nocleanup`: Do not remove temp files on exit

### Examples

To transcribe [this podcast episode](https://www.youtube.com/watch?v=Nq6WxJ0PgJ4) from YouTube
from Stephan Livera's podcast and add the associated metadata, we would run either
of the below commands. The first uses short argument tags, while the second uses
long argument tags. The result is the same.

- `tstbtc transcribe Nq6WxJ0PgJ4 --loc "stephan-livera-podcast" -t 'OP_Vault - A New Way to HODL?' -d '2023-01-30' -T 'script' -T 'op_vault' -s 'James O’Beirne' -s 'Stephan Livera' -c ‘podcast’`
- `tstbtc transcribe Nq6WxJ0PgJ4 --loc "stephan-livera-podcast" --title 'OP_Vault - A New Way to HODL?' --date '2023-01-30' --tags 'script' --tags 'op_vault' --speakers 'James O’Beirne' --speakers 'Stephan Livera' --category ‘podcast’`

You can also transcribe a remote audio/mp3 link, such as the following from Stephan Livera's podcast: 
```shell
mp3_link="https://anchor.fm/s/7d083a4/podcast/play/64348045/https%3A%2F%2Fd3ctxlq1ktw2nl.cloudfront.net%2Fstaging%2F2023-1-1%2Ff7fafb12-9441-7d85-d557-e9e5d18ab788.mp3"
tstbtc transcribe $mp3_link --loc "stephan-livera-podcast" --title 'SLP455 Anant Tapadia - Single Sig or Multi Sig?' --date '2023-02-01' --tags 'multisig' --speakers 'Anant Tapadia' --speakers 'Stephan Livera' --category 'podcast'
```

## Testing

To run the unit tests

`pytest -v -m main -s`

To run the feature tests

`pytest -v -m feature -s`

To run the full test suite

`pytest -v -s`


## License

Transcriber to Bitcoin Transcript is released under the terms of the MIT
license. See [LICENSE](LICENSE) for more information or
see https://opensource.org/licenses/MIT.
