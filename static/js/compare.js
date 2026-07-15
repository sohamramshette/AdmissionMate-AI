/**
 * compare.js — Dynamic College Comparison Feature
 * ================================================
 * Handles:
 *   - "+ Add College" → opens modal with live search
 *   - Adding/removing college pills
 *   - Fetching comparison data from /api/compare
 *   - Building the comparison table dynamically
 *   - Highlighting best values (green)
 *   - Displaying AI summary
 *   - sessionStorage integration (pre-populate from Find Colleges page)
 *
 * No page reloads — fully SPA-style interaction.
 */

"use strict";

/* ── Constants ─────────────────────────────────────────────────────────── */
const MAX_COLLEGES = 4;
const MIN_COLLEGES = 2;
const STORAGE_KEY  = "compareCollegeIds";

/* ── State ─────────────────────────────────────────────────────────────── */
let selectedColleges = [];   // Array of { id, name, city }
let searchDebounceTimer = null;

/* ── DOM refs (assigned after DOMContentLoaded) ─────────────────────── */
let addCollegeBtn, compareBtn, maxReachedMsg, noCollegesHint;
let selectedPillsContainer;
let comparisonSection, emptyState;
let compareLoading, compareTableCard, aiSummaryCard;
let compareThead, compareTbody, aiSummaryBody;
let collegeSearchInput, searchResults, duplicateWarning;
let addCollegeModal;

/* ================================================================== */
document.addEventListener("DOMContentLoaded", () => {
  /* Bind DOM refs */
  addCollegeBtn          = document.getElementById("add-college-btn");
  compareBtn             = document.getElementById("compare-btn");
  maxReachedMsg          = document.getElementById("max-reached-msg");
  noCollegesHint         = document.getElementById("no-colleges-hint");
  selectedPillsContainer = document.getElementById("selected-pills");

  comparisonSection = document.getElementById("comparison-section");
  emptyState        = document.getElementById("empty-state");

  compareLoading    = document.getElementById("compare-loading");
  compareTableCard  = document.getElementById("compare-table-card");
  aiSummaryCard     = document.getElementById("ai-summary-card");

  compareThead      = document.getElementById("compare-thead");
  compareTbody      = document.getElementById("compare-tbody");
  aiSummaryBody     = document.getElementById("ai-summary-body");

  collegeSearchInput = document.getElementById("college-search-input");
  searchResults      = document.getElementById("search-results");
  duplicateWarning   = document.getElementById("duplicate-warning");

  /* Init Bootstrap modal */
  const modalEl = document.getElementById("addCollegeModal");
  addCollegeModal = new bootstrap.Modal(modalEl);

  /* Clear search input when modal opens */
  modalEl.addEventListener("show.bs.modal", () => {
    collegeSearchInput.value = "";
    duplicateWarning.classList.add("d-none");
    resetSearchResults();
  });
  /* Focus search input after modal is shown */
  modalEl.addEventListener("shown.bs.modal", () => {
    collegeSearchInput.focus();
  });

  /* Wire up buttons */
  addCollegeBtn.addEventListener("click", openAddModal);
  compareBtn.addEventListener("click", runComparison);
  collegeSearchInput.addEventListener("input", onSearchInput);

  /* Restore from sessionStorage (pre-populated from Find Colleges page) */
  restoreFromStorage();

  /* If colleges were restored, auto-run the comparison */
  if (selectedColleges.length >= MIN_COLLEGES) {
    runComparison();
  }
});

/* ── Open the Add College Modal ────────────────────────────────────── */
function openAddModal() {
  if (selectedColleges.length >= MAX_COLLEGES) return;
  addCollegeModal.show();
}

/* ── Search input handler (debounced) ──────────────────────────────── */
function onSearchInput() {
  duplicateWarning.classList.add("d-none");
  clearTimeout(searchDebounceTimer);
  searchDebounceTimer = setTimeout(() => {
    const q = collegeSearchInput.value.trim();
    if (q.length === 0) {
      resetSearchResults();
      return;
    }
    fetchSearchResults(q);
  }, 200);
}

/* ── Reset search results to initial state ─────────────────────────── */
function resetSearchResults() {
  searchResults.innerHTML = `
    <p class="text-muted small text-center py-4" id="search-placeholder">
      <i class="bi bi-keyboard me-1"></i> Start typing to search colleges…
    </p>`;
}

