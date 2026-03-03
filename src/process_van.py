#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Process Vanguard reports into consistent rows and add classifications.
copyright (c) 2026, Eric Bing
All rights reserved."""

import sys
import os
from datetime import datetime
import argparse
import re
import warnings
import pandas as pd
import numpy as np

import constants


def ensure_dataframe_columns(
    df: pd.DataFrame,
    required_columns: list[str],
    *,
    data_name: str,
) -> None:
    """
    Ensure a DataFrame contains required columns before downstream processing.
    """
    actual_columns = list(df.columns)
    missing_columns = sorted(set(required_columns) - set(actual_columns))
    if missing_columns:
        raise ValueError(
            f"{data_name} is missing required columns: {missing_columns}. "
            f"Found: {actual_columns}."
        )


def validate_csv_schema(
    df: pd.DataFrame,
    expected_columns: list[str],
    *,
    schema_name: str,
    csv_path: str,
) -> pd.DataFrame:
    """
    Validate CSV schema against an expected ordered column list.

    Raises ValueError for missing required columns.
    Warns for extra columns and returns a DataFrame subset in expected column order.
    """
    actual_columns = list(df.columns)
    expected_set = set(expected_columns)
    actual_set = set(actual_columns)
    missing_columns = sorted(expected_set - actual_set)
    extra_columns = sorted(actual_set - expected_set)

    if missing_columns:
        raise ValueError(
            f"{schema_name} CSV at {csv_path} has invalid columns. "
            f"Expected: {expected_columns}. "
            f"Found: {actual_columns}. "
            f"Missing: {missing_columns}."
        )

    if extra_columns:
        warnings.warn(
            (
                f"{schema_name} CSV at {csv_path} has extra columns that will be ignored. "
                f"Extra: {extra_columns}."
            ),
            UserWarning,
            stacklevel=2,
        )

    return df[expected_columns]


def resolve_working_directory_path(working_directory: str) -> str:
    """
    Resolve a working directory path by expanding '~' and normalizing to an absolute path.
    """
    return os.path.abspath(os.path.expanduser(working_directory))


def resolve_path_with_working_directory(path_value: str, working_directory: str) -> str:
    """
    Resolve a user-provided path against working_directory when it is relative.
    """
    expanded = os.path.expanduser(path_value)
    if os.path.isabs(expanded):
        return os.path.abspath(expanded)
    return os.path.abspath(os.path.join(working_directory, expanded))


def resolve_input_csv_path(
    csv_path: str | None,
    csv_path_positional: str | None,
    working_directory: str,
) -> str:
    """
    Resolve the portfolio CSV input path from explicit and positional CLI arguments.

    Precedence:
        1) --csv-path
        2) positional fallback
        3) default <working_directory>/downloads/PortfolioWatchData.csv
    """
    if csv_path:
        return resolve_path_with_working_directory(csv_path, working_directory)
    if csv_path_positional:
        return resolve_path_with_working_directory(
            csv_path_positional, working_directory
        )
    return os.path.join(
        working_directory, constants.DEFAULT_DOWNLOADS_DIRECTORY, constants.DEFAULT_CSV_FILE
    )


def validate_input_csv_path(csv_path: str) -> None:
    """
    Validate that the input CSV path exists before running the processing pipeline.
    """
    if not os.path.isfile(csv_path):
        expected_name = constants.DEFAULT_CSV_FILE
        expected_dir = os.path.abspath(os.path.dirname(csv_path) or ".")
        raise FileNotFoundError(
            f'Input CSV file not found at "{csv_path}". '
            f'Expected a Vanguard export named "{expected_name}" in "{expected_dir}", '
            f'or pass --csv-path /path/to/{expected_name}.'
        )


def load_inputs(
    csv_path: str,
    class_map_path: str,
    asset_map_path: str,
    *,
    quiet: bool = False,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Load all input dataframes used in the processing pipeline.
    """
    portfolio_df = read_csv_portfolio(csv_path)
    class_map_df = read_class_map(class_map_path, quiet)
    asset_map_df = read_asset_map(asset_map_path, quiet)
    return portfolio_df, class_map_df, asset_map_df


