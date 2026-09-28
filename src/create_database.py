import argparse
from pathlib import Path

import duckdb

def create_tables():
    parser = argparse.ArgumentParser(description="Create a table in the quality database.")
    parser.add_argument(
        "table",
        choices=("parts", "station_visits", "measurements"),
        help="Table to create",
    )
    args = parser.parse_args()

    database = Path("data/processed/quality.duckdb")
    sql = Path(f"sql/schema/create_{args.table}.sql").read_text(encoding="utf-8")
    database.parent.mkdir(parents=True, exist_ok=True)

    with duckdb.connect(str(database)) as connection:
        connection.execute(sql)

    print(f"Created table {args.table} in {database}")


if __name__ == "__main__":
    create_tables()
