/**
 * College Admission Assistant — Main JavaScript Module
 * main.js · Vanilla ES6+, no external dependencies beyond Bootstrap
 * ================================================================
 */

"use strict";

/* ── Bootstrap toast helper ─────────────────────────────────────────── */
/**
 * Show a Bootstrap 5 toast notification.
 * @param {string} message  - Text to display
 * @param {string} type     - 'success' | 'danger' | 'warning' | 'info'
 */
function showToast(message, type = "info") {
  const container = document.getElementById("toast-container");
  if (!container) return;

  const id = `toast-${Date.now()}`;
  const html = `
    <div id="${id}" class="toast align-items-center text-bg-${type} border-0 shadow-sm"
         role="alert" aria-live="assertive" aria-atomic="true" data-bs-delay="4000">
      <div class="d-flex">
        <div class="toast-body fw-semibold">${message}</div>
        <button type="button" class="btn-close btn-close-white me-2 m-auto"
                data-bs-dismiss="toast" aria-label="Close"></button>
      </div>
    </div>`;
  container.insertAdjacentHTML("beforeend", html);
  const el = document.getElementById(id);
  const toast = new bootstrap.Toast(el);
  toast.show();
  el.addEventListener("hidden.bs.toast", () => el.remove());
}

/* ── Navbar scroll effect ────────────────────────────────────────────── */
(function initNavbarScroll() {
  const navbar = document.querySelector(".navbar-glass");
  if (!navbar) return;
  const handler = () =>
    navbar.classList.toggle("shadow-sm", window.scrollY > 20);
  window.addEventListener("scroll", handler, { passive: true });
  handler(); // run once on load
})();

/* ── Smooth active-link highlighting ─────────────────────────────────── */
(function highlightActiveNav() {
  const path = window.location.pathname;
  document.querySelectorAll(".nav-link").forEach((link) => {
    const href = link.getAttribute("href");
    if (href && path.startsWith(href) && href !== "/") {
      link.classList.add("active");
    } else if (href === "/" && path === "/") {
      link.classList.add("active");
    }
  });
})();

/* ── Scroll-reveal (Intersection Observer) ───────────────────────────── */
(function initScrollReveal() {
  const targets = document.querySelectorAll(".reveal");
  if (!targets.length || !("IntersectionObserver" in window)) return;

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((e) => {
        if (e.isIntersecting) {
          e.target.classList.add("fade-in-up");
          observer.unobserve(e.target);
        }
      });
    },
    { threshold: 0.12 }
  );
  targets.forEach((el) => observer.observe(el));
})();

/* ── Student Form — client-side validation ───────────────────────────── */
(function initStudentForm() {
  const form = document.getElementById("student-form");
  if (!form) return;

  form.addEventListener("submit", function (e) {
    // Let Bootstrap handle visual state
    if (!form.checkValidity()) {
      e.preventDefault();
      e.stopPropagation();
      showToast("Please fill in all required fields.", "warning");
    }
    form.classList.add("was-validated");
  });

  // Real-time percentile range guard
  const pctInput = document.getElementById("cet_percentile");
  if (pctInput) {
    pctInput.addEventListener("input", () => {
      const v = parseFloat(pctInput.value);
      if (v < 0 || v > 100) {
        pctInput.setCustomValidity("Percentile must be between 0 and 100.");
      } else {
        pctInput.setCustomValidity("");
      }
    });
  }
})();

