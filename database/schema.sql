CREATE DATABASE IF NOT EXISTS academicq;

USE academicq;

-- =========================================
-- STUDENTS
-- =========================================

CREATE TABLE IF NOT EXISTS students (
    regn_no VARCHAR(20) PRIMARY KEY,
    department VARCHAR(50),
    batch_year INT
);


-- =========================================
-- SUBJECTS
-- =========================================

CREATE TABLE IF NOT EXISTS subjects (
    subject_code VARCHAR(20) PRIMARY KEY,
    credits INT NOT NULL
);


-- =========================================
-- RESULTS
-- =========================================

CREATE TABLE IF NOT EXISTS results (
    regn_no VARCHAR(20) NOT NULL,
    semester INT NOT NULL,
    subject_code VARCHAR(20) NOT NULL,
    grade_point DECIMAL(4,2),
    grade VARCHAR(10),

    PRIMARY KEY (regn_no, semester, subject_code),

    FOREIGN KEY (regn_no)
        REFERENCES students(regn_no),

    FOREIGN KEY (subject_code)
        REFERENCES subjects(subject_code)
);


-- =========================================
-- SEMESTER SUMMARY
-- =========================================

CREATE TABLE IF NOT EXISTS semester_summary (
    regn_no VARCHAR(20) NOT NULL,
    semester INT NOT NULL,
    gp DECIMAL(8,2),
    sgpa DECIMAL(4,2),
    eaa VARCHAR(20),

    PRIMARY KEY (regn_no, semester),

    FOREIGN KEY (regn_no)
        REFERENCES students(regn_no)
);