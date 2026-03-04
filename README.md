# process_van

This program processes Vanguard allocation reports into consistent rows and adds classifications.
Primary input is from the Vanguard Portfolio Watch detail page. The CSV export is preferred
because of its stability.

## Installation

`process_van` works on Linux/macOS and Windows.

```text
# Runtime usage (installs the process_van command)
python -m pip install -e .

# Development tooling (tests + lint)
python -m pip install -e ".[dev]"
```

Alternative (without package install):

Linux/macOS:

```bash
PYTHONPATH=src python src/process_van.py --help
```

Windows PowerShell:

```powershell
$env:PYTHONPATH = "src"
python .\src\process_van.py --help
```

## CSV Download Instructions

1. Log into Vanguard.
2. Go to Portfolio Watch -> Asset Mix: <https://personal1.vanguard.com/pw1-portfolio-analysis/asset-mix>
3. Expand "Holdings by asset type".
4. Click "Export Data" to download `PortfolioWatchData.csv` (typically into `~/Downloads`).

## Quick Start

Linux/macOS:

```bash
# 1) Prepare working directory layout
mkdir -p ~/allocations/downloads ~/allocations/out

# 2) Move the downloaded file into the expected default location
cp ~/Downloads/PortfolioWatchData.csv ~/allocations/downloads/PortfolioWatchData.csv

# 3) Run the command (installed via pip)
process_van
```

Windows PowerShell:

```powershell
# 1) Prepare working directory layout
New-Item -ItemType Directory -Force -Path "$HOME\allocations\downloads", "$HOME\allocations\out" | Out-Null

# 2) Move the downloaded file into the expected default location
Copy-Item "$HOME\Downloads\PortfolioWatchData.csv" "$HOME\allocations\downloads\PortfolioWatchData.csv"

# 3) Run the command (installed via pip)
process_van
```

## Usage

```text
process_van [-h] [-q] [-f] [-wd WORKING_DIR] [--csv-path CSV_PATH] [-am ASSET_MAP]
            [-cm CLASS_MAP] [--no-date] [--date-format DATE_FORMAT]
```

## Default Working Directory

If `--working-dir` is not provided, `process_van` defaults to `<user-home>/allocations`.

- Linux/macOS example: `/home/alice/allocations`
- Windows example: `C:\Users\Alice\allocations`

## Options

```text
options:
  -h, --help            show this help message and exit
  -q, --quiet           quiet mode - no warnings or status
  -f, --fixed           Group CDs and Treasuries in Fixed
  -wd WORKING_DIR, --working-dir WORKING_DIR
                        base working directory for defaults (default
                        <user-home>/allocations)
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
#   input: <working-dir>/downloads/PortfolioWatchData.csv
#   class map: <working-dir>/Class-Map.csv
#   asset map: <working-dir>/Asset-Map.csv
#   outputs: <working-dir>/out/*.csv
process_van

# explicit input path (recommended)
process_van --csv-path /full/path/PortfolioWatchData.csv

# run from a custom working directory layout
process_van --working-dir <working-dir>

# keep output filenames without date suffix
process_van --csv-path <working-dir>/downloads/PortfolioWatchData.csv --no-date
```

Legacy positional input is still accepted for compatibility:

```bash
process_van <working-dir>/downloads/PortfolioWatchData.csv
```

## Output Files

By default, outputs are written under `<working-dir>/out` (default working dir is user-home `allocations`, e.g. `~/allocations` on Linux/macOS).

- `Van-Alloc-Rep-YYYY-MM-DD.csv`: report-style output, including subtotal/total rows.
- `Van-Alloc-YYYY-MM-DD.csv`: sorted allocation output without subtotal/total rows.

Candidate mapping output is written to the working dir root:

- `Asset-Map-Candidates-YYYY-MM-DD.csv`: emitted when `Other*` classes are detected.

If `--no-date` is used, filenames are written without the `-YYYY-MM-DD` suffix.

## Troubleshooting

- Missing input CSV:
  Run with `--csv-path /full/path/PortfolioWatchData.csv`, or place the file at
  `<working-dir>/downloads/PortfolioWatchData.csv`.
- Missing/invalid map schemas:
  Ensure class map columns are exactly `Class, ClassMap, Order` and asset map columns are
  exactly `Name, Class, %`.
- Relative path confusion:
  Relative paths are resolved against `--working-dir`; pass absolute paths to avoid ambiguity.
- CSV parse issues:
  Re-export from Vanguard in CSV format and confirm the file is not empty/corrupted.

## Test Coverage

Install dev dependencies, then run:

```bash
python -m pip install -e ".[dev]"
python -m pytest --cov=process_van --cov=constants --cov-report=term-missing --cov-report=xml --cov-fail-under=80
```

This prints line-by-line missing coverage in the terminal and writes `coverage.xml` for CI tooling.

GitHub Actions already runs this in `.github/workflows/pytest.yml` and uploads `coverage.xml` as an artifact on each run.
In the Actions UI, open a workflow run and download the `coverage-xml` artifact.

## CI Status

[![Pylint](https://github.com/ewbing/process_van/actions/workflows/pylint.yml/badge.svg)](https://github.com/ewbing/process_van/actions/workflows/pylint.yml) [![Pytest](https://github.com/ewbing/process_van/actions/workflows/pytest.yml/badge.svg)](https://github.com/ewbing/process_van/actions/workflows/pytest.yml)

## License

Apache License 2.0
