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
import pandas as pd
import numpy as np

import constants


def resolve_input_csv_path(csv_path: str | None, csv_path_positional: str | None) -> str:
    """
    Resolve the portfolio CSV input path from explicit and positional CLI arguments.

    Precedence:
        1) --csv-path
        2) positional fallback
        3) default data/PortfolioWatchData.csv
    """
    if csv_path:
        return csv_path
    if csv_path_positional:
        return csv_path_positional
    return f"data/{constants.DEFAULT_CSV_FILE}"


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
        "--csv-path",
        dest="csv_path",
        default=None,
        help=(
            "input export csv file from Vanguard assets "
            f"(default data/{constants.DEFAULT_CSV_FILE})"
        ),
    )
    parser.add_argument(
        "csv_path_positional",
        nargs="?",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "-am", "--asset_map", help="mapping file for assets", default="Asset-Map.csv"
    )
    parser.add_argument(
        "-cm", "--class_map", help="mapping file for classes", default="Class-Map.csv"
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

    resolved_csv_path = resolve_input_csv_path(args.csv_path, args.csv_path_positional)
    validate_input_csv_path(resolved_csv_path)

    # Bring in (required) input file
    vadf = read_csv_portfolio(resolved_csv_path)

    # Bring in (semi-optional) Class Map - provides / overrides mapping for specific classes
    cmdf = read_class_map(args.class_map, args.quiet)

    # Bring in (optional) Asset Map - provides / overrides mapping for specific assets to classes
    # A new candidate file will be output later on as Asset-Map-Candidates.csv
    amdf = read_asset_map(args.asset_map, args.quiet)

    # CSV post processing
    vadf = csv_post_process(vadf)

    # Common post processing
    post_process(vadf, cmdf, amdf, args.fixed, args.quiet)

    # Write results out (pass date-suffix preference and format)
    write_results(vadf, cmdf, args.quiet, args.date_suffix, args.date_format)

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
    try:
        asset_map_df = pd.read_csv(asset_map_path)[["Name", "Class", "%"]]
        if not quiet:
            print(f"Read Asset map from {asset_map_path}")
    except FileNotFoundError:
        # Always print this message, regardless of the quiet flag
        print(
            f"Asset Map not found at {asset_map_path} - no additional asset mapping will be done"
        )
        asset_map_df = pd.DataFrame(columns=["Name", "Class", "%"])
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
    try:
        class_map = pd.read_csv(class_map_path)[["Class", "ClassMap", "Order"]]
        if len(class_map.columns) != 3:
            raise ValueError(
                f"Class map file at {class_map_path} has incorrect columns - "
                f"should be 'Class','ClassMap','Order'"
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
    try:
        columns_in = ["Account Name", "Fund Name", "Symbol", "Value", "% of Portfolio"]
        columns_out = ["Fund Name", "Account Name", "Symbol", "Value", "% of Portfolio"]
        # Read the CSV file using the specified columns
        with open(csv_path, "r", encoding="utf-8-sig") as file:
            portfolio_data = pd.read_csv(file, usecols=columns_in)[columns_out]
            if len(portfolio_data.columns) != 5:
                # Raise a ValueError if the CSV file has incorrect columns
                raise ValueError(
                    f"CSV file at {csv_path} has incorrect columns - "
                    f"should have {columns_in} columns."
                )
            return portfolio_data
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


def post_process(vadf, cmdf, amdf, fixed, quiet=False):
    """
    Post-process the given DataFrame `vadf` by performing various operations on it.

    Args:
        vadf (pandas.DataFrame): The DataFrame to be post-processed.
        cmdf (pandas.DataFrame): The DataFrame containing classification information.
        amdf (pandas.DataFrame): The DataFrame containing asset information.
        fixed (bool): A flag indicating whether to process fixed assets.
        quiet (bool, optional): A flag indicating whether to suppress output. Defaults to False.

    Returns:
        None

    Description:
        This function performs the following operations on the given DataFrame `vadf`:

        1. Nulls out the 'Class' column for rows with 'Subtotal:' or 'Total:'
        in the 'Symbol' column.
        2. If `fixed` is True, checks for fixed income assets in the 'Name' column
        and remaps them to 'Fixed' in the 'Class' column.
        3. Remaps any classes specified in `cmdf` to their corresponding class maps
        in the 'Class' column.
        4. Remaps any assets specified in `amdf` to their corresponding classes
        in the 'Class' column.
    """
    # Null out Class for Subtotals & Totals - not needed?
    vadf.loc[
        vadf[(vadf.Symbol == "Subtotal:") | (vadf.Symbol == "Total:")].index, "Class"
    ] = np.nan

    # Deal with fixed assets
    if fixed:
        if not quiet:
            print("Fixed mode")
        # should never have NaN in the Name column, but if we do...
        # Avoid inplace on a Series to prevent chained-assignment FutureWarning
        vadf["Name"] = vadf["Name"].fillna("None")

        # Use this expression to check for fixed income assets
        fixed_regex = re.compile(r"(UNITED STATES TREAS|CPN|NTS)")
        # remap fixed securities to 'Fixed'
        vadf["Class"] = vadf.apply(
            lambda row: "Fixed" if fixed_regex.search(row.Name) else row.Class,
            axis=1,
        )

    # remap any Classes to classes specified in cmdf
    vadf.loc[vadf["Class"].isin(cmdf.Class), "Class"] = vadf["Class"].map(
        dict(zip(cmdf.Class, cmdf.ClassMap))
    )

    # remap any Assets to classes specifed in amdf
    vadf.loc[vadf["Name"].isin(amdf.Name), "Class"] = vadf["Name"].map(
        dict(zip(amdf.Name, amdf.Class))
    )


def write_results(
    vadf, cmdf, quiet=False, date_on: bool = True, date_format: str = "%Y-%m-%d"
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

    # Build an ISO date suffix for output files when enabled: -YYYY-MM-DD
    if date_on:
        now = datetime.now()
        # date_format is an strftime fragment, add leading '-' automatically
        date_suffix = f"-{now.strftime(date_format)}"
    else:
        date_suffix = ""

    # Any Class still starting with 'Other' are candidates for mapping - output the candidates
    other_mask = vadf["Class"].fillna("").str.startswith("Other")
    odf = vadf.loc[other_mask, ["Name", "Class"]].dropna(subset=["Class"]).reset_index(
        drop=True
    )
    if len(odf) > 0:
        odf["%"] = 1.0
        # Using utf-8-sig to include BOM for Excel compatibility on Windows
        odf_name = f"Asset-Map-Candidates{date_suffix}.csv"
        if not quiet:
            print(f"Outputting 'Other' Assets as '{odf_name}'")
        odf.to_csv(odf_name, index=False, encoding="utf-8-sig")

    # Output the Allocations with headers and totals for pretty report
    # Ensure output dir exists
    os.makedirs("out", exist_ok=True)
    rep_name = f"out/Van-Alloc-Rep{date_suffix}.csv"
    if not quiet:
        print(f"Outputting allocations as csv report: {rep_name}")
    vadf.to_csv(rep_name, index=False, encoding="utf-8-sig")

    # Remove rows with Headers, Subtotals & Totals
    vadf.drop(
        vadf[
            (vadf.Symbol == "Subtotal:")
            | (vadf.Symbol == "Total:")
            | (vadf.Name == "Name")
        ].index,
        inplace=True,
    )
    # Sort by cl_dict using mergesort (to maintain the current order) - use
    # ClassMap ordering if non-nulls
    if cmdf.Order.notnull().values.sum() > 0:
        vadf = vadf.sort_values(
            by=["Class"],
            kind="mergesort",
            key=lambda x: x.map(dict(zip(cmdf.ClassMap, cmdf.Order))),
        )
    else:
        vadf = vadf.sort_values(by=["Class"], kind="mergesort")

    # Output the ordered Allocations
    alloc_name = f"out/Van-Alloc{date_suffix}.csv"
    if not quiet:
        print(f"Outputting sorted allocations without totals as csv: {alloc_name}")
    vadf.to_csv(alloc_name, index=False, encoding="utf-8-sig")


if __name__ == "__main__":
    main()
