import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import pyarrow.parquet as pq

RAW = Path("data/raw")
DB = Path("data/processed/quality.duckdb")
PARQUET = Path("data/processed/mapped_measurements.parquet")
REPORT = Path("reports/phase3_validation.json")


def header(path):
    with path.open(newline="", encoding="utf-8") as file:
        return next(csv.reader(file))


numeric_columns = header(RAW / "train_numeric.csv")
date_columns = header(RAW / "train_date.csv")

with duckdb.connect(str(DB), read_only=True) as con:
    parts, failures = con.execute(
        "SELECT COUNT(*), SUM(response) FROM parts"
    ).fetchone()
    station_rows, stations = con.execute(
        "SELECT COUNT(*), COUNT(DISTINCT station) FROM station_visits"
    ).fetchone()
    measurements, features, missing_times = con.execute("""
        SELECT COUNT(*),
               COUNT(DISTINCT feature_name),
               COUNT(*) FILTER (WHERE observed_time IS NULL)
        FROM mapped_measurements
    """).fetchone()

parquet_rows = pq.ParquetFile(PARQUET).metadata.num_rows

checks = {
    "part_count": parts == 1_183_747,
    "failure_count": failures == 6_879,
    "station_count": stations == 52,
    "measurement_count_matches_parquet": measurements == parquet_rows,
    "mapped_feature_count": features == 366,
    "matched_times_present": missing_times == 0,
    "numeric_header_shape": len(numeric_columns) == 970,
    "date_header_shape": len(date_columns) == 1_157,
}

report = {
    "created_utc": datetime.now(timezone.utc).isoformat(),
    "source": {
        "numeric_file": "train_numeric.csv",
        "numeric_columns": len(numeric_columns),
        "numeric_header_sha256": hashlib.sha256(
            json.dumps(numeric_columns).encode()
        ).hexdigest(),
        "date_file": "train_date.csv",
        "date_columns": len(date_columns),
        "date_header_sha256": hashlib.sha256(
            json.dumps(date_columns).encode()
        ).hexdigest(),
    },
    "loaded": {
        "parts": parts,
        "failed_parts": failures,
        "station_observations": station_rows,
        "distinct_stations": stations,
        "mapped_measurements": measurements,
        "mapped_features": features,
        "missing_matched_times": missing_times,
    },
    "coverage_note": (
        "366 numeric features were loaded with directly matched date columns. "
        "602 other numeric features remain in the raw CSV; their individual "
        "measurement times have not been established."
    ),
    "checks": checks,
    "status": "passed" if all(checks.values()) else "failed",
}

REPORT.parent.mkdir(parents=True, exist_ok=True)
REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")

print(f"Phase 3 validation: {report['status']}")
print(f"Report: {REPORT}")
for name, passed in checks.items():
    print(f"{name}: {'PASS' if passed else 'FAIL'}")

if not all(checks.values()):
    raise SystemExit("One or more validation checks failed")