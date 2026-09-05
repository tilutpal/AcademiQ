"""
AcademiQ — Multi-Semester JSON & JS Dataset Exporter
Aggregates semester results without subject names, computes SGPA & CGPA,
and generates client-side database files.
Preserves official result sheet values and stores blacked-out/unread subjects as NA without synthetic inputs.
"""

import csv
import json
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "output"
DATA_DIR = BASE_DIR / "data"

DEPARTMENT_MAP = {
    "11": {"code": "CE", "name": "Civil Engineering"},
    "12": {"code": "ME", "name": "Mechanical Engineering"},
    "13": {"code": "EE", "name": "Electrical Engineering"},
    "14": {"code": "EC", "name": "Electronics & Communication Engineering"},
    "15": {"code": "CS", "name": "Computer Science & Engineering"},
    "16": {"code": "CH", "name": "Chemical Engineering"},
}

def get_department_info(regn_no):
    """Derive department and batch from registration number."""
    if len(regn_no) >= 4:
        batch_prefix = regn_no[:2]
        dept_prefix = regn_no[2:4]
        batch_year = f"20{batch_prefix}" if batch_prefix.isdigit() else "2023"
        dept_info = DEPARTMENT_MAP.get(dept_prefix, {"code": "GEN", "name": "Engineering Department"})
        return dept_info["name"], dept_info["code"], batch_year
    return "Engineering Department", "GEN", "2023"

