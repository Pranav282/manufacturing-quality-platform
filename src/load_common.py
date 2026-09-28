"""Shared settings and transaction handling for the table loaders."""

from pathlib import Path

import duckdb

RAW = Path("data/raw")
DB = Path("data/processed/quality.duckdb")
CHUNK_SIZE = 10_000
EXPECTED_ROWS = 1_183_747


def run_loaders(*loaders, raw=RAW, db=DB, chunk_size=CHUNK_SIZE,
                expected_rows=EXPECTED_ROWS):
    """Run one or more table loaders atomically and report committed totals."""
    totals = {}
    with duckdb.connect(str(db)) as connection:
        connection.execute("BEGIN TRANSACTION")
        try:
            for loader in loaders:
                totals.update(loader(connection, Path(raw), chunk_size, expected_rows))

            # A standalone parts refresh must not orphan existing station visits.
            orphan = connection.execute("""
                SELECT 1 FROM station_visits v
                WHERE NOT EXISTS (
                    SELECT 1 FROM parts p WHERE p.part_id = v.part_id
                ) LIMIT 1
            """).fetchone()
            if orphan:
                raise ValueError("Station visits reference IDs missing from parts")
            connection.execute("COMMIT")
        except Exception:
            connection.execute("ROLLBACK")
            raise

    for label, count in totals.items():
        print(f"{label}: {count:,}")
    return totals
