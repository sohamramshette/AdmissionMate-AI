/**
 * branch_advisor.js
 * Multi-step wizard controller for the AI Branch Advisor.
 *
 * Steps:
 *   1 — Favourite Subjects     (checkbox, at least 1)
 *   2 — Work Type              (checkbox, at least 1)
 *   3 — Activities             (checkbox, at least 1)
 *   4 — Career Goal            (radio or custom text input, required)
 *   5 — Enjoys Programming     (radio, required)
 *   6 — Work Environment       (radio, required)
 *   7 — Priority               (radio, required)
 *   8 — Math Comfort           (radio, required)
 *
 * On final submit: show AI loading overlay, then submit form.
 */

(function () {
  "use strict";

  const TOTAL_STEPS = 8;

  /* ── DOM refs ─────────────────────────────────────────── */
  const form        = document.getElementById("baForm");
  const progressBar = document.getElementById("baProgressBar");
  const stepPanels  = document.querySelectorAll(".ba-step-panel");
  const stepDots    = document.querySelectorAll(".ba-step-dot");
  const stepLabels  = document.querySelectorAll(".ba-step-label");
  const connectors  = document.querySelectorAll(".ba-step-connector");
  const btnPrev     = document.getElementById("baBtnPrev");
  const btnNext     = document.getElementById("baBtnNext");
  const btnGenerate = document.getElementById("baBtnGenerate");
  const stepCounter = document.getElementById("baStepCounter");
  const overlay     = document.getElementById("baLoadingOverlay");

  /* Career custom text + radio sync */
  const careerCustom = document.getElementById("career_custom");

  let currentStep = 1;

  /* ─── Render step ───────────────────────────────────── */
  function renderStep(step) {
    stepPanels.forEach(function (p) { p.classList.remove("active"); });
    const target = document.getElementById("ba-step" + step);
    if (target) target.classList.add("active");

    /* Dots & labels */
    stepDots.forEach(function (dot, i) {
      const n = i + 1;
      dot.classList.remove("active", "completed");
      if (stepLabels[i]) stepLabels[i].classList.remove("active", "completed");

      if (n < step) {
        dot.classList.add("completed");
        dot.innerHTML = '<i class="bi bi-check" style="font-size:.7rem"></i>';
        if (stepLabels[i]) stepLabels[i].classList.add("completed");
      } else if (n === step) {
        dot.classList.add("active");
        dot.textContent = n;
        if (stepLabels[i]) stepLabels[i].classList.add("active");
      } else {
        dot.textContent = n;
      }
    });

    /* Connectors */
    connectors.forEach(function (c, i) {
      c.classList.toggle("completed", i + 1 < step);
    });

    /* Progress */
    const pct = Math.round(((step - 1) / TOTAL_STEPS) * 100);
    progressBar.style.width = pct + "%";

    /* Counter */
    if (stepCounter) stepCounter.textContent = "Step " + step + " of " + TOTAL_STEPS;

    /* Nav buttons */
    btnPrev.style.display    = step === 1 ? "none" : "";
    btnNext.style.display    = step === TOTAL_STEPS ? "none" : "";
    btnGenerate.style.display = step === TOTAL_STEPS ? "inline-block" : "none";

    /* Clear error for this step */
    clearError(step);

    /* Scroll wizard into view on mobile */
    const card = document.getElementById("baWizardCard");
    if (card) card.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  /* ─── Validation per step ───────────────────────────── */
  function validate(step) {
    clearError(step);

    /* Checkbox groups: at least 1 checked */
    if (step === 1) {
      if (!anyChecked('input[name="subjects"]')) {
        return setError(step, "Please select at least one subject.");
      }
    }
    if (step === 2) {
      if (!anyChecked('input[name="work_type"]')) {
        return setError(step, "Please select at least one work type.");
      }
    }
    if (step === 3) {
      if (!anyChecked('input[name="activities"]')) {
        return setError(step, "Please select at least one activity.");
      }
    }

    /* Career goal: either a radio OR custom text */
    if (step === 4) {
      const radioSelected = anyChecked('input[name="career_goal"]');
      const customVal     = (careerCustom && careerCustom.value.trim()) || "";
      if (!radioSelected && !customVal) {
        return setError(step, "Please choose a career goal or type one in the box.");
      }
    }

    /* Radio fields: required */
    if (step === 5 && !anyChecked('input[name="enjoys_programming"]')) {
      return setError(step, "Please select an option.");
    }
    if (step === 6 && !anyChecked('input[name="work_env"]')) {
      return setError(step, "Please select a work environment.");
    }
    if (step === 7 && !anyChecked('input[name="priority"]')) {
      return setError(step, "Please select your priority.");
    }
    if (step === 8 && !anyChecked('input[name="math_comfort"]')) {
      return setError(step, "Please select your comfort level.");
    }

    return true;
  }

  function anyChecked(selector) {
    return document.querySelectorAll(selector + ":checked").length > 0;
  }

  function setError(step, msg) {
    const el = document.getElementById("ba-err" + step);
    if (el) el.textContent = msg;
    return false;
  }

  function clearError(step) {
    const el = document.getElementById("ba-err" + step);
    if (el) el.textContent = "";
  }

  /* ─── Step 4 career radio → clear custom text and vice-versa ─ */
  if (careerCustom) {
    careerCustom.addEventListener("input", function () {
      if (careerCustom.value.trim()) {
        /* Typing in custom box → uncheck all radio buttons */
        document.querySelectorAll('input[name="career_goal"]').forEach(function (r) {
          r.checked = false;
        });
      }
    });

    document.querySelectorAll('input[name="career_goal"]').forEach(function (r) {
      r.addEventListener("change", function () {
        /* Selecting a radio → clear custom text */
        if (careerCustom) careerCustom.value = "";
      });
    });
  }

  /* ─── On form submit — inject custom career if needed ── */
  form && form.addEventListener("submit", function () {
    /* If user typed a custom career goal, inject it via a hidden input */
    if (careerCustom && careerCustom.value.trim() && !anyChecked('input[name="career_goal"]')) {
      const hidden  = document.createElement("input");
      hidden.type   = "hidden";
      hidden.name   = "career_goal";
      hidden.value  = careerCustom.value.trim();
      form.appendChild(hidden);
    }

    /* Show loading overlay */
    if (overlay) overlay.classList.add("active");
  });

  /* ─── Button events ─────────────────────────────────── */
  btnNext.addEventListener("click", function () {
    if (!validate(currentStep)) return;
    if (currentStep < TOTAL_STEPS) {
      currentStep++;
      renderStep(currentStep);
    }
  });

  btnPrev.addEventListener("click", function () {
    if (currentStep > 1) {
      currentStep--;
      renderStep(currentStep);
    }
  });

  /* Final generate button validation */
  btnGenerate.addEventListener("click", function (e) {
    if (!validate(TOTAL_STEPS)) {
      e.preventDefault();
    }
    /* Form will submit naturally (overlay shown via submit listener) */
  });

  /* ─── Init ──────────────────────────────────────────── */
  renderStep(1);

})();
