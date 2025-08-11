# Transcription Pipeline: End-to-End Flow

This document provides a comprehensive overview of the complete transcription pipeline within the tstbtc project, from curation through AI-generated transcript delivery.

## Pipeline Overview

The tstbtc system implements a complete transcription workflow that transforms source material (individual resources or recurring sources like podcasts) into AI-generated transcripts ready for the Bitcoin Transcripts repository. The pipeline supports both manual curation workflows and automated frontend integration.

## Complete Pipeline Flow

The transcription pipeline consists of five main phases:

### Phase 1: Source Discovery & Curation

**Purpose**: Discover and manage source material from the Bitcoin Transcripts repository backlog

**Key Components**:
- **Curator API Routes** (`routes/curator.py`) - RESTful endpoints for accessing Bitcoin Transcripts data
- **DataFetcher Class** (`app/data_fetcher.py`) - Interface to Bitcoin Transcripts repository (`btctranscripts.com`)
- **CLI Commands** (`app/commands/curator.py`) - Command-line tools for manual curation

**Workflow**:
1. **Source Discovery**: `DataFetcher` retrieves source lists and transcription backlog from `btctranscripts.com`
2. **Filtering**: Sources filtered by location (`loc`) and transcription coverage (`full`/`none`)
3. **Duplicate Prevention**: Existing media checked to avoid reprocessing
4. **Export**: Curated sources exported as JSON files for further processing

### Phase 2: Source Preprocessing

**Purpose**: Expand recurring sources (podcasts, playlists) into individual resources and prepare metadata

**Key Components**:
- **Preprocessing Route** (`/transcription/preprocess/`) - API endpoint for source expansion
- **Source Types** (`app/transcript.py`) - `RSS`, `Playlist`, `Audio`, `Video` classes
- **YouTube Integration** - Metadata extraction and playlist expansion

**Workflow for Recurring Sources**:
1. **RSS/Podcast Processing**: Parse RSS feeds to extract individual episodes
2. **Playlist Expansion**: Extract individual videos from YouTube playlists  
3. **Metadata Extraction**: Gather title, date, speakers, tags for each resource
4. **Cutoff Date Filtering**: Only process content newer than specified date
5. **Output**: JSON file with individual resources ready for transcription

**Workflow for Individual Resources**:
- Direct processing of single videos, audio files, or local media
- Metadata validation and enhancement
- Format detection and source type assignment

### Phase 3: Queue Management

**Purpose**: Add sources to transcription queue and manage processing workflow

**Key Components**:
- **Queue Route** (`/transcription/add_to_queue/`) - Add sources to processing queue
- **Transcription Class** (`app/transcription.py`) - Core transcription management
- **APIClient** (`app/api_client.py`) - Frontend integration interface

**Workflow**:
1. **Source Addition**: Individual resources or preprocessed JSON added to queue
2. **Configuration**: Transcription settings (model, service, output formats) configured
3. **Validation**: Source validation and duplicate checking
4. **Queue Status**: Track queued, in-progress, and completed transcripts

### Phase 4: AI Transcription Processing

**Purpose**: Convert audio/video to text using AI transcription services

**Key Components**:
- **Transcription Services** (`app/services/`) - Whisper (local) and Deepgram (cloud) 
- **Media Processing** - Audio extraction from video, chunking for long content
- **Source Processing** (`app/transcript.py`) - Download and prepare media files

**Workflow**:
1. **Media Download**: Download and process source media files
2. **Audio Extraction**: Extract audio from video sources using FFmpeg
3. **Service Selection**: Choose between local Whisper or cloud Deepgram
4. **Transcription**: Generate text transcription with optional features:
   - **Speaker Diarization**: Identify different speakers (Deepgram)
   - **Summarization**: AI-generated summaries (Deepgram)
   - **Chunking**: Split long audio for processing
5. **Raw Output**: Store transcription service output as JSON

### Phase 5: Postprocessing & Export

**Purpose**: Format transcripts and generate final output files

