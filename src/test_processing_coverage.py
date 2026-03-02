# pylint: skip-file

import sys
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

from process_van import csv_post_process
from process_van import main
from process_van import post_process
from process_van import read_csv_portfolio
from process_van import write_results


def test_read_csv_portfolio_reorders_columns(tmp_path):
    csv_path = tmp_path / "portfolio.csv"
    pd.DataFrame(
        {
            "Account Name": ["Acct A"],
            "Fund Name": ["Fund A"],
            "Symbol": ["AAA"],
            "Value": [100.0],
            "% of Portfolio": ["10.00%"],
            "Ignored": ["x"],
        }
    ).to_csv(csv_path, index=False)

    actual = read_csv_portfolio(str(csv_path))

    assert actual.columns.tolist() == [
        "Fund Name",
        "Account Name",
        "Symbol",
        "Value",
        "% of Portfolio",
    ]
    assert actual.iloc[0]["Fund Name"] == "Fund A"


def test_read_csv_portfolio_missing_required_columns_raises_value_error(tmp_path):
    csv_path = tmp_path / "bad-portfolio.csv"
    pd.DataFrame(
        {
            "Account Name": ["Acct A"],
            "Fund Name": ["Fund A"],
            "Symbol": ["AAA"],
            "Value": [100.0],
        }
    ).to_csv(csv_path, index=False)

    with pytest.raises(ValueError):
        read_csv_portfolio(str(csv_path))


def test_csv_post_process_normalizes_rows_and_drops_nan_values():
    input_df = pd.DataFrame(
        {
            "Account Name": [
                "U.S. stocks & stock funds",
                "Acct 1",
                None,
                "International stocks & stock funds",
            ],
            "Fund Name": [None, "Fund A", None, None],
            "Symbol": [None, "AAA", "Subtotal:", None],
            "Value": [None, 100.0, 100.0, None],
            "% of Portfolio": [None, "10.00%", "10.00%", None],
        }
    )

    output_df = csv_post_process(input_df)

    assert output_df.columns.tolist() == [
        "Class",
        "Account",
        "Name",
        "Symbol",
        "Value",
        "% of Portfolio",
    ]
    assert output_df["Value"].isna().sum() == 0
    assert output_df["Class"].tolist() == [
        "U.S. stocks & stock funds",
        "U.S. stocks & stock funds",
    ]


def test_post_process_applies_fixed_class_and_asset_overrides():
    vadf = pd.DataFrame(
        {
            "Class": [
                "U.S. bonds & bond funds",
                "U.S. stocks & stock funds",
                "U.S. stocks & stock funds",
                "Other asset types",
            ],
            "Name": [
                "UNITED STATES TREAS 07/10/2027",
                "Stock Fund",
                "Asset Override",
                "Subtotal Row",
            ],
            "Symbol": ["UST", "S1", "S2", "Subtotal:"],
            "Value": [100.0, 200.0, 300.0, 600.0],
            "Account": ["A", "B", "C", "D"],
            "% of Portfolio": ["1%", "2%", "3%", "6%"],
        }
    )
    cmdf = pd.DataFrame(
        {
            "Class": [
                "U.S. bonds & bond funds",
                "U.S. stocks & stock funds",
            ],
            "ClassMap": ["U.S. bonds", "U.S. stocks"],
            "Order": ["1", "2"],
        }
    )
    amdf = pd.DataFrame({"Name": ["Asset Override"], "Class": ["Custom"], "%": [1.0]})

    post_process(vadf, cmdf, amdf, fixed=True, quiet=True)

    assert vadf.loc[0, "Class"] == "Fixed"
    assert vadf.loc[1, "Class"] == "U.S. stocks"
    assert vadf.loc[2, "Class"] == "Custom"
    assert pd.isna(vadf.loc[3, "Class"])


def test_write_results_outputs_candidates_report_and_sorted_alloc(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    vadf = pd.DataFrame(
        {
            "Class": [
                "U.S. stocks",
                "Cash",
                "U.S. stocks",
                "Intl stocks",
                "Other asset types",
                "U.S. stocks",
            ],
            "Name": [
                "Stock A",
                "Cash A",
                "Stock B",
                "Intl A",
                "Needs Mapping",
                "Name",
            ],
            "Account": ["A", "B", "C", "D", "E", "F"],
            "Symbol": ["A", "C", "B", "I", "O", "Header"],
            "Value": [20.0, 10.0, 30.0, 15.0, 5.0, 0.0],
            "% of Portfolio": ["20%", "10%", "30%", "15%", "5%", "0%"],
        }
    )
    vadf.loc[len(vadf)] = ["U.S. stocks", "Subtotal row", "Z", "Subtotal:", 50.0, "50%"]
    cmdf = pd.DataFrame(
        {
            "Class": ["Cash", "Intl stocks", "U.S. stocks", "Other asset types"],
            "ClassMap": ["Cash", "Intl stocks", "U.S. stocks", "Other asset types"],
            "Order": ["0", "1", "2", "3"],
        }
    )

    write_results(vadf, cmdf, quiet=True, date_on=False)

    candidates_path = tmp_path / "Asset-Map-Candidates.csv"
    report_path = tmp_path / "out" / "Van-Alloc-Rep.csv"
    alloc_path = tmp_path / "out" / "Van-Alloc.csv"

    assert candidates_path.exists()
    assert report_path.exists()
    assert alloc_path.exists()

    candidates_df = pd.read_csv(candidates_path, encoding="utf-8-sig")
    report_df = pd.read_csv(report_path, encoding="utf-8-sig")
    alloc_df = pd.read_csv(alloc_path, encoding="utf-8-sig")

    assert candidates_df["Name"].tolist() == ["Needs Mapping"]
    assert "Subtotal:" in report_df["Symbol"].tolist()
    assert "Subtotal:" not in alloc_df["Symbol"].tolist()
    assert alloc_df["Class"].tolist() == [
        "Cash",
        "Intl stocks",
        "U.S. stocks",
        "U.S. stocks",
        "Other asset types",
    ]
    assert (
        alloc_df.loc[alloc_df["Class"] == "U.S. stocks", "Name"].tolist()
        == ["Stock A", "Stock B"]
    )


def test_hogwarts_subset_rows_are_present_in_full_pipeline_output(tmp_path, monkeypatch):
    repo_root = Path(__file__).resolve().parents[1]
    input_csv = repo_root / "hogwarts_test" / "Hogwarts-DataExport.csv"
    class_map = repo_root / "Class-Map.csv"
    expected_csv = repo_root / "hogwarts_test" / "Hogwarts-Van-Alloc.csv"

    monkeypatch.chdir(tmp_path)
    with patch.object(
        sys,
        "argv",
        [
            "process_van.py",
            "-q",
            "-f",
            "--no-date",
            "--csv-path",
            str(input_csv),
            "--class_map",
            str(class_map),
            "--working-dir",
            str(tmp_path),
        ],
    ):
        main()

    actual = pd.read_csv(tmp_path / "out" / "Van-Alloc.csv", encoding="utf-8-sig")
    expected = pd.read_csv(expected_csv)

    expected_subset = expected.iloc[:6][["Class", "Name", "Account", "Symbol"]]
    for row in expected_subset.itertuples(index=False):
        matches = (
            (actual["Class"] == row.Class)
            & (actual["Name"] == row.Name)
            & (actual["Account"] == row.Account)
            & (actual["Symbol"] == row.Symbol)
        )
        assert matches.any()
