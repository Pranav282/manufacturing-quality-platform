# Save as src/inspect_headers.py
import csv
from itertools import islice
from pathlib import Path

import pandas as pd

for filename in ("train_numeric.csv", "train_date.csv"):
    path = Path("data/raw") / filename

    with path.open(newline="", encoding="utf-8") as file:
        reader = csv.reader(file)
        columns = next(reader)
        first_rows = list(islice(reader, 3))

    print(f"\n{filename}")
    print(f"Columns: {len(columns):,}")
    print(f"First 10 names: {columns[:10]}")
    print(f"Last 5 names: {columns[-5:]}")
    df = pd.DataFrame(first_rows, columns=columns)
    print("\nDataFrame preview:")
    print(df.head(3))
