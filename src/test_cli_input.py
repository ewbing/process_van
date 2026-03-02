# pylint: skip-file

import sys
from unittest.mock import patch
import os

from datetime import datetime
from pathlib import Path

import pandas as pd
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

    expected = os.path.abspath(
        os.path.join(
            os.path.expanduser(constants.DEFAULT_WORKING_DIRECTORY),
            constants.DEFAULT_DOWNLOADS_DIRECTORY,
            constants.DEFAULT_CSV_FILE,
        )
    )
    assert mock_validate.call_args.args[0] == expected
    assert mock_read.call_args.args[0] == expected


def test_explicit_path_handling():
    explicit_path = "/tmp/portfolio.csv"
    mock_validate, mock_read = run_main_for_path_resolution(
        ["process_van.py", "-q", "--csv-path", explicit_path]
    )

    assert mock_validate.call_args.args[0] == explicit_path
    assert mock_read.call_args.args[0] == explicit_path


def test_positional_fallback_path_handling():
    positional_path = "/tmp/legacy-positional.csv"
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


def write_minimal_portfolio_csv(csv_path: Path):
    pd.DataFrame(
        {
            "Account Name": ["U.S. stocks & stock funds", "Test Account", None],
            "Fund Name": [None, "TEST FUND", None],
            "Symbol": [None, "TST", "Subtotal:"],
            "Value": [None, 100.0, 100.0],
            "% of Portfolio": [None, "10.00%", "10.00%"],
        }
    ).to_csv(csv_path, index=False)


def write_minimal_class_map(csv_path: Path):
    pd.DataFrame(
        {
            "Class": ["U.S. stocks & stock funds", "U.S. stocks"],
            "ClassMap": ["U.S. stocks", "U.S. stocks"],
            "Order": ["1", "1"],
        }
    ).to_csv(csv_path, index=False)


def write_minimal_asset_map(csv_path: Path):
    pd.DataFrame(
        {
            "Name": ["TEST FUND"],
            "Class": ["U.S. stocks"],
            "%": [1.0],
        }
    ).to_csv(csv_path, index=False)


def test_cli_help_flag_prints_usage_and_exits_cleanly(capsys):
    with patch.object(sys, "argv", ["process_van.py", "-h"]):
        with pytest.raises(SystemExit) as exc_info:
            main()

    captured = capsys.readouterr()
    assert exc_info.value.code == 0
    assert "usage:" in captured.out
    assert "--working-dir" in captured.out
    assert "--csv-path" in captured.out


def test_cli_missing_input_file_raises_file_not_found(tmp_path):
    missing_path = tmp_path / "not-there.csv"

    with patch.object(
        sys, "argv", ["process_van.py", "-q", "--csv-path", str(missing_path)]
    ):
        with pytest.raises(FileNotFoundError):
            main()


def test_cli_invalid_class_map_schema_raises_value_error(tmp_path, monkeypatch):
    portfolio_path = tmp_path / "portfolio.csv"
    class_map_path = tmp_path / "bad-class-map.csv"
    monkeypatch.chdir(tmp_path)

    write_minimal_portfolio_csv(portfolio_path)
    pd.DataFrame({"Class": ["x"], "ClassMap": ["y"]}).to_csv(class_map_path, index=False)

    with patch.object(
        sys,
        "argv",
        [
            "process_van.py",
            "-q",
            "--csv-path",
            str(portfolio_path),
            "--class_map",
            str(class_map_path),
        ],
    ):
        with pytest.raises(ValueError) as exc_info:
            main()
    message = str(exc_info.value)
    assert "Class map CSV" in message
    assert "Missing: ['Order']" in message


def test_cli_invalid_portfolio_schema_raises_value_error(tmp_path, monkeypatch):
    portfolio_path = tmp_path / "bad-portfolio.csv"
    monkeypatch.chdir(tmp_path)

    pd.DataFrame(
        {
            "Account Name": ["Acct A"],
            "Fund Name": ["Fund A"],
            "Symbol": ["AAA"],
            "Value": [100.0],
        }
    ).to_csv(portfolio_path, index=False)

    with patch.object(
        sys,
        "argv",
        [
            "process_van.py",
            "-q",
            "--csv-path",
            str(portfolio_path),
            "--working-dir",
            str(tmp_path),
        ],
    ):
        with pytest.raises(ValueError) as exc_info:
            main()
    message = str(exc_info.value)
    assert "Portfolio CSV" in message
    assert "Missing: ['% of Portfolio']" in message


def test_cli_invalid_asset_map_schema_raises_value_error(tmp_path, monkeypatch):
    portfolio_path = tmp_path / "portfolio.csv"
    class_map_path = tmp_path / "class-map.csv"
    asset_map_path = tmp_path / "bad-asset-map.csv"
    monkeypatch.chdir(tmp_path)

    write_minimal_portfolio_csv(portfolio_path)
    write_minimal_class_map(class_map_path)
    pd.DataFrame({"Class": ["x"], "%": [1.0]}).to_csv(asset_map_path, index=False)

    with patch.object(
        sys,
        "argv",
        [
            "process_van.py",
            "-q",
            "--csv-path",
            str(portfolio_path),
            "--class_map",
            str(class_map_path),
            "--asset_map",
            str(asset_map_path),
        ],
    ):
        with pytest.raises(ValueError) as exc_info:
            main()
    message = str(exc_info.value)
    assert "Asset map CSV" in message
    assert "Missing: ['Name']" in message


def test_cli_no_date_option_writes_non_suffixed_output_files(tmp_path, monkeypatch):
    portfolio_path = tmp_path / "portfolio.csv"
    class_map_path = tmp_path / "class-map.csv"
    asset_map_path = tmp_path / "asset-map.csv"
    monkeypatch.chdir(tmp_path)

    write_minimal_portfolio_csv(portfolio_path)
    write_minimal_class_map(class_map_path)
    write_minimal_asset_map(asset_map_path)

    with patch.object(
        sys,
        "argv",
        [
            "process_van.py",
            "-q",
            "--csv-path",
            str(portfolio_path),
            "--class_map",
            str(class_map_path),
            "--asset_map",
            str(asset_map_path),
            "--no-date",
            "--working-dir",
            str(tmp_path),
        ],
    ):
        main()

    assert (tmp_path / "out" / "Van-Alloc.csv").exists()
    assert (tmp_path / "out" / "Van-Alloc-Rep.csv").exists()
    assert list((tmp_path / "out").glob("Van-Alloc-[0-9]*.csv")) == []


def test_cli_custom_date_format_writes_formatted_suffix(tmp_path, monkeypatch):
    portfolio_path = tmp_path / "portfolio.csv"
    class_map_path = tmp_path / "class-map.csv"
    asset_map_path = tmp_path / "asset-map.csv"
    monkeypatch.chdir(tmp_path)

    write_minimal_portfolio_csv(portfolio_path)
    write_minimal_class_map(class_map_path)
    write_minimal_asset_map(asset_map_path)

    with patch("process_van.datetime") as mock_datetime:
        mock_datetime.now.return_value = datetime(2026, 1, 15)
        with patch.object(
            sys,
            "argv",
            [
                "process_van.py",
                "-q",
                "--csv-path",
                str(portfolio_path),
                "--class_map",
                str(class_map_path),
                "--asset_map",
                str(asset_map_path),
                "--date-format",
                "%Y%m%d",
                "--working-dir",
                str(tmp_path),
            ],
        ):
            main()

    assert (tmp_path / "out" / "Van-Alloc-20260115.csv").exists()
    assert (tmp_path / "out" / "Van-Alloc-Rep-20260115.csv").exists()
