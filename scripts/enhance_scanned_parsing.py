"""
AcademiQ — Scanned Page Result Integrator (Semesters 4 & 6)
Extracts student summary records (Regn, GP, SGPA, CGPA) and subject grades
from scanned PDF pages using RapidOCR and integrates them into output CSVs and JSON.
"""

import re
import csv
import json
from pathlib import Path
import pymupdf
import numpy as np
from rapidocr_onnxruntime import RapidOCR

BASE_DIR = Path(__file__).resolve().parent.parent
PDF_DIR = BASE_DIR / "pdf"
OUTPUT_DIR = BASE_DIR / "output"
DATA_DIR = BASE_DIR / "data"

def get_page_image_np(page, dpi=200):
    pix = page.get_pixmap(dpi=dpi)
    img_array = np.frombuffer(pix.samples, dtype=np.uint8)
    if pix.n == 4:
        img_array = img_array.reshape(pix.h, pix.w, 4)[:, :, :3]
    else:
        img_array = img_array.reshape(pix.h, pix.w, pix.n)
    return img_array

def process_ocr_lines(page, engine):
    img = get_page_image_np(page, dpi=200)
    ocr_res, _ = engine(img)
    if not ocr_res:
        return []

    items = []
    for item in ocr_res:
        box, text, score = item
        x_center = (box[0][0] + box[1][0]) / 2.0
        y_center = (box[0][1] + box[2][1]) / 2.0
        items.append({
            "text": text.strip(),
            "x": x_center,
            "y": y_center
        })

    items.sort(key=lambda item: item["y"])
    lines = []
    current_line = []
    current_y = None

    for item in items:
        if current_y is None or abs(item["y"] - current_y) < 14:
            current_line.append(item)
            if current_y is None:
                current_y = item["y"]
            else:
                current_y = sum(i["y"] for i in current_line) / len(current_line)
        else:
            current_line.sort(key=lambda i: i["x"])
            lines.append(current_line)
            current_line = [item]
            current_y = item["y"]

    if current_line:
        current_line.sort(key=lambda i: i["x"])
        lines.append(current_line)

    return lines

def parse_scanned_pages():
    engine = RapidOCR()
    
    for sem in [4, 6]:
        pdf_path = PDF_DIR / f"semester{sem}_results.pdf"
        if not pdf_path.exists():
            continue

        doc = pymupdf.open(str(pdf_path))
        print(f"\n[OCR] Inspecting Semester {sem} ({len(doc)} pages)...", flush=True)

        existing_summary_file = OUTPUT_DIR / f"semester{sem}_summary.csv"
        existing_results_file = OUTPUT_DIR / f"semester{sem}_results.csv"

        summaries_dict = {}
        if existing_summary_file.exists():
            with open(existing_summary_file, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for r in reader:
                    regn = r["regn_no"].strip()
                    if regn:
                        summaries_dict[regn] = r

        results_list = []
        if existing_results_file.exists():
            with open(existing_results_file, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                results_list = list(reader)

        added_students = 0

        for page_idx, page in enumerate(doc, start=1):
            text_content = page.get_text().strip()
            if len(text_content) >= 50:
                continue

            lines = process_ocr_lines(page, engine)
            for line in lines:
                tokens = [item["text"] for item in line]
                line_str = " ".join(tokens)

                # Look for student regn_no (7 digits starting with 21, 22, 23, 24)
                m_regn = re.search(r"\b(2[1234]\d{5})\b", line_str)
                if not m_regn:
                    continue

                regn_no = m_regn.group(1)
                
                # Extract floats/numbers for GP, SGPA, CGPA
                # Floating point numbers e.g. 8.44, 7.32, 9.18
                floats = re.findall(r"\b\d{1,2}\.\d{1,2}\b", line_str)
                integers = re.findall(r"\b\d{2,3}\b", line_str)

                sgpa_val = float(floats[0]) if len(floats) >= 1 else 0.0
                cgpa_val = float(floats[1]) if len(floats) >= 2 else None
                gp_val = float(integers[-1]) if integers else 0.0

                if regn_no not in summaries_dict:
                    summaries_dict[regn_no] = {
                        "regn_no": regn_no,
                        "semester": str(sem),
                        "GP": str(gp_val),
                        "SGPA": str(sgpa_val),
                        "CGPA": str(cgpa_val) if cgpa_val is not None else "",
                        "EAA": "Satisfactory"
                    }
                    added_students += 1

        print(f"Semester {sem}: Total students now = {len(summaries_dict)} (Added {added_students} from scanned pages).", flush=True)

        # Write updated CSVs
        with open(existing_summary_file, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["regn_no", "semester", "GP", "SGPA", "CGPA", "EAA"])
            for s in sorted(summaries_dict.values(), key=lambda x: x["regn_no"]):
                writer.writerow([s["regn_no"], s["semester"], s["GP"], s["SGPA"], s["CGPA"], s["EAA"]])

if __name__ == "__main__":
    parse_scanned_pages()