**Key Components**:
- **Exporter Factory** (`app/exporters.py`) - Multiple output format support
- **Markdown Exporter** - Bitcoin Transcripts format with YAML frontmatter
- **JSON/Text Exporters** - Additional output formats
- **GitHub Integration** - Automated repository submission

**Workflow**:
1. **Content Formatting**: Structure transcript with chapters and metadata
2. **Multiple Exports**: Generate files in requested formats:
   - **Markdown**: YAML frontmatter + transcript body (primary format)
   - **JSON**: Structured data format
   - **Plain Text**: Clean text output
   - **SRT**: Subtitle format with timestamps
3. **GitHub Submission**: Automated pull request creation (optional)
4. **S3 Upload**: Cloud storage of transcription artifacts (optional)

## Frontend Integration Architecture

### API Endpoints

The pipeline exposes several HTTP API endpoints for frontend integration:

**Curation APIs** (`/curator/*`):
- `/curator/get_sources/` - Retrieve filtered source information
- `/curator/get_transcription_backlog/` - Get items needing transcription

**Transcription APIs** (`/transcription/*`):
- `/transcription/preprocess/` - Expand recurring sources to individual resources
- `/transcription/add_to_queue/` - Add sources to transcription queue
- `/transcription/queue/` - Get current queue status
- `/transcription/start/` - Begin processing queued items
- `/transcription/remove_from_queue/` - Remove items from queue

### Data Flow Architecture

```
1. SOURCE DISCOVERY
Bitcoin Transcripts Repository (btctranscripts.com)
    ↓ (JSON APIs: status.json, sources.json)
DataFetcher → Curator Routes → Frontend/CLI

2. PREPROCESSING (for recurring sources)
Frontend/CLI → Preprocess Route → Source Expansion → JSON Output

3. QUEUE MANAGEMENT  
Frontend/CLI → Add to Queue Route → Transcription Queue

4. AI PROCESSING
Start Route → Media Download → AI Transcription → Raw Output

5. POSTPROCESSING
Raw Transcript → Exporters → Multiple Formats → GitHub/Storage
```

### Frontend Workflow Patterns

**Pattern 1: Individual Resource Processing**
1. Get transcription backlog via `/curator/get_transcription_backlog/`
2. Add individual resources directly to queue via `/transcription/add_to_queue/`
3. Start processing and monitor progress

**Pattern 2: Recurring Source Processing** 
1. Get sources via `/curator/get_sources/` with coverage and location filters
2. Preprocess recurring sources via `/transcription/preprocess/` to expand episodes/videos
3. Review and edit preprocessed JSON output
4. Submit preprocessed JSON to queue via `/transcription/add_to_queue/`
5. Start processing batch

**Pattern 3: Manual Source Addition**
1. Submit individual URLs or local files directly to `/transcription/add_to_queue/`
2. Configure transcription settings (service, model, output formats)
3. Process immediately or queue for later processing

## Technical Implementation Details

### Server Architecture

The tstbtc server uses FastAPI with the following structure:

**Route Organization**:
- `/curator/*` - Source discovery and curation management
- `/transcription/*` - Core transcription workflow management  
- `/media/*` - Media-specific utilities

**Core Components**:
- **FastAPI Server** (`server.py`) - Main application with CORS configuration
- **Global Transcription Instance** - Manages transcription state across requests
- **Background Tasks** - Asynchronous processing for long-running transcriptions
- **Error Handling** - Consistent error responses and logging

### Configuration System

**Environment Variables** (`.env` file):
- `BTC_TRANSCRIPTS_URL` - Bitcoin Transcripts repository URL
- `TRANSCRIPTION_SERVER_URL` - Server URL for CLI/frontend integration
- `DEEPGRAM_API_KEY` - Cloud transcription service key
- `GITHUB_APP_*` - GitHub integration credentials
- `S3_BUCKET` - Cloud storage configuration

**Runtime Configuration** (`config.ini`):
- Server modes and default settings
- Transcription service preferences
- Output format defaults

### Source Type Handling

**Individual Resources**:
- **Audio Files**: Direct processing (.mp3, .wav, .m4a, .aac)
- **Video Files**: Audio extraction then processing (.mp4, .webm, .mov)
- **YouTube Videos**: Metadata extraction and download
- **Local Files**: File upload and processing

