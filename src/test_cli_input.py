# pylint: skip-file

import sys
from unittest.mock import patch

import pytest

import constants
from process_van import main
from process_van import validate_input_csv_path


class StopMain(Exception):
    """Used to short-circuit main() after argument/path resolution in tests."""


def run_main_for_path_resolution(argv):
    with patch.object(sys, "argv", argv):
        with patch("process_van.validate_input_csv_path") as mock_validate:
            with patch("process_van.read_csv_portfolio", side_effect=StopMain) as mock_read:
                with pytest.raises(StopMain):
                    main()
    return mock_validate, mock_read


def test_default_path_behavior():
    mock_validate, mock_read = run_main_for_path_resolution(["process_van.py", "-q"])

    expected = f"data/{constants.DEFAULT_CSV_FILE}"
    assert mock_validate.call_args.args[0] == expected
    assert mock_read.call_args.args[0] == expected


def test_explicit_path_handling():
    explicit_path = "tmp/portfolio.csv"
    mock_validate, mock_read = run_main_for_path_resolution(
        ["process_van.py", "-q", "--csv-path", explicit_path]
    )

    assert mock_validate.call_args.args[0] == explicit_path
    assert mock_read.call_args.args[0] == explicit_path


def test_positional_fallback_path_handling():
    positional_path = "tmp/legacy-positional.csv"
    mock_validate, mock_read = run_main_for_path_resolution(
        ["process_van.py", "-q", positional_path]
    )

    assert mock_validate.call_args.args[0] == positional_path
    assert mock_read.call_args.args[0] == positional_path


def test_validate_input_path_has_clear_hint(tmp_path):
    missing_path = tmp_path / "missing.csv"

    with pytest.raises(FileNotFoundError) as exc_info:
        validate_input_csv_path(str(missing_path))

    message = str(exc_info.value)
    assert f'Input CSV file not found at "{missing_path}"' in message
    assert constants.DEFAULT_CSV_FILE in message
    assert "--csv-path" in message
