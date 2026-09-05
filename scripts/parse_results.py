"""
AcademiQ — Dynamic Multi-Semester Result Parser & Extractor
Handles page-level dynamic course groupings and swapped branch subjects
across Semester 1 and Semester 2.
"""

import re
import csv
from pathlib import Path
import pymupdf

BASE_DIR = Path(__file__).resolve().parent.parent
PDF_DIR = BASE_DIR / "pdf"
OUTPUT_DIR = BASE_DIR / "output"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Department Code Mapping from Registration Number Prefix (digits 3-4)
DEPARTMENT_MAP = {
    "11": {"code": "CE", "name": "Civil Engineering"},
    "12": {"code": "ME", "name": "Mechanical Engineering"},
    "13": {"code": "EE", "name": "Electrical Engineering"},
    "14": {"code": "EC", "name": "Electronics & Communication Engineering"},
    "15": {"code": "CS", "name": "Computer Science & Engineering"},
    "16": {"code": "CH", "name": "Chemical Engineering"},
}

def clean_subject_code(raw_code):
    """Normalize subject code by removing newlines and fixing spacing."""
    if not raw_code:
        return ""
    code = str(raw_code).replace("\n", " ").strip()
    # Normalize 'CE102' -> 'CE 102'
    code = re.sub(r"([A-Za-z]{2,3})\s*(\d{3})", r"\1 \2", code)
    # Remove extra spaces
    code = re.sub(r"\s+", " ", code).strip()
    return code

def parse_semester_pdf(pdf_path, semester_num):
    """Extract and parse all student rows and subject grades from a semester PDF."""
    if not pdf_path.exists():
        print(f"[Warning] PDF not found: {pdf_path}")
        return [], [], {}

    doc = pymupdf.open(str(pdf_path))
    results = []
    summaries = []
    subjects_master = {}

    print(f"\nProcessing Semester {semester_num} from {pdf_path.name} ({len(doc)} pages)...", flush=True)

    for page_idx, page in enumerate(doc, start=1):
        tables = page.find_tables()
        if not tables.tables:
            continue

        for table in tables.tables:
            raw_rows = table.extract()
            if not raw_rows or len(raw_rows) < 2:
                continue

            # Locate header row containing Regn or Slno
            header_idx = -1
            for r_idx, r in enumerate(raw_rows):
                r_clean = [str(c).replace("\n", " ").strip().lower() for c in r if c]
                if any("regn" in c for c in r_clean) or any("slno" in c or "sl no" in c for c in r_clean):
                    header_idx = r_idx
                    break

            if header_idx == -1:
                continue

            raw_header = raw_rows[header_idx]
            header = [str(c).replace("\n", " ").strip() for c in raw_header]

            # Find subject start column (after Regn. No.)
            start_col = 0
            for idx, col in enumerate(header):
                if "regn" in col.lower():
                    start_col = idx + 1
                    break

            # Find GP column from right to left
            gp_col = -1
            for idx in range(len(header) - 1, -1, -1):
                if header[idx].upper() == "GP":
                    gp_col = idx
                    break

            if gp_col == -1 or start_col >= gp_col:
                continue

            # Extract subject list for this table section
            page_subjects = []
            c_idx = start_col
            while c_idx < gp_col:
                sub_code = clean_subject_code(header[c_idx])
                if not sub_code:
                    c_idx += 1
                    continue

                credits = None
                if c_idx + 1 < gp_col:
                    cred_txt = header[c_idx + 1]
                    m = re.search(r"\((\d+)\)", cred_txt)
                    if m:
                        credits = int(m.group(1))
                        c_idx += 2
                    else:
                        c_idx += 1
                else:
                    c_idx += 1

                if sub_code:
                    page_subjects.append({
                        "code": sub_code,
                        "credits": credits
                    })
                    if sub_code not in subjects_master and credits is not None:
                        subjects_master[sub_code] = credits

            # Tail headers e.g. ['GP', 'SGPA', 'EAA'] or ['GP', 'SGPA', 'CGPA', 'EAA']
            tail_headers = [header[k].upper() for k in range(gp_col, len(header))]

            # Process student data rows
            for row_idx in range(header_idx + 1, len(raw_rows)):
                row = raw_rows[row_idx]
                if not row or not any(row):
                    continue

                first_cell = str(row[0]).replace("\n", " ").strip().lower()
                if first_cell in ["slno", "sl no"] or "regn" in first_cell:
                    continue

                regn_no = str(row[start_col - 1]).strip()
                if not regn_no or not re.match(r"^\d{7,10}$", regn_no):
                    if re.match(r"^\d{7,10}$", first_cell):
                        regn_no = first_cell
                    else:
                        continue

                # Subject grades
                s_col = start_col
                for sub in page_subjects:
                    gp_val = str(row[s_col]).strip() if s_col < len(row) and row[s_col] is not None else ""
                    grade_val = str(row[s_col + 1]).strip() if (s_col + 1) < len(row) and row[s_col + 1] is not None else ""

                    # Skip non-credit EAA placeholder columns in subject records
                    if not sub["code"].startswith("EAA"):
                        is_blacked_out = (gp_val == "" or gp_val == "-") and (grade_val == "" or grade_val == "-")
                        if is_blacked_out:
                            results.append({
                                "regn_no": regn_no,
                                "semester": semester_num,
                                "subject_code": sub["code"],
                                "credits": "NA",
                                "grade_point": None,
                                "grade": "NA"
                            })
                        else:
                            results.append({
                                "regn_no": regn_no,
                                "semester": semester_num,
                                "subject_code": sub["code"],
                                "credits": sub["credits"] if sub["credits"] is not None else "NA",
                                "grade_point": float(gp_val) if gp_val.replace(".", "", 1).isdigit() else None,
                                "grade": grade_val if grade_val else "NA"
                            })
                    s_col += 2

                # Tail summary metrics
                gp_val = ""
                sgpa_val = ""
                cgpa_val = ""
                eaa_val = ""

                for offset, h_name in enumerate(tail_headers):
                    col_pos = gp_col + offset
                    if col_pos < len(row) and row[col_pos] is not None:
                        val = str(row[col_pos]).strip()
                        if h_name == "GP":
                            gp_val = val
                        elif h_name == "SGPA":
                            sgpa_val = val
                        elif h_name == "CGPA":
                            cgpa_val = val
                        elif h_name == "EAA":
                            eaa_val = val

                sgpa_float = float(sgpa_val) if sgpa_val.replace(".", "", 1).isdigit() else 0.0
                cgpa_float = float(cgpa_val) if cgpa_val.replace(".", "", 1).isdigit() else None

                summaries.append({
                    "regn_no": regn_no,
                    "semester": semester_num,
                    "gp": float(gp_val) if gp_val.replace(".", "", 1).isdigit() else 0.0,
                    "sgpa": sgpa_float,
                    "cgpa": cgpa_float,
                    "eaa": eaa_val if eaa_val and eaa_val != "-" else "Satisfactory"
                })

    doc.close()
    print(f"Semester {semester_num} extracted: {len(summaries)} students, {len(results)} course grade entries.")
    return summaries, results, subjects_master

