import duckdb

with duckdb.connect("data/processed/quality.duckdb", read_only=True) as con:
    checks = {
        "parts": "SELECT COUNT(*) FROM parts",
        "failures": "SELECT COUNT(*) FROM parts WHERE response = 1",
        "station_visits": "SELECT COUNT(*) FROM station_visits",
        "distinct_stations": "SELECT COUNT(DISTINCT station) FROM station_visits",
        "parts_without_visits": """
            SELECT COUNT(*)
            FROM parts p
            WHERE NOT EXISTS (
                SELECT 1 FROM station_visits v WHERE v.part_id = p.part_id
            )
        """,
        "orphan_visits": """
            SELECT COUNT(*)
            FROM station_visits v
            WHERE NOT EXISTS (
                SELECT 1 FROM parts p WHERE p.part_id = v.part_id
            )
        """,
        "invalid_time_order": """
            SELECT COUNT(*) FROM station_visits
            WHERE first_observed_time > last_observed_time
        """,
    }

    for name, query in checks.items():
        print(f"{name}: {con.execute(query).fetchone()[0]:,}")