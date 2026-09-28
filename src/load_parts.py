"""Load part IDs and failure labels from train_numeric.csv."""

import pandas as pd

if __package__:
    from .load_common import run_loaders
else:
    from load_common import run_loaders


def load_parts(connection, raw, chunk_size, expected_rows):
    """Replace parts within the transaction owned by run_loaders."""
    total_parts = 0
    total_failures = 0
    connection.execute("DELETE FROM parts")

    # Read only the two columns needed by the parts table, in bounded batches.
    with pd.read_csv(raw / "train_numeric.csv", usecols=["Id", "Response"],
                     chunksize=chunk_size) as reader:
        for batch_number, numeric in enumerate(reader, start=1):
            if numeric["Id"].isna().any():
                raise ValueError(f"Batch {batch_number}: missing ID")
            if numeric["Id"].duplicated().any():
                raise ValueError(f"Batch {batch_number}: duplicate ID")
            if not numeric["Response"].isin([0, 1]).all():
                raise ValueError(f"Batch {batch_number}: invalid Response")

            parts = numeric.rename(columns={"Id": "part_id", "Response": "response"})
            connection.register("batch_parts", parts)
            try:
                # The primary key also catches duplicate IDs across batches.
                connection.execute("INSERT INTO parts SELECT * FROM batch_parts")
            finally:
                connection.unregister("batch_parts")
            total_parts += len(parts)
            total_failures += int(parts["response"].sum())
            if batch_number % 10 == 0:
                print(f"Processed {total_parts:,} parts", flush=True)

    if total_parts != expected_rows:
        raise ValueError(f"Expected {expected_rows:,} parts; found {total_parts:,}")
    stored = connection.execute(
        "SELECT COUNT(*), COALESCE(SUM(response), 0) FROM parts"
    ).fetchone()
    if stored != (total_parts, total_failures):
        raise ValueError("Stored parts counts do not match ingestion counts")
    return {"Loaded parts": total_parts, "Failed parts": total_failures}


if __name__ == "__main__":
    run_loaders(load_parts)
