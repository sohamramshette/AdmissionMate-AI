/**
 * cap_generator.js
 * Multi-step wizard controller for the AI CAP Preference Generator.
 *
 * Step map:
 *   1 — CET Percentile
 *   2 — Category
 *   3 — Gender
 *   4 — Home University
 *   5 — Preferred Cities  (with Any City toggle)
 *   6 — Preferred Branches (dual-list with order)
 *   7 — Priority Style    (+ optional Max Preferences)
 *   8 — Strategy          (Balanced / Aggressive / Safe)
 *   9 — Review & Generate
 *
 * No external dependencies beyond Bootstrap 5 (already loaded).
 */

(function () {
  "use strict";

  /* ─── Configuration ─────────────────────────────────── */
  const TOTAL_STEPS = 9;

  /* ─── DOM refs ──────────────────────────────────────── */
  const form        = document.getElementById("capForm");
  const progressBar = document.getElementById("capProgressBar");
  const stepPanels  = document.querySelectorAll(".step-panel");
  const stepDots    = document.querySelectorAll(".step-dot");
  const stepLabels  = document.querySelectorAll(".step-label");
  const connectors  = document.querySelectorAll(".step-connector");
  const btnPrev     = document.getElementById("btnPrev");
  const btnNext     = document.getElementById("btnNext");
  const btnGenerate = document.getElementById("btnGenerate");
  const stepCounter = document.getElementById("stepCounter");

  let currentStep = 1;

  /* ─── Step render ───────────────────────────────────── */
  function renderStep(step) {
    stepPanels.forEach((p) => p.classList.remove("active"));
    const target = document.getElementById("step" + step);
    if (target) target.classList.add("active");

    // Dots & labels
    stepDots.forEach((dot, i) => {
      const n = i + 1;
      dot.classList.remove("active", "completed");
      if (stepLabels[i]) stepLabels[i].classList.remove("active", "completed");

      if (n < step) {
        dot.classList.add("completed");
        dot.innerHTML = '<i class="bi bi-check"></i>';
        if (stepLabels[i]) stepLabels[i].classList.add("completed");
      } else if (n === step) {
        dot.classList.add("active");
        dot.textContent = n;
        if (stepLabels[i]) stepLabels[i].classList.add("active");
      } else {
        dot.textContent = n;
      }
    });

    // Connectors
    connectors.forEach((c, i) => {
      c.classList.toggle("done", i + 1 < step);
    });

    // Progress bar
    const pct = Math.round(((step - 1) / (TOTAL_STEPS - 1)) * 100);
    progressBar.style.width = pct + "%";
    progressBar.setAttribute("aria-valuenow", pct);

    // Step counter label
    if (stepCounter) stepCounter.textContent = "Step " + step + " of " + TOTAL_STEPS;

    // Nav buttons
    btnPrev.style.visibility = step === 1 ? "hidden" : "visible";
    const isLast = step === TOTAL_STEPS;
    btnNext.style.display     = isLast ? "none"         : "inline-block";
    btnGenerate.style.display = isLast ? "inline-block" : "none";

    document.getElementById("wizardCard").scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  /* ─── Validation ────────────────────────────────────── */
  function validateStep(step) {
    clearErrors();

    // Step 1 — CET Percentile
    if (step === 1) {
      const v = parseFloat(document.getElementById("cetPercentile").value);
      if (isNaN(v) || v < 0 || v > 100) {
        showError("err1", "Please enter a valid CET percentile between 0 and 100.");
        return false;
      }
    }

    // Step 2 — Category
    if (step === 2) {
      if (!document.querySelector('input[name="category"]:checked')) {
        showError("err2", "Please select a category.");
        return false;
      }
    }

    // Step 3 — Gender
    if (step === 3) {
      if (!document.querySelector('input[name="gender"]:checked')) {
        showError("err3", "Please select your gender.");
        return false;
      }
    }

    // Step 4 — Home University
    if (step === 4) {
      if (!document.getElementById("homeUniversity").value) {
        showError("err4", "Please select your home university.");
        return false;
      }
    }

    // Step 5 — Preferred Cities (Any City OR at least one specific city)
    if (step === 5) {
      const anyChecked      = document.getElementById("city_any") && document.getElementById("city_any").checked;
      const specificChecked = document.querySelector('input[name="preferred_cities"]:checked');
      if (!anyChecked && !specificChecked) {
        showError("err5", "Please select at least one preferred city, or choose Any City.");
        return false;
      }
    }

    // Step 6 — Preferred Branches
    if (step === 6) {
      const selected = document.getElementById("selectedBranches");
      if (!selected || selected.options.length === 0) {
        showError("err6", "Please add at least one preferred branch group.");
        return false;
      }
    }

    // Step 7 — Priority Style
    if (step === 7) {
      if (!document.querySelector('input[name="priority_style"]:checked')) {
        showError("err7", "Please select a priority style.");
        return false;
      }
    }

    // Step 8 — Strategy
    if (step === 8) {
      if (!document.querySelector('input[name="strategy"]:checked')) {
        showError("err8", "Please select a strategy.");
        return false;
      }
    }

    return true;
  }

  function showError(id, msg) {
    const el = document.getElementById(id);
    if (el) { el.textContent = msg; el.classList.add("visible"); }
  }

  function clearErrors() {
    document.querySelectorAll(".step-error").forEach((e) => e.classList.remove("visible"));
  }

  /* ─── Navigation ────────────────────────────────────── */
  btnNext.addEventListener("click", () => {
    if (!validateStep(currentStep)) return;
    // Populate review just before showing step 9
    if (currentStep === 8) populateReview();
    currentStep++;
    renderStep(currentStep);
  });

  btnPrev.addEventListener("click", () => {
    if (currentStep > 1) { currentStep--; renderStep(currentStep); }
  });

  /* ─── Pre-submit: sync hidden branch field ──────────── */
  form.addEventListener("submit", (e) => {
    if (!validateStep(currentStep)) { e.preventDefault(); return; }
    syncSelectedBranches();
  });

  /* ─── Any City toggle ────────────────────────────────── */
  // Exposed on window so the inline onchange= attribute in the template can call it.
  window.handleAnyCityToggle = function (checkbox) {
    const specifics = document.querySelectorAll(".city-specific");
    if (checkbox.checked) {
      // Disable and un-check all specific city tiles
      specifics.forEach((cb) => {
        cb.checked  = false;
        cb.disabled = true;
        const tile = document.querySelector('label[for="' + cb.id + '"]');
        if (tile) tile.classList.add("city-tile-disabled");
      });
    } else {
      specifics.forEach((cb) => {
        cb.disabled = false;
        const tile = document.querySelector('label[for="' + cb.id + '"]');
        if (tile) tile.classList.remove("city-tile-disabled");
      });
    }
  };

  /* ─── Dual-list helpers ──────────────────────────────── */
  function moveOptions(fromId, toId) {
    const from = document.getElementById(fromId);
    const to   = document.getElementById(toId);
    if (!from || !to) return;
    Array.from(from.selectedOptions).forEach((opt) => {
      from.removeChild(opt);
      to.appendChild(opt);
      opt.selected = false;
    });
  }

  function moveUp() {
    const sel  = document.getElementById("selectedBranches");
    if (!sel) return;
    const opts = Array.from(sel.options);
    for (let i = 1; i < opts.length; i++) {
      if (opts[i].selected && !opts[i - 1].selected) {
        sel.insertBefore(opts[i], opts[i - 1]);
      }
    }
  }

  function moveDown() {
    const sel  = document.getElementById("selectedBranches");
    if (!sel) return;
    const opts = Array.from(sel.options);
    for (let i = opts.length - 2; i >= 0; i--) {
      if (opts[i].selected && !opts[i + 1].selected) {
        sel.insertBefore(opts[i + 1], opts[i]);
      }
    }
  }

  function syncSelectedBranches() {
    const sel    = document.getElementById("selectedBranches");
    const hidden = document.getElementById("selectedBranchesHidden");
    if (!sel || !hidden) return;
    // Select all options so they are included in the multiselect POST value
    Array.from(sel.options).forEach((o) => (o.selected = true));
    // Write ordered comma-separated list to the dedicated hidden field
    hidden.value = Array.from(sel.options).map((o) => o.value).join(",");
  }

  // Wire dual-list buttons
  const _el = (id) => document.getElementById(id);
  _el("btnAddBranch")    && _el("btnAddBranch").addEventListener("click",    () => moveOptions("availableBranches", "selectedBranches"));
  _el("btnRemoveBranch") && _el("btnRemoveBranch").addEventListener("click", () => moveOptions("selectedBranches",  "availableBranches"));
  _el("btnMoveUp")       && _el("btnMoveUp").addEventListener("click",       moveUp);
  _el("btnMoveDown")     && _el("btnMoveDown").addEventListener("click",     moveDown);

  // Double-click to transfer
  _el("availableBranches") && _el("availableBranches").addEventListener("dblclick", () => moveOptions("availableBranches", "selectedBranches"));
  _el("selectedBranches")  && _el("selectedBranches").addEventListener("dblclick",  () => moveOptions("selectedBranches",  "availableBranches"));

  /* ─── Review summary ────────────────────────────────── */
  function getCheckedLabels(name) {
    return Array.from(document.querySelectorAll('input[name="' + name + '"]:checked'))
      .map((el) => el.value).join(", ") || "—";
  }

  function fieldVal(id) {
    const el = document.getElementById(id);
    return el ? (el.value || "—") : "—";
  }

  function populateReview() {
    // Branch groups from the Selected list (preserves order)
    const branches = Array.from((_el("selectedBranches") || { options: [] }).options)
      .map((o) => o.text).join(", ") || "—";

    // Cities: either "Any City" or the checked specific cities
    const anyCity = _el("city_any") && _el("city_any").checked;
    const cities  = anyCity
      ? "Any City"
      : Array.from(document.querySelectorAll('input[name="preferred_cities"]:checked'))
          .map((el) => el.value).join(", ") || "—";

    // Max preferences
    const maxPrefEl = document.querySelector('input[name="max_preferences"]:checked');
    const maxPref   = maxPrefEl ? maxPrefEl.value : "No limit";

    // University select text
    const uniSel  = _el("homeUniversity");
    const uniText = uniSel && uniSel.selectedIndex > 0
      ? uniSel.options[uniSel.selectedIndex].text
      : "—";

    const map = {
      rv_percentile: fieldVal("cetPercentile"),
      rv_category:   getCheckedLabels("category"),
      rv_gender:     getCheckedLabels("gender"),
      rv_university: uniText,
      rv_cities:     cities,
      rv_branches:   branches,
      rv_priority:   getCheckedLabels("priority_style"),
      rv_strategy:   getCheckedLabels("strategy"),
      rv_max_pref:   maxPref,
    };

    Object.entries(map).forEach(([id, value]) => {
      const el = document.getElementById(id);
      if (el) el.textContent = value;
    });
  }

  /* ─── Init ───────────────────────────────────────────── */
  renderStep(1);
})();
