import csv
import re
from itertools import zip_longest
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

RAW = Path("data/raw")
PROCESSED = Path("data/processed")
DB = PROCESSED / "quality.duckdb"
PENDING = PROCESSED / "mapped_measurements.pending.parquet"
FINAL = PROCESSED / "mapped_measurements.parquet"

CHUNK_SIZE = 500
EXPECTED_PARTS = 1_183_747
EXPECTED_PAIRS = 366


def read_header(path):
    with path.open(newline="", encoding="utf-8") as file:
        return next(csv.reader(file))


numeric_header = read_header(RAW / "train_numeric.csv")
date_header = set(read_header(RAW / "train_date.csv"))

pairs = {}
for feature in numeric_header:
    match = re.fullmatch(r"(L\d+_S\d+)_F(\d+)", feature)
    if match:
        station, number = match.groups()
        date_feature = f"{station}_D{int(number) + 1}"
        if date_feature in date_header:
            pairs[feature] = date_feature

if len(pairs) != EXPECTED_PAIRS:
    raise ValueError(f"Expected {EXPECTED_PAIRS} pairs; found {len(pairs)}")

if PENDING.exists():
    raise FileExistsError(
        f"{PENDING} exists from an earlier attempt. Inspect it before removing it."
    )
if FINAL.exists():
    raise FileExistsError(
        f"{FINAL} already exists. This script will not overwrite a completed load."
    )

PROCESSED.mkdir(parents=True, exist_ok=True)

features = list(pairs)
date_features = list(pairs.values())
feature_names = np.asarray(features, dtype=object)
date_names = np.asarray(date_features, dtype=object)
station_names = np.asarray(
    [feature.split("_F")[0] for feature in features],
    dtype=object,
)

schema = pa.schema([
    ("part_id", pa.int64()),
    ("station", pa.string()),
    ("feature_name", pa.string()),
    ("measurement_value", pa.float64()),
    ("date_feature_name", pa.string()),
    ("observed_time", pa.float64()),
])

numeric_reader = pd.read_csv(
    RAW / "train_numeric.csv",
    usecols=["Id", *features],
    chunksize=CHUNK_SIZE,
)
date_reader = pd.read_csv(
    RAW / "train_date.csv",
    usecols=["Id", *date_features],
    chunksize=CHUNK_SIZE,
)

parts_read = 0
measurements_written = 0
missing_times = 0
writer = None

try:
    with numeric_reader, date_reader:
        for batch_number, (numeric, dates) in enumerate(
            zip_longest(numeric_reader, date_reader), start=1
        ):
            if numeric is None or dates is None:
                raise ValueError("Numeric and date files have different lengths")
            if len(numeric) != len(dates):
                raise ValueError(f"Batch {batch_number}: row counts differ")
            if not numeric["Id"].equals(dates["Id"]):
                raise ValueError(f"Batch {batch_number}: IDs or order differ")
            if numeric["Id"].isna().any() or numeric["Id"].duplicated().any():
                raise ValueError(f"Batch {batch_number}: invalid IDs")

            # Select columns in the same order as the feature/date mapping.
            values = numeric[features].to_numpy(dtype="float64")
            times = dates[date_features].to_numpy(dtype="float64")
            row_index, column_index = np.nonzero(~np.isnan(values))

            if len(row_index):
                selected_times = times[row_index, column_index]

                table = pa.Table.from_arrays(
                    [
                        pa.array(
                            numeric["Id"].to_numpy()[row_index],
                            type=pa.int64(),
                        ),
                        pa.array(
                            station_names[column_index],
                            type=pa.string(),
                        ),
                        pa.array(
                            feature_names[column_index],
                            type=pa.string(),
                        ),
                        pa.array(
                            values[row_index, column_index],
                            type=pa.float64(),
                        ),
                        pa.array(
                            date_names[column_index],
                            type=pa.string(),
                        ),
                        pa.array(
                            selected_times,
                            mask=np.isnan(selected_times),
                            type=pa.float64(),
                        ),
                    ],
                    schema=schema,
                )

                if writer is None:
                    writer = pq.ParquetWriter(PENDING, schema, compression="snappy")
                writer.write_table(table)

                measurements_written += table.num_rows
                missing_times += int(np.isnan(selected_times).sum())

            parts_read += len(numeric)
            if batch_number % 200 == 0:
                print(f"Scanned {parts_read:,} parts", flush=True)

    if parts_read != EXPECTED_PARTS:
        raise ValueError(
            f"Expected {EXPECTED_PARTS:,} parts; read {parts_read:,}"
        )
    if writer is None:
        raise ValueError("No measurements were written")

finally:
    if writer is not None:
        writer.close()

# Check the finished file before making it available for queries.
stored_rows = pq.ParquetFile(PENDING).metadata.num_rows
if stored_rows != measurements_written:
    raise ValueError(
        f"Wrote {measurements_written:,} rows; Parquet has {stored_rows:,}"
    )

PENDING.rename(FINAL)

# The existing pilot `measurements` table remains untouched.
with duckdb.connect(str(DB)) as con:
    path = FINAL.resolve().as_posix().replace("'", "''")
    con.execute(
        "CREATE OR REPLACE VIEW mapped_measurements AS "
        f"SELECT * FROM read_parquet('{path}')"
    )

print(f"Pairs loaded: {len(pairs):,}")
print(f"Parts scanned: {parts_read:,}")
print(f"Measurements loaded: {measurements_written:,}")
print(f"Measurements without a matched time: {missing_times:,}")
print("Query the complete data with: SELECT * FROM mapped_measurements LIMIT 10")