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

### Phase 3: Direct Processing (Simplified Workflow)

**Purpose**: Process transcription backlog directly without manual queue management

**Key Components**:
- **Direct Processing Route** (`/transcription/process_backlog/`) - Single endpoint for complete workflow
- **Transcription Class** (`app/transcription.py`) - Core transcription management with new direct processing methods
- **Progress Tracking** (`/transcription/progress/{processing_id}`) - Monitor processing status

**Workflow**:
1. **Backlog Retrieval**: Fetch current transcription backlog from Bitcoin Transcripts
2. **Source Expansion**: Automatically expand recurring sources (RSS feeds, playlists) into individual resources
3. **Intelligent Filtering**: Remove already processed items, existing media, and recent duplicates
4. **Direct Processing**: Immediately start transcription processing using existing AI services
5. **Progress Tracking**: Monitor processing status and completion

**Benefits**:
- **Single Endpoint**: Replaces multi-step queue management with one API call
- **Automated Workflow**: Perfect for daily cron job execution
- **Duplicate Prevention**: File-based tracking prevents re-processing of items
- **Backward Compatibility**: Maintains existing queue-based workflow for manual operations

### Phase 4: Queue Management (Legacy Workflow)

**Purpose**: Add sources to transcription queue and manage processing workflow (maintained for backward compatibility)

**Key Components**:
- **Queue Route** (`/transcription/add_to_queue/`) - Add sources to processing queue
- **Transcription Class** (`app/transcription.py`) - Core transcription management
- **APIClient** (`app/api_client.py`) - Frontend integration interface

**Workflow**:
1. **Source Addition**: Individual resources or preprocessed JSON added to queue
2. **Configuration**: Transcription settings (model, service, output formats) configured
3. **Validation**: Source validation and duplicate checking
4. **Queue Status**: Track queued, in-progress, and completed transcripts

### Phase 5: AI Transcription Processing

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

### Phase 6: Postprocessing & Export

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
- `/transcription/process_backlog/` - **NEW**: Direct processing endpoint for simplified workflow
- `/transcription/progress/` - **NEW**: Progress tracking for current transcription job
- `/transcription/add_to_queue/` - Add sources to transcription queue (legacy)
- `/transcription/queue/` - Get current queue status (legacy)
- `/transcription/start/` - Begin processing queued items (legacy)
- `/transcription/remove_from_queue/` - Remove items from queue (legacy)

### Data Flow Architecture

#### Simplified Direct Processing Flow
```
1. SOURCE DISCOVERY
Bitcoin Transcripts Repository (btctranscripts.com)
    ↓ (JSON APIs: status.json, sources.json)
DataFetcher → Direct Processing Endpoint → AI Transcription → Export

2. AUTOMATED WORKFLOW
Single API Call → Backlog Fetch → Source Expansion → Filtering → Processing → GitHub
```

#### Legacy Queue-Based Flow
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

**Pattern 1: Simplified Direct Processing (Recommended)**
1. Call `/transcription/process_backlog/` with desired configuration
2. Monitor progress via `/transcription/progress/{processing_id}`
3. Processing completes automatically with GitHub integration

**Pattern 2: Individual Resource Processing**
1. Get transcription backlog via `/curator/get_transcription_backlog/`
2. Add individual resources directly to queue via `/transcription/add_to_queue/`
3. Start processing and monitor progress

**Pattern 3: Recurring Source Processing** 
1. Get sources via `/curator/get_sources/` with coverage and location filters
2. Preprocess recurring sources via `/transcription/preprocess/` to expand episodes/videos
3. Review and edit preprocessed JSON output
4. Submit preprocessed JSON to queue via `/transcription/add_to_queue/`
5. Start processing batch

**Pattern 4: Manual Source Addition**
1. Submit individual URLs or local files directly to `/transcription/add_to_queue/`
2. Configure transcription settings (service, model, output formats)
3. Process immediately or queue for later processing

## Technical Implementation Details

### Server Architecture

The tstbtc server uses FastAPI with the following structure:

**Route Organization**:
- `/curator/*` - Source discovery and curation management
- `/transcription/*` - Core transcription workflow management (simplified + legacy)
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

### Direct Processing System

**Processing States**:
- `"started"` - Processing initiated successfully
- `"in_progress"` - Currently processing backlog items
- `"completed"` - All items processed successfully
- `"failed"` - Processing encountered errors

**Processing Features**:
- **Automatic Backlog Fetching**: Retrieves current transcription needs
- **Intelligent Filtering**: Removes duplicates and already processed items
- **Recurring Source Expansion**: Automatically expands RSS feeds and playlists
- **Duplicate Prevention**: File-based tracking prevents re-processing
- **Background Execution**: Non-blocking processing for long-running operations

### Queue Management System (Legacy)

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

# Direct transcription (simplified workflow)
tstbtc transcribe "https://youtube.com/watch?v=..." --loc misc --deepgram --diarize --github

# Simplified backlog processing (NEW)
tstbtc process-backlog --deepgram --diarize --github --markdown
tstbtc process-backlog --dry-run --limit 25 --loc stephan-livera-podcast

# Progress monitoring (NEW)
tstbtc get-progress
```

**Enhanced Dry Run Example Output**:
```bash
$ tstbtc process-backlog --dry-run --limit 10 --loc stephan-livera-podcast

[INFO] Dry run completed. 8 items would be processed.

