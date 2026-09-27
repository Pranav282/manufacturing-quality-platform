from collections import defaultdict

import pandas as pd

N = 20_000

dates = pd.read_csv("data/raw/train_date.csv", nrows=N)
labels = pd.read_csv(
    "data/raw/train_numeric.csv",
    usecols=["Id", "Response"],
    nrows=N,
)

sample = dates.merge(labels, on="Id", validate="one_to_one")
station_columns = defaultdict(list)

for column in dates.columns:
    if column != "Id":
        station = "_".join(column.split("_")[:2])
        station_columns[station].append(column)

results = []
for station, columns in station_columns.items():
    visited = sample[columns].notna().any(axis=1)
    parts = int(visited.sum())
    failures = int(sample.loc[visited, "Response"].sum())

    results.append({
        "station": station,
        "parts_visited": parts,
        "failed_parts": failures,
        "failure_rate": failures / parts if parts else None,
    })

summary = pd.DataFrame(results).sort_values(
    "parts_visited", ascending=False
)

print(f"Sample parts: {len(sample):,}")
print(f"Sample failures: {int(sample['Response'].sum()):,}")
print("\nMost visited stations:")
print(summary.head(10).to_string(index=False))
print("\nLeast visited stations:")
print(summary.tail(10).to_string(index=False))