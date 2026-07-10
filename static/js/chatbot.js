/**
 * chatbot.js — Chat Assistant UI
 * =====================================================
 * Handles all chatbot interaction:
 *   - Message rendering with Markdown (marked.js)
 *   - Auto-growing textarea (Enter=send, Shift+Enter=newline)
 *   - Typing indicator
 *   - Copy button
 *   - Suggested prompt chips
 *   - Auto-scroll & loading state
 *
 * POSTs to /api/chat — no backend changes.
 * =====================================================
 */

"use strict";

(function initChatbot() {

  /* ── DOM refs ──────────────────────────────────────────────── */
  const chatForm      = document.getElementById("chat-form");
  const chatInput     = document.getElementById("chat-input");
  const msgContainer  = document.getElementById("chat-messages");
  const sendBtn       = document.getElementById("send-btn");
  const clearBtn      = document.getElementById("clear-chat-btn");
  const promptChips   = document.getElementById("prompt-chips");

  // Only run on the chatbot page
  if (!chatForm || !chatInput || !msgContainer) return;

  /* ── Configure marked.js ──────────────────────────────────── */
  if (typeof marked !== "undefined") {
    try {
      marked.use({ breaks: true, gfm: true });
    } catch (_) {
      // older marked v1/v2
      marked.setOptions && marked.setOptions({ breaks: true, gfm: true });
    }
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

  /* ── Textarea auto-grow ───────────────────────────────────── */
  function autoGrow() {
    chatInput.style.height = "auto";
    chatInput.style.height = chatInput.scrollHeight + "px";
  }

  chatInput.addEventListener("input", autoGrow);

  /* ── Enter / Shift+Enter ──────────────────────────────────── */
  chatInput.addEventListener("keydown", function (e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (!sendBtn.disabled) {
        chatForm.dispatchEvent(new Event("submit", { cancelable: true }));
      }
    }
  });

  /* ── Copy button logic ────────────────────────────────────── */
  function copyResponse(btn, rawText) {
    navigator.clipboard.writeText(rawText).then(() => {
      btn.classList.add("copied");
      btn.innerHTML = `<i class="bi bi-check2"></i> Copied!`;
      setTimeout(() => {
        btn.classList.remove("copied");
        btn.innerHTML = `<i class="bi bi-clipboard"></i> Copy`;
      }, 2000);
    }).catch(() => {
      // Fallback for older browsers / non-secure contexts
      const ta = document.createElement("textarea");
      ta.value = rawText;
      ta.style.position = "fixed";
      ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      document.body.removeChild(ta);
      btn.classList.add("copied");
      btn.innerHTML = `<i class="bi bi-check2"></i> Copied!`;
      setTimeout(() => {
        btn.classList.remove("copied");
        btn.innerHTML = `<i class="bi bi-clipboard"></i> Copy`;
      }, 2000);
    });
  }

  /* ── Append a message bubble ──────────────────────────────── */
  function appendMessage(text, role) {
    const isUser = role === "user";

    const row = document.createElement("div");
    row.className = `cb-msg-row${isUser ? " cb-msg-row--user" : " cb-msg-row--bot"}`;

    // Markdown for bot; escaped plain text for user
    const content =
      !isUser && typeof marked !== "undefined"
        ? marked.parse(text)
        : `<p style="margin:0">${escapeHtml(text)}</p>`;

    const copyBtnHtml = !isUser
      ? `<button class="cb-copy-btn" title="Copy response" aria-label="Copy response">
           <i class="bi bi-clipboard"></i> Copy
         </button>`
      : "";

    const avatarIcon = isUser
      ? `<div class="cb-msg-avatar cb-msg-avatar--user"><i class="bi bi-person-fill"></i></div>`
      : `<div class="cb-msg-avatar"><i class="bi bi-robot"></i></div>`;

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

    // Wire copy button
    if (!isUser) {
      const copyBtn = row.querySelector(".cb-copy-btn");
      if (copyBtn) {
        copyBtn.addEventListener("click", () => copyResponse(copyBtn, text));
      }
    }

    msgContainer.appendChild(row);
    scrollToBottom();
  }

  /* ── Typing indicator ─────────────────────────────────────── */
  function showTypingIndicator() {
    const row = document.createElement("div");
    row.className = "cb-msg-row cb-msg-row--bot";
    row.id = "typing-row";
    row.innerHTML = `
      <div class="cb-msg-avatar"><i class="bi bi-robot"></i></div>
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

  /* ── Loading state ────────────────────────────────────────── */
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

  /* ── Welcome message (after clear) ───────────────────────── */
  function appendWelcomeMessage() {
    appendMessage(
      `👋 Hi there! I'm your **College Admission Assistant**.\nI can help you with:\n- Finding colleges based on your CET percentile\n- Understanding cutoff trends\n- Comparing branches and career paths\n- Scholarship and fee information\n\nWhat would you like to know? 🎓`,
      "bot"
    );
  }

  /* ── Prompt chips ─────────────────────────────────────────── */
  if (promptChips) {
    promptChips.querySelectorAll(".cb-chip").forEach((chip) => {
      chip.addEventListener("click", () => {
        const msg = chip.dataset.msg;
        if (!msg) return;
        chatInput.value = msg;
        autoGrow();
        chatInput.focus();
        promptChips.classList.add("hidden");
      });
    });
  }

  /* ── Clear chat ───────────────────────────────────────────── */
  if (clearBtn) {
    clearBtn.addEventListener("click", () => {
      msgContainer.innerHTML = "";
      if (promptChips) promptChips.classList.remove("hidden");
      appendWelcomeMessage();
    });
  }

  /* ── Form submit ──────────────────────────────────────────── */
  chatForm.addEventListener("submit", async function (e) {
    e.preventDefault();

    const message = chatInput.value.trim();
    if (!message) return;

    if (promptChips) promptChips.classList.add("hidden");

    appendMessage(message, "user");
    chatInput.value = "";
    autoGrow();

    setLoading(true);
    showTypingIndicator();

    try {
      const response = await fetch("/api/chat", {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify({ message }),
      });

      removeTypingIndicator();

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();
      appendMessage(
        data.reply || "Sorry, I didn't get a response. Please try again.",
        "bot"
      );

    } catch (err) {
      removeTypingIndicator();
      appendMessage("⚠️ Connection error. Please check your network and try again.", "bot");

      if (typeof showToast === "function") {
        showToast("Could not reach the AI service.", "danger");
      }

      console.error("[Chatbot] Fetch error:", err);
    } finally {
      setLoading(false);
    }
  });

  /* ── Init: wire copy buttons on server-rendered bubbles ───── */
  document.querySelectorAll(".cb-copy-btn[data-copy-text]").forEach((btn) => {
    btn.addEventListener("click", () => copyResponse(btn, btn.dataset.copyText));
  });

  // Focus input on load
  chatInput.focus();

})();
