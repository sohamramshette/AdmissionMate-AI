/**
 * chatbot.js — Dual-Mode Admission & Document AI Assistant Controller
 * ===================================================================
 * Modes:
 *   1. "admission" -> College, cutoff, comparison, and branch advisor
 *   2. "documents" -> Mandatory documents, category rules, NCL, CVC, Proformas, FC scrutiny
 * ===================================================================
 */

"use strict";

(function initChatbot() {

  /* ── DOM Elements ──────────────────────────────────────────── */
  const chatForm        = document.getElementById("chat-form");
  const chatInput       = document.getElementById("chat-input");
  const msgContainer    = document.getElementById("chat-messages");
  const sendBtn         = document.getElementById("send-btn");
  const clearBtn        = document.getElementById("clear-chat-btn");
  const shuffleBtn      = document.getElementById("shuffle-prompts-btn");
  const quickShuffleBtn = document.getElementById("btn-quick-shuffle");
  const promptChipsBox  = document.getElementById("prompt-chips");
  const tabAdmission    = document.getElementById("tab-mode-admission");
  const tabDocuments    = document.getElementById("tab-mode-documents");

  // Only run if on chatbot page
  if (!chatForm || !chatInput || !msgContainer) return;

  let currentMode = "admission"; // "admission" or "documents"

  /* ── Configure marked.js ──────────────────────────────────── */
  if (typeof marked !== "undefined") {
    try {
      marked.use({ breaks: true, gfm: true });
    } catch (_) {
      if (marked.setOptions) marked.setOptions({ breaks: true, gfm: true });
    }
  }

  /* ── 1. Admission Suggestion Prompts Pool ─────────────────── */
  const ADMISSION_POOL = [
    { label: "⚖️ Compare COEP vs PICT", msg: "Compare COEP and PICT colleges — cutoff percentiles, annual fees, and average placement packages." },
    { label: "🎯 95 %ile College Options", msg: "Suggest the top 5 engineering colleges in Maharashtra for 95 percentile score in OPEN category." },
    { label: "📋 Explain CAP Round Rules", msg: "Explain step-by-step how Maharashtra CET CAP option form submission and seat allotment work." },
    { label: "🤖 Best AI & Data Science Colleges", msg: "Which colleges offer the best Artificial Intelligence & Data Science programs in Pune and Mumbai?" },
    { label: "🏆 VJTI Mumbai Cutoffs", msg: "What were the previous year cutoffs and closing percentiles for VJTI Mumbai Computer Engineering?" },
    { label: "💰 OBC / EWS Fee Concessions", msg: "What scholarships and government fee waivers (EBC/MahaDBT) are available for OBC and EWS students?" },
    { label: "⚡ TFWS Scheme Eligibility", msg: "How does the TFWS (Tuition Fee Waiver Scheme) work in MHT-CET, and what is the family income limit?" },
    { label: "🏛️ Govt vs Autonomous Colleges", msg: "What is the difference between Government, Autonomous, and Private engineering colleges in Maharashtra?" },
    { label: "📍 Top Colleges in Pune", msg: "List the top 10 engineering colleges in Pune with their highest and average placement packages." },
    { label: "🎯 85 %ile Best Branches", msg: "What are the best college and branch options for an 85 percentile score in MHT-CET?" },
    { label: "💻 CE vs IT vs AI-DS", msg: "What is the difference in curriculum, coding scope, and jobs between Computer Engineering, IT, and AI-DS?" },
    { label: "🏢 SPIT Mumbai CS Cutoffs", msg: "What are the closing percentiles and placement statistics for SPIT (Sardar Patel) Mumbai?" },
    { label: "🎓 SPPU vs Mumbai University", msg: "Compare engineering under Savitribai Phule Pune University (SPPU) versus Mumbai University (MU)." },
    { label: "🏠 Home University (HU/OHU) Quotas", msg: "Explain Home University (HU) vs Other than Home University (OHU) 70-30 quota reservation rules." },
    { label: "🎯 90 %ile OBC Colleges", msg: "Suggest the best engineering colleges for 90 percentile OBC category in Pune and Mumbai." },
    { label: "📡 ENTC vs Mechanical Scope", msg: "Compare career prospects, semiconductor jobs, and IT eligibility for ENTC vs Mechanical Engineering." },
    { label: "🏫 Walchand Sangli Overview", msg: "Provide a detailed review of Walchand College of Engineering Sangli regarding campus and placements." },
    { label: "💼 100% Placement Colleges", msg: "Which engineering colleges in Maharashtra have consistent 90%+ placement records for CSE/IT?" },
    { label: "📝 Betterment vs Freeze in CAP", msg: "What is the difference between Auto-Freeze, Self-Freeze, and Betterment in MHT-CET CAP Round 1?" },
    { label: "🌟 Best Colleges in Nagpur & Nashik", msg: "What are the best engineering colleges in Nagpur (e.g. VNIT, RCOEM) and Nashik (KK Wagh)?" }
  ];

  /* ── 2. Documents & Verification Suggestion Prompts Pool ─── */
  const DOCUMENTS_POOL = [
    { label: "📑 Documents for OBC Category", msg: "What documents are required for OBC category in MHT-CET? Is Non-Creamy Layer mandatory?" },
    { label: "🔍 Non-Creamy Layer Validity Rule", msg: "What is the validity date requirement for Non-Creamy Layer (NCL) Certificate in Maharashtra CET admissions?" },
    { label: "🏛️ Caste Certificate vs Validity", msg: "What is the difference between Caste Certificate and Caste Validity Certificate (CVC)? What if validity is pending?" },
    { label: "💰 EWS Certificate & Proforma-V", msg: "What are the eligibility criteria and documents required for EWS (Economically Weaker Section) quota?" },
    { label: "⚡ TFWS Income Certificate Criteria", msg: "What document proof is needed for TFWS (Tuition Fee Waiver Scheme) and who issues the income certificate?" },
    { label: "📝 Gap Certificate Affidavit Format", msg: "What is the format and stamp paper requirement for Gap Certificate if I took a 1-year drop after 12th?" },
    { label: "🏠 Domicile Type A vs Type B", msg: "Explain Maharashtra Candidature Type A, B, C, D, and E with their required domicile proofs." },
    { label: "⏳ Caste Validity Pending (Receipt)", msg: "Can I get admission with Caste Validity Application Receipt if my original validity is still in process?" },
    { label: "♿ PWD / Divyangjan Disability Proof", msg: "What certificate is required for 5% PWD / Divyangjan reservation in Maharashtra CET?" },
    { label: "🎖️ Defence Ward Quota (Def 1, 2, 3)", msg: "What proforma certificate is required for Children of Ex-Service / Active Defence Personnel (Def-1/2/3)?" },
    { label: "🕌 Linguistic / Religious Minority", msg: "How to prove Minority status (Gujarati, Hindi, Sindhi, Jain, Muslim) for minority quota college seats?" },
    { label: "🌐 OMS / All India Candidate Documents", msg: "What documents do Outside Maharashtra State (OMS / All India) candidates need to produce at FC?" },
    { label: "🏢 Physical Scrutiny vs E-Scrutiny", msg: "What is the difference between Physical Scrutiny at Facilitation Center (FC) and Online E-Scrutiny?" },
    { label: "📋 Full Document Master Checklist", msg: "Give me the complete master checklist of original documents needed on the day of college admission." }
  ];

  const NUM_VISIBLE_CHIPS = 5;
  let poolIndex = 0;
  let activeChips = [];

  function getActivePool() {
    return currentMode === "documents" ? DOCUMENTS_POOL : ADMISSION_POOL;
  }

  function getNextFromPool() {
    const pool = getActivePool();
    const item = pool[poolIndex % pool.length];
    poolIndex++;
    return item;
  }

  function initSuggestions() {
    poolIndex = 0;
    activeChips = [];
    for (let i = 0; i < NUM_VISIBLE_CHIPS; i++) {
      activeChips.push(getNextFromPool());
    }
    renderChips();
  }

  function renderChips() {
    if (!promptChipsBox) return;
    promptChipsBox.innerHTML = "";

    activeChips.forEach((item, slotIndex) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "cb-chip chip-pop";
      btn.innerHTML = item.label;
      btn.title = item.msg;
      btn.setAttribute("aria-label", item.msg);

      btn.addEventListener("click", () => {
        handleChipClick(slotIndex);
      });

      promptChipsBox.appendChild(btn);
    });
  }

  function handleChipClick(slotIndex) {
    const clickedItem = activeChips[slotIndex];
    if (!clickedItem) return;

    chatInput.value = clickedItem.msg;
    autoGrow();
    submitChatMessage();

    // Rotate in new suggestion on the spot
    const newItem = getNextFromPool();
    activeChips[slotIndex] = newItem;

    const chipBtns = promptChipsBox.querySelectorAll(".cb-chip");
    if (chipBtns[slotIndex]) {
      const chipEl = chipBtns[slotIndex];
      chipEl.classList.remove("chip-pop");
      void chipEl.offsetWidth;
      chipEl.innerHTML = newItem.label;
      chipEl.title = newItem.msg;
      chipEl.setAttribute("aria-label", newItem.msg);
      chipEl.classList.add("chip-pop");
    }
  }

  function shuffleAllSuggestions() {
    activeChips = [];
    for (let i = 0; i < NUM_VISIBLE_CHIPS; i++) {
      activeChips.push(getNextFromPool());
    }
    renderChips();
  }

  if (shuffleBtn) shuffleBtn.addEventListener("click", shuffleAllSuggestions);
  if (quickShuffleBtn) quickShuffleBtn.addEventListener("click", shuffleAllSuggestions);

  /* ── Mode Switching ────────────────────────────────────────── */
  function switchMode(mode) {
    if (currentMode === mode) return;
    currentMode = mode;

    if (tabAdmission && tabDocuments) {
      tabAdmission.classList.toggle("active", mode === "admission");
      tabDocuments.classList.toggle("active", mode === "documents");
    }

    if (mode === "documents") {
      chatInput.placeholder = "Ask about required certificates, NCL validity, EWS Proforma, Gap affidavit, Domicile…";
      appendMessage(
        `### 📑 **MHT-CET Document & Verification AI Advisor**\n\nI specialize in Maharashtra CET Scrutiny & Admission Document Regulations:\n- **Category Verification:** OBC, SC, ST, EWS, VJ/NT, SEBC certificate rules\n- **Validity Deadlines:** Non-Creamy Layer (NCL) validity, Caste Validity receipt rules\n- **Proformas & Affidavits:** Gap Certificate format, TFWS income proof, Domicile Types A–E\n- **Scrutiny Guidelines:** Physical vs E-Scrutiny facilitation center checklist\n\n*Click a suggestion below or ask any document question!*`,
        "bot"
      );
    } else {
      chatInput.placeholder = "Ask about colleges, cutoff percentiles, branches, CAP rounds…";
      appendMessage(
        `### 🎓 **College & Cutoff AI Advisor**\n\nI can help you explore colleges, analyze percentiles, compare branches, and plan your CAP preference list!`,
        "bot"
      );
    }

    initSuggestions();
  }

  if (tabAdmission) {
    tabAdmission.addEventListener("click", () => switchMode("admission"));
  }
  if (tabDocuments) {
    tabDocuments.addEventListener("click", () => switchMode("documents"));
  }

  /* ── Helpers ──────────────────────────────────────────────── */
  function formatTime(d) {
    return (d || new Date()).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  }

  function escapeHtml(str) {
    return str
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function scrollToBottom() {
    requestAnimationFrame(() => {
      msgContainer.scrollTop = msgContainer.scrollHeight;
    });
  }

  /* ── Textarea Auto-Grow ───────────────────────────────────── */
  function autoGrow() {
    chatInput.style.height = "auto";
    chatInput.style.height = Math.min(chatInput.scrollHeight, 120) + "px";
  }

  chatInput.addEventListener("input", autoGrow);

  /* ── Enter / Shift+Enter ──────────────────────────────────── */
  chatInput.addEventListener("keydown", function (e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (!sendBtn.disabled) {
        submitChatMessage();
      }
    }
  });

  /* ── Copy Response Button ─────────────────────────────────── */
  function copyResponse(btn, rawText) {
    const onSuccess = () => {
      btn.classList.add("copied");
      btn.innerHTML = `<i class="bi bi-check2"></i> Copied!`;
      setTimeout(() => {
        btn.classList.remove("copied");
        btn.innerHTML = `<i class="bi bi-clipboard"></i> Copy`;
      }, 2000);
    };

    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(rawText).then(onSuccess).catch(() => fallbackCopy(rawText, onSuccess));
    } else {
      fallbackCopy(rawText, onSuccess);
    }
  }

  function fallbackCopy(rawText, callback) {
    const ta = document.createElement("textarea");
    ta.value = rawText;
    ta.style.position = "fixed";
    ta.style.opacity = "0";
    document.body.appendChild(ta);
    ta.select();
    document.execCommand("copy");
    document.body.removeChild(ta);
    if (callback) callback();
  }

  /* ── Append Message Bubble ────────────────────────────────── */
  function appendMessage(text, role) {
    const isUser = role === "user";
    const row = document.createElement("div");
    row.className = `cb-msg-row${isUser ? " cb-msg-row--user" : " cb-msg-row--bot"}`;

    const content = !isUser && typeof marked !== "undefined"
      ? marked.parse(text)
      : `<p style="margin:0">${escapeHtml(text)}</p>`;

    const copyBtnHtml = !isUser
      ? `<button class="cb-copy-btn" title="Copy response" aria-label="Copy response">
           <i class="bi bi-clipboard"></i> Copy
         </button>`
      : "";

    const avatarIcon = isUser
      ? `<div class="cb-msg-avatar cb-msg-avatar--user"><i class="bi bi-person-fill"></i></div>`
      : `<div class="cb-msg-avatar"><i class="bi ${currentMode === 'documents' ? 'bi-file-earmark-check-fill' : 'bi-robot'}"></i></div>`;

    row.innerHTML = `
      ${!isUser ? avatarIcon : ""}
      <div class="cb-msg-group">
        <div class="cb-bubble cb-bubble--${role}">
          ${content}
          ${copyBtnHtml}
        </div>
        <div class="cb-timestamp">${formatTime()}</div>
      </div>
      ${isUser ? avatarIcon : ""}
    `;

    if (!isUser) {
      const copyBtn = row.querySelector(".cb-copy-btn");
      if (copyBtn) {
        copyBtn.addEventListener("click", () => copyResponse(copyBtn, text));
      }
    }

    msgContainer.appendChild(row);
    scrollToBottom();
  }

  /* ── Typing Indicator ─────────────────────────────────────── */
  function showTypingIndicator() {
    const row = document.createElement("div");
    row.className = "cb-msg-row cb-msg-row--bot";
    row.id = "typing-row";
    row.innerHTML = `
      <div class="cb-msg-avatar"><i class="bi ${currentMode === 'documents' ? 'bi-file-earmark-check-fill' : 'bi-robot'}"></i></div>
      <div class="cb-bubble cb-bubble--bot cb-typing-indicator">
        <span></span><span></span><span></span>
      </div>`;
    msgContainer.appendChild(row);
    scrollToBottom();
    return row;
  }

  function removeTypingIndicator() {
    const row = document.getElementById("typing-row");
    if (row) row.remove();
  }

  /* ── Loading State ────────────────────────────────────────── */
  function setLoading(isLoading) {
    chatInput.disabled = isLoading;
    sendBtn.disabled   = isLoading;
    if (isLoading) {
      sendBtn.innerHTML = `<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>`;
    } else {
      sendBtn.innerHTML = `<i class="bi bi-send-fill"></i>`;
      chatInput.focus();
      chatInput.style.height = "auto";
    }
  }

  /* ── Form & Message Submit ────────────────────────────────── */
  async function submitChatMessage() {
    const message = chatInput.value.trim();
    if (!message) return;

    appendMessage(message, "user");
    chatInput.value = "";
    autoGrow();

    setLoading(true);
    showTypingIndicator();

    try {
      const response = await fetch("/api/chat", {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify({ message, mode: currentMode }),
      });

      removeTypingIndicator();

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();
      appendMessage(
        data.reply || "I received your query. Please let me know if you need specific document criteria, validity dates, or college cutoffs!",
        "bot"
      );

    } catch (err) {
      removeTypingIndicator();
      appendMessage("⚠️ Connection error. Please verify your connection and try asking again.", "bot");
      console.error("[Chatbot] API error:", err);
    } finally {
      setLoading(false);
    }
  }

  chatForm.addEventListener("submit", function (e) {
    e.preventDefault();
    submitChatMessage();
  });

  /* ── Clear Chat ───────────────────────────────────────────── */
  if (clearBtn) {
    clearBtn.addEventListener("click", () => {
      msgContainer.innerHTML = "";
      if (currentMode === "documents") {
        appendMessage(
          `### 📑 **MHT-CET Document & Verification AI Advisor**\n\nAsk any question about certificates, NCL validity, EWS Proforma-V, TFWS income proof, Caste validity receipt, Gap affidavits, and Scrutiny Center verification!`,
          "bot"
        );
      } else {
        appendMessage(
          `👋 Welcome to AdmissionMate AI!\nI can assist you with:\n- **Cutoff Analysis:** Check college & branch cutoffs for your category\n- **College Comparisons:** Compare COEP, VJTI, PICT, SPIT, VIT, etc.\n- **CAP Rounds & Rules:** Step-by-step guidance on option form & seat allocation\n- **Fees & Scholarships:** TFWS, EWS, and government fee concession rules\n\nClick any suggestion below or ask your question! 🎓`,
          "bot"
        );
      }
      shuffleAllSuggestions();
    });
  }

  /* ── Wire Copy Buttons ────────────────────────────────────── */
  document.querySelectorAll(".cb-copy-btn[data-copy-text]").forEach((btn) => {
    btn.addEventListener("click", () => copyResponse(btn, btn.dataset.copyText));
  });

  /* ── Start ────────────────────────────────────────────────── */
  initSuggestions();
  chatInput.focus();

})();
