import pandas as pd

N = 20_000

for name in ("train_numeric", "train_date"):
    df = pd.read_csv(f"data/raw/{name}.csv", nrows=N)

    coverage = df.notna().mean()
    feature_coverage = coverage.drop(labels=["Id", "Response"], errors="ignore")

    print(f"\n{name}: {len(df):,} sampled rows")
    print(f"Feature coverage — min: {feature_coverage.min():.1%}, "
          f"median: {feature_coverage.median():.1%}, "
          f"max: {feature_coverage.max():.1%}")
    print(f"Features entirely empty in sample: {(feature_coverage == 0).sum():,}")
    print(f"Features over 90% empty: {(feature_coverage < 0.10).sum():,}")

    if name == "train_date":
        stations = sorted({
            "_".join(column.split("_")[:2])
            for column in feature_coverage.index
        })
        print(f"Distinct station names in schema: {len(stations)}")
        print(f"First 10: {stations[:10]}")