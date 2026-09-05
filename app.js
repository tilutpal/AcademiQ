/**
 * AcademiQ — Academic Result & Grade Verification Logic
 * Obsidian Slate & Emerald Edition — Multi-Semester SGPA & CGPA Support
 */

(function () {
  'use strict';

  // --------------------------------------------------------------------------
  // 1. State & DOM References
  // --------------------------------------------------------------------------
  let database = window.ACADEMIQ_DATA || null;
  let currentStudent = null;
  let activeSemester = '1';

  const DOM = {
    html: document.documentElement,
    themeToggleBtn: document.getElementById('theme-toggle-btn'),
    searchForm: document.getElementById('result-search-form'),
    regnInput: document.getElementById('regn-input'),
    clearInputBtn: document.getElementById('clear-input-btn'),
    semesterSelect: document.getElementById('semester-select'),
    submitBtn: document.getElementById('search-submit-btn'),
    btnSpinner: document.querySelector('.btn-spinner'),
    searchIcon: document.querySelector('.search-icon'),
    sampleChips: document.querySelectorAll('.sample-chip'),
    formFeedback: document.getElementById('form-feedback'),
    feedbackMessage: document.getElementById('feedback-message'),
    
    // Modal Elements
    modal: document.getElementById('result-modal'),
    closeModalBtn: document.getElementById('close-modal-btn'),
    modalDoneBtn: document.getElementById('modal-done-btn'),
    modalDeptBadge: document.getElementById('modal-dept-badge'),
    modalBatchBadge: document.getElementById('modal-batch-badge'),
    modalSemBadge: document.getElementById('modal-sem-badge'),
    modalStudentId: document.getElementById('modal-student-id'),
    modalStatusBadge: document.getElementById('modal-status-badge'),
    
    // Metrics
    modalSgpaLabel: document.getElementById('modal-sgpa-label'),
    modalSgpaVal: document.getElementById('modal-sgpa-val'),
    modalSgpaBar: document.getElementById('modal-sgpa-bar'),
    modalCgpaVal: document.getElementById('modal-cgpa-val'),
    modalCgpaBar: document.getElementById('modal-cgpa-bar'),
    modalCourseCount: document.getElementById('modal-course-count'),
    resultsTableBody: document.getElementById('results-table-body'),
    modalSemesterTabs: document.getElementById('modal-semester-tabs'),
    
    toastContainer: document.getElementById('toast-container')
  };

  // --------------------------------------------------------------------------
  // 2. Initialization & Data Loading
  // --------------------------------------------------------------------------
  async function init() {
    initTheme();
    setupEventListeners();

    // If data was not embedded via <script>, fetch from data/results_data.json
    if (!database) {
      try {
        const response = await fetch('data/results_data.json');
        if (response.ok) {
          database = await response.json();
          console.log(`[AcademiQ] Loaded ${database.total_students} student records.`);
        }
      } catch (err) {
        console.warn('[AcademiQ] Running in direct local mode; checking window.ACADEMIQ_DATA');
      }
    }
  }

  // --------------------------------------------------------------------------
  // 3. Theme Management
  // --------------------------------------------------------------------------
  function initTheme() {
    const savedTheme = localStorage.getItem('academiq_theme') || 'dark';
    setTheme(savedTheme);
  }

  function setTheme(theme) {
    DOM.html.setAttribute('data-theme', theme);
    localStorage.setItem('academiq_theme', theme);
  }

  function toggleTheme() {
    const current = DOM.html.getAttribute('data-theme') || 'dark';
    const next = current === 'dark' ? 'light' : 'dark';
    setTheme(next);
    showToast(`Switched to ${next} mode`, 'info');
  }

  // --------------------------------------------------------------------------
  // 4. Search & Result Lookup
  // --------------------------------------------------------------------------
  function handleSearch(e) {
    if (e) e.preventDefault();
    hideFeedback();

    const regnNo = DOM.regnInput.value.trim();
    const semester = DOM.semesterSelect.value;

    if (!regnNo) {
      showFeedback('Please enter your student registration number.');
      DOM.regnInput.focus();
      return;
    }

    setLoading(true);

    setTimeout(() => {
      try {
        findAndDisplayResult(regnNo, semester);
      } catch (err) {
        console.error('[AcademiQ] Search error:', err);
        showFeedback('An unexpected error occurred while processing results.');
      } finally {
        setLoading(false);
      }
    }, 120);
  }

  function findAndDisplayResult(regnNo, requestedSem) {
    if (!database || !database.students) {
      showFeedback('Database is loading. Please try again in a moment.');
      return;
    }

    const student = database.students[regnNo];
    if (!student) {
      showFeedback(`No examination records found for Registration ID "${regnNo}". Please verify and try again.`);
      return;
    }

    currentStudent = student;
    
    const availableSems = Object.keys(student.semesters).sort((a, b) => parseInt(a) - parseInt(b));
    
    if (!student.semesters[requestedSem]) {
      showFeedback(`Semester ${requestedSem} result is not available for Registration ID "${regnNo}". (Published semesters: Semester ${availableSems.join(', Semester ')})`);
      return;
    }

    activeSemester = requestedSem;
    renderStudentModal(student, requestedSem);
    openModal();
  }

  // --------------------------------------------------------------------------
  // 5. Modal Population & Multi-Semester Tabs
  // --------------------------------------------------------------------------
  function renderStudentModal(student, semKey) {
    const semData = student.semesters[semKey];
    if (!semData) return;

    activeSemester = semKey;
    if (DOM.semesterSelect) DOM.semesterSelect.value = semKey;
    const subjects = semData.subjects || [];

    // Header Badges
    DOM.modalDeptBadge.textContent = student.department || 'Engineering';
    DOM.modalBatchBadge.textContent = `Batch ${student.batch_year || '2023'}`;
    DOM.modalSemBadge.textContent = `Semester ${semKey}`;
    DOM.modalStudentId.textContent = student.regn_no;

    // Render Semester Switcher Tabs Bar
    if (DOM.modalSemesterTabs) {
      DOM.modalSemesterTabs.innerHTML = '';
      const allSems = ['1', '2', '3', '4', '5', '6'];
      allSems.forEach(s => {
        const btn = document.createElement('button');
        btn.type = 'button';
        const isAvailable = !!student.semesters[s];
        const isActive = s === semKey;

        btn.className = `sem-tab-btn ${isActive ? 'active' : ''} ${!isAvailable ? 'disabled' : ''}`;
        btn.textContent = `Semester ${s}`;
        if (!isAvailable) {
          btn.title = `Semester ${s} result not available for ${student.regn_no}`;
        }

        btn.addEventListener('click', () => {
          if (isAvailable && s !== semKey) {
            renderStudentModal(student, s);
          } else if (!isAvailable) {
            showToast(`Semester ${s} result is not available for student ${student.regn_no}`, 'warning');
          }
        });

        DOM.modalSemesterTabs.appendChild(btn);
      });
    }

    // Status Badge
    DOM.modalStatusBadge.className = 'status-badge';
    if (semData.status === 'PASSED') {
      DOM.modalStatusBadge.classList.add('status-passed');
      DOM.modalStatusBadge.textContent = 'PASSED';
    } else if (semData.status === 'RE-APPEAR') {
      DOM.modalStatusBadge.classList.add('status-reappear');
      DOM.modalStatusBadge.textContent = 'RE-APPEAR';
    } else {
      DOM.modalStatusBadge.classList.add('status-withheld');
      DOM.modalStatusBadge.textContent = semData.status || 'WITHHELD';
    }

    // SGPA Metric
    DOM.modalSgpaLabel.textContent = `Semester ${semKey} SGPA`;
    const sgpaVal = semData.sgpa ? semData.sgpa.toFixed(2) : '0.00';
    DOM.modalSgpaVal.textContent = sgpaVal;
    const sgpaPercent = Math.min(100, Math.max(0, (semData.sgpa / 10.0) * 100));
    DOM.modalSgpaBar.style.width = `${sgpaPercent}%`;

    // CGPA Metric
    const cgpaScore = semData.cgpa !== null && semData.cgpa !== undefined ? semData.cgpa : (student.overall_cgpa || semData.sgpa);
    const cgpaVal = cgpaScore ? cgpaScore.toFixed(2) : '0.00';
    DOM.modalCgpaVal.textContent = cgpaVal;
    const cgpaPercent = Math.min(100, Math.max(0, (cgpaScore / 10.0) * 100));
    DOM.modalCgpaBar.style.width = `${cgpaPercent}%`;

    // Course Count
    DOM.modalCourseCount.textContent = `${subjects.length} Courses`;

    // Populate Results Table (Only Course Code, Credits, GP, Grade)
    DOM.resultsTableBody.innerHTML = '';
    
    subjects.forEach(sub => {
      const row = document.createElement('tr');
      const gradeDisplay = (sub.grade && sub.grade.trim() !== '') ? sub.grade.trim() : 'NA';
      const gradeClass = getGradePillClass(gradeDisplay);
      const gpDisplay = (sub.grade_point !== null && sub.grade_point !== undefined && sub.grade_point !== 'NA') ? sub.grade_point : '-';
      const credDisplay = (sub.credits !== null && sub.credits !== undefined && sub.credits !== '') ? sub.credits : 'NA';

      row.innerHTML = `
        <td class="td-code">${escapeHtml(sub.subject_code)}</td>
        <td class="text-center"><strong>${escapeHtml(credDisplay)}</strong></td>
        <td class="text-center">${escapeHtml(gpDisplay)}</td>
        <td class="text-center">
          <span class="grade-badge ${gradeClass}">${escapeHtml(gradeDisplay)}</span>
        </td>
      `;

      DOM.resultsTableBody.appendChild(row);
    });
  }



  function getGradePillClass(grade) {
    if (!grade) return 'grade-pill-NA';
    const clean = grade.trim().toUpperCase();
    switch (clean) {
      case 'AA': return 'grade-pill-AA';
      case 'AB': return 'grade-pill-AB';
      case 'BB': return 'grade-pill-BB';
      case 'BC': return 'grade-pill-BC';
      case 'CC': return 'grade-pill-CC';
      case 'CD': return 'grade-pill-CD';
      case 'DD': return 'grade-pill-DD';
      case 'F':  return 'grade-pill-F';
      default:   return 'grade-pill-NA';
    }
  }

  function openModal() {
    if (typeof DOM.modal.showModal === 'function') {
      DOM.modal.showModal();
    } else {
      DOM.modal.setAttribute('open', '');
    }
    document.body.style.overflow = 'hidden';
  }

  function closeModal() {
    if (typeof DOM.modal.close === 'function') {
      DOM.modal.close();
    } else {
      DOM.modal.removeAttribute('open');
    }
    document.body.style.overflow = '';
  }

  // --------------------------------------------------------------------------
  // 6. UI Helpers & Event Listeners
  // --------------------------------------------------------------------------
  function setLoading(loading) {
    if (loading) {
      DOM.submitBtn.disabled = true;
      if (DOM.btnSpinner) DOM.btnSpinner.hidden = false;
      if (DOM.searchIcon) DOM.searchIcon.hidden = true;
    } else {
      DOM.submitBtn.disabled = false;
      if (DOM.btnSpinner) DOM.btnSpinner.hidden = true;
      if (DOM.searchIcon) DOM.searchIcon.hidden = false;
    }
  }

  function showFeedback(message) {
    DOM.feedbackMessage.textContent = message;
    DOM.formFeedback.hidden = false;
  }

  function hideFeedback() {
    DOM.formFeedback.hidden = true;
    DOM.feedbackMessage.textContent = '';
  }

  function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.textContent = message;
    DOM.toastContainer.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(10px)';
      toast.style.transition = 'all 0.2s ease-out';
      setTimeout(() => toast.remove(), 200);
    }, 2400);
  }

  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function setupEventListeners() {
    // Theme Toggle
    if (DOM.themeToggleBtn) {
      DOM.themeToggleBtn.addEventListener('click', toggleTheme);
    }

    // Keyboard shortcut for theme toggle ('T')
    window.addEventListener('keydown', (e) => {
      if (e.key.toLowerCase() === 't' && document.activeElement.tagName !== 'INPUT' && document.activeElement.tagName !== 'SELECT') {
        toggleTheme();
      }
    });

    // Form Submit
    if (DOM.searchForm) {
      DOM.searchForm.addEventListener('submit', handleSearch);
    }

    // Registration Input formatting & clear button visibility
    if (DOM.regnInput) {
      DOM.regnInput.addEventListener('input', () => {
        hideFeedback();
        DOM.clearInputBtn.hidden = DOM.regnInput.value.length === 0;
      });
    }

    if (DOM.clearInputBtn) {
      DOM.clearInputBtn.addEventListener('click', () => {
        DOM.regnInput.value = '';
        DOM.clearInputBtn.hidden = true;
        hideFeedback();
        DOM.regnInput.focus();
      });
    }

    // Sample Chips
    DOM.sampleChips.forEach(chip => {
      chip.addEventListener('click', () => {
        const regn = chip.getAttribute('data-regn');
        const sem = chip.getAttribute('data-sem') || '2';
        if (regn) {
          DOM.regnInput.value = regn;
          DOM.clearInputBtn.hidden = false;
          if (DOM.semesterSelect) {
            DOM.semesterSelect.value = sem;
          }
          handleSearch();
        }
      });
    });

    // Modal Close
    if (DOM.closeModalBtn) {
      DOM.closeModalBtn.addEventListener('click', closeModal);
    }
    if (DOM.modalDoneBtn) {
      DOM.modalDoneBtn.addEventListener('click', closeModal);
    }

    // Click outside modal card to close
    if (DOM.modal) {
      DOM.modal.addEventListener('click', (e) => {
        if (e.target === DOM.modal) {
          closeModal();
        }
      });
    }
  }

  // --------------------------------------------------------------------------
  // 7. Auto Run
  // --------------------------------------------------------------------------
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
