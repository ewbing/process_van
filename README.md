# process_van

This program processes Vanguard allocation reports into consistent rows and adds classifications.
Primary input is from the Vanguard portfolio watch detail page.  The CSV export
is preferred because of its stability.

## Installation

`pip install -r requirements.txt`

## CSV Download Instructions

1. Log into Vanguard.
2. Drill down to Portfolio Watch -> Asset Mix: <https://personal1.vanguard.com/pw1-portfolio-analysis/asset-mix>
3. Expand "Holdings by asset type".
4. Click "Export Data" - this will likely download as `PortfolioWatchData.csv` in your Downloads folder.

## Usage

> `process_van.py [-h] [-q] [-f] [-wd WORKING_DIR] [--csv-path CSV_PATH] [-am ASSET_MAP] [-cm CLASS_MAP] [--no-date] [--date-format DATE_FORMAT]`

## Options

```text
options:
  -h, --help            show this help message and exit
  -q, --quiet           quiet mode - no warnings or status
  -f, --fixed           Group CDs and Treasuries in Fixed
  -wd WORKING_DIR, --working-dir WORKING_DIR
                        base working directory for defaults (default
                        user-home/allocations)
  --csv-path CSV_PATH   input export csv file from Vanguard assets (default
                        <working-dir>/downloads/PortfolioWatchData.csv)
  -am ASSET_MAP, --asset_map ASSET_MAP
                        mapping file for assets (default
                        <working-dir>/Asset-Map.csv)
  -cm CLASS_MAP, --class_map CLASS_MAP
                        mapping file for classes (default
                        <working-dir>/Class-Map.csv)
  --no-date             Do NOT append an ISO date (-YYYY-MM-DD) to output
                        filenames (default: append date)
  --date-format DATE_FORMAT
                        strftime format for the date suffix (default:
                        %Y-%m-%d). Do not include a leading '-' (it's added
                        automatically).
```

## Examples

```bash
# default paths:
#   input: <home>/allocations/downloads/PortfolioWatchData.csv
#   class map: <home>/allocations/Class-Map.csv
#   asset map: <home>/allocations/Asset-Map.csv
#   outputs: <home>/allocations/out/*.csv
.venv/bin/python src/process_van.py

# explicit input path (recommended)
.venv/bin/python src/process_van.py --csv-path <home>/allocations/downloads/PortfolioWatchData.csv

# run from a custom working directory layout
.venv/bin/python src/process_van.py --working-dir <home>/my-allocation-workdir

# keep output filenames without date suffix
.venv/bin/python src/process_van.py --csv-path <home>/allocations/downloads/PortfolioWatchData.csv --no-date
```

Legacy positional input is still accepted for compatibility:

```bash
.venv/bin/python src/process_van.py <home>/allocations/downloads/PortfolioWatchData.csv
```

## CI Status

[![Pylint](https://github.com/ewbing/process_van/actions/workflows/pylint.yml/badge.svg)](https://github.com/ewbing/process_van/actions/workflows/pylint.yml) [![Pytest](https://github.com/ewbing/process_van/actions/workflows/pytest.yml/badge.svg)](https://github.com/ewbing/process_van/actions/workflows/pytest.yml)

## License

Apache License 2.0
