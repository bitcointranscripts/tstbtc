# Testing the Transcription Tool

This directory contains the comprehensive test suite for the transcription tool, built using pytest. The tests are organized by type and component to maintain a clear structure and facilitate future extensions.

## Test Structure

```
tests/
  conftest.py           # Common fixtures and setup
  
  exporters/            # Tests for exporter components
  services/             # Tests for transcription services
  ...
  
  integration/          # Integration tests (testing component interactions)

pytest.ini            # pytest configuration
```

## Running Tests

### Running All Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v
```

### Running Specific Test Categories

```bash
# Run unit tests only
pytest -m unit

# Run tests related to exporters
pytest -m exporters

# Run integration tests related to exporters
pytest -m "integration and exporters"

# Run tests in a specific file
pytest tests/exporters/test_markdown.py
```

### Running With Coverage Reports

```bash
# Run with terminal coverage report
pytest --cov=app

# Run with HTML coverage report
pytest --cov=app --cov-report=html
```

## Test Categories

The test suite uses markers to categorize tests:

- **unit**: Tests for individual components in isolation
- **integration**: Tests for interactions between components
- **cli**: Tests for command-line interfaces
- **functional**: End-to-end tests of complete workflows
- **exporters**: Tests related to the exporter architecture
- **services**: Tests related to transcription services
- **slow**: Tests that are slow to run

## Fixtures

Common fixtures are defined in `conftest.py` files at different levels:

- **Root level**: Common fixtures used across all tests
- **Category level**: Fixtures specific to a category (e.g., unit tests)
- **Module level**: Fixtures specific to a module (e.g., exporter tests)

Key fixtures include:

- `temp_dir`: Creates a temporary directory for test files
- `mock_transcript`: Creates a mock transcript for testing
- `markdown_exporter`, `json_exporter`, `text_exporter`: Create exporter instances
- `patched_transcription`: Sets up mocks for Transcription dependencies
- `cli_runner`: Sets up a Click CLI test runner

## Adding New Tests

### For Adding Tests to Existing Components

1. Find the appropriate test file or create a new one in the correct directory
2. Use existing fixtures where possible
3. Add the appropriate markers for test categorization

Example:
```python
@pytest.mark.unit
@pytest.mark.exporters
def test_new_exporter_feature(exporter_fixture):
    # Test implementation
```

### For Adding Tests for New Components

1. Create a new test file in the appropriate directory
2. Add any necessary fixtures to the nearest `conftest.py`
3. Add appropriate markers to categorize the tests

## Best Practices

- Keep tests independent of each other
- Write focused tests that test one thing each
- Use descriptive test names
- Use fixtures for common setup and teardown
- Mock external dependencies
- Test both success and error scenarios

## Troubleshooting

If you encounter issues with tests:

1. Run specific failing tests with `-v` for more details
2. Use `print()` statements for debugging (output is shown for failing tests)
3. Ensure fixtures are creating the expected objects
4. Check that mocks are correctly configured