from collections import defaultdict
from pathlib import Path

import duckdb
import pandas as pd

SAMPLE_ROWS = 2_000
RAW = Path("data/raw")
DB = Path("data/processed/quality.duckdb")

numeric = pd.read_csv(
    RAW / "train_numeric.csv",
    usecols=["Id", "Response"],
    nrows=SAMPLE_ROWS,
)
dates = pd.read_csv(RAW / "train_date.csv", nrows=SAMPLE_ROWS)

# Validate the sample before writing anything.
if numeric["Id"].isna().any() or dates["Id"].isna().any():
    raise ValueError("Missing part ID")
if numeric["Id"].duplicated().any() or dates["Id"].duplicated().any():
    raise ValueError("Duplicate part ID")
if not numeric["Response"].isin([0, 1]).all():
    raise ValueError("Response must be 0 or 1")
if set(numeric["Id"]) != set(dates["Id"]):
    raise ValueError("Numeric and date IDs do not match")

parts = numeric.rename(columns={"Id": "part_id", "Response": "response"})

station_columns = defaultdict(list)
for column in dates.columns:
    if column != "Id":
        station = "_".join(column.split("_")[:2])
        station_columns[station].append(column)

visits = []
for station, columns in station_columns.items():
    observed = dates[columns].notna().any(axis=1)
    if not observed.any():
        continue

    station_rows = dates.loc[observed, ["Id", *columns]]
    visits.append(pd.DataFrame({
        "part_id": station_rows["Id"].to_numpy(),
        "station": station,
        "first_observed_time": station_rows[columns].min(axis=1).to_numpy(),
        "last_observed_time": station_rows[columns].max(axis=1).to_numpy(),
    }))

station_visits = pd.concat(visits, ignore_index=True)

with duckdb.connect(str(DB)) as connection:
    connection.execute("BEGIN TRANSACTION")
    try:
        # Replace the test load so rerunning this script is safe.
        connection.execute("DELETE FROM station_visits")
        connection.execute("DELETE FROM parts")

        connection.register("new_parts", parts)
        connection.register("new_visits", station_visits)

        connection.execute("INSERT INTO parts SELECT * FROM new_parts")
        connection.execute(
            "INSERT INTO station_visits SELECT * FROM new_visits"
        )
        connection.execute("COMMIT")
    except Exception:
        connection.execute("ROLLBACK")
        raise

print(f"Loaded {len(parts):,} parts and {len(station_visits):,} station visits")
print(f"Failed parts: {int(parts['response'].sum()):,}")