/* ── Fetch search results from API ─────────────────────────────────── */
async function fetchSearchResults(query) {
  searchResults.innerHTML = `
    <p class="text-muted small text-center py-3">
      <span class="spinner-border spinner-border-sm me-2"></span>Searching…
    </p>`;

  try {
    const res  = await fetch(`/api/colleges/search?q=${encodeURIComponent(query)}`);
    const data = await res.json();
    renderSearchResults(data);
  } catch (err) {
    searchResults.innerHTML = `
      <p class="text-danger small text-center py-3">
        <i class="bi bi-exclamation-circle me-1"></i>Search failed. Try again.
      </p>`;
  }
}

/* ── Render search result list ──────────────────────────────────────── */
function renderSearchResults(colleges) {
  if (!colleges.length) {
    searchResults.innerHTML = `
      <p class="text-muted small text-center py-4">
        <i class="bi bi-search me-1"></i> No colleges found. Try a different search.
      </p>`;
    return;
  }

  const items = colleges.map((c) => {
    const alreadySelected = selectedColleges.some((s) => s.id === c.id);
    const disabledClass   = alreadySelected ? "disabled" : "";
    const checkIcon       = alreadySelected
      ? '<i class="bi bi-check-circle-fill text-success me-2"></i>'
      : '<i class="bi bi-plus-circle me-2 text-primary"></i>';

    return `
      <button class="college-result-item ${disabledClass}"
              data-id="${c.id}"
              data-name="${escapeHtml(c.name)}"
              data-city="${escapeHtml(c.city)}"
              ${alreadySelected ? "disabled" : ""}>
        <div class="d-flex align-items-center">
          ${checkIcon}
          <div>
            <div class="fw-600 small">${escapeHtml(c.name)}</div>
            <div class="text-muted" style="font-size:.75rem">
              <i class="bi bi-geo-alt me-1"></i>${escapeHtml(c.city)}
              &nbsp;·&nbsp;
              <i class="bi bi-diagram-3 me-1"></i>${c.branch_count} branches
            </div>
          </div>
        </div>
      </button>`;
  });

  searchResults.innerHTML = items.join("");

  /* Attach click handlers */
  searchResults.querySelectorAll(".college-result-item:not([disabled])").forEach((btn) => {
    btn.addEventListener("click", () => {
      const college = {
        id:   parseInt(btn.dataset.id, 10),
        name: btn.dataset.name,
        city: btn.dataset.city,
      };
      handleAddCollege(college);
    });
  });
}

/* ── Handle adding a college ────────────────────────────────────────── */
function handleAddCollege(college) {
  /* Duplicate check */
  if (selectedColleges.some((c) => c.id === college.id)) {
    duplicateWarning.classList.remove("d-none");
    return;
  }
  duplicateWarning.classList.add("d-none");

  /* Max limit check */
  if (selectedColleges.length >= MAX_COLLEGES) {
    showToast("Maximum 4 colleges can be compared.", "warning");
    return;
  }

  selectedColleges.push(college);
  persistToStorage();
  addCollegeModal.hide();
  renderPills();
  updateActionBar();

  showToast(`${college.name} added to comparison.`, "success");
}

/* ── Remove a college ───────────────────────────────────────────────── */
function removeCollege(id) {
  selectedColleges = selectedColleges.filter((c) => c.id !== id);
  persistToStorage();
  renderPills();
  updateActionBar();

  /* If the comparison was showing, re-run or hide */
  if (selectedColleges.length >= MIN_COLLEGES) {
    runComparison();
  } else {
    hideComparisonResults();
  }
}

/* ── Render selected pills ──────────────────────────────────────────── */
function renderPills() {
  /* Remove existing pills (keep the label span and hint span) */
  const existingPills = selectedPillsContainer.querySelectorAll(".compare-pill");
  existingPills.forEach((p) => p.remove());

  /* Update hint visibility */
  noCollegesHint.classList.toggle("d-none", selectedColleges.length > 0);

  /* Insert pills before the hint */
  selectedColleges.forEach((c) => {
    const pill = document.createElement("span");
    pill.className = "compare-pill badge rounded-pill px-3 py-2";
    pill.innerHTML = `
      <i class="bi bi-building me-1"></i>${escapeHtml(c.name)}
      <button class="compare-pill-remove ms-2" aria-label="Remove ${escapeHtml(c.name)}"
              data-id="${c.id}">×</button>`;
    pill.querySelector(".compare-pill-remove").addEventListener("click", () => {
      removeCollege(c.id);
    });
    /* Insert before the hint span */
    selectedPillsContainer.insertBefore(pill, noCollegesHint);
  });
}