**Recurring Sources**:
- **RSS Feeds**: Parse podcast feeds to extract episodes with cutoff date filtering
- **YouTube Playlists**: Extract individual videos with metadata and filtering
- **Batch Processing**: Handle multiple resources with shared metadata

### Queue Management System

**Queue States**:
- `"queued"` - Added to queue, awaiting processing
- `"in_progress"` - Currently being processed
- `"completed"` - Successfully transcribed
- `"failed"` - Processing encountered errors

**Queue Operations**:
- **Add Sources**: Individual or batch addition with validation
- **Remove Sources**: JSON-based removal of specific items
- **Status Tracking**: Real-time queue status and progress monitoring
- **Background Processing**: Non-blocking transcription execution

### AI Transcription Services

**Whisper (Local Processing)**:
- OpenAI's Whisper model for local transcription
- Multiple model sizes (tiny, base, small, medium, large)
- Generates SRT subtitle files with timestamps
- No external dependencies after model download

**Deepgram (Cloud Processing)**:
- Cloud-based transcription with advanced features
- Speaker diarization and identification
- AI-generated summaries and topic detection
- Automatic chunking for long audio files
- Enhanced accuracy for professional content

### Export and Output Management

**Exporter Architecture** (`app/exporters.py`):
- **Factory Pattern**: Dynamic creation of exporters based on configuration
- **Multiple Formats**: Simultaneous generation of different output formats
- **Extensible Design**: Easy addition of new export formats

**Output Formats**:
- **Markdown**: Primary format with YAML frontmatter for Bitcoin Transcripts
- **JSON**: Structured data with metadata and transcript content
- **Plain Text**: Clean text output without formatting
- **SRT**: Subtitle format with precise timestamps

**File Organization**:
- Organized by source location (`loc` parameter)
- Slugified titles for consistent file naming
- Optional timestamp suffixes for versioning
- Automatic directory creation and management

## Usage Examples

### CLI Commands

```bash
# Discovery and curation
tstbtc curator get-sources stephan-livera-podcast --coverage none
tstbtc curator get-transcription-backlog

# Preprocessing recurring sources  
tstbtc preprocess "https://youtube.com/playlist?list=..." --loc stephan-livera-podcast --cutoff-date 2024-01-01

# Direct transcription
tstbtc transcribe "https://youtube.com/watch?v=..." --loc misc --deepgram --diarize --github
```

### API Integration

```python
# Frontend workflow example
import requests

# 1. Get sources for curation
response = requests.post("http://localhost:8000/curator/get_sources/", 
                        json={"loc": "all", "coverage": "none"})
sources = response.json()["data"]

# 2. Preprocess recurring source
response = requests.post("http://localhost:8000/transcription/preprocess/",
                        data={"source": "https://feeds.example.com/podcast.rss",
                              "loc": "example-podcast", 
                              "cutoff_date": "2024-01-01"})
preprocessed = response.json()["data"]

# 3. Add to queue and start processing
response = requests.post("http://localhost:8000/transcription/add_to_queue/",
                        data={"source": preprocessed_json_file,
                              "deepgram": True, "diarize": True})

response = requests.post("http://localhost:8000/transcription/start/")
```

## Conclusion

The tstbtc transcription pipeline provides a comprehensive solution for transforming source material into AI-generated transcripts ready for the Bitcoin Transcripts repository. The architecture supports both manual curation workflows and automated frontend integration, handling individual resources and recurring sources with equal efficiency.

Key strengths of the system include:
- **Flexible Source Handling**: Support for various media types and recurring sources
- **Dual AI Services**: Choice between local Whisper and cloud Deepgram processing
- **Queue-Based Processing**: Efficient batch processing with status tracking
- **Multiple Output Formats**: Simultaneous generation of various export formats
- **Integration Ready**: RESTful APIs designed for frontend and external system integration

The modular design ensures components can evolve independently while maintaining the complete workflow from source discovery through final transcript delivery. 