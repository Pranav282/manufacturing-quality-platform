# Save as src/inspect_headers.py
import csv
from pathlib import Path

for filename in ("train_numeric.csv", "train_date.csv"):
    path = Path("data/raw") / filename

    with path.open(newline="", encoding="utf-8") as file:
        reader = csv.reader(file)
        columns = next(reader)
        first_rows = [next(reader) for _ in range(3)]

    print(f"\n{filename}")
    print(f"Columns: {len(columns):,}")
    print(f"First 10 names: {columns[:10]}")
    print(f"Last 5 names: {columns[-5:]}")
    print(f"First 3 IDs: {[row[0] for row in first_rows]}")
    print(f"First 3 row widths: {[len(row) for row in first_rows]}")