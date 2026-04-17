#!/bin/bash

# Daily Transcription Processing Script
# This script runs the simplified transcription pipeline to process backlog items
# Designed to be executed via cron job for automated daily processing

# Configuration
API_URL="http://localhost:8000"
LOG_FILE="/var/log/transcription.log"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Log function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Change to project directory
cd "$PROJECT_DIR" || {
    log "ERROR: Failed to change to project directory: $PROJECT_DIR"
    exit 1
}

log "Starting daily transcription processing..."

# Check if API server is running
if ! curl -s "$API_URL/health" > /dev/null 2>&1; then
    log "ERROR: API server is not running at $API_URL"
    log "Starting API server..."
    
    # Start the server in background
    python server.py &
    SERVER_PID=$!
    
    # Wait for server to start
    sleep 10
    
    # Check if server started successfully
    if ! curl -s "$API_URL/health" > /dev/null 2>&1; then
        log "ERROR: Failed to start API server"
        exit 1
    fi
    
    log "API server started with PID: $SERVER_PID"
fi

# Run daily processing with recommended settings
log "Initiating backlog processing..."

RESPONSE=$(curl -s -X POST "$API_URL/transcription/process_backlog/" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "deepgram=true" \
  -d "diarize=true" \
  -d "github=true" \
  -d "markdown=true" \
  -d "limit=50" \
  -d "loc=all"\
 -d "username=0tuedon")
# Log the response
log "Processing response: $RESPONSE"

# Check if processing started successfully
if echo "$RESPONSE" | grep -q '"status":"started"'; then
    log "Daily transcription processing started successfully"
    
    # Wait a bit for processing to begin
    sleep 30
    
    # Check progress
    PROGRESS=$(curl -s "$API_URL/transcription/progress/")
    log "Progress check: $PROGRESS"
    
else
    log "ERROR: Failed to start daily transcription processing"
    log "Response: $RESPONSE"
    exit 1
fi

log "Daily transcription processing completed at $(date)"

# Optional: Clean up old log files (keep last 30 days)
find /var/log -name "transcription.log.*" -mtime +30 -delete 2>/dev/null || true

exit 0 