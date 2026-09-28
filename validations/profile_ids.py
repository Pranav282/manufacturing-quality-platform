from collections import Counter
from pathlib import Path

import pandas as pd

RAW = Path("data/raw")
CHUNK_SIZE = 100_000


def profile(filename, columns):
    ids = set()
    duplicate_count = 0
    row_count = 0
    labels = Counter()

    for chunk in pd.read_csv(
        RAW / filename,
        usecols=columns,
        chunksize=CHUNK_SIZE,
    ):
        row_count += len(chunk)

        chunk_ids = chunk["Id"]
        duplicate_count += len(chunk_ids) - chunk_ids.nunique()
        duplicate_count += sum(part_id in ids for part_id in chunk_ids.unique())
        ids.update(chunk_ids)

        if "Response" in chunk:
            labels.update(chunk["Response"].value_counts(dropna=False).to_dict())

    print(f"{filename}: {row_count:,} rows, {len(ids):,} unique IDs")
    print(f"Duplicate IDs: {duplicate_count:,}")
    if labels:
        print(f"Response counts: {dict(labels)}")

    return ids


numeric_ids = profile("train_numeric.csv", ["Id", "Response"])
date_ids = profile("train_date.csv", ["Id"])

print(f"Numeric IDs missing from date: {len(numeric_ids - date_ids):,}")
print(f"Date IDs missing from numeric: {len(date_ids - numeric_ids):,}")