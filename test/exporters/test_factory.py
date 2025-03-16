import pytest

from app.exporters import (
    ExporterFactory,
    MarkdownExporter,
    JsonExporter,
    TextExporter,
)


@pytest.mark.unit
@pytest.mark.exporters
class TestExporterFactory:
    """Tests for the ExporterFactory class"""

    def test_create_all_exporters(self, temp_dir):
        """Test creating all available exporters"""
        # Define configuration with all exporters enabled
        config = {
            "markdown": True,
            "text_output": True,
            "noqueue": True,
            "model_output_dir": temp_dir,
        }

        # Create exporters
        exporters = ExporterFactory.create_exporters(
            config=config, transcript_by="Test User"
        )

        # Check all requested exporters were created
        assert "markdown" in exporters
        assert "text" in exporters
        assert "json" in exporters

        # Check exporters are of the right types
        assert isinstance(exporters["markdown"], MarkdownExporter)
        assert isinstance(exporters["text"], TextExporter)
        assert isinstance(exporters["json"], JsonExporter)

        # Check that transcript_by was passed correctly
        assert exporters["markdown"].transcript_by == "Test User"
        assert exporters["json"].transcript_by == "Test User"

        # Check that output directories were set correctly
        assert exporters["markdown"].output_dir == temp_dir
        assert exporters["text"].output_dir == temp_dir
        assert exporters["json"].output_dir == temp_dir

    def test_create_partial_exporters(self, temp_dir):
        """Test creating a subset of exporters"""
        # Define configuration with only markdown exporter enabled
        config = {
            "markdown": True,
            "text_output": False,
            "noqueue": False,
            "model_output_dir": temp_dir,
        }

        # Create exporters
        exporters = ExporterFactory.create_exporters(
            config=config, transcript_by="Test User"
        )

        # Check only markdown exporter was created
        assert "markdown" in exporters
        assert "text" not in exporters
        assert "json" not in exporters

        # Check the exporter is of the right type
        assert isinstance(exporters["markdown"], MarkdownExporter)

    def test_no_exporters(self, temp_dir):
        """Test creating no exporters when all are disabled"""
        # Define configuration with no exporters enabled
        config = {
            "markdown": False,
            "text_output": False,
            "noqueue": False,
            "model_output_dir": temp_dir,
        }

        # Create exporters
        exporters = ExporterFactory.create_exporters(
            config=config, transcript_by="Test User"
        )

        # Check that no exporters were created
        assert not exporters
        assert isinstance(exporters, dict)

    def test_custom_output_dir(self):
        """Test creating exporters with custom output directory"""
        # Define configuration with custom output directory
        custom_dir = "/custom/output/dir"
        config = {
            "markdown": True,
            "text_output": True,
            "noqueue": True,
            "model_output_dir": custom_dir,
        }

        # Create exporters
        exporters = ExporterFactory.create_exporters(
            config=config, transcript_by="Test User"
        )

        # Check that all exporters use the custom output directory
        assert exporters["markdown"].output_dir == custom_dir
        assert exporters["text"].output_dir == custom_dir
        assert exporters["json"].output_dir == custom_dir

    def test_transcript_by_none(self, temp_dir):
        """Test creating exporters with transcript_by=None"""
        # Define configuration
        config = {
            "markdown": True,
            "text_output": True,
            "noqueue": True,
            "model_output_dir": temp_dir,
        }

        # Create exporters without transcript_by
        exporters = ExporterFactory.create_exporters(
            config=config, transcript_by=None
        )

        # Check that transcript_by is None for relevant exporters
        assert exporters["markdown"].transcript_by is None
        assert exporters["json"].transcript_by is None
