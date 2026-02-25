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

> `process_van.py [-h] [-q] [-f] [-am ASSET_MAP] [-cm CLASS_MAP] [csv_path]`


## Options
```
positional arguments:
  csv_path              input export csv file from Vanguard assets (default data/PortfolioWatchData.csv) 

other arguments:
  -h, --help            show this help message and exit
  -q, --quiet           quiet mode - no warnings or status
  -f, --fixed           Group CDs and Treasuries in Fixed
  -am ASSET_MAP, --asset_map ASSET_MAP
                        mapping file for assets
  -cm CLASS_MAP, --class_map CLASS_MAP
                        mapping file for classes
```

## CI Status

[![Pylint](https://github.com/arunkv/wordle/actions/workflows/pylint.yml/badge.svg)](https://github.com/arunkv/wordle/actions/workflows/pylint.yml) [![Pytest](https://github.com/ewbing/process_van/actions/workflows/pytest.yml/badge.svg)](https://github.com/ewbing/process_van/actions/workflows/pytest.yml)

## License

Apache License 2.0
