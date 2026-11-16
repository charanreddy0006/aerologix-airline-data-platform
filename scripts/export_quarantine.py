"""Export manually corrected quarantine JSONL records as a feed CSV for review."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from aerologix.load import FEEDS


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="corrected quarantine JSONL file")
    parser.add_argument("output", type=Path, help="destination CSV path")
    args = parser.parse_args()
    basename = args.input.name.removesuffix(".jsonl")
    feed_name = basename.rsplit("-", 1)[-1]
    feed = next((item for item in FEEDS if item.filename == feed_name), None)
    if feed is None:
        raise SystemExit(f"Could not infer a supported feed name from {args.input.name!r}")
    records = []
    with args.input.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            item = json.loads(line)
            record = item.get("record")
            if not isinstance(record, dict) or set(record) != set(feed.headers):
                raise ValueError(f"Line {line_number}: corrected record fields must exactly match {feed.headers}")
            records.append(record)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=feed.headers)
        writer.writeheader()
        writer.writerows(records)
    print(f"Exported {len(records)} corrected rows to {args.output}; review and merge before loading")


if __name__ == "__main__":
    main()
