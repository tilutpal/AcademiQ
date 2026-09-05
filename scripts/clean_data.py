"""
AcademiQ — Data Cleaner
Cleans raw table CSVs for all available semesters, removing SlNo and blank rows
while preserving page-level multi-group course headers.
"""

import csv
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "output"

def clean_semester_csv(input_file, output_file):
    if not input_file.exists():
        print(f"[Skip] {input_file} does not exist.")
        return

    with open(input_file, "r", encoding="utf-8-sig", newline="") as infile:
        reader = csv.reader(infile)
        rows = list(reader)

    clean_rows = []
    for row in rows:
        if not row or not any(row):
            continue

        # If first column is SlNo, check and strip
        first = str(row[0]).strip().lower()
        if first in ["slno", "sl no"]:
            # Header row
            clean_rows.append(row[1:])
        elif len(row) > 1 and re.match(r"^\d{7,10}$", str(row[1]).strip()):
            # Student row with SlNo in column 0
            clean_rows.append(row[1:])
        elif re.match(r"^\d{7,10}$", first):
            # Student row without SlNo
            clean_rows.append(row)
        elif any("regn" in str(c).lower() for c in row):
            # Header row without SlNo
            clean_rows.append(row)

    with open(output_file, "w", encoding="utf-8", newline="") as outfile:
        writer = csv.writer(outfile)
        writer.writerows(clean_rows)

    print(f"Cleaned {input_file.name} -> {output_file.name} ({len(clean_rows)} total rows)")

def main():
    for sem in [1, 2]:
        inp = OUTPUT_DIR / f"semester{sem}_data.csv"
        out = OUTPUT_DIR / f"semester{sem}_clean.csv"
        clean_semester_csv(inp, out)

if __name__ == "__main__":
    main()