def save_csvs(sem_num, summaries, results):
    """Save parsed summaries and results to CSV."""
    results_file = OUTPUT_DIR / f"semester{sem_num}_results.csv"
    summary_file = OUTPUT_DIR / f"semester{sem_num}_summary.csv"

    with open(results_file, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["regn_no", "semester", "subject_code", "credits", "grade_point", "grade"])
        for r in results:
            writer.writerow([r["regn_no"], r["semester"], r["subject_code"], r["credits"], r["grade_point"] if r["grade_point"] is not None else "", r["grade"]])

    with open(summary_file, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["regn_no", "semester", "GP", "SGPA", "CGPA", "EAA"])
        for s in summaries:
            writer.writerow([s["regn_no"], s["semester"], s["gp"], s["sgpa"], s["cgpa"] if s["cgpa"] is not None else "", s["eaa"]])

    print(f"Saved: {results_file.name}, {summary_file.name}")

def main():
    all_subjects = {}

    # Process Semesters 1 through 6
    for sem in [1, 2, 3, 4, 5, 6]:
        pdf_file = PDF_DIR / f"semester{sem}_results.pdf"
        if pdf_file.exists():
            summaries, results, subjects = parse_semester_pdf(pdf_file, sem)
            save_csvs(sem, summaries, results)
            all_subjects.update(subjects)

    # Save master subjects file
    subjects_file = OUTPUT_DIR / "subjects.csv"
    with open(subjects_file, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["subject_code", "credits"])
        for code, cred in sorted(all_subjects.items()):
            if not code.startswith("EAA"):
                writer.writerow([code, cred])
    print(f"Saved master subjects: {subjects_file.name} ({len(all_subjects)} total course codes)")

if __name__ == "__main__":
    main()