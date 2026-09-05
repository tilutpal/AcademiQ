import os
import json
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__, static_folder=".", static_url_path="")

BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "data" / "results_data.json"

# In-memory cached dataset
DATA_CACHE = None

def load_data():
    global DATA_CACHE
    if DATA_CACHE is None and DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            DATA_CACHE = json.load(f)
    return DATA_CACHE

@app.route("/")
def serve_index():
    return send_from_directory(".", "index.html")

@app.route("/<path:path>")
def serve_static(path):
    return send_from_directory(".", path)

@app.route("/api/health", methods=["GET"])
def health_check():
    data = load_data()
    total = data.get("total_students", 0) if data else 0
    return jsonify({
        "status": "healthy",
        "service": "AcademiQ Result Server",
        "total_records": total
    })

@app.route("/api/semesters", methods=["GET"])
def get_semesters():
    return jsonify({
        "active_semesters": [
            {"id": 1, "name": "Semester 1", "status": "Published"},
            {"id": 2, "name": "Semester 2", "status": "Published"},
            {"id": 3, "name": "Semester 3", "status": "Published"},
            {"id": 4, "name": "Semester 4", "status": "Published"},
            {"id": 5, "name": "Semester 5", "status": "Published"},
            {"id": 6, "name": "Semester 6", "status": "Published"}
        ],
        "upcoming_semesters": [
            {"id": 7, "name": "Semester 7", "status": "Upcoming"},
            {"id": 8, "name": "Semester 8", "status": "Upcoming"}
        ]
    })

@app.route("/api/result", methods=["GET"])
def get_student_result():
    regn_no = request.args.get("regn_no", "").strip()
    semester = request.args.get("semester", "1").strip()

    if not regn_no:
        return jsonify({"error": "Missing 'regn_no' query parameter"}), 400

    data = load_data()
    if not data or "students" not in data:
        return jsonify({"error": "Dataset not initialized"}), 500

    student = data["students"].get(regn_no)
    if not student:
        return jsonify({"error": f"No records found for Registration ID '{regn_no}'"}), 404

    sem_data = student["semesters"].get(semester)
    if not sem_data:
        return jsonify({"error": f"No records published for Semester {semester}"}), 404

    return jsonify({
        "student": {
            "regn_no": student["regn_no"],
            "department": student["department"],
            "dept_code": student.get("dept_code", "GEN"),
            "batch_year": student["batch_year"],
            "overall_cgpa": student.get("overall_cgpa", 0.0),
            "available_semesters": list(student["semesters"].keys())
        },
        "semester_data": sem_data
    })

if __name__ == "__main__":
    load_data()
    port = int(os.environ.get("PORT", 5000))
    print(f"AcademiQ Portal running on http://127.0.0.1:{port}")
    app.run(host="127.0.0.1", port=port, debug=False)
