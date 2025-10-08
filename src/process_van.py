#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Process Vanguard reports into consistent rows and add classifications.
copyright (c) 2024, Eric Bing
All rights reserved."""

import sys
import os
from datetime import datetime
import argparse
import re
import pandas as pd
import numpy as np

import constants


def main():
    """
    This program processes Vanguard allocation reports into consistent rows and adds
    classifications. Primary input is from the Vanguard portfolio watch detail page.
    The CSV export (default -PortfolioWatchData.csv) is preferred because of its stability.
    However, the HTML saved page from the website page can be used as well.

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
        "-m",
        "--mode",
        help="type of input file",
        choices=["html", "csv"],
        default="csv",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "csv_path",
        nargs="?",
        help="input file from Vanguard assets (csv)",
        default=f"data/{constants.DEFAULT_CSV_FILE}",
    )
    group.add_argument(
        "html_path",
        nargs="?",
        help="input file from Vanguard assets (html)",
        default=f"data/{constants.DEFAULT_HTML_FILE}",
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

    html_dfs = pd.DataFrame()
    vadf = pd.DataFrame()

    # Bring in (required) input file - via html_path or csv_path depending on mode
    if args.mode == "csv":
        if not args.quiet:
            print("CSV mode")
        vadf = read_csv_portfolio(args.csv_path)
    elif args.mode == "html":
        print(
            "HTML mode currently disabled due to changes to Vanguard website  - use CSV mode"
        )
        if not args.quiet:
            print("HTML mode")
        html_dfs = read_html_portfolio(args.html_path)
        sys.exit(1)

    # Bring in (semi-optional) Class Map - provides / overrides mapping for specific classes
    cmdf = read_class_map(args.class_map, args.quiet)

    # Bring in (optional) Asset Map - provides / overrides mapping for specific assets to classes
    # A new candidate file will be output later on as Asset-Map-Candidates.csv
    amdf = read_asset_map(args.asset_map, args.quiet)

    # HTML post processing
    if args.mode == "html":
        vadf = html_post_process(vadf, cmdf)

    # CSV post processing
    elif args.mode == "csv":
        vadf = csv_post_process(vadf)
    else:
        raise ValueError("Can't get thar from here...invalid value for mode")

    # Common post processing
    post_process(vadf, cmdf, amdf, args.fixed, args.quiet)

    # Write results out (pass date-suffix preference and format)
    write_results(vadf, cmdf, args.quiet, args.date_suffix, args.date_format)

    # Output U.S. Stock Market share (HTML only)
    if args.mode == "html":
        write_us_market(html_dfs, args.quiet, args.date_suffix, args.date_format)


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
    Provides the ordering that the Asset Classifications come in (for HTML table).
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
            f"for HTML mapping."
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


def read_html_portfolio(file_path: str) -> pd.DataFrame:
    """
    Reads the HTML file and extracts the table with the asset information.

    Args:
        file_path (str): The path to the HTML file.

    Returns:
        pandas.DataFrame: The DataFrame containing the asset information.

    Raises:
        FileNotFoundError: If the HTML file is not found.
        ValueError: If the table has an incorrect number of columns.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            tables = pd.read_html(file.read())
            asset_table = tables[3]
            expected_columns = 3
            if len(asset_table.columns) != expected_columns:
                raise ValueError(
                    "The HTML output has an incorrect number of columns for assets. "
                    f"Expected {expected_columns} columns."
                )
            return asset_table
    except FileNotFoundError as fnfe:
        raise FileNotFoundError(f"The HTML file '{file_path}' was not found.") from fnfe


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

    # Rename Account Name to Account and Fund Name to Name for consistency
    vadf.rename(columns={"Account Name": "Account", "Fund Name": "Name"}, inplace=True)

    # vadf.loc[vadf.Account.isnull(),'Class']=vadf.Name
    # Assign the value in Account over to the Class column if the Name is null
    vadf.loc[vadf.Name.isnull(), "Class"] = vadf["Account"]

    # Propagate Class down
    # Avoid inplace on a Series to prevent chained-assignment FutureWarning
    vadf["Class"] = vadf["Class"].ffill()

    # Remove rows that have the Account (NaN in 'Value') - these have been propagated down
    # Need to reset index after rows are removed
    vadf = vadf.dropna(subset=["Value"]).reset_index(drop=True)
    return vadf


def html_post_process(vadf, cmdf):
    """
    Post-processes the given DataFrame `vadf` by adding the 'Account' and 'Class' columns
    based on the values in the 'Value' column.

    Parameters:
        vadf (pandas.DataFrame): The DataFrame to be post-processed.
        cmdf (pandas.DataFrame): The DataFrame containing the 'ClassMap' column used for
        assigning values to the 'Class' column.

    Returns:
        pandas.DataFrame: The post-processed DataFrame with the 'Account' and 'Class' columns added.
    """
    # Account
    # Create with where...but nested where clauses don't work -
    # nan throws them off so need two lines :-(
    vadf.insert(1, "Account", np.where(vadf.Value.isnull(), vadf.Name, np.nan))
    vadf["Account"] = np.where(vadf.Value == "Value", "Account", vadf["Account"])

    # Propagate account down
    # Avoid inplace on a Series to prevent chained-assignment FutureWarning
    vadf["Account"] = vadf["Account"].ffill()
    # Null out Subtotals & Totals
    vadf.loc[
        vadf[(vadf.Name == "Subtotal:") | (vadf.Name == "Total:")].index, "Account"
    ] = np.nan

    # Remove rows that have the Account (NaN in 'Value') - these have been propagated down
    # Need to reset index after rows are removed
    vadf = vadf.dropna(subset=["Value"]).reset_index(drop=True)

    # Class
    # Why None rather than np.nan?  Because it works...
    vadf.insert(0, "Class", vadf.Value.where(vadf.Value == "Value", "Class", None))

    # Add ClassMap values to row after header rows - start with 0 because no explicit header:
    cmdfi = 0
    vadf.at[0, "Class"] = cmdf["ClassMap"].iloc[cmdfi]
    # For each header row add next Asset Classification value to the next row - use the ClassMap
    # column for the Class:
    for i in vadf[vadf["Class"] == "Class"].index:
        cmdfi += 1
        vadf.at[i + 1, "Class"] = cmdf["ClassMap"].iloc[cmdfi]

    if cmdfi != len(cmdf["ClassMap"]) - 1:
        print("Warning: Rowcount mismatch in ClassMap: cmdfi - ", cmdfi)
        print(cmdf["ClassMap"])

    # Propagate Class down
    # Avoid inplace on a Series to prevent chained-assignment FutureWarning
    vadf["Class"] = vadf["Class"].ffill()
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
        html_dfs (list of DataFrames): The list of DataFrames containing the HTML output.
        quiet (bool, optional): If True, suppresses the output messages. Defaults to False.

    Returns:
        None

    Description:
        This function writes the results of the asset allocation out:
        1) unclassified assets (candidate for mapping next time the program is run)
        2) unordered report with subtotals and totals maintained
        3) ordered report with consistent rows (for spreadsheet processing)
        4) US Asset Market Share (HTML input only)
    """

    # Build an ISO date suffix for output files when enabled: -YYYY-MM-DD
    if date_on:
        now = datetime.now()
        # date_format is an strftime fragment, add leading '-' automatically
        date_suffix = f"-{now.strftime(date_format)}"
    else:
        date_suffix = ""

    # Any Class still starting with 'Other' are candidates for mapping - output the candidates
    odf = vadf.dropna(subset=["Class"])[vadf.Class.str.startswith("Other").dropna()][
        ["Name", "Class"]
    ].reset_index(drop=True)
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


def write_us_market(
    html_dfs, quiet, date_on: bool = True, date_format: str = "%Y-%m-%d"
):
    """
    Writes the US stock market share data to a CSV file.  Only in HTML mode.

    Args:
        html_dfs (list): A list of pandas DataFrames representing the HTML tables.
        quiet (bool): If True, suppresses the output message.

    Returns:
        None

    Raises:
        SystemExit: If the HTML output table 4 has incorrect columns for the US market share.

    Description:
        This function extracts the US stock market share data from the 4th table in the `html_dfs`
        list.  It checks if the DataFrame has the correct number of columns (4) and an exception
        if it doesn't. The function then converts the "Your U.S. Stock Portfolio" column from
        strings of the form '3.05%' to fractional percentages '.0305'.  Finally, it outputs the
        US stock market share data to a CSV file named "Van-Market.csv" unless `quiet` is True.
    """

    stockdf = html_dfs[4][
        [
            "Size",
            "Your U.S. Stock Portfolio",
            "U.S. Stock Market",
            "Difference from Market",
        ]
    ]
    if len(stockdf.columns) != 4:
        sys.exit(
            "HTML output [table 4] has incorrect columns for U.S. market share - correct page?"
        )

        # Convert strings of the form '3.05%' to fractional percentages '.0305'
        # - the way god intended them:
    stockdf["Your U.S. Stock Portfolio"] = (
        stockdf["Your U.S. Stock Portfolio"]
        .str.replace("%", "")
        .apply(lambda x: float(x) / 100)
    )

    # Output the Asset Market share
    if date_on:
        now = datetime.now()
        date_suffix = f"-{now.strftime(date_format)}"
    else:
        date_suffix = ""
    market_name = f"Van-Market{date_suffix}.csv"
    if not quiet:
        print(f"Outputting US Stock Market shares as csv report: {market_name}")
    stockdf.to_csv(market_name, index=False, encoding="utf-8-sig")


if __name__ == "__main__":
    main()
