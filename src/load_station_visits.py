"""Load station time bounds from train_date.csv after loading parts."""

from collections import defaultdict

import numpy as np
import pandas as pd

if __package__:
    from .load_common import run_loaders
else:
    from load_common import run_loaders


def load_station_visits(connection, raw, chunk_size, expected_rows):
    """Replace station visits within the transaction owned by run_loaders."""
    stored_parts = connection.execute("SELECT COUNT(*) FROM parts").fetchone()[0]
    if stored_parts != expected_rows:
        raise ValueError(f"Load parts first: expected {expected_rows:,}; found {stored_parts:,}")

    # Build station selectors once, e.g. L0_S1_D26 belongs to L0_S1.
    date_columns = pd.read_csv(raw / "train_date.csv", nrows=0).columns
    time_columns = [column for column in date_columns if column != "Id"]
    station_columns = defaultdict(list)
    for index, column in enumerate(time_columns):
        station_columns["_".join(column.split("_")[:2])].append(index)
    # Adjacent columns use a NumPy view; scattered columns use explicit positions.
    station_selectors = {
        station: (slice(indices[0], indices[-1] + 1)
                  if indices == list(range(indices[0], indices[-1] + 1)) else indices)
        for station, indices in station_columns.items()
    }

    connection.execute("DELETE FROM station_visits")
    # Track all date IDs, including parts with no visits, to catch duplicates
    # across batches and verify complete coverage of the loaded parts.
    connection.execute("CREATE TEMP TABLE date_ids (part_id BIGINT PRIMARY KEY)")
    total_rows = 0
    total_visits = 0
    with pd.read_csv(raw / "train_date.csv", chunksize=chunk_size,
                     dtype={column: "float64" for column in time_columns}) as reader:
        for batch_number, dates in enumerate(reader, start=1):
            if dates["Id"].isna().any():
                raise ValueError(f"Batch {batch_number}: missing ID")
            if dates["Id"].duplicated().any():
                raise ValueError(f"Batch {batch_number}: duplicate ID")
            connection.register("batch_date_ids", dates[["Id"]])
            try:
                # Match by ID rather than CSV row order now that loads are separate.
                unknown = connection.execute('''
                    SELECT 1 FROM batch_date_ids d
                    WHERE NOT EXISTS (SELECT 1 FROM parts p WHERE p.part_id = d."Id")
                    LIMIT 1
                ''').fetchone()
                if unknown:
                    raise ValueError(f"Batch {batch_number}: date ID missing from parts")
                connection.execute("INSERT INTO date_ids SELECT * FROM batch_date_ids")
            finally:
                connection.unregister("batch_date_ids")

            times = dates[time_columns].to_numpy(copy=False)
            part_ids = dates["Id"].to_numpy(copy=False)
            visits = []
            for station, selector in station_selectors.items():
                station_times = times[:, selector]
                # Ignore missing timestamps; omit entirely unobserved visits.
                first_times = np.fmin.reduce(station_times, axis=1)
                observed = ~np.isnan(first_times)
                if not observed.any():
                    continue
                last_times = np.fmax.reduce(station_times, axis=1)
                # These are observed bounds, not necessarily arrival/departure times.
                visits.append(pd.DataFrame({
                    "part_id": part_ids[observed],
                    "station": station,
                    "first_observed_time": first_times[observed],
                    "last_observed_time": last_times[observed],
                }))

            if visits:
                batch_visits = pd.concat(visits, ignore_index=True)
                connection.register("batch_visits", batch_visits)
                try:
                    connection.execute("INSERT INTO station_visits SELECT * FROM batch_visits")
                finally:
                    connection.unregister("batch_visits")
                total_visits += len(batch_visits)
            total_rows += len(dates)
            if batch_number % 10 == 0:
                print(f"Processed station dates for {total_rows:,} parts", flush=True)

    # Unique date IDs are a subset of parts; equal counts ensure full coverage.
    if total_rows != expected_rows:
        raise ValueError(f"Expected {expected_rows:,} date rows; found {total_rows:,}")
    stored_visits = connection.execute("SELECT COUNT(*) FROM station_visits").fetchone()[0]
    if stored_visits != total_visits:
        raise ValueError("Stored station visit count does not match ingestion count")
    connection.execute("DROP TABLE date_ids")
    return {"Station visits": total_visits}


if __name__ == "__main__":
    run_loaders(load_station_visits)