def normalize_portfolio_rows(portfolio_df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize portfolio rows from raw CSV shape into processing shape.
    """
    return csv_post_process(portfolio_df.copy())


def apply_class_mappings(
    normalized_df: pd.DataFrame,
    class_map_df: pd.DataFrame,
    asset_map_df: pd.DataFrame,
    fixed: bool,
    quiet: bool = False,
) -> pd.DataFrame:
    """
    Apply fixed-income, class-level, and asset-level mapping transforms.
    Returns a new dataframe and does not mutate inputs.
    """
    ensure_dataframe_columns(
        normalized_df,
        ["Class", "Name", "Symbol"],
        data_name="Portfolio post-process data",
    )
    ensure_dataframe_columns(
        class_map_df,
        ["Class", "ClassMap"],
        data_name="Class map data",
    )
    ensure_dataframe_columns(
        asset_map_df,
        ["Name", "Class"],
        data_name="Asset map data",
    )

    mapped_df = normalized_df.copy()

    # Null out Class for Subtotals & Totals - not needed?
    subtotal_or_total = (mapped_df.Symbol == "Subtotal:") | (mapped_df.Symbol == "Total:")
    mapped_df.loc[mapped_df[subtotal_or_total].index, "Class"] = np.nan

    if fixed:
        if not quiet:
            print("Fixed mode")
        mapped_df["Name"] = mapped_df["Name"].fillna("None")
        fixed_regex = re.compile(r"(UNITED STATES TREAS|CPN|NTS)")
        mapped_df["Class"] = mapped_df.apply(
            lambda row: "Fixed" if fixed_regex.search(row.Name) else row.Class,
            axis=1,
        )

    mapped_df.loc[mapped_df["Class"].isin(class_map_df.Class), "Class"] = mapped_df[
        "Class"
    ].map(dict(zip(class_map_df.Class, class_map_df.ClassMap)))

    mapped_df.loc[mapped_df["Name"].isin(asset_map_df.Name), "Class"] = mapped_df[
        "Name"
    ].map(dict(zip(asset_map_df.Name, asset_map_df.Class)))
    return mapped_df


def main():
    """
    This program processes Vanguard allocation reports into consistent rows and adds
    classifications. Primary input is from the Vanguard portfolio watch detail page.
    The CSV export (default -PortfolioWatchData.csv) is preferred because of its stability.

    Args:
        None

    Returns:
        None
    """
    parser = argparse.ArgumentParser(
        description="Process Vanguard reports into consistent rows and add classifications"
    )
    parser.add_argument(
        "-q", "--quiet", help="quiet mode - no warnings or status", action="store_true"
    )
    parser.add_argument(
        "-f", "--fixed", help="Group CDs and Treasuries in Fixed", action="store_true"
    )
    parser.add_argument(
        "-wd",
        "--working-dir",
        dest="working_dir",
        default=constants.DEFAULT_WORKING_DIRECTORY,
        help=(
            "base working directory for defaults "
            f"(default {constants.DEFAULT_WORKING_DIRECTORY})"
        ),
    )
    parser.add_argument(
        "--csv-path",
        dest="csv_path",
        default=None,
        help=(
            "input export csv file from Vanguard assets "
            f"(default <working-dir>/{constants.DEFAULT_DOWNLOADS_DIRECTORY}/"
            f"{constants.DEFAULT_CSV_FILE})"
        ),
    )
    parser.add_argument(
        "csv_path_positional",
        nargs="?",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "-am",
        "--asset_map",
        help="mapping file for assets (default <working-dir>/Asset-Map.csv)",
        default=None,
    )
    parser.add_argument(
        "-cm",
        "--class_map",
        help="mapping file for classes (default <working-dir>/Class-Map.csv)",
        default=None,
    )
    parser.add_argument(
        "--no-date",
        dest="date_suffix",
        action="store_false",
        default=True,
        help="Do NOT append an ISO date (-YYYY-MM-DD) to output filenames (default: append date)",
    )
    parser.add_argument(
        "--date-format",
        dest="date_format",
        default="%Y-%m-%d",
        help="strftime format for the date suffix (default: %%Y-%%m-%%d). "
             "Do not include a leading '-' (it's added automatically).",
    )
    args = parser.parse_args()

    if not args.quiet:
        print(f"Arguments of the script : {sys.argv[1:]=}")

    if not args.quiet:
        print("Process Vanguard Allocations - v1.1 by Eric Bing")

    if not args.quiet:
        print("CSV mode")

    working_directory = resolve_working_directory_path(args.working_dir)
    resolved_csv_path = resolve_input_csv_path(
        args.csv_path, args.csv_path_positional, working_directory
    )
    resolved_class_map_path = resolve_path_with_working_directory(
        args.class_map or constants.DEFAULT_CLASS_MAP_FILE, working_directory
    )
    resolved_asset_map_path = resolve_path_with_working_directory(
        args.asset_map or constants.DEFAULT_ASSET_MAP_FILE, working_directory
    )
    validate_input_csv_path(resolved_csv_path)

    portfolio_df, class_map_df, asset_map_df = load_inputs(
        resolved_csv_path,
        resolved_class_map_path,
        resolved_asset_map_path,
        quiet=args.quiet,
    )
    normalized_df = normalize_portfolio_rows(portfolio_df)
    processed_df = apply_class_mappings(
        normalized_df,
        class_map_df,
        asset_map_df,
        args.fixed,
        args.quiet,
    )
    write_results(
        processed_df,
        class_map_df,
        quiet=args.quiet,
        date_on=args.date_suffix,
        date_format=args.date_format,
        working_directory=working_directory,
    )

def read_asset_map(asset_map_path: str, quiet: bool = False) -> pd.DataFrame:
    """
    A function that reads an asset map from a CSV file and returns it as a pandas DataFrame.
    Bring in (optional) Asset Map - provides / overrides mapping for specific assets to classes.

    Args:
        asset_map (str): The file path to the asset map CSV file.
        quiet (bool, optional): A flag to suppress printing messages. Defaults to False.

    Returns:
        pd.DataFrame: A DataFrame containing the asset map data
        with columns 'Name', 'Class', and '%'.
    """
    expected_columns = ["Name", "Class", "%"]
    try:
        asset_map_df = validate_csv_schema(
            pd.read_csv(asset_map_path),
            expected_columns,
            schema_name="Asset map",
            csv_path=asset_map_path,
        )
        if not quiet:
            print(f"Read Asset map from {asset_map_path}")
    except FileNotFoundError:
        # Always print this message, regardless of the quiet flag
        print(
            f"Asset Map not found at {asset_map_path} - no additional asset mapping will be done"
        )
        asset_map_df = pd.DataFrame(columns=expected_columns)
    return asset_map_df


def read_class_map(class_map_path: str, quiet: bool = False) -> pd.DataFrame:
    """
    Read a class map from a given path and return it as a pandas DataFrame.

    Bring in (semi-optional) Class Map - provides / overrides mapping for specific classes.
    Provides the ordering that the Asset Classifications come in (for reports).
    Also provides the mapping to new classifications (ClassMap column) where they can be mapped
    at a classification level as well as the target ordering of Asset Classifications.

    Args:
        class_map_path (str): The file path to the class map CSV file.
        quiet (bool, optional): A flag to suppress printing messages. Defaults to False.

    Returns:
        pd.DataFrame: A DataFrame containing the class map data with columns
        'Class', 'ClassMap', and 'Order'.
    """
    expected_columns = ["Class", "ClassMap", "Order"]
    try:
        class_map = validate_csv_schema(
            pd.read_csv(class_map_path),
            expected_columns,
            schema_name="Class map",
            csv_path=class_map_path,
        )

        if not quiet:
            print(f"Read Class map from {class_map_path}")
    except FileNotFoundError:
        print(
            f"Class Map not found at {class_map_path} - falling over to hardcoded Asset Classes"
            f" for CSV mapping."
        )
        class_map = pd.DataFrame(
            {
                "Class": pd.Series(
                    [
                        "U.S. stocks & stock funds",
                        "International stocks & stock funds",
                        "Other stocks",
                        "U.S. bonds & bond funds",
                        "International bonds & bond funds",
                        "Other bonds",
                        "Short term reserves",
                        "Other asset types",
                    ]
                ),
                "ClassMap": pd.Series(
                    [
                        "U.S. stocks",
                        "Intl stocks",
                        "Other stocks",
                        "U.S. bonds",
                        "Intl bonds",
                        "Other bonds",
                        "Cash",
                        "Other asset types",
                    ]
                ),
                "Order": pd.Series(
                    [
                        "3",
                        "4",
                        "6",
                        "1",
                        "2",
                        "5",
                        "0",
                        "7",
                    ]
                ),
            }
        )

    return class_map


def read_csv_portfolio(csv_path: str) -> pd.DataFrame:
    """
    Read a CSV file with a specific set of columns, returning a pandas DataFrame.

    Args:
        csv_path (str): The path to the CSV file.

    Returns:
        pandas.DataFrame: The DataFrame containing the data from the CSV file.

    Raises:
        FileNotFoundError: If the CSV file is not found at the specified path.
        ValueError: If the CSV file has incorrect columns.
    """
    columns_in = ["Account Name", "Fund Name", "Symbol", "Value", "% of Portfolio"]
    columns_out = ["Fund Name", "Account Name", "Symbol", "Value", "% of Portfolio"]
    if not set(columns_out).issubset(set(columns_in)):
        raise RuntimeError(
            "Internal column config mismatch: columns_out must be a subset of columns_in. "
            f"columns_in={columns_in}, columns_out={columns_out}"
        )
    try:
        # Read and validate schema before reordering output columns.
        with open(csv_path, "r", encoding="utf-8-sig") as file:
            portfolio_data = validate_csv_schema(
                pd.read_csv(file),
                columns_in,
                schema_name="Portfolio",
                csv_path=csv_path,
            )
            return portfolio_data[columns_out]
    except FileNotFoundError:
        # Raise a FileNotFoundError if the CSV file is not found at the specified path
        raise FileNotFoundError(
            f'Vanguard Portfolio CSV file not found at "{csv_path}"'
        ) from None


def csv_post_process(vadf) -> pd.DataFrame:
    """
    Performs post-processing on the DataFrame `vadf` by inserting a 'Class' column based on
    the 'Value' column.  If 'Name' is null, assigns 'Account' to 'Class', propagates 'Class'
    down, and removes rows with NaN in 'Value'.  Returns the post-processed DataFrame.

    Parameters:
    vadf (pandas.DataFrame): The DataFrame to be post-processed.

    Returns:
    pandas.DataFrame: The post-processed DataFrame with 'Class' column added and NaN values handled.
    """
    ensure_dataframe_columns(
        vadf,
        ["Account Name", "Fund Name", "Symbol", "Value", "% of Portfolio"],
        data_name="Portfolio data",
    )

    # vadf.insert(0, "Class", np.where(vadf.Value == "Value", "Class", None))
    vadf.insert(0, "Class", vadf.Value.where(vadf.Value == "Value", None))
    # Force object dtype so later string assignments do not fail on numeric-heavy inputs.
    vadf["Class"] = vadf["Class"].astype("object")

    # Rename Account Name to Account and Fund Name to Name for consistency
    vadf.rename(columns={"Account Name": "Account", "Fund Name": "Name"}, inplace=True)

    # vadf.loc[vadf.Account.isnull(),'Class']=vadf.Name
    # Assign the value in Account over to the Class column if the Name is null
    null_name_mask = vadf["Name"].isnull()
    vadf.loc[null_name_mask, "Class"] = vadf.loc[null_name_mask, "Account"]

    # Propagate Class down
    # Avoid inplace on a Series to prevent chained-assignment FutureWarning
    vadf["Class"] = vadf["Class"].ffill()

    # Remove rows that have the Account (NaN in 'Value') - these have been propagated down
    # Need to reset index after rows are removed
    vadf = vadf.dropna(subset=["Value"]).reset_index(drop=True)
    return vadf


def write_results(
    vadf,
    cmdf,
    quiet=False,
    date_on: bool = True,
    date_format: str = "%Y-%m-%d",
    working_directory: str = ".",
):
    """
    Writes the results of the asset allocation to various files.

    Parameters:
        vadf (DataFrame): The DataFrame containing the asset allocation data.
        cmdf (DataFrame): The DataFrame containing the command file data.
        quiet (bool, optional): If True, suppresses the output messages. Defaults to False.

    Returns:
        None

    Description:
        This function writes the results of the asset allocation out:
        1) unclassified assets (candidate for mapping next time the program is run)
        2) unordered report with subtotals and totals maintained
        3) ordered report with consistent rows (for spreadsheet processing)
        4) report outputs for downstream spreadsheet processing
    """
    ensure_dataframe_columns(
        vadf,
        ["Class", "Name", "Symbol"],
        data_name="Portfolio output data",
    )
    ensure_dataframe_columns(
        cmdf,
        ["ClassMap", "Order"],
        data_name="Class map output data",
    )

    working_directory = resolve_working_directory_path(working_directory)

    # Build an ISO date suffix for output files when enabled: -YYYY-MM-DD
    if date_on:
        now = datetime.now()
        # date_format is an strftime fragment, add leading '-' automatically
        date_suffix = f"-{now.strftime(date_format)}"
    else:
        date_suffix = ""

    # Keep output paths pure by deriving explicit output DataFrames from the input.
    report_df = vadf.copy()

    other_mask = report_df["Class"].fillna("").str.startswith("Other")
    candidates_df = (
        report_df.loc[other_mask, ["Name", "Class"]]
        .dropna(subset=["Class"])
        .reset_index(drop=True)
    )
    if len(candidates_df) > 0:
        candidates_df["%"] = 1.0
        # Using utf-8-sig to include BOM for Excel compatibility on Windows
        odf_name = os.path.join(
            working_directory, f"Asset-Map-Candidates{date_suffix}.csv"
        )
        if not quiet:
            print(f"Outputting 'Other' Assets as '{odf_name}'")
        candidates_df.to_csv(odf_name, index=False, encoding="utf-8-sig")

    # Output the Allocations with headers and totals for pretty report
    # Ensure output dir exists
    output_directory = os.path.join(working_directory, constants.DEFAULT_OUTPUT_DIRECTORY)
    os.makedirs(output_directory, exist_ok=True)
    rep_name = os.path.join(output_directory, f"Van-Alloc-Rep{date_suffix}.csv")
    if not quiet:
        print(f"Outputting allocations as csv report: {rep_name}")
    report_df.to_csv(rep_name, index=False, encoding="utf-8-sig")

    # Build alloc_df explicitly instead of mutating the source frame.
    # This is the spreadsheet form for use in spreadsheets
    alloc_df = report_df.loc[
        (report_df.Symbol != "Subtotal:")
        & (report_df.Symbol != "Total:")
        & (report_df.Name != "Name")
    ].copy()
    # Sort by cl_dict using mergesort (to maintain the current order) - use
    # ClassMap ordering if non-nulls
    if cmdf.Order.notnull().values.sum() > 0:
        alloc_df = alloc_df.sort_values(
            by=["Class"],
            kind="mergesort",
            key=lambda x: x.map(dict(zip(cmdf.ClassMap, cmdf.Order))),
        )
    else:
        alloc_df = alloc_df.sort_values(by=["Class"], kind="mergesort")

    # Output the ordered Allocations
    alloc_name = os.path.join(output_directory, f"Van-Alloc{date_suffix}.csv")
    if not quiet:
        print(f"Outputting sorted allocations without totals as csv: {alloc_name}")
    alloc_df.to_csv(alloc_name, index=False, encoding="utf-8-sig")


def cli_entrypoint() -> int:
    """
    CLI entrypoint that converts known user-input failures to non-zero exit.
    """
    try:
        main()
    except (FileNotFoundError, ValueError, pd.errors.ParserError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(cli_entrypoint())
