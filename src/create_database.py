from pathlib import Path

import duckdb

database = Path("data/processed/quality.duckdb")
database.parent.mkdir(parents=True, exist_ok=True)

with duckdb.connect(str(database)) as connection:
    connection.execute(Path("sql/create_tables.sql").read_text())

print(f"Created tables in {database}")