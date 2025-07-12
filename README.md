# TRANSCRIBER TO BITCOIN TRANSCRIPT

This project provides a comprehensive toolkit for transcribing audio and video content, specifically designed for seamless submission to the [Bitcoin Transcripts](https://github.com/bitcointranscripts/bitcointranscripts) repository. It automates the entire transcription workflow, from fetching various source types and generating high-quality text, to formatting the final output according to the repository's specific Markdown standards.

## About the Project

This tool is designed to make it easy to contribute to Bitcoin Transcripts by automating many of the tedious steps involved in transcription.

- **🎙️ Multiple Transcription Engines**: Choose between local transcription with Whisper or cloud-based transcription with [Deepgram](#deepgram-integration).
- **🔊 Advanced Audio Features**: Get speaker diarization and AI-generated summaries.
- **🔗 Flexible Source Input**: Transcribe from YouTube videos & playlists, RSS feeds, and local or remote audio & video files.
- **⚙️ Four-Stage Workflow**: A structured process ensures quality:
  1.  **Preprocess**: Gathers metadata for each source.
  2.  **Process**: Downloads and prepares media for transcription.
  3.  **Transcription**: Generates text using the selected engine.
  4.  **Postprocess**: Formats the transcript into Markdown, JSON, and other formats.
- **📤 [GitHub Integration](#github-integration)**: Automatically create pull requests with new transcripts to a repository of choice.
- **💾 Multiple Export Formats**: Save transcripts as Markdown, JSON, SRT, or plain text.

## Technical Architecture

This project is a Python-based command-line application with a client-server architecture.

- **Backend**: A Python server that handles the heavy lifting of transcription.
- **CLI**: A Python client to interact with the server and manage the transcription workflow.
- **Transcription**: Integrates with [OpenAI's Whisper](https://github.com/openai/whisper) for local processing and [Deepgram](https://deepgram.com/) for a more powerful remote alternative.

### Prerequisites

Before you begin, ensure you have the following installed:

- Python 3.8+
- [FFmpeg](https://ffmpeg.org/): For audio/video conversion.
- [AWS CLI](https://aws.amazon.com/cli/): (Optional) If you plan to use the S3 upload feature.


## Development Setup

We welcome contributions from the community! To get started, you'll need to set up the project on your local machine.

### Configuration

The application is configured using a `.env` file for secrets and a `config.ini` file for other settings.

1.  **Create the environment file**:
    Copy the example file. You will need to fill this out with your own credentials.
    ```bash
    cp env.example .env
    ```

2.  **Create the configuration file**:
    Copy the example configuration file. You can modify this to set default values for command-line options and various transcription settings.
    ```bash
    cp config.ini.example config.ini
    ```

### Docker Setup (Recommended)

The easiest way to get started is using Docker Compose.

1.  **Start the server**:
    ```sh
    docker-compose up server
    ```
2.  **Use the CLI**:
    ```sh
    docker-compose run --rm cli [command] [arguments]
    ```

> **Note:**  
> For more detailed instructions on using Docker with this project, including how to work with local files, environment variables, and custom builds, please refer to our [Docker Guide](docs/docker-guide.md).

### Manual Setup

If you prefer to run the application without Docker:

1.  **Create and activate a virtual environment**:
    ```sh
    python3 -m venv venv
    source venv/bin/activate
    ```

2.  **Install dependencies**:
    ```sh
    # Install the base application
    pip3 install .

    # To include Whisper for local transcription
    pip3 install .[whisper]

    # For development, install in editable mode
    pip3 install -e .
    ```

3.  **Verify the installation**:
    ```sh
    tstbtc --version
    tstbtc --help
    ```

## Usage

The application has a server component that handles the transcription processing. This allows the heavy 
lifting of transcription to be done on a separate machine if desired. You can let the CLI manage the server automatically or run it manually.

### Server Management

**Automatic Mode (default)**:
The CLI starts the server automatically when needed. This is the easiest way to use the tool for most users. You can control this behavior with flags like `--auto-server`, `--server-mode`, and `--server-verbose`.

**Manual Mode**:
For more control, you can manage the server yourself.

```sh
# Start the server in the background
tstbtc server start

# Check the server status
tstbtc server status

# Stop the server
tstbtc server stop

# View server logs
tstbtc server logs [--follow] [--lines 100]
```

### Transcript Format and Metadata

The primary output of this tool is a Markdown file tailored for the `bitcointranscripts` repository. The format includes a YAML front matter header for metadata, followed by the transcript content.

**Metadata Schema:**

The transcript's metadata is structured as follows in a YAML front matter block:

```yaml
---
title: The title of the content
date: YYYY-MM-DD
speakers: ["Speaker One", "Speaker Two"]
tags: ["tag-one", "tag-two"]
categories: ["Category"]
---
```

While you can specify all of these using command-line arguments (e.g., `--title`, `--speakers`), the application will attempt to automatically derive as much information as possible during its `preprocess` and `postprocess` stages.

**File and Directory Structure:**

The final location of the transcript is determined by two key elements:

-   **Directory Path (`--loc`)**: This argument specifies the destination directory within the target repository. The directory structure is organized by source, so this value should correspond to the event, podcast, or content series the transcript belongs to (e.g., `stephan-livera-podcast`).
-   **Filename**: The name of the Markdown file is automatically generated by "slugifying" the transcript's title (e.g., `'OP_Vault - A New Way to HODL?'` becomes `op-vault-a-new-way-to-hodl.md`).

**Chapters and Structure:**

The body of the transcript is structured with Markdown headings to represent chapters, which makes the content easier to navigate.

- Chapters are automatically extracted from YouTube videos when available.
- We are working on a feature to automatically generate chapters during postprocessing for sources that lack them.

### Examples

Here’s how you can use the CLI to transcribe content and generate a fully formatted Markdown file.

**Transcribe a YouTube video:**

This command transcribes an episode from Stephan Livera's podcast. The tool will fetch the video, transcribe it, and use the provided metadata to generate the final Markdown file. The `--loc` and `--title` arguments determine the final path and filename.

```sh
tstbtc transcribe Nq6WxJ0PgJ4 \
  --loc "stephan-livera-podcast" \
  --title 'OP_Vault - A New Way to HODL?' \
  --date '2023-01-30' \
  --tags 'script' --tags 'op_vault' \
  --speakers 'James O’Beirne' --speakers 'Stephan Livera' \
  --category 'podcast'
```
This will result in a file being created at `stephan-livera-podcast/op-vault-a-new-way-to-hodl.md` in the output directory.

**Transcribe a remote audio file:**

You can also transcribe directly from an audio URL. For sources like this where metadata is not readily available, providing it through arguments is essential for a well-formatted output. The same file and directory logic applies.

```shell
mp3_link="https://anchor.fm/s/7d083a4/podcast/play/64348045/https%3A%2F%2Fd3ctxlq1ktw2nl.cloudfront.net%2Fstaging%2F2023-1-1%2Ff7fafb12-9441-7d85-d557-e9e5d18ab788.mp3"

tstbtc transcribe "$mp3_link" \
  --loc "stephan-livera-podcast" \
  --title 'SLP455 Anant Tapadia - Single Sig or Multi Sig?' \
  --date '2023-02-01' \
  --tags 'multisig' \
  --speakers 'Anant Tapadia' \
  --speakers 'Stephan Livera' \
  --category 'podcast'
```

## Feature Configuration

### Deepgram Integration

To use Deepgram, set your API key in the `.env` file:
```
DEEPGRAM_API_KEY=your_deepgram_api_key
```
Then, use the `--deepgram` flag when transcribing. Additional features like `--diarize` and `--summarize` will become available.

### AWS S3 Upload

To upload transcription artifacts to S3:
1. Configure your AWS CLI with credentials that have S3 write access.
2. Set your bucket name in the `.env` file:
   ```
   S3_BUCKET=your-s3-bucket-name
   ```
3. Use the `--upload` flag when transcribing.

### GitHub Integration

To automatically create pull requests with new transcripts:
1. Create a GitHub App with permissions for content and pull requests.
2. Install the app on your fork of the `bitcointranscripts` repository.
3. Add the app's credentials to your `.env` file:
   ```
   GITHUB_APP_ID=your_app_id
   GITHUB_PRIVATE_KEY_BASE64=your_base64_encoded_private_key
   GITHUB_INSTALLATION_ID=your_installation_id
   GITHUB_REPO_OWNER=target_repo_owner
   GITHUB_REPO_NAME=target_repo_name
   GITHUB_METADATA_REPO_NAME=target_metadata_repo_name
   ```
   > To base64-encode your private key file, run: `base64 -w 0 path/to/your/private-key.pem`
4. Use the `--github` flag when transcribing.

## Testing

The project includes a comprehensive test suite using pytest.

```sh
# Run all tests
pytest

# Run specific test categories
pytest -m unit       # Run only unit tests
pytest -m exporters  # Run only exporter-related tests

# Run with coverage report
pytest --cov=app
```
> For more details on the testing infrastructure, see the [tests directory README](tests/README.md).

## License

This project is released under the MIT License. See [LICENSE](LICENSE) for more information.
