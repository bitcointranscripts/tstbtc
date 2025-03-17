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
      - Save as JSON: Preserves the output of the transcription service for future use.
      - Save as SRT: Generates SRT file [whisper only]
   2. Summarize: Generates a summary of the transcript. [deepgram only]
   3. Upload: Saves transcription service output in an AWS S3 Bucket [optional]
   4. Finalizes the resulting transcript.
      - Process diarization. [deepgram only]
      - Process chapters.
4. Postprocess: Offers multiple options for further actions:
   - **Push to GitHub**: Push transcripts to your fork of the [bitcointranscripts](https://github.com/bitcointranscripts/bitcointranscripts) repo.
   - **Markdown**: Saves transcripts in a markdown format supported by bitcointranscripts.
   - **Upload**: Saves transcripts in an AWS S3 Bucket.
   - **Save as JSON**: Preserves transcripts for future use.

## Prerequisites

- This tool requires a running server component. Make sure you have the server running before using the CLI commands. You need to set the `TRANSCRIPTION_SERVER_URL` in your `.env` file. This should point to the URL where your transcription server is running (e.g., `http://localhost:8000`).

- To use [deepgram](https://deepgram.com/) as a transcription service,
  you must have a valid `DEEPGRAM_API_KEY` in the `.env` file.

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

- To use a specific [configuration profile](#configuration), set the `PROFILE` variable in your `.env` file.

## Configuration

This application supports configuration via a `config.ini` file.
This file allows you to set default values for various options and flags, reducing the need to specify them on the command line every time.
Additionally, the configuration file can include options not available through the command line, offering greater flexibility and control over the application's behavior.

### Creating a Configuration File

An example configuration file named `config.ini.example` is included in the repository.
To use it, copy it to `config.ini` and modify it according to your needs:

```sh
cp config.ini.example config.ini
```

## Installation and Setup

```sh
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install the application
pip3 install .
# With Whisper support
pip3 install .[whisper]
# In edit/dev mode
pip3 install -e .

# Create .env file with required variables
# See Prerequisites section

# Verify installation
tstbtc --version
tstbtc --help
```

To uninstall: `pip3 uninstall tstbtc`

## Usage

The application has a server component that handles the transcription processing. This allows the heavy lifting of transcription to be done on a separate machine if desired. The CLI can automatically start this server locally when needed, or you can manage it manually.

### Server Management

**Automatic Mode** (default):
- CLI starts server automatically when needed
- Control with `--auto-server`, `--server-mode`, `--server-verbose` flags
  ```

**Manual Mode**:
```sh
# Start server
tstbtc server start

# Check status
tstbtc server status

# Stop server
tstbtc server stop

# View logs
tstbtc server logs [--follow] [--lines 100]
```

### Using the CLI

```sh
# Basic usage
tstbtc transcribe <source_file/url>
```

**Supported Sources**:
- YouTube videos and playlists
- Local and remote audio files
- JSON files containing individual sources

**Metadata Parameters**:
- `--loc`: Location in bitcointranscripts hierarchy [default: "misc"]
- `--title`: Title for transcript (required for audio files)
- `--date`: Event date (yyyy-mm-dd)
- `--tags`: Add tags (can use multiple times)
- `--speakers`: Add speakers (can use multiple times)
- `--category`: Add categories (can use multiple times)

**Transcription Options**:
- `--model`: Select whisper model [default: tiny.en]
- `--deepgram`: Use Deepgram instead of Whisper
- `--diarize`: Enable speaker diarization (Deepgram only)
- `--summarize`: Generate summary (Deepgram only)
- `--github`: Push to GitHub
- `--upload`: Upload to AWS S3
- `--markdown`: Save as markdown
- `--text`: Save as txt
- `--json`: Save as JSON
- `--nocleanup`: Keep temporary files

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

## GitHub Integration

To push the resulting transcript(s) to GitHub:

1. Ensure a GitHub App is created and installed on both the main repository and the metadata repository you want to push data to. The app should have the necessary permissions for content manipulation and pull request creation.
2. Add these to your `.env` file:
   ```
   GITHUB_APP_ID=your_app_id
   GITHUB_PRIVATE_KEY_BASE64=your_base64_encoded_private_key
   GITHUB_INSTALLATION_ID=your_installation_id
   GITHUB_REPO_OWNER=target_repo_owner
   GITHUB_REPO_NAME=target_repo_name
   GITHUB_METADATA_REPO_NAME=target_metadata_repo_name
   ```
   Replace the placeholders with your actual GitHub App details and target repository information.
3. Use the `--github` flag when running the script to automatically create a branch in the target repositories and submit pull requests with the new transcripts and associated metadata.

To convert your GitHub App private key file to base64, use the following command:

```
base64 -w 0 path/to/your/private-key.pem
```

## Docker Support

This application can be run using Docker Compose, which simplifies the process of running both the server and CLI components.

Quick start:

1. Start the server:

   ```sh
   docker-compose up server
   ```

2. Use the CLI:
   ```sh
   docker-compose run --rm cli [command] [arguments]
   ```

For detailed instructions on using Docker with this project, including how to work with local files, environment variables, and custom builds, please refer to our [Docker Guide](docs/docker-guide.md).

## Testing

The transcription tool includes a comprehensive test suite built using pytest.

```sh
# Run all tests
pytest

# Run specific test categories
pytest -m unit       # Run only unit tests
pytest -m exporters  # Run only exporter-related tests

# Run with coverage report
pytest --cov=app
```

For detailed documentation on the testing infrastructure, test organization, and how to add new tests, please see the [tests directory README](tests/README.md).

## License

Transcriber to Bitcoin Transcript is released under the terms of the MIT
license. See [LICENSE](LICENSE) for more information or
see https://opensource.org/licenses/MIT.
