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

> `process_van.py [-h] [-q] [-f] [--csv-path CSV_PATH] [-am ASSET_MAP] [-cm CLASS_MAP] [--no-date] [--date-format DATE_FORMAT]`

## Options

```text
options:
  -h, --help            show this help message and exit
  -q, --quiet           quiet mode - no warnings or status
  -f, --fixed           Group CDs and Treasuries in Fixed
  --csv-path CSV_PATH   input export csv file from Vanguard assets (default
                        data/PortfolioWatchData.csv)
  -am ASSET_MAP, --asset_map ASSET_MAP
                        mapping file for assets
  -cm CLASS_MAP, --class_map CLASS_MAP
                        mapping file for classes
  --no-date             Do NOT append an ISO date (-YYYY-MM-DD) to output
                        filenames (default: append date)
  --date-format DATE_FORMAT
                        strftime format for the date suffix (default:
                        %Y-%m-%d). Do not include a leading '-' (it's added
                        automatically).
```

## Examples

```bash
# default input path: data/PortfolioWatchData.csv
.venv/bin/python src/process_van.py

# explicit input path (recommended)
.venv/bin/python src/process_van.py --csv-path ~/Downloads/PortfolioWatchData.csv

# keep output filenames without date suffix
.venv/bin/python src/process_van.py --csv-path ~/Downloads/PortfolioWatchData.csv --no-date
```

Legacy positional input is still accepted for compatibility:

```bash
.venv/bin/python src/process_van.py ~/Downloads/PortfolioWatchData.csv
```

## CI Status

[![Pylint](https://github.com/ewbing/process_van/actions/workflows/pylint.yml/badge.svg)](https://github.com/ewbing/process_van/actions/workflows/pylint.yml) [![Pytest](https://github.com/ewbing/process_van/actions/workflows/pytest.yml/badge.svg)](https://github.com/ewbing/process_van/actions/workflows/pytest.yml)

## License

Apache License 2.0
