# Manufacturing Quality Monitoring and Failure Investigation

A local analytics project using the anonymized Bosch Production Line Performance dataset to investigate final quality outcomes, recorded station exposure, and production-line combinations. Python loaders prepare the data, DuckDB runs the SQL analysis, and Streamlit presents the results.

## Current status

Implemented: parts and station ingestion, mapped measurement export to Parquet, ingestion validation, SQL metric views, cohort and station comparisons, and a Streamlit dashboard. The project runs locally; scheduled orchestration, streaming ingestion, and distributed processing are not implemented.

The saved [validation report](reports/phase3_validation.json), generated on September 28, 2026, records a passing run:

| Measure | Recorded result |
| --- | ---: |
| Parts | 1,183,747 |
| Failed parts | 6,879 |
| Station observations | 14,382,158 |
| Distinct stations | 52 |
| Mapped measurements | 112,772,532 |
| Mapped numeric features | 366 |
| Measurements missing a matched timestamp | 0 |

These are saved validation results, not a live check of your local database.

## Questions explored

- What is the overall final failure rate?
- How does the final failure rate vary by recorded station and line combination?
- How do parts observed at L3_S32 compare with other parts on L3?
- Does that comparison change within recorded line groups or time cohorts?
- What measurement coverage and missing-data limitations affect interpretation?

## Architecture and data model

```text
train_numeric.csv + train_date.csv
    |
    +-- parts and station loaders --> quality.duckdb
    |                                  |
    |                                  +-- metric views --> Streamlit
    |
    +-- mapped measurement loader --> mapped_measurements.parquet
                                       |
                                       +-- DuckDB mapped_measurements view
```

| Object | Storage / grain | Purpose |
| --- | --- | --- |
| `parts` | DuckDB table; one row per part | Part ID and final binary `response` |
| `station_visits` | DuckDB table; one row per observed part/station pair | Earliest and latest recorded station timestamps |
| `mapped_measurements` | DuckDB view over Parquet; one row per non-missing mapped measurement | Measurement value, station, feature, matched date feature, and timestamp |
| `measurements` | Optional DuckDB table | Earlier pilot storage; not populated by the current Parquet loader |
| `overall_quality_metrics` | DuckDB view | Part count, failure count, and failure rate |
| `station_exposure_metrics` | DuckDB view | Station exposure counts and associated final failure rates |
| `production_path_metrics` | DuckDB view | Counts and failure rates by recorded line combination |

The active measurement loader pairs a feature named `Lx_Sy_Fn` with `Lx_Sy_D(n+1)` when that date column exists. It expects 366 matching pairs. The other 602 numeric features remain in the raw CSV; this project has not established their individual measurement times. Matching column names is the implemented rule, not independent proof of the physical meaning of the timestamps.

## Repository layout

```text
pipelines/load_full.py         Combined parts and station-visits entry point
src/                          Table creation and data loaders
sql/schema/                   Table definitions
sql/metrics/                  Reusable metric views
sql/analysis/                 Station, line-group, and cohort queries
sql/validation/               Measurement validation queries
validations/                  Source profiling and ingestion checks
streamlit/app.py              Dashboard
reports/phase3_validation.json Saved ingestion validation report
run_sql_file.py                SQL file runner
requirements.txt              Existing environment dependency snapshot
data/raw/                     Input CSVs (excluded from Git)
data/processed/               DuckDB and Parquet outputs (excluded from Git)
```

## Setup

