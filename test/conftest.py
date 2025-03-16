"""
Common pytest fixtures for the entire test suite.
"""

import os
import tempfile
import pytest
from unittest import mock
import shutil

from app import __version__
from app.transcript import Transcript, Source
from app.exporters import MarkdownExporter, JsonExporter, TextExporter


# --- Basic Fixtures ---


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Clean up after test
    shutil.rmtree(temp_dir)


@pytest.fixture
def mock_transcript():
    """Create a mock transcript for testing."""
    transcript = mock.MagicMock(spec=Transcript)
    transcript.title = "Test Transcript"

    # Configure source
    transcript.source = mock.MagicMock(spec=Source)
    transcript.source.loc = "test/location"
    transcript.source.title = "Test Transcript"
    transcript.source.tags = ["tag1", "tag2"]
    transcript.source.category = ["category1"]
    transcript.source.speakers = ["Speaker 1"]
    transcript.source.type = "video"
    transcript.source.media = "http://example.com/video.mp4"
    transcript.source.to_json.return_value = {
        "title": "Test Transcript",
        "speakers": ["Speaker 1", "Speaker 2"],
        "tags": ["tag1", "tag2"],
        "type": "video",
        "loc": "test/location",
        "source_file": "http://example.com/video.mp4",
        "categories": ["category1", "category2"],
        "media": "http://example.com/video.mp4",
        "date": "2023-01-01",
        "chapters": [],
    }

    # Configure outputs
    transcript.outputs = {
        "raw": "This is a test transcript.\n\nIt has multiple paragraphs.",
        "markdown": None,
        "json": None,
        "text": None,
    }

    # Configure other methods
    transcript.to_json.return_value = {
        "title": "Test Transcript",
        "speakers": ["Speaker 1", "Speaker 2"],
        "tags": ["tag1", "tag2"],
        "categories": ["category1", "category2"],
        "loc": "test/location",
        "body": "This is a test transcript.\n\nIt has multiple paragraphs.",
    }

    return transcript


# --- Exporter Fixtures ---


@pytest.fixture
def markdown_exporter(temp_dir):
    """Create a markdown exporter for testing."""
    return MarkdownExporter(temp_dir, transcript_by="Test User")


@pytest.fixture
def json_exporter(temp_dir):
    """Create a JSON exporter for testing."""
    return JsonExporter(temp_dir, transcript_by="Test User")


@pytest.fixture
def text_exporter(temp_dir):
    """Create a text exporter for testing."""
    return TextExporter(temp_dir)


# --- Service Fixtures ---


@pytest.fixture
def mock_deepgram_service():
    """Create a mock Deepgram service for testing."""
    service = mock.MagicMock()
    service.transcribe.return_value = None
    service.write_to_json_file.return_value = "/path/to/deepgram_output.json"
    return service


@pytest.fixture
def mock_whisper_service():
    """Create a mock Whisper service for testing."""
    service = mock.MagicMock()
    service.transcribe.return_value = None
    service.write_to_json_file.return_value = "/path/to/whisper_output.json"
    return service


# --- Transcription Fixtures ---


@pytest.fixture
def mock_transcription_deps():
    """Create mock dependencies for the Transcription class."""
    deps = {
        "settings": mock.MagicMock(),
        "services": mock.MagicMock(),
        "GitHubAPIHandler": mock.MagicMock(),
        "Queuer": mock.MagicMock(),
        "DataFetcher": mock.MagicMock(),
        "DataWriter": mock.MagicMock(),
        "ExporterFactory": mock.MagicMock(),
    }

    # Configure settings
    deps["settings"].TSTBTC_METADATA_DIR = "metadata/"

    # Configure mock factory to return mock exporters
    deps["ExporterFactory"].create_exporters.return_value = {
        "markdown": mock.MagicMock(spec=MarkdownExporter),
        "text": mock.MagicMock(spec=TextExporter),
        "json": mock.MagicMock(spec=JsonExporter),
    }
    deps["ExporterFactory"].create_exporters.return_value[
        "markdown"
    ].export.return_value = "/path/to/markdown.md"
    deps["ExporterFactory"].create_exporters.return_value[
        "text"
    ].export.return_value = "/path/to/transcript.txt"
    deps["ExporterFactory"].create_exporters.return_value[
        "json"
    ].export.return_value = "/path/to/transcript.json"

    return deps


@pytest.fixture
def patched_transcription(mock_transcription_deps):
    """Create a fixture to patch Transcription dependencies."""
    patches = []
    for name, mock_obj in mock_transcription_deps.items():
        patch = mock.patch(f"app.transcription.{name}", mock_obj)
        patches.append(patch)

    # Also patch __version__
    version_patch = mock.patch("app.transcription.__version__", "1.0.0")
    patches.append(version_patch)

    # Start all patches
    for p in patches:
        p.start()

    yield

    # Stop all patches
    for p in patches:
        p.stop()
