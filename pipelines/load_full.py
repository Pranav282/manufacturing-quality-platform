"""Run both table pipelines in one transaction."""

import sys
from pathlib import Path

# Make src importable when running python pipelines/load_full.py directly.
if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.load_common import run_loaders
from src.load_parts import load_parts
from src.load_station_visits import load_station_visits


if __name__ == "__main__":
    run_loaders(load_parts, load_station_visits)
