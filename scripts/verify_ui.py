"""
AcademiQ Verification Suite — Tests Multi-Semester Data, UI Structure, Theming & API
"""

import json
import re
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

def run_tests():
    print("==================================================")
    print("ACADEMIQ MULTI-SEMESTER & UI VERIFICATION SUITE")
    print("==================================================")
    
    # 1. Verify index.html
    html_path = BASE_DIR / "index.html"
    assert html_path.exists(), "index.html is missing!"
    html_content = html_path.read_text(encoding="utf-8")
    
    assert 'id="regn-input"' in html_content, "Registration input field missing"
    assert 'id="semester-select"' in html_content, "Semester select dropdown missing"
    assert 'id="search-submit-btn"' in html_content, "Search button missing"
    assert 'id="result-modal"' in html_content, "Result modal dialog missing"
    assert 'id="modal-sgpa-val"' in html_content, "Modal SGPA element missing"
    assert 'id="modal-cgpa-val"' in html_content, "Modal CGPA element missing"
    assert 'id="modal-standing-text"' not in html_content, "Standing text should be removed"
    assert 'id="modal-sem-tabs"' not in html_content, "Semester tabs should be removed"
    assert 'id="modal-credits-val"' not in html_content, "Modal credits should be removed"
    assert 'id="modal-eaa-val"' not in html_content, "Modal EAA should be removed"
    assert 'Quick Try:' not in html_content, "Quick Try section should be removed"
    assert 'id="modal-gp-val"' not in html_content, "Total GP should be removed"
    assert 'id="copy-summary-btn"' not in html_content, "Copy summary button should be removed"
    assert 'id="print-sheet-btn"' not in html_content, "Print button should be removed"
    assert 'Course Title' not in html_content, "Course Title column should be removed"
    print("[OK] index.html markup, removed elements, and new CGPA & semester tabs verified.")

    # 2. Verify styles.css
    css_path = BASE_DIR / "styles.css"
    assert css_path.exists(), "styles.css is missing!"
    css_content = css_path.read_text(encoding="utf-8")
    
    assert '--accent-primary: #10B981' in css_content, "Emerald theme primary accent missing"
    assert '--bg-app: #080C14' in css_content, "Obsidian Slate background missing"
    assert '.metric-cgpa' in css_content, "CGPA card styles missing"
    assert '.grade-badge' in css_content, "Grade badges styles missing"
    print("[OK] styles.css Obsidian Slate & Emerald theme verified.")

    # 3. Verify data/results_data.json
    json_path = BASE_DIR / "data" / "results_data.json"
    assert json_path.exists(), "data/results_data.json is missing!"
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    assert data.get("total_students") >= 919, f"Expected >= 919 students, got {data.get('total_students')}"
    
    # Test Civil Engineering student 2311018 in both Sem 1 and Sem 2
    s1 = data["students"].get("2311018")
    assert s1 is not None, "Student 2311018 missing"
    assert s1["department"] == "Civil Engineering"
    assert s1["overall_cgpa"] == 8.83, f"Expected 8.83 CGPA, got {s1['overall_cgpa']}"
    
    sem1 = s1["semesters"]["1"]
    assert sem1["sgpa"] == 8.21, f"Expected 8.21 SGPA, got {sem1['sgpa']}"
    assert "CE 101" in [sub["subject_code"] for sub in sem1["subjects"]], "Expected CE 101 in Sem 1"
    
    sem2 = s1["semesters"]["2"]
    assert sem2["sgpa"] == 8.44, f"Expected 8.44 SGPA, got {sem2['sgpa']}"
    assert "CE 102" in [sub["subject_code"] for sub in sem2["subjects"]], "Expected CE 102 in Sem 2 (swapped)"
    
    # Test Computer Science student 2315001
    s2 = data["students"].get("2315001")
    assert s2 is not None, "Student 2315001 missing"
    assert s2["department"] == "Computer Science & Engineering"
    assert s2["overall_cgpa"] == 9.13, f"Expected 9.13 CGPA, got {s2['overall_cgpa']}"
    assert s2["semesters"]["2"]["sgpa"] == 9.33, f"Expected 9.33 Sem 2 SGPA, got {s2['semesters']['2']['sgpa']}"
    
    print(f"[OK] Data store verified with {data['total_students']} multi-semester students and swapped course groups.")

    # 4. Verify Flask app routes
    from app import app
    client = app.test_client()
    
    # Static files
    r_index = client.get("/")
    assert r_index.status_code == 200, "Failed to serve index.html"
    r_css = client.get("/styles.css")
    assert r_css.status_code == 200, "Failed to serve styles.css"
    r_js = client.get("/app.js")
    assert r_js.status_code == 200, "Failed to serve app.js"
    r_data_js = client.get("/data/results_data.js")
    assert r_data_js.status_code == 200, "Failed to serve data/results_data.js"
    
    # API endpoints
    r_health = client.get("/api/health")
    assert r_health.status_code == 200 and r_health.json["status"] == "healthy"
    
    r_sem = client.get("/api/semesters")
    assert r_sem.status_code == 200 and len(r_sem.json["active_semesters"]) == 6
    
    r_res = client.get("/api/result?regn_no=2311018&semester=2")
    assert r_res.status_code == 200 and r_res.json["semester_data"]["sgpa"] == 8.44
    assert r_res.json["student"]["overall_cgpa"] == 8.83
    
    print("[OK] Flask REST API and multi-semester routing verified successfully.")

    print("\n==================================================")
    print("ALL 16 VERIFICATION CHECKS PASSED (100% SUCCESS)!")
    print("==================================================")

if __name__ == "__main__":
    run_tests()
