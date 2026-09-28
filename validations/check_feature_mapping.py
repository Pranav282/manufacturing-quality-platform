import csv
import re

def headers(path):
    with open(path, newline="", encoding="utf-8") as file:
        return next(csv.reader(file))

numeric = headers("data/raw/train_numeric.csv")
dates = set(headers("data/raw/train_date.csv"))

mapped = []
unmapped = []

for feature in numeric:
    match = re.fullmatch(r"(L\d+_S\d+)_F(\d+)", feature)
    if not match:
        continue

    station, number = match.groups()
    date_feature = f"{station}_D{int(number) + 1}"

    if date_feature in dates:
        mapped.append((feature, date_feature))
    else:
        unmapped.append(feature)

print(f"Numeric features mapped: {len(mapped):,}")
print(f"Numeric features without a matching date: {len(unmapped):,}")
print("First 10 mappings:", mapped[:10])
print("First 10 unmapped:", unmapped[:10])