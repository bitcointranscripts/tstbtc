# Simplified Transcription Pipeline: Product Requirements Document

## Overview

Transform the current queue-based transcription pipeline into a simplified direct processing workflow that eliminates manual queue management complexity while maintaining all existing functionality.

## Goals & Objectives

**Primary Goal**: Simplify transcription pipeline by removing manual queue management complexity

**Success Metrics**:
- Reduce API endpoints from 5 to 1 for the main workflow
- Enable fully automated daily processing via cron job
- Maintain all existing transcription quality and output formats
- Preserve existing configuration options and Transcription class architecture

## Current System Analysis

The existing system has these key phases:
1. **Source Discovery** - Get backlog from btctranscripts.com
2. **Queue Management** - Add sources to transcription queue via multiple endpoints  
3. **Manual Start** - Trigger transcription processing via `/transcription/start/`
4. **AI Processing** - Process queued items through Whisper/Deepgram
5. **Export & GitHub Integration** - Generate transcripts and optionally submit PRs

**Complexity to Remove**: Steps 2-3 (queue management and manual start)

## Proposed Simplified Architecture

### New Direct Processing Flow

```
1. FETCH & EXPAND BACKLOG → 2. FILTER & PROCESS → 3. EXPORT & GITHUB
     ↓                           ↓                    ↓
btctranscripts.com         AI Transcription      Multiple Formats
  status.json +           (Whisper/Deepgram)      + GitHub PRs
  sources.json
```

### Single Endpoint Design

**New Endpoint**: `POST /transcription/process_backlog/`

This endpoint will:
1. Fetch current transcription backlog from Bitcoin Transcripts
2. Expand recurring sources (RSS feeds, playlists) into individual resources
3. Filter out items that already have media/transcripts or were recently processed
4. Immediately start transcription processing using existing Transcription class
5. Return status and progress information

## Functional Requirements

### 1. Backlog Processing Logic

#### 1.1 Backlog Retrieval
- **Primary Source**: Use existing `DataFetcher.get_transcription_backlog()` method
- **Recurring Sources**: Use existing `DataFetcher.get_sources()` to expand RSS feeds and playlists
- **Combined Processing**: Merge individual backlog items with expanded recurring sources

#### 1.2 Intelligent Filtering
- **Existing Media Check**: Skip items already in `status.json.existing.media[]`
- **Existing Transcripts**: Skip items with existing transcripts in Bitcoin Transcripts repo
- **Recently Processed**: Track processed items in memory/file to prevent re-processing
- **Date-based Filtering**: Optional cutoff date filtering for incremental processing

#### 1.3 Duplicate Prevention Strategy
Since PRs may not be merged before the next cron run, implement lightweight tracking:

**File-based Tracking with Repository Validation**
- Create `processed_items.json` file in working directory
- Store processed item identifiers (URL + timestamp + metadata)
- **Smart Cleanup**: Only remove entries when they no longer appear in the backlog
- **Repository Validation**: Use the backlog itself as the source of truth for cleanup
- **Persistent Tracking**: Maintain processed items list across runs until confirmed in repo

### 2. API Endpoint Design

#### 2.1 Core Processing Endpoint

**Endpoint**: `POST /transcription/process_backlog/`

**Request Parameters** (using existing transcription flags):
```json
{
  "model": "tiny.en",           // Whisper model
  "deepgram": false,            // Use Deepgram instead of Whisper
  "summarize": false,           // Enable AI summaries (Deepgram)
  "diarize": false,             // Enable speaker identification (Deepgram)
  "github": true,               // Auto-submit to GitHub
  "markdown": true,             // Generate markdown output
  "json": false,                // Generate JSON output
  "text": false,                // Generate text output
  "limit": null,                // Max items to process
  "dry_run": false,             // Preview mode without processing
  "cutoff_date": null,          // Only process items newer than this date
  "loc": "all"                  // Location filter for sources
}
```

**Response Format**:
```json
{
  "status": "started|completed|failed",
  "message": "Processing started for 15 items",
  "data": {
    "total_items": 15,
    "processing_items": [
      {
        "title": "Bitcoin Core Dev Meeting #123",
        "media": "https://youtube.com/watch?v=abc123",
        "status": "in_progress|completed|failed",
        "error": "Error message if failed"
      }
    ],
    "skipped_items": [
      {
        "title": "Already transcribed item",
        "reason": "existing_transcript|recently_processed|existing_media"
      }
    ]
  }
}
```