/* ── Update action bar (Add College button + Compare button) ────────── */
function updateActionBar() {
  const count = selectedColleges.length;
  const atMax = count >= MAX_COLLEGES;

  addCollegeBtn.disabled = atMax;
  addCollegeBtn.classList.toggle("disabled", atMax);
  maxReachedMsg.classList.toggle("d-none", !atMax);

  /* Show Compare Now button when ≥ 2 colleges are selected */
  if (count >= MIN_COLLEGES) {
    compareBtn.classList.remove("d-none");
    compareBtn.textContent = "";
    compareBtn.innerHTML = `<i class="bi bi-bar-chart-steps me-1"></i>Compare (${count})`;
  } else {
    compareBtn.classList.add("d-none");
  }
}

/* ── Run comparison — fetch from API and render table ──────────────── */
async function runComparison() {
  if (selectedColleges.length < MIN_COLLEGES) return;

  /* Show comparison section, hide empty state */
  comparisonSection.classList.remove("d-none");
  emptyState.classList.add("d-none");

  /* Show loader, hide old results */
  compareLoading.classList.remove("d-none");
  compareTableCard.classList.add("d-none");
  aiSummaryCard.classList.add("d-none");

  const ids = selectedColleges.map((c) => c.id);

  try {
    const res  = await fetch("/api/compare", {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ ids }),
    });
    const data = await res.json();

    compareLoading.classList.add("d-none");

    if (data.error) {
      showToast(data.error, "danger");
      return;
    }

    renderComparisonTable(data.colleges);
    renderAISummary(data.summary);

  } catch (err) {
    compareLoading.classList.add("d-none");
    showToast("Failed to load comparison data. Please try again.", "danger");
  }
}

/* ── Hide comparison results ─────────────────────────────────────────── */
function hideComparisonResults() {
  comparisonSection.classList.add("d-none");
  emptyState.classList.remove("d-none");
}

/* ── Build comparison table ──────────────────────────────────────────── */
function renderComparisonTable(colleges) {
  if (!colleges.length) return;

  /* ── Pre-compute best values for highlighting ── */
  const bestFees    = minVal(colleges, (c) => c.fees_raw > 0 ? c.fees_raw : Infinity);
  const bestCutoff  = maxVal(colleges, (c) => c.cutoff_open ?? -1);
  const mostBranch  = maxVal(colleges, (c) => c.branch_count);
  const mostIntake  = maxVal(colleges, (c) => c.intake);

  /* ── Header row ── */
  const thCells = colleges.map((c) => `
    <th class="compare-col-header text-center" style="min-width:190px">
      <div class="fw-700">${escapeHtml(c.name)}</div>
      <div class="text-white-50 small fw-normal mt-1">
        <i class="bi bi-geo-alt me-1"></i>${escapeHtml(c.city)}
      </div>
    </th>`).join("");

  compareThead.innerHTML = `
    <tr>
      <th class="compare-metric-col py-3 ps-4" style="min-width:200px">Metric</th>
      ${thCells}
    </tr>`;

  /* ── Row definitions ── */
  const rows = [
    {
      label: "OPEN Cutoff Percentile",
      icon:  "bi-percent",
      alt:   true,
      cells: colleges.map((c) => ({
        val:       c.cutoff_open ?? null,
        display:   c.cutoff_open_display,
        highlight: c.cutoff_open !== null && c.cutoff_open === bestCutoff,
        tag:       c.cutoff_open !== null && c.cutoff_open === bestCutoff ? "Highest" : null,
      })),
    },
    {
      label: "SC Cutoff Percentile",
      icon:  "bi-percent",
      alt:   false,
      cells: colleges.map((c) => ({
        val:       null,
        display:   c.cutoff_sc_display,
        highlight: false,
        tag:       null,
      })),
    },
    {
      label: "OBC Cutoff Percentile",
      icon:  "bi-percent",
      alt:   true,
      cells: colleges.map((c) => ({
        val:       null,
        display:   c.cutoff_obc_display,
        highlight: false,
        tag:       null,
      })),
    },
    {
      label: "Average Annual Fees",
      icon:  "bi-cash-coin",
      alt:   false,
      cells: colleges.map((c) => ({
        val:       c.fees_raw,
        display:   c.fees_display,
        highlight: c.fees_raw > 0 && c.fees_raw === bestFees,
        tag:       c.fees_raw > 0 && c.fees_raw === bestFees ? "Lowest" : null,
      })),
    },
    {
      label: "Branches Offered",
      icon:  "bi-diagram-3",
      alt:   true,
      cells: colleges.map((c) => ({
        val:       c.branch_count,
        display:   c.branches_display,
        highlight: c.branch_count === mostBranch,
        tag:       c.branch_count === mostBranch ? "Most" : null,
      })),
    },
    {
      label: "Number of Branches",
      icon:  "bi-list-ol",
      alt:   false,
      cells: colleges.map((c) => ({
        val:       c.branch_count,
        display:   c.branch_count.toString(),
        highlight: c.branch_count === mostBranch,
        tag:       null,
      })),
    },
    {
      label: "Total Intake",
      icon:  "bi-people",
      alt:   true,
      cells: colleges.map((c) => ({
        val:       c.intake,
        display:   c.intake > 0 ? c.intake.toLocaleString() : "N/A",
        highlight: c.intake === mostIntake,
        tag:       c.intake === mostIntake ? "Largest" : null,
      })),
    },
    {
      label: "Home University",
      icon:  "bi-mortarboard",
      alt:   false,
      cells: colleges.map((c) => ({
        val:       null,
        display:   c.home_university || "N/A",
        highlight: false,
        tag:       null,
      })),
    },
    {
      label: "Categories Available",
      icon:  "bi-tag",
      alt:   true,
      cells: colleges.map((c) => ({
        val:       null,
        display:   (c.categories || []).join(", ") || "N/A",
        highlight: false,
        tag:       null,
      })),
    },
  ];

  /* ── Render tbody ── */
  const rowsHtml = rows.map((row) => {
    const tdCells = row.cells.map((cell) => {
      const hlClass = cell.highlight ? "compare-best" : "";
      const tagHtml = cell.tag
        ? `<span class="compare-best-badge ms-1">${cell.tag}</span>`
        : "";
      return `<td class="text-center ${hlClass}">${escapeHtml(cell.display)}${tagHtml}</td>`;
    }).join("");

    const rowBg = row.alt ? 'style="background:rgba(79,70,229,0.025)"' : "";
    return `
      <tr ${rowBg}>
        <td class="ps-4 metric-label">
          <i class="bi ${row.icon} me-2 text-primary"></i>${row.label}
        </td>
        ${tdCells}
      </tr>`;
  }).join("");

  /* ── Action row ── */
  const actionCells = colleges.map((c) => `
    <td class="text-center py-3">
      <a href="/college/${c.id}"
         class="btn btn-primary-custom btn-sm px-3">
        <i class="bi bi-eye me-1"></i>View Details
      </a>
    </td>`).join("");

  compareTbody.innerHTML = rowsHtml + `
    <tr>
      <td class="ps-4 metric-label">
        <i class="bi bi-info-circle me-2 text-primary"></i>Actions
      </td>
      ${actionCells}
    </tr>`;

  compareTableCard.classList.remove("d-none");
}