Detailed dry run report:
{
  "status": "dry_run_report",
  "summary": {
    "total_items_found": 45,
    "total_items_to_process": 8,
    "total_items_skipped": 37,
    "limit_applied": 10
  },
  "expansion_details": {
    "backlog_items": 12,
    "expanded_sources": 3,
    "expanded_items": 33,
    "location_filter": "stephan-livera-podcast",
    "cutoff_date": null,
    "source_details": [
      {
        "source": "Stephan Livera Podcast",
        "type": "rss",
        "url": "https://feeds.example.com/stephan-livera.rss",
        "expanded_count": 28,
        "location": "stephan-livera-podcast"
      },
      {
        "source": "Bitcoin Rapid-Fire",
        "type": "playlist",
        "url": "https://youtube.com/playlist?list=...",
        "expanded_count": 5,
        "location": "stephan-livera-podcast"
      }
    ]
  },
  "filtering_details": {
    "existing_media_count": 15,
    "processed_tracking_count": 22,
    "skipped_items": [
      {
        "title": "Bitcoin Core Dev Meeting #123",
        "media": "https://youtube.com/watch?v=abc123",
        "reason": "existing_media",
        "location": "stephan-livera-podcast",
        "details": "Media already exists in repository"
      }
    ],
    "items_to_process": [
      {
        "title": "Stephan Livera Episode 789",
        "media": "https://feeds.example.com/episode789",
        "location": "stephan-livera-podcast",
        "type": "expanded_source",
        "date": "2024-01-15",
        "tags": ["bitcoin", "podcast"],
        "speakers": ["Stephan Livera"],
        "category": ["education"]
      },
      {
        "title": "Bitcoin Rapid-Fire #45",
        "media": "https://youtube.com/watch?v=xyz789",
        "location": "stephan-livera-podcast",
        "type": "expanded_source",
        "date": "2024-01-14",
        "tags": ["bitcoin", "news"],
        "speakers": ["Host"],
        "category": ["news"]
      }
    ]
  },
  "configuration": {
    "deepgram": false,
    "diarize": false,
    "summarize": false,
    "github": false,
    "markdown": true,
    "json": false,
    "text": false
  }
}
```

### API Integration

#### Simplified Direct Processing (Recommended)
```python
# Frontend workflow example - simplified approach
import requests

# Single call to process entire backlog
response = requests.post("http://localhost:8000/transcription/process_backlog/",
                        data={
                            "deepgram": True,
                            "diarize": True,
                            "github": True,
                            "markdown": True,
                            "limit": 50,
                            "loc": "all"
                        })

if response.json()["status"] == "started":
    # Monitor progress
    progress = requests.get("http://localhost:8000/transcription/progress/")
    print(f"Processing status: {progress.json()['status']}")
```

#### Legacy Queue-Based Processing
```python
# Frontend workflow example - legacy approach
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

### Automated Daily Processing

**Cron Job Setup**:
```bash
# Add to crontab for daily execution at 2 AM UTC
0 2 * * * /path/to/scripts/daily-transcription.sh >> /var/log/transcription.log 2>&1
```

**Daily Processing Script** (`scripts/daily-transcription.sh`):
```bash
#!/bin/bash
# Configuration
API_URL="http://localhost:8000"

# Run daily processing with recommended settings
curl -X POST "$API_URL/transcription/process_backlog/" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "deepgram=true" \
  -d "diarize=true" \
  -d "github=true" \
  -d "markdown=true" \
  -d "limit=50" \
  -d "loc=all"

echo "Daily transcription processing completed at $(date)"
```

## Migration Guide

### From Queue-Based to Direct Processing

**Benefits of Migration**:
- **Simplified API**: Single endpoint replaces multi-step workflow
- **Automated Operations**: Perfect for daily cron job execution
- **Reduced Complexity**: Fewer moving parts and potential failure points
- **Better Resource Utilization**: Direct processing without queue overhead

**Migration Steps**:
1. **Update API Calls**: Replace queue management calls with single `process_backlog` endpoint
2. **Configure Processing Options**: Set transcription parameters in the request
3. **Monitor Progress**: Use progress endpoint to track processing status
4. **Remove Queue Logic**: Eliminate manual queue management from frontend

**Backward Compatibility**:
- All existing queue-based endpoints remain functional
- Gradual migration possible without breaking changes
- Legacy workflow supported for manual operations

## Conclusion

The tstbtc transcription pipeline provides a comprehensive solution for transforming source material into AI-generated transcripts ready for the Bitcoin Transcripts repository. The architecture supports both simplified automated workflows and traditional manual curation workflows, handling individual resources and recurring sources with equal efficiency.

**Key strengths of the system include**:
- **Flexible Source Handling**: Support for various media types and recurring sources
- **Dual AI Services**: Choice between local Whisper and cloud Deepgram processing
- **Simplified Workflow**: Direct processing endpoint for automated operations
- **Legacy Support**: Maintains queue-based processing for manual workflows
- **Multiple Output Formats**: Simultaneous generation of various export formats
- **Integration Ready**: RESTful APIs designed for frontend and external system integration

**Recent Improvements**:
- **Simplified Pipeline**: New direct processing endpoint eliminates queue management complexity
- **Automated Workflow**: Perfect for daily cron job execution and batch processing
- **Duplicate Prevention**: Intelligent filtering prevents re-processing of items
- **Progress Tracking**: Real-time monitoring of processing status

The modular design ensures components can evolve independently while maintaining the complete workflow from source discovery through final transcript delivery. The simplified architecture makes it ideal for automated daily processing while preserving all the powerful features of the original system. 