"""
AcademiQ — Complete Subject Grade Extractor for Scanned PDF Pages (Semesters 4 & 6)
Parses full course grade breakdowns for all students on scanned pages using exact department course mappings
and robust grade-token pairing.
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

DEPARTMENT_MAP = {
    "11": "CE",
    "12": "ME",
    "13": "EE",
    "14": "EC",
    "15": "CS",
    "16": "CH",
}

# Authoritative Department Subjects for Semesters 4 & 6
DEPT_SUBJECTS_SEM6 = {
    "CE": ["CE 306", "CE 307", "CE 308", "CE 309", "CE 315", "CE 316", "CE 317", "CE 331", "CE 332", "CE 334", "CE 381", "CE 382", "CS 382", "EC 382", "EC 389", "EI 381"],
    "ME": ["CS 382", "EC 389", "ME 307", "ME 308", "ME 309", "ME 310", "ME 314", "ME 315", "ME 316", "ME 332", "ME 338", "ME 339", "ME 381", "ME 383", "ME 385", "ME 5138"],
    "EE": ["EE 307", "EE 308", "EE 309", "EE 310", "EE 314", "EE 315", "EE 316", "EE 331", "EE 332", "EE 385", "CE 382", "CS 382", "EC 382", "EC 389", "EI 381"],
    "EC": ["CS 382", "EC 307", "EC 308", "EC 309", "EC 310", "EC 314", "EC 315", "EC 316", "EC 333", "EC 337", "EC 382", "EC 389", "EE 385", "EI 381"],
    "CS": ["CE 382", "CS 306", "CS 307", "CS 308", "CS 309", "CS 314", "CS 315", "CS 316", "CS 331", "CS 332", "CS 382", "EC 382", "EC 389", "EE 385", "EI 381"],
    "EI": ["CE 382", "CS 382", "EC 382", "EC 389", "EE 385", "EI 306", "EI 307", "EI 308", "EI 315", "EI 316", "EI 317", "EI 318", "EI 331", "EI 338", "EI 381", "EI 382"],
}

DEPT_SUBJECTS_SEM4 = {
    "CE": ["CE 206", "CE 207", "CE 208", "CE 209", "CE 215", "CE 216", "CE 217", "MA 204"],
    "ME": ["ME 206", "ME 207", "ME 208", "ME 209", "ME 214", "ME 215", "ME 216", "MA 204"],
    "EE": ["EE 206", "EE 207", "EE 208", "EE 209", "EE 214", "EE 215", "EE 216", "MA 204"],
    "EC": ["EC 206", "EC 207", "EC 208", "EC 209", "EC 214", "EC 215", "EC 216", "MA 204"],
    "CS": ["CS 206", "CS 207", "CS 208", "CS 209", "CS 214", "CS 215", "CS 216", "MA 204"],
    "CH": ["CH 206", "CH 207", "CH 208", "CH 209", "CH 214", "CH 215", "CH 216", "MA 204"],
}

CREDITS_MAP = {
    "CE 306": 3, "CE 307": 4, "CE 308": 4, "CE 309": 4, "CE 315": 2, "CE 316": 2, "CE 317": 2, "CE 331": 4, "CE 332": 4, "CE 334": 4, "CE 381": 3, "CE 382": 3,
    "CS 306": 3, "CS 307": 4, "CS 308": 4, "CS 309": 4, "CS 314": 2, "CS 315": 2, "CS 316": 2, "CS 331": 4, "CS 332": 4, "CS 382": 3,
    "EC 307": 4, "EC 308": 4, "EC 309": 4, "EC 310": 4, "EC 314": 2, "EC 315": 2, "EC 316": 2, "EC 333": 3, "EC 337": 3, "EC 382": 3, "EC 389": 3,
    "EE 307": 4, "EE 308": 4, "EE 309": 4, "EE 310": 4, "EE 314": 2, "EE 315": 2, "EE 316": 2, "EE 331": 4, "EE 332": 4, "EE 385": 3,
    "EI 306": 4, "EI 307": 4, "EI 308": 4, "EI 315": 2, "EI 316": 2, "EI 317": 2, "EI 318": 2, "EI 331": 4, "EI 338": 3, "EI 381": 3, "EI 382": 3,
    "ME 307": 4, "ME 308": 4, "ME 309": 4, "ME 310": 4, "ME 314": 2, "ME 315": 2, "ME 316": 2, "ME 332": 3, "ME 338": 3, "ME 339": 3, "ME 381": 3, "ME 383": 3, "ME 385": 3, "ME 5138": 3,
    "CE 206": 4, "CE 207": 4, "CE 208": 4, "CE 209": 3, "CE 215": 2, "CE 216": 2, "CE 217": 2, "MA 204": 3,
    "CS 206": 4, "CS 207": 4, "CS 208": 4, "CS 209": 3, "CS 214": 2, "CS 215": 2, "CS 216": 2,
    "EC 206": 4, "EC 207": 4, "EC 208": 4, "EC 209": 3, "EC 214": 2, "EC 215": 2, "EC 216": 2,
    "EE 206": 4, "EE 207": 4, "EE 208": 4, "EE 209": 3, "EE 214": 2, "EE 215": 2, "EE 216": 2,
    "ME 206": 4, "ME 207": 4, "ME 208": 4, "ME 209": 3, "ME 214": 2, "ME 215": 2, "ME 216": 2,
    "CH 206": 4, "CH 207": 4, "CH 208": 4, "CH 209": 3, "CH 214": 2, "CH 215": 2, "CH 216": 2
}

GRADE_POINTS = {
    "AA": 10, "AB": 9, "BB": 8, "BC": 7, "CC": 6, "CD": 5, "DD": 4, "F": 0
}

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

def extract_grades_from_tokens(tokens):
    grades = []
    i = 0
    gp_to_letter = {10: "AA", 9: "AB", 8: "BB", 7: "BC", 6: "CC", 5: "CD", 4: "DD", 0: "F"}

    while i < len(tokens):
        t = tokens[i].upper()
        if t in GRADE_POINTS:
            res_letter = t
            res_gp = GRADE_POINTS[t]
            grades.append((res_letter, res_gp))
            i += 1
        elif t.isdigit() and int(t) in [0, 4, 5, 6, 7, 8, 9, 10]:
            v = int(t)
            if i + 1 < len(tokens) and tokens[i+1].upper() in GRADE_POINTS:
                res_letter = tokens[i+1].upper()
                grades.append((res_letter, v))
                i += 2
            else:
                res_letter = gp_to_letter.get(v, "AA")
                grades.append((res_letter, v))
                i += 1
        else:
            i += 1

    return grades

def run_extraction():
    engine = RapidOCR()
    
    for sem in [4, 6]:
        pdf_path = PDF_DIR / f"semester{sem}_results.pdf"
        if not pdf_path.exists():
            continue

        doc = pymupdf.open(str(pdf_path))
        print(f"\n[OCR Robust Subject Grade Extractor] Processing Semester {sem}...", flush=True)

        res_file = OUTPUT_DIR / f"semester{sem}_results.csv"
        
        # Identify regn_nos present on scanned pages
        scanned_regns = set()
        for page in doc:
            if len(page.get_text().strip()) < 50:
                lines = process_ocr_lines(page, engine)
                for l in lines:
                    line_str = " ".join([x["text"] for x in l])
                    m = re.search(r"\b(2[1234]\d{5})\b", line_str)
                    if m:
                        scanned_regns.add(m.group(1))

        # Keep existing results from digital pages only
        existing_results = []
        if res_file.exists():
            with open(res_file, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for r in reader:
                    if r["regn_no"] not in scanned_regns:
                        existing_results.append(r)

        existing_pairs = set((r["regn_no"], r["subject_code"]) for r in existing_results)
        dept_subjects_map = DEPT_SUBJECTS_SEM6 if sem == 6 else DEPT_SUBJECTS_SEM4

        new_entries = 0

        for page_idx, page in enumerate(doc, start=1):
            text_content = page.get_text().strip()
            if len(text_content) >= 50:
                continue

            lines = process_ocr_lines(page, engine)

            for line in lines:
                tokens = [item["text"] for item in line]
                line_str = " ".join(tokens)

                m_regn = re.search(r"\b(2[1234]\d{5})\b", line_str)
                if not m_regn:
                    continue

                regn_no = m_regn.group(1)
                dept_code = DEPARTMENT_MAP.get(regn_no[2:4], "CE")
                active_subjects = dept_subjects_map.get(dept_code, dept_subjects_map["CE"])

                parsed_grades = extract_grades_from_tokens(tokens[1:])

                if parsed_grades:
                    matched_count = min(len(active_subjects), len(parsed_grades))
                    for k in range(matched_count):
                        sub_code = active_subjects[k]
                        grd, gp = parsed_grades[k]
                        cred = CREDITS_MAP.get(sub_code, 3)

                        if (regn_no, sub_code) not in existing_pairs:
                            existing_pairs.add((regn_no, sub_code))
                            existing_results.append({
                                "regn_no": regn_no,
                                "semester": str(sem),
                                "subject_code": sub_code,
                                "credits": str(cred),
                                "grade_point": str(gp),
                                "grade": grd
                            })
                            new_entries += 1

        print(f"Semester {sem}: Generated {new_entries} complete department-specific course grade entries.", flush=True)

        # Write updated results CSV
        with open(res_file, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["regn_no", "semester", "subject_code", "credits", "grade_point", "grade"])
            for r in existing_results:
                writer.writerow([r["regn_no"], r["semester"], r["subject_code"], r["credits"], r["grade_point"], r["grade"]])

if __name__ == "__main__":
    run_extraction()
