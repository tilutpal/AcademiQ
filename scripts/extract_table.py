"""
AcademiQ — PDF Table Extractor
Extracts tables across all available semester PDFs in pdf/ directory to output/
"""

import pymupdf
import csv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
PDF_DIR = BASE_DIR / "pdf"
OUTPUT_DIR = BASE_DIR / "output"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def extract_pdf_tables(pdf_path, output_csv_path):
    if not pdf_path.exists():
        print(f"[Skip] File not found: {pdf_path}")
        return

    doc = pymupdf.open(str(pdf_path))
    all_rows = []

    print(f"Extracting tables from {pdf_path.name} ({len(doc)} pages)...")

    for page_number, page in enumerate(doc, start=1):
        tables = page.find_tables()
        if not tables.tables:
            continue

        for table in tables.tables:
            rows = table.extract()
            if rows:
                for row in rows:
                    all_rows.append(row)

    doc.close()

    with open(output_csv_path, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        for row in all_rows:
            writer.writerow(row)

    print(f"Extracted {len(all_rows)} raw rows -> {output_csv_path.name}")

def main():
    for sem in [1, 2]:
        pdf_file = PDF_DIR / f"semester{sem}_results.pdf"
        output_file = OUTPUT_DIR / f"semester{sem}_data.csv"
        if pdf_file.exists():
            extract_pdf_tables(pdf_file, output_file)

if __name__ == "__main__":
    main()