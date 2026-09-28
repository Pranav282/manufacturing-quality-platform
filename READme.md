# Manufacturing Quality Monitoring and Failure Investigation

A portfolio project that uses the anonymized [Bosch Production Line Performance dataset](https://www.kaggle.com/competitions/bosch-production-line-performance/overview) to explore manufacturing quality data. The goal is to build a reproducible pipeline and an investigation dashboard that help identify changes in final quality outcomes and prioritize follow-up analysis.

## Project questions

- How many parts were processed, and what proportion failed final quality control?
- Do failure rates change across groups of parts or production paths?
- Which station visits and measurements are associated with higher failure rates?
- Could missing or inconsistent data affect an apparent trend?

## Planned workflow

1. **Profile the data:** Inspect the numeric and date files, IDs, labels, missing values, and station fields.
2. **Ingest and validate:** Load the CSV files and check schema, duplicate IDs, label values, row counts, and join coverage.
3. **Model metrics:** Create part-level and station-exposure tables with documented SQL definitions.
4. **Investigate:** Compare affected groups with a baseline and document the evidence and remaining questions.
5. **Present:** Build a Streamlit dashboard for trends, data-quality checks, and investigation drill-downs.
6. **Operationalize:** Add Airflow orchestration and Spark processing after the initial workflow is working.

## Initial technology stack

Python, pandas, SQL, PostgreSQL, Streamlit, Apache Spark, and Apache Airflow. Tools will be added as the relevant phase is implemented.

## Data source

The Bosch dataset contains anonymized production-line measurements and a final quality outcome for each part. Download the data through Kaggle and place the training files in `data/raw/`. Source data is excluded from Git.

## DuckDB commands

Run these commands from the project root with your Python virtual environment activated.

Install the DuckDB Python package:

```powershell
python -m pip install duckdb
```

Create the tables, load the training CSVs, and validate the stored data:

```powershell
python src/create_database.py parts
python src/create_database.py station_visits
python pipelines/load_full.py
python validations/validate_load.py
```

The full loader replaces existing records in `data/processed/quality.duckdb`.

To load each table separately, run the parts pipeline first:

```powershell
python src/load_parts.py
python src/load_station_visits.py
python validations/validate_load.py
```

The parts pipeline reads `train_numeric.csv`; the station-visits pipeline reads
`train_date.csv` and checks that its IDs match the loaded parts, regardless of row
order. Each command replaces only its own table in a transaction. If a separate
station-visits run fails, the completed parts load remains committed. Use
`python pipelines/load_full.py` to load both tables in a single transaction instead.

Open the same database in the DuckDB browser UI using the CLI:

```powershell
duckdb -ui data/processed/quality.duckdb
```

Keep the terminal running while using the UI. The UI requires write access to
store notebooks, so omit `-readonly`. See the [DuckDB UI documentation](https://duckdb.org/docs/current/core_extensions/ui).

## Interpretation limits

The dataset’s features and production details are anonymized. An association between a station visit or measurement and a failed part does **not** establish a physical root cause. This is an independent portfolio project, not professional manufacturing experience.

## Status

**Phase 1 — repository setup.** Data profiling and ingestion are next.