#### 2.2 Progress Monitoring Endpoint

**Endpoint**: `GET /transcription/progress/`

**Response**:
```json
{
  "status": "idle|in_progress|completed|failed",
  "progress": {
    "total_items": 15,
    "completed": 8,
    "failed": 2,
    "in_progress": 5
  },
  "items": [
    {
      "title": "Item Title",
      "status": "completed|failed|in_progress",
      "error": "Error details if failed"
    }
  ]
}
```

### 3. Implementation Approach

#### 3.1 Extend Existing Transcription Class

**No new class needed** - extend existing `Transcription` class with new methods:

```python
class Transcription:
    # ... existing methods ...
    
    def process_backlog_directly(self, **options):
        """Process transcription backlog directly without queue management"""
        # 1. Fetch and expand backlog
        # 2. Filter already processed items
        # 3. Process items sequentially
        # 4. Track progress and update processed items list
        # 5. Return processing summary
    
    def _fetch_and_expand_backlog(self, **options):
        """Fetch backlog and expand recurring sources"""
        
    def _filter_processed_items(self, items):
        """Filter out already processed items"""
        
    def _update_processed_tracking(self, processed_items):
        """Update tracking of processed items"""
        
    def get_processing_status(self):
        """Get current processing status and progress"""
```

**Key Design Principle**: Since the application runs only one transcription job at a time, we use the existing Transcription instance to track progress directly, eliminating the need for complex processing IDs or external state management.

#### 3.2 Backlog Processing Workflow

1. **Fetch Backlog**: Combine `get_transcription_backlog()` and `get_sources()`
2. **Expand Recurring Sources**: Parse RSS feeds, expand YouTube playlists
3. **Cleanup Tracking**: Remove processed items that are no longer in backlog (merged to repo)
4. **Filter Items**: Remove already processed, existing media, existing transcripts
5. **Sequential Processing**: Process items one by one using existing transcription logic
6. **Progress Tracking**: Update status for each item as it completes
7. **Duplicate Prevention**: Track newly processed items for future runs

#### 3.3 Duplicate Prevention Implementation

**File-based tracking with repository validation**:

```python
def _load_processed_items(self):
    """Load list of processed items from file"""
    try:
        with open('processed_items.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def _mark_item_processed(self, item_id, item_data):
    """Mark item as processed with timestamp and metadata"""
    processed = self._load_processed_items()
    processed[item_id] = {
        'processed_at': datetime.now().isoformat(),
        'title': item_data.get('title'),
        'media': item_data.get('media'),
        'loc': item_data.get('loc'),
        'last_backlog_check': datetime.now().isoformat()
    }
    
    with open('processed_items.json', 'w') as f:
        json.dump(processed, f, indent=2)

def _cleanup_processed_items(self, current_backlog):
    """Remove processed items that are no longer in the backlog (merged to repo)"""
    processed = self._load_processed_items()
    current_backlog_urls = {item.get('media') for item in current_backlog if item.get('media')}
    
    # Only remove items that are no longer in the backlog
    items_to_remove = []
    for item_id, item_data in processed.items():
        if item_data.get('media') not in current_backlog_urls:
            items_to_remove.append(item_id)
    
    # Remove confirmed items from tracking
    for item_id in items_to_remove:
        del processed[item_id]
        self.logger.info(f"Removed {item_id} from processed items (confirmed in repository)")
    
    # Update the tracking file
    with open('processed_items.json', 'w') as f:
        json.dump(processed, f, indent=2)
    
    return len(items_to_remove)
```

### 4. Technical Requirements

#### 4.1 Error Handling & Resilience

- **Graceful Failures**: If one item fails, continue processing others
- **Retry Logic**: Automatic retry for transient failures (network, rate limits)
- **Error Reporting**: Detailed error logs with actionable messages
- **Resource Management**: Proper cleanup of temporary files and media

#### 4.2 Performance Considerations

- **Sequential Processing**: Process items one at a time (no concurrency)
- **Resource Limits**: Configurable limits on items processed per run
- **Storage Management**: Automatic cleanup of processed media files
- **Rate Limiting**: Respect YouTube/external service rate limits

