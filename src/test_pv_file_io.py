# pylint: skip-file

from unittest.mock import patch
import pandas as pd
import pytest

import process_van
#from ..src import process_van
#from process_van.src.process_van import read_asset_map


@pytest.fixture(name="asset_map_path")
def fixture_asset_map_path():
    return "path/to/asset_map.csv"


def test_read_asset_map_with_valid_file(asset_map_path):
    # Arrange
    expected_columns = ["Name", "Class", "%"]
    expected_df = pd.DataFrame(
        [["Asset1", "Class1", "100%"], ["Asset2", "Class2", "50%"]],
        columns=expected_columns,
    )
    with patch("pandas.read_csv") as mock_read_csv:
        mock_read_csv.return_value = expected_df

        # Act
        result_df = read_asset_map(asset_map_path)

        # Assert
        assert result_df.columns.tolist() == expected_columns
        assert result_df.equals(expected_df)


def test_read_asset_map_with_invalid_columns(asset_map_path):
    # Arrange
    invalid_columns_df = pd.DataFrame(
        [["Asset1", "Class1", "100%"], ["Asset2", "Class2", "50%"]],
        columns=["Invalid", "Class", "%"],
    )
    with patch("pandas.read_csv") as mock_read_csv:
        mock_read_csv.return_value = invalid_columns_df

        # Act & Assert
        with pytest.raises(KeyError) as excinfo:
            read_asset_map(asset_map_path, quiet=True)
        assert str(excinfo.value) == "\"['Name'] not in index\""


def test_read_asset_map_with_file_not_found(asset_map_path):
    # Arrange
    expected_columns = ["Name", "Class", "%"]

    with patch("pandas.read_csv") as mock_read_csv:
        mock_read_csv.side_effect = FileNotFoundError

        # Act
        result_df = read_asset_map(asset_map_path, quiet=True)

        # Assert
        assert result_df.columns.tolist() == expected_columns
        assert result_df.empty
