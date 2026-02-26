# process_van Tasks

Tracking list for remaining issues and refactors.

## CLI and Input Handling

- [ ] Replace positional `csv_path` with explicit `--csv-path` (optionally keep positional fallback).
- [ ] Validate input path early with a clear error + expected filename/location hint.
- [ ] Add tests for default path behavior and explicit path handling.

## CSV Schema Validation

- [ ] Add a shared helper to validate required columns for portfolio/class-map/asset-map CSVs.
- [ ] Raise user-friendly `ValueError` messages listing missing and extra columns.
- [ ] Remove ineffective `len(columns)` checks after column subsetting.

## Error Handling Consistency

- [ ] Ensure malformed input errors are deterministic and readable (no raw pandas `KeyError` leaks).
- [ ] Standardize helper behavior: raise exceptions in helpers, exit only in CLI entry path.
- [ ] Add tests covering malformed portfolio/class-map/asset-map files.

## Pipeline Refactor

- [ ] Split processing into smaller functions: `load_inputs`, `normalize_portfolio_rows`, `apply_class_mappings`, `write_outputs`.
- [ ] Prefer pure DataFrame transforms and reduce cross-function side effects.
- [ ] Simplify `main()` to orchestration only.

## Output-Path Refactor

- [ ] Remove in-place mutation in `write_results`.
- [ ] Use explicit derived frames (`report_df`, `alloc_df`, `candidates_df`) before writing.
- [ ] Add regression test to verify pre-output DataFrame is unchanged.

## Test Coverage Expansion

- [ ] Add tests for `read_csv_portfolio`.
- [ ] Add tests for `csv_post_process`.
- [ ] Add tests for `post_process`.
- [ ] Add tests for `write_results` outputs and ordering behavior.
- [ ] Add CLI tests for `-h`, missing file, and invalid map schemas.
- [ ] Add tests for date suffix options: `--no-date` and `--date-format`.

## Packaging and Dependencies

- [ ] Move `pytest`/`pylint` to dev dependencies (keep runtime deps minimal).
- [ ] Consider migrating packaging to `pyproject.toml`.
- [ ] Add/verify console entry point for running `process_van` as a command.
- [ ] Align install/run instructions with the final packaging approach.

## Documentation

- [ ] Add a "Quick Start" run example using downloaded `PortfolioWatchData.csv`.
- [ ] Document expected output files and locations.
- [ ] Add troubleshooting notes for common file/path/schema failures.

## CI / Quality Gates (Optional)

- [ ] Add `python -m compileall src` to CI.
- [ ] Pin lint/test tool versions for reproducibility.
- [ ] Add coverage collection and threshold after expanding tests.
