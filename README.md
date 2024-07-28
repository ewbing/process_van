# process_van

This program processes Vanguard allocation reports into consistent rows and adds classifications. 
Primary input is from the Vanguard portfolio watch detail page.  The CSV export 
is preferred because of its stability.  However, the HTML  saved page from the website page can be 
used as well.

## Installation

`pip install -r requirements.txt`

## Usage

> `process_van.py [-h] [-q] [-f] [-m {html,csv}] [-am ASSET_MAP] [-cm CLASS_MAP] [csv_path | html_path]`


## Options
```
positional arguments - *mode* controls which one is used:
  csv_path              input export csv file from Vanguard assets (default data/PortfolioWatchData.csv) 
  html_path             input html file saved from Vanguard assets page (data/Vanguard - Portfolio Analysis.html)

other arguments:
  -h, --help            show this help message and exit
  -q, --quiet           quiet mode - no warnings or status
  -f, --fixed           Group CDs and Treasuries in Fixed
  -m {html,csv}, --mode {html,csv}
                        type of input file
  -am ASSET_MAP, --asset_map ASSET_MAP
                        mapping file for assets
  -cm CLASS_MAP, --class_map CLASS_MAP
                        mapping file for classes
```

## CI Status

[![Pylint](https://github.com/arunkv/wordle/actions/workflows/pylint.yml/badge.svg)](https://github.com/arunkv/wordle/actions/workflows/pylint.yml)

## License

Apache License 2.0
