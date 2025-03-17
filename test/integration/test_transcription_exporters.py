import pytest
from unittest import mock

from app.transcription import Transcription
from app.exporters import MarkdownExporter, JsonExporter, TextExporter


@pytest.mark.integration
@pytest.mark.exporters
class TestTranscriptionWithExporters:
    """Tests for the integration of exporters with the Transcription class"""

    @pytest.fixture
    def transcription_with_exporters(
        self, patched_transcription, mock_transcription_deps, temp_dir
    ):
        """Create a Transcription instance with exporters for testing."""
        from app.transcription import Transcription

        # Create a Transcription instance with all export options enabled
        transcription = Transcription(
            model_output_dir=temp_dir,
            markdown=True,
            text_output=True,
            username="Test User",
            json=True,
            include_metadata=True,
        )

        return transcription

    def test_transcription_initialization(
        self, transcription_with_exporters, mock_transcription_deps
    ):
        """Test that Transcription creates exporters correctly"""
        # Check that the factory was called with the right config
        factory = mock_transcription_deps["ExporterFactory"]
        factory.create_exporters.assert_called_once()

        # Extract the config from the call
        call_args = factory.create_exporters.call_args[1]
        config = call_args["config"]

        # Verify config
        assert config["markdown"] is True
        assert config["text_output"] is True
        assert config["json"] is True
        assert "model_output_dir" in config

        # Check transcript_by was passed correctly
        assert call_args["transcript_by"] == "Test User"

    def test_write_to_markdown_file(
        self,
        transcription_with_exporters,
        mock_transcript,
        mock_transcription_deps,
    ):
        """Test that write_to_markdown_file uses the markdown exporter"""
        # Get the mock exporters
        exporters = mock_transcription_deps[
            "ExporterFactory"
        ].create_exporters.return_value
        markdown_exporter = exporters["markdown"]

        # Set up the exporter to return a specific path
        markdown_exporter.export.return_value = "/path/to/exported/markdown.md"

        # Call the method
        result = transcription_with_exporters.write_to_markdown_file(
            mock_transcript
        )

        # Check that the exporter was called with the right parameters
        markdown_exporter.export.assert_called_once()
        call_kwargs = markdown_exporter.export.call_args[1]

        assert call_kwargs["version"] == "1.0.0"
        assert call_kwargs["add_timestamp"] is False
        assert call_kwargs["include_metadata"] is True

        # Check the result
        assert result == "/path/to/exported/markdown.md"

    def test_postprocess_with_markdown(
        self, transcription_with_exporters, mock_transcript
    ):
        """Test postprocess with markdown output"""
        # Mock the write_to_markdown_file method to avoid calling the exporter directly
        transcription_with_exporters.write_to_markdown_file = mock.MagicMock()
        transcription_with_exporters.write_to_markdown_file.return_value = (
            "/path/to/exported/markdown.md"
        )

        # Call postprocess
        transcription_with_exporters.postprocess(mock_transcript)

        # Check that write_to_markdown_file was called
        transcription_with_exporters.write_to_markdown_file.assert_called_once()

        # Check that the output was stored in the transcript outputs
        assert (
            mock_transcript.outputs["markdown"]
            == "/path/to/exported/markdown.md"
        )

    def test_postprocess_with_text(
        self,
        transcription_with_exporters,
        mock_transcript,
        mock_transcription_deps,
    ):
        """Test postprocess with text output"""
        # Get the mock exporters
        exporters = mock_transcription_deps[
            "ExporterFactory"
        ].create_exporters.return_value
        text_exporter = exporters["text"]

        # Set up the exporter to return a specific path
        text_exporter.export.return_value = "/path/to/exported/transcript.txt"

        # Mock write_to_markdown_file to avoid calling it
        transcription_with_exporters.write_to_markdown_file = mock.MagicMock()
        transcription_with_exporters.write_to_markdown_file.return_value = (
            "/path/to/exported/markdown.md"
        )

        # Call postprocess
        transcription_with_exporters.postprocess(mock_transcript)

        # Check that the text exporter was called
        text_exporter.export.assert_called_once()
        assert text_exporter.export.call_args[1]["add_timestamp"] is False

        # Check that the output was stored in the transcript
        assert (
            mock_transcript.outputs["text"]
            == "/path/to/exported/transcript.txt"
        )

    def test_postprocess_with_json(
        self, transcription_with_exporters, mock_transcript, mock_transcription_deps
    ):
        """Test postprocess with JSON output"""
        # Get the mock exporters
        exporters = mock_transcription_deps[
            "ExporterFactory"
        ].create_exporters.return_value
        json_exporter = exporters["json"]

        # Set up the exporter to return a specific path
        json_exporter.export.return_value = "/path/to/exported/transcript.json"

        # Mock write_to_markdown_file to avoid calling it
        transcription_with_exporters.write_to_markdown_file = mock.MagicMock()
        transcription_with_exporters.write_to_markdown_file.return_value = (
            "/path/to/exported/markdown.md"
        )

        # Call postprocess
        transcription_with_exporters.postprocess(mock_transcript)

        # Check that the json exporter was called
        json_exporter.export.assert_called_once()

        # Check that the output was stored in the transcript
        assert (
            mock_transcript.outputs["json"]
            == "/path/to/exported/transcript.json"
        )