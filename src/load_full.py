from collections import defaultdict
from itertools import zip_longest
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

RAW = Path("data/raw")
DB = Path("data/processed/quality.duckdb")
# Limit memory usage by processing the training files in matching batches.
CHUNK_SIZE = 10_000
# Expected size of the complete Bosch training dataset.
EXPECTED_ROWS = 1_183_747

# Build station groups once; contiguous columns can be accessed without a copy.
date_columns = pd.read_csv(RAW / "train_date.csv", nrows=0).columns
time_columns = [column for column in date_columns if column != "Id"]
station_columns = defaultdict(list)
for index, column in enumerate(time_columns):
    # For example, L0_S1_D26 belongs to station L0_S1.
    station = "_".join(column.split("_")[:2])
    station_columns[station].append(index)
# Use a slice for adjacent columns, or explicit positions for scattered columns.
station_selectors = {
    station: (
        slice(indices[0], indices[-1] + 1)
        if indices == list(range(indices[0], indices[-1] + 1))
        else indices
    )
    for station, indices in station_columns.items()
}

# Only the part ID and failure label are needed from the numeric measurements.
numeric_reader = pd.read_csv(
    RAW / "train_numeric.csv",
    usecols=["Id", "Response"],
    chunksize=CHUNK_SIZE,
)
# Keep timestamp columns numeric even when a batch contains only missing values.
date_reader = pd.read_csv(
    RAW / "train_date.csv",
    dtype={column: "float64" for column in time_columns},
    chunksize=CHUNK_SIZE,
)

# Track ingestion totals independently for comparison with the stored records.
total_parts = 0
total_failures = 0
total_visits = 0

with numeric_reader, date_reader, duckdb.connect(str(DB)) as connection:
    # Replace existing data atomically: any error restores the previous contents.
    connection.execute("BEGIN TRANSACTION")

    try:
        connection.execute("DELETE FROM station_visits")
        connection.execute("DELETE FROM parts")

        # zip_longest exposes an extra batch in either file instead of hiding it.
        for batch_number, (numeric, dates) in enumerate(
            zip_longest(numeric_reader, date_reader), start=1
        ):
            if numeric is None or dates is None:
                raise ValueError("Numeric and date files have different row counts")

            if len(numeric) != len(dates):
                raise ValueError(f"Batch {batch_number}: row counts differ")

            # Rows are paired by position, so IDs must be present and aligned.
            if numeric["Id"].isna().any() or dates["Id"].isna().any():
                raise ValueError(f"Batch {batch_number}: missing ID")

            if not numeric["Id"].equals(dates["Id"]):
                raise ValueError(
                    f"Batch {batch_number}: ID order differs between files"
                )

            # Response is binary: 1 indicates a failed part, 0 a non-failed part.
            if not numeric["Response"].isin([0, 1]).all():
                raise ValueError(f"Batch {batch_number}: invalid Response")

            # The database primary key also rejects duplicates across batches.
            if numeric["Id"].duplicated().any():
                raise ValueError(f"Batch {batch_number}: duplicate ID")

            # Match the destination table's column names.
            parts = numeric.rename(
                columns={"Id": "part_id", "Response": "response"}
            )

            # Reduce station timestamps across columns for all parts at once.
            times = dates[time_columns].to_numpy(copy=False)
            part_ids = dates["Id"].to_numpy(copy=False)
            visits = []
            for station, selector in station_selectors.items():
                station_times = times[:, selector]
                # fmin/fmax ignore missing values and keep all-missing rows NaN.
                first_times = np.fmin.reduce(station_times, axis=1)
                # A visit requires at least one recorded timestamp at the station.
                observed = ~np.isnan(first_times)
                if not observed.any():
                    continue

                last_times = np.fmax.reduce(station_times, axis=1)
                # Store one record per observed part/station pair. These are
                # observed time bounds, not necessarily arrival/departure times.
                visits.append(pd.DataFrame({
                    "part_id": part_ids[observed],
                    "station": station,
                    "first_observed_time": first_times[observed],
                    "last_observed_time": last_times[observed],
                }))

            # Expose DataFrames to DuckDB and insert each batch in bulk.
            connection.register("batch_parts", parts)
            connection.execute("INSERT INTO parts SELECT * FROM batch_parts")

            if visits:
                station_visits = pd.concat(visits, ignore_index=True)
                connection.register("batch_visits", station_visits)
                connection.execute(
                    "INSERT INTO station_visits SELECT * FROM batch_visits"
                )
                total_visits += len(station_visits)

            total_parts += len(parts)
            total_failures += int(parts["response"].sum())

            if batch_number % 10 == 0:
                print(f"Processed {total_parts:,} parts", flush=True)

        # Reject incomplete input before committing the replacement dataset.
        if total_parts != EXPECTED_ROWS:
            raise ValueError(
                f"Expected {EXPECTED_ROWS:,} parts; found {total_parts:,}"
            )

        # Reconcile database totals with ingestion counters before committing.
        stored_parts, stored_failures = connection.execute(
            "SELECT COUNT(*), SUM(response) FROM parts"
        ).fetchone()
        stored_visits = connection.execute(
            "SELECT COUNT(*) FROM station_visits"
        ).fetchone()[0]

        if (stored_parts, stored_failures, stored_visits) != (
            total_parts, total_failures, total_visits
        ):
            raise ValueError("Stored counts do not match ingestion counts")

        connection.execute("COMMIT")

    except Exception:
        connection.execute("ROLLBACK")
        raise

# Report final totals only after the transaction commits successfully.
print(f"Loaded parts: {total_parts:,}")
print(f"Failed parts: {total_failures:,}")
print(f"Station visits: {total_visits:,}")