Run all commands below from the repository root. Examples use Windows PowerShell and assume Python is installed.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install duckdb pandas numpy pyarrow streamlit
```

These packages cover the current ingestion, validation, and dashboard workflow. `requirements.txt` contains a broader environment snapshot but currently omits DuckDB and Streamlit, so it is not a complete dependency lock for this application.

Download the training data from the [Bosch Production Line Performance competition](https://www.kaggle.com/competitions/bosch-production-line-performance) and extract these files:

```text
data/raw/train_numeric.csv
data/raw/train_date.csv
```

The documented workflow does not require the categorical training file. Keep the raw files and generated data out of Git; the repository already ignores the raw and processed directories.

## Build the database

### 1. Create the core tables

```powershell
python src/create_database.py parts
python src/create_database.py station_visits
```

The table name selects its definition from `sql/schema/`. Creating the optional pilot table uses `python src/create_database.py measurements`; it is not required for the Parquet measurement workflow or dashboard.

### 2. Load parts and station visits

```powershell
python pipelines/load_full.py
python validations/validate_load.py
```

The combined loader replaces both tables in one transaction. A failure rolls back both replacements. It processes 10,000-row batches and expects 1,183,747 parts. It does not load measurements or build metric views.

To refresh the tables separately, load parts first:

```powershell
python src/load_parts.py
python src/load_station_visits.py
```

Each standalone run replaces only its own table. The station loader checks date IDs against loaded parts and accepts a different CSV row order. If a separate station load fails, the previously completed parts load remains committed.

### 3. Load mapped measurements

```powershell
python validations/check_feature_mapping.py
python src/load_mapped_measurements.py
```

The loader reads both CSVs in matching 500-row batches, checks ID alignment, and writes non-missing measurements to Snappy-compressed Parquet. Unlike the station loader, this step requires the numeric and date rows to have matching IDs in the same order.

It writes `data/processed/mapped_measurements.pending.parquet`, checks the completed file's row count, then renames it to `mapped_measurements.parquet`. Finally, it creates the `mapped_measurements` DuckDB view. The pilot `measurements` table remains untouched.

This is a one-shot load: the script refuses to run if either the pending or final file already exists. Inspect an interrupted pending file before manually removing or archiving it. A completed Parquet file is not automatically overwritten. Parquet publication and DuckDB view creation are separate steps, not one transaction.

### 4. Validate the full ingestion

```powershell
python validations/check_ingestion.py
python run_sql_file.py sql/validation/validate_measurements.sql
```

`check_ingestion.py` compares loaded counts, mapped feature coverage, missing timestamps, source header sizes, and Parquet row counts. It writes `reports/phase3_validation.json` and exits with an error if any defined check fails. The report includes header hashes, not hashes of the complete source files.

`validate_load.py` prints core table counts and checks such as orphan visits and invalid time order. It is a diagnostic report; it does not automatically fail on every unexpected count.

### 5. Create metric views

```powershell
python run_sql_file.py sql/metrics/quality_metrics.sql
python run_sql_file.py sql/metrics/production_path_metrics.sql
```

These scripts create or replace the views consumed by the dashboard. They must be run before launching it.

## Launch the dashboard

```powershell
python -m streamlit run streamlit/app.py
```

The dashboard opens the database read-only and displays:

- Total parts, failed parts, and the final failure rate.
- The 15 highest failure-rate stations among those with at least 1,000 observed parts, plus a station table.
- Recorded production-line combinations and their failure rates.
- L3_S32 versus other L3 parts, including comparisons within recorded line groups.

The dashboard requires the two core tables and the three metric views. It does not currently query `mapped_measurements`, so the measurement export can be skipped when only setting up the dashboard. Queries are cached; clear the Streamlit cache or restart the app after refreshing the data.

## Run SQL analyses

Pass a saved SQL file to the runner:

```powershell
python run_sql_file.py sql/analysis/check_failure.sql
python run_sql_file.py sql/analysis/same_line_failure.sql
python run_sql_file.py sql/analysis/cohort_analysis.sql
python run_sql_file.py sql/analysis/s32_analysis.sql
```

The runner executes the file and prints the final statement's result. `s32_analysis.sql` requires the `mapped_measurements` view; the other listed analyses use the core tables.

For interactive inspection, install the DuckDB CLI separately and run:

```powershell
duckdb -ui data/processed/quality.duckdb
```

Keep the terminal running while using the browser UI. See the [DuckDB UI documentation](https://duckdb.org/docs/current/core_extensions/ui).

## Profiling tools

The `validations/` directory also contains `inspect_headers.py`, `profile_sample.py`, `profile_ids.py`, and `profile_stations.py` for inspecting source structure, sample data, IDs, and stations. These are optional exploratory steps; they are not called by `pipelines/load_full.py`.

## Interpretation limits and next steps

`Response` describes the final part outcome: 1 indicates failure and 0 indicates non-failure. It does not locate the failure at a particular station or time. A station visit means at least one timestamp was recorded there; its minimum and maximum timestamps are observed bounds, not confirmed arrival and departure times.

Recorded line combinations describe which lines appear in the data, not the exact sequence of a production route. Station and cohort comparisons are observational: differences can reflect product mix, routing, time, or other unobserved conditions. Associations do not establish a physical root cause.

Future work could add repeatable dependency locking, automated regression tests, batch tracking and resumable ingestion, scheduled validation, and deeper measurement-level investigations. This is an independent portfolio project using anonymized data.