def export_data():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Load Master Subjects
    subjects_file = OUTPUT_DIR / "subjects.csv"
    subjects_master = {}
    if subjects_file.exists():
        with open(subjects_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                code = row["subject_code"].strip()
                credits_val = int(row["credits"]) if row.get("credits") and row["credits"].strip().isdigit() else "NA"
                subjects_master[code] = {
                    "code": code,
                    "credits": credits_val
                }

    # 2. Collect summaries and results across all available semesters
    students_db = {}
    semester_files = sorted(OUTPUT_DIR.glob("semester*_summary.csv"))

    for sum_file in semester_files:
        m = re.search(r"semester(\d+)_summary\.csv", sum_file.name)
        if not m:
            continue
        sem_num = int(m.group(1))
        res_file = OUTPUT_DIR / f"semester{sem_num}_results.csv"

        # Load results for this semester
        sem_results = {}
        if res_file.exists():
            with open(res_file, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    regn = row["regn_no"].strip()
                    code = row["subject_code"].strip()
                    cred_str = row.get("credits", "").strip()
                    
                    if cred_str.isdigit():
                        cred = int(cred_str)
                    elif cred_str.upper() in ["NA", "N/A", ""]:
                        cred = "NA"
                    else:
                        master_cred = subjects_master.get(code, {}).get("credits", "NA")
                        cred = master_cred

                    gp_txt = row.get("grade_point", "").strip()
                    grade = row.get("grade", "").strip()
                    if not grade or grade.upper() in ["N/A", "NA"]:
                        grade = "NA"

                    gp = float(gp_txt) if gp_txt and gp_txt.replace(".", "", 1).isdigit() else None
                    if regn not in sem_results:
                        sem_results[regn] = []
                    
                    sem_results[regn].append({
                        "subject_code": code,
                        "credits": cred,
                        "grade_point": gp,
                        "grade": grade
                    })

        # Load summaries for this semester
        with open(sum_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                regn = row["regn_no"].strip()
                if not regn:
                    continue

                gp_val = float(row["GP"]) if row.get("GP") and row["GP"].strip().replace(".", "", 1).isdigit() else 0.0
                sgpa_val = float(row["SGPA"]) if row.get("SGPA") and row["SGPA"].strip().replace(".", "", 1).isdigit() else 0.0
                cgpa_val = float(row["CGPA"]) if row.get("CGPA") and row["CGPA"].strip().replace(".", "", 1).isdigit() else None
                eaa_val = row.get("EAA", "").strip()
                if not eaa_val or eaa_val == "-":
                    eaa_val = "Satisfactory"

                dept_name, dept_code, batch_year = get_department_info(regn)

                if regn not in students_db:
                    students_db[regn] = {
                        "regn_no": regn,
                        "department": dept_name,
                        "dept_code": dept_code,
                        "batch_year": batch_year,
                        "semesters": {}
                    }

                subs = sem_results.get(regn, [])

                # Sum only valid numeric credits
                total_credits = sum(s["credits"] for s in subs if isinstance(s["credits"], (int, float)))
                earned_credits = sum(s["credits"] for s in subs if isinstance(s["credits"], (int, float)) and s["grade"] not in ["F", "NA", "N/A", ""])
                has_failed = any(s["grade"] == "F" for s in subs)

                # Determine Standing & Status
                if sgpa_val >= 8.5 and not has_failed:
                    standing = "First Class with Distinction"
                    status = "PASSED"
                elif sgpa_val >= 6.5 and not has_failed:
                    standing = "First Class"
                    status = "PASSED"
                elif sgpa_val >= 5.0 and not has_failed:
                    standing = "Second Class"
                    status = "PASSED"
                elif sgpa_val > 0:
                    standing = "Pass Class" if not has_failed else "Needs Re-examination"
                    status = "RE-APPEAR" if has_failed else "PASSED"
                else:
                    standing = "Incomplete / Absent"
                    status = "WITHHELD"

                students_db[regn]["semesters"][str(sem_num)] = {
                    "semester": sem_num,
                    "sgpa": sgpa_val,
                    "cgpa": cgpa_val,
                    "gp": gp_val,
                    "eaa": eaa_val,
                    "standing": standing,
                    "status": status,
                    "total_credits": total_credits,
                    "earned_credits": earned_credits,
                    "subjects": subs
                }

    # Post-process overall CGPA for each student
    for regn, student in students_db.items():
        sorted_sems = sorted(student["semesters"].keys(), key=lambda x: int(x))
        total_cred_all = 0
        total_weighted_points = 0.0
        latest_cgpa = None

        for s_key in sorted_sems:
            sem_obj = student["semesters"][s_key]
            if sem_obj["cgpa"] is not None:
                latest_cgpa = sem_obj["cgpa"]
            else:
                if latest_cgpa is None and sem_obj["sgpa"] > 0:
                    sem_obj["cgpa"] = sem_obj["sgpa"]
                    latest_cgpa = sem_obj["sgpa"]

            total_cred_all += sem_obj["earned_credits"]
            total_weighted_points += (sem_obj["sgpa"] * sem_obj["total_credits"])

        total_credits_denom = sum(student["semesters"][s]["total_credits"] for s in sorted_sems)
        if latest_cgpa is None and total_credits_denom > 0:
            latest_cgpa = round(total_weighted_points / total_credits_denom, 2)

        student["overall_cgpa"] = latest_cgpa if latest_cgpa is not None else 0.0
        student["total_credits_earned"] = total_cred_all
        student["total_semesters_active"] = len(sorted_sems)

    # 3. Export to JSON
    output_json = DATA_DIR / "results_data.json"
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump({
            "total_students": len(students_db),
            "subjects": subjects_master,
            "students": students_db
        }, f, indent=2)

    # 4. Export to JavaScript for direct offline local browser execution
    output_js = DATA_DIR / "results_data.js"
    with open(output_js, "w", encoding="utf-8") as f:
        f.write("window.ACADEMIQ_DATA = ")
        json.dump({
            "total_students": len(students_db),
            "subjects": subjects_master,
            "students": students_db
        }, f, indent=2)
        f.write(";\n")

    print(f"\n[Success] Exported {len(students_db)} total students across all semesters to:")
    print(f" - {output_json}")
    print(f" - {output_js}")

if __name__ == "__main__":
    export_data()
