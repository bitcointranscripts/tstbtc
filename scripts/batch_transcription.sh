#!/bin/bash

# Check if required arguments are provided
if [ $# -lt 2 ]; then
    echo "Usage: $0 <directory_path> <location_value>"
    echo "Example: $0 /path/to/videos bitcoin-meetup"
    exit 1
fi

# Get arguments
DIRECTORY_PATH="$1"
LOCATION_VALUE="$2"

# Check if directory exists
if [ ! -d "$DIRECTORY_PATH" ]; then
    echo "Error: Directory '$DIRECTORY_PATH' does not exist."
    exit 1
fi

# Video file extensions to look for
VIDEO_EXTENSIONS=("mp4" "mkv" "avi" "mov" "webm" "flv" "wmv" "m4v" "mpg" "mpeg" "mxf")

# Function to check if a file has a video extension
is_video_file() {
    local file="$1"
    local ext="${file##*.}"
    ext=$(echo "$ext" | tr '[:upper:]' '[:lower:]')
    
    for valid_ext in "${VIDEO_EXTENSIONS[@]}"; do
        if [ "$ext" = "$valid_ext" ]; then
            return 0
        fi
    done
    return 1
}

# Process each file in the directory (only top level, no subdirectories)
echo "Starting transcription of videos in $DIRECTORY_PATH"
echo "Using location value: $LOCATION_VALUE"
echo "-------------------------------------------"

file_count=0
processed_count=0

for file in "$DIRECTORY_PATH"/*; do
    # Skip if it's a directory
    if [ -d "$file" ]; then
        continue
    fi
    
    # Check if it's a video file
    if is_video_file "$file"; then
        file_count=$((file_count + 1))
        
        # Get filename without path
        filename=$(basename "$file")
        # Get filename without extension for title
        title="${filename%.*}"
        
        echo "Processing: $filename"
        echo "Title: $title"
        
        # Execute the transcription command
        tstbtc transcribe "$file" --loc "$LOCATION_VALUE" --title "$title"
        
        # Check if the command was successful
        if [ $? -eq 0 ]; then
            echo "✓ Successfully transcribed: $filename"
            processed_count=$((processed_count + 1))
        else
            echo "✗ Failed to transcribe: $filename"
        fi
        echo "-------------------------------------------"
    fi
done

# Summary
echo "Transcription complete!"
echo "Files processed: $processed_count/$file_count"

if [ $file_count -eq 0 ]; then
    echo "No video files found in the specified directory."
fi

exit 0