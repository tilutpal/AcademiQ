"""
AcademiQ — OCR Page Extractor for Scanned PDF Pages (Semesters 4 & 6)
Extracts student rows, grades, SGPA, and CGPA from image pages using RapidOCR.
"""

import re
import csv
from pathlib import Path
import pymupdf
import numpy as np
from rapidocr_onnxruntime import RapidOCR

BASE_DIR = Path(__file__).resolve().parent.parent
PDF_DIR = BASE_DIR / "pdf"
OUTPUT_DIR = BASE_DIR / "output"

def get_page_image_np(page, dpi=200):
    pix = page.get_pixmap(dpi=dpi)
    img_array = np.frombuffer(pix.samples, dtype=np.uint8)
    if pix.n == 4:
        img_array = img_array.reshape(pix.h, pix.w, 4)[:, :, :3]
    else:
        img_array = img_array.reshape(pix.h, pix.w, pix.n)
    return img_array

def process_ocr_page(page, engine):
    img = get_page_image_np(page, dpi=200)
    ocr_res, _ = engine(img)
    if not ocr_res:
        return []

    # Sort boxes top-to-bottom
    items = []
    for item in ocr_res:
        box, text, score = item
        x_center = (box[0][0] + box[1][0]) / 2.0
        y_center = (box[0][1] + box[2][1]) / 2.0
        items.append({
            "text": text.strip(),
            "x": x_center,
            "y": y_center,
            "h": abs(box[2][1] - box[0][1])
        })

    # Group into lines by y-coordinate
    items.sort(key=lambda item: item["y"])
    lines = []
    current_line = []
    current_y = None

    for item in items:
        if current_y is None or abs(item["y"] - current_y) < 12:
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

def test_ocr_extraction():
    engine = RapidOCR()
    for sem in [4, 6]:
        pdf_path = PDF_DIR / f"semester{sem}_results.pdf"
        if not pdf_path.exists():
            continue
        doc = pymupdf.open(str(pdf_path))
        print(f"\n--- Semester {sem} ({len(doc)} pages) ---", flush=True)
        for i, page in enumerate(doc):
            text_content = page.get_text().strip()
            if len(text_content) < 50:
                lines = process_ocr_page(page, engine)
                student_ids = []
                for line in lines:
                    line_txt = " | ".join([item["text"] for item in line])
                    m = re.search(r"\b(2[1234]\d{5})\b", line_txt)
                    if m:
                        student_ids.append(m.group(1))
                print(f"Page {i+1} (SCANNED): {len(lines)} OCR lines, {len(student_ids)} students found: {student_ids[:5]}...", flush=True)

if __name__ == "__main__":
    test_ocr_extraction()