/* ── Render AI Summary ───────────────────────────────────────────────── */
function renderAISummary(summary) {
  if (!summary) {
    aiSummaryCard.classList.add("d-none");
    return;
  }

  /* Convert plain-text lines to styled HTML */
  const lines = summary.split("\n").filter((l) => l.trim());
  const html  = lines.map((line) => {
    const trimmed = line.trim();

    /* Key: Value lines */
    const colonIdx = trimmed.indexOf(":");
    if (colonIdx > 0 && colonIdx < 40) {
      const key = trimmed.slice(0, colonIdx).trim();
      const val = trimmed.slice(colonIdx + 1).trim();
      if (val) {
        return `<div class="ai-summary-row">
          <span class="ai-summary-key">${escapeHtml(key)}</span>
          <span class="ai-summary-val">${escapeHtml(val)}</span>
        </div>`;
      }
    }

    /* Plain paragraph */
    return `<p class="mb-2 small">${escapeHtml(trimmed)}</p>`;
  }).join("");

  aiSummaryBody.innerHTML = html;
  aiSummaryCard.classList.remove("d-none");
}

/* ── sessionStorage helpers ──────────────────────────────────────────── */
function persistToStorage() {
  try {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(selectedColleges));
  } catch (_) {}
}

function restoreFromStorage() {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return;
    const parsed = JSON.parse(raw);
    if (Array.isArray(parsed) && parsed.length > 0) {
      selectedColleges = parsed.slice(0, MAX_COLLEGES);
      renderPills();
      updateActionBar();
    }
  } catch (_) {}
}

/* ── Utility: compute min/max across an array by accessor ────────────── */
function minVal(arr, accessor) {
  const vals = arr.map(accessor).filter((v) => v !== Infinity && v > 0);
  return vals.length ? Math.min(...vals) : null;
}

function maxVal(arr, accessor) {
  const vals = arr.map(accessor).filter((v) => v !== null && v >= 0);
  return vals.length ? Math.max(...vals) : null;
}

/* ── HTML escape utility ─────────────────────────────────────────────── */
function escapeHtml(str) {
  if (str == null) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}
