import argparse
from pathlib import Path

import duckdb


def main():
    parser = argparse.ArgumentParser(description="Run a SQL file against the quality database.")
    parser.add_argument("sql_file", type=Path, help="Path to the file containing SQL to execute")
    args = parser.parse_args()

    try:
        sql = args.sql_file.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError) as exc:
        parser.error(f"Cannot read SQL file: {exc}")
    if not sql.strip():
        parser.error("SQL file is empty")

    with duckdb.connect("data/processed/quality.duckdb") as con:
        results = con.execute(sql).fetchdf()
        print(results.to_string(index=False))


if __name__ == "__main__":
    main()
