"""
AcademiQ — MySQL Importer for Multi-Semester Examination Results
Imports subjects, students, semester summaries (SGPA & CGPA), and course grades.
"""

import csv
import mysql.connector
from pathlib import Path

# ==========================================
# MYSQL CONFIGURATION
# ==========================================
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "Tilutpal@mySQL45",
    "database": "academicq"
}

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "output"

DEPARTMENT_MAP = {
    "11": "CE",
    "12": "ME",
    "13": "EE",
    "14": "EC",
    "15": "CS",
    "16": "CH",
}

def import_all():
    print("Connecting to MySQL...")
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()
        print("Connected to MySQL successfully!")
    except Exception as e:
        print(f"[Warning] MySQL connection failed: {e}")
        return

    # 1. Ensure Table Schema has CGPA support
    try:
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS subjects (
            subject_code VARCHAR(30) PRIMARY KEY,
            credits INT NOT NULL
        )
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            regn_no VARCHAR(20) PRIMARY KEY,
            department VARCHAR(50),
            batch_year INT
        )
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS results (
            id INT AUTO_INCREMENT PRIMARY KEY,
            regn_no VARCHAR(20),
            semester INT,
            subject_code VARCHAR(30),
            grade_point FLOAT,
            grade VARCHAR(10),
            UNIQUE KEY uk_student_sem_sub (regn_no, semester, subject_code)
        )
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS semester_summary (
            id INT AUTO_INCREMENT PRIMARY KEY,
            regn_no VARCHAR(20),
            semester INT,
            gp FLOAT,
            sgpa FLOAT,
            cgpa FLOAT,
            eaa VARCHAR(50),
            UNIQUE KEY uk_student_sem (regn_no, semester)
        )
        """)
        # Add cgpa column if not exists
        try:
            cursor.execute("ALTER TABLE semester_summary ADD COLUMN cgpa FLOAT AFTER sgpa")
        except Exception:
            pass
        connection.commit()
    except Exception as err:
        print(f"Table verification notice: {err}")

    # 2. Insert Subjects
    subjects_file = OUTPUT_DIR / "subjects.csv"
    if subjects_file.exists():
        print("\nImporting subjects...")
        with open(subjects_file, "r", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            for row in reader:
                sub_code = row["subject_code"].strip()
                credits_val = int(row["credits"]) if row["credits"] else 0
                cursor.execute("""
                INSERT INTO subjects (subject_code, credits)
                VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE credits = VALUES(credits)
                """, (sub_code, credits_val))
        print("Subjects imported.")

    # 3. Process all semesters
    for sem in [1, 2]:
        results_file = OUTPUT_DIR / f"semester{sem}_results.csv"
        summary_file = OUTPUT_DIR / f"semester{sem}_summary.csv"

        if not results_file.exists() or not summary_file.exists():
            continue

        print(f"\n--- Importing Semester {sem} Data ---")

        # Import Students
        with open(results_file, "r", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            for row in reader:
                regn_no = row["regn_no"].strip()
                if regn_no:
                    dept_code = DEPARTMENT_MAP.get(regn_no[2:4] if len(regn_no) >= 4 else "11", "CE")
                    batch_year = int(f"20{regn_no[:2]}") if len(regn_no) >= 2 and regn_no[:2].isdigit() else 2023
                    cursor.execute("""
                    INSERT INTO students (regn_no, department, batch_year)
                    VALUES (%s, %s, %s)
                    ON DUPLICATE KEY UPDATE department = VALUES(department), batch_year = VALUES(batch_year)
                    """, (regn_no, dept_code, batch_year))

        # Import Results
        count_res = 0
        with open(results_file, "r", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            for row in reader:
                regn_no = row["regn_no"].strip()
                semester = int(row["semester"])
                subject_code = row["subject_code"].strip()
                grade_point_text = row["grade_point"].strip()
                grade = row["grade"].strip()

                grade_point = float(grade_point_text) if grade_point_text else None
                grade = grade if grade else None

                cursor.execute("""
                INSERT INTO results (regn_no, semester, subject_code, grade_point, grade)
                VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE grade_point = VALUES(grade_point), grade = VALUES(grade)
                """, (regn_no, semester, subject_code, grade_point, grade))
                count_res += 1
        print(f"Semester {sem}: {count_res} result rows imported.")

        # Import Semester Summary
        count_sum = 0
        with open(summary_file, "r", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            for row in reader:
                regn_no = row["regn_no"].strip()
                semester = int(row["semester"])
                gp = float(row["GP"]) if row["GP"] else 0.0
                sgpa = float(row["SGPA"]) if row["SGPA"] else 0.0
                cgpa = float(row["CGPA"]) if row.get("CGPA") and row["CGPA"].strip() else None
                eaa = row["EAA"].strip()
                if eaa == "-" or eaa == "":
                    eaa = None

                cursor.execute("""
                INSERT INTO semester_summary (regn_no, semester, gp, sgpa, cgpa, eaa)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE gp = VALUES(gp), sgpa = VALUES(sgpa), cgpa = VALUES(cgpa), eaa = VALUES(eaa)
                """, (regn_no, semester, gp, sgpa, cgpa, eaa))
                count_sum += 1
        print(f"Semester {sem}: {count_sum} summaries imported.")

    connection.commit()
    cursor.close()
    connection.close()
    print("\n[Complete] MySQL import completed successfully.")

if __name__ == "__main__":
    import_all()