#### 4.3 Progress Tracking

- **Real-time Updates**: Status updates stored in memory during processing
- **Persistent Tracking**: Save progress to file for crash recovery
- **Completion Summary**: Detailed report of successful/failed items

### 5. Implementation Plan

#### Phase 1: Core Functionality (Week 1-2)
1. Extend `Transcription` class with `process_backlog_directly()` method
2. Implement backlog fetching and recurring source expansion
3. Add duplicate prevention with file-based tracking
4. Create `/transcription/process_backlog/` endpoint

#### Phase 2: Enhanced Features (Week 3)
1. Add progress tracking using existing Transcription instance
2. Implement comprehensive error handling
3. Add dry-run functionality for testing
4. Comprehensive testing and validation

#### Phase 3: Deployment & Scripts (Week 4)
1. Create cron job scripts and deployment guides
2. Update documentation and API guides
3. Performance testing and optimization
4. Migration guide for existing users

### 6. API Changes Summary

#### New Endpoints
- `POST /transcription/process_backlog/` - Direct processing endpoint
- `GET /transcription/progress/{processing_id}` - Progress tracking

#### Modified Endpoints  
- Keep existing endpoints for backward compatibility
- Extend existing `Transcription` class with new methods

#### Removed Complexity
- No more manual queue management
- No more separate "add to queue" + "start processing" steps
- Simplified configuration using existing transcription parameters

### 7. Cron Job Integration

**Daily Processing Script** (`scripts/daily-transcription.sh`):
```bash
#!/bin/bash
# Configuration
API_URL="http://localhost:8000"

# Run daily processing with existing transcription parameters
curl -X POST "$API_URL/transcription/process_backlog/" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "deepgram=true" \
  -d "diarize=true" \
  -d "github=true" \
  -d "markdown=true" \
  -d "limit=50" \
  -d "loc=all" | jq .

# Log results
echo "Daily processing completed at $(date)"
```

**Crontab Entry**:
```
# Run daily at 2 AM UTC
0 2 * * * /path/to/scripts/daily-transcription.sh >> /var/log/transcription.log 2>&1
```

### 8. Migration Strategy

1. **Parallel Deployment**: Deploy new endpoint alongside existing ones
2. **Gradual Migration**: Test with limited items first 
3. **Backward Compatibility**: Keep existing endpoints for external integrations
4. **Documentation Update**: Clear migration guide for users
5. **Monitoring**: Enhanced logging and monitoring during transition

### 9. Risk Mitigation

**Potential Risks**:
- Processing large backlogs could take significant time
- External API rate limits (YouTube, Deepgram) could cause failures
- Loss of manual control over individual items
- File-based tracking could become corrupted
- Backlog API changes could affect cleanup logic

**Mitigation Strategies**:
- Implement configurable processing limits per run
- Add circuit breakers and exponential backoff for external APIs
- Provide override mechanisms for manual intervention when needed
- Implement file corruption detection and recovery
- Validate backlog API responses before cleanup operations
- Comprehensive monitoring and alerting

## Benefits of Simplified Architecture

### Operational Benefits
- **Reduced Complexity**: Single endpoint replaces multi-step queue management
- **Automated Operations**: Perfect for daily cron job execution
- **Improved Reliability**: Fewer moving parts and potential failure points
- **Better Resource Utilization**: Direct processing without queue overhead

### Development Benefits
- **Simplified Integration**: Single API call for complete workflow
- **Easier Testing**: Straightforward end-to-end testing
- **Reduced Maintenance**: Less code to maintain and debug
- **Clearer Data Flow**: Obvious processing pipeline without intermediary steps

### User Experience Benefits
- **Immediate Processing**: No manual queue management required
- **Real-time Feedback**: Live progress updates during processing
- **Predictable Behavior**: Consistent automated processing
- **Error Transparency**: Clear error reporting and recovery options

## Conclusion

This simplified architecture maintains all the powerful features of the original system while removing unnecessary complexity. By extending the existing `Transcription` class and using file-based duplicate prevention, we achieve the goal of automated daily processing without introducing database dependencies or losing the benefits of the current architecture.

The single endpoint approach makes it perfect for automated daily cron jobs while still supporting manual execution when needed. The duplicate prevention strategy ensures that resources aren't re-processed even if GitHub PRs haven't been merged yet. 