const faqForm = document.getElementById("faq-form");
const faqList = document.getElementById("faq-list");
const handoffList = document.getElementById("handoff-list");
const conversationList = document.getElementById("conversation-list");
const sessionHistory = document.getElementById("session-history");
const faqCount = document.getElementById("faq-count");
const conversationCount = document.getElementById("conversation-count");
const handoffCount = document.getElementById("handoff-count");
const refreshButton = document.getElementById("refresh-dashboard");
const reindexButton = document.getElementById("reindex-vectors");
const runtimeEndpoint = document.getElementById("runtime-endpoint");
const runtimeMode = document.getElementById("runtime-mode");
const vectorMode = document.getElementById("vector-mode");
const openaiHealthPill = document.getElementById("openai-health-pill");
const openaiHealthMessage = document.getElementById("openai-health-message");
const openaiLastKind = document.getElementById("openai-last-kind");
const openaiLastSuccess = document.getElementById("openai-last-success");
const openaiLastUsage = document.getElementById("openai-last-usage");
const openaiLastError = document.getElementById("openai-last-error");
const assistantSummary = document.getElementById("assistant-summary");
const assistantReply = document.getElementById("assistant-reply");
const assistantProvider = document.getElementById("assistant-provider");
const copyAssistantReplyButton = document.getElementById("copy-assistant-reply");
const faqGapList = document.getElementById("faq-gap-list");
const faqGapCount = document.getElementById("faq-gap-count");
const ordersSearchInput = document.getElementById("orders-search");
const ordersList = document.getElementById("orders-list");
const logoutButton = document.getElementById("logout-button");
const adminUser = document.getElementById("admin-user");

let allConversationsCache = [];
let selectedSessionId = "";
let selectedTicketId = "";
let selectedOrderId = "";
let orderSearchTimer = null;

function escapeHtml(text) {
  return String(text ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function formatTimestamp(value) {
  if (!value) {
    return "尚無紀錄";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return String(value);
  }
  return new Intl.DateTimeFormat("zh-TW", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(date);
}

function formatRequestKind(kind) {
  const labels = {
    customer_reply: "顧客對話回覆",
    staff_assistance: "工單 AI 協助",
    embeddings: "向量索引 / Embedding",
    generic: "一般 OpenAI 請求",
  };
  return labels[kind] || "尚無紀錄";
}

function formatUsage(usage) {
  if (!usage || typeof usage !== "object") {
    return "尚無紀錄";
  }
  const total = Number(usage.total_tokens);
  const input = Number(usage.input_tokens ?? usage.prompt_tokens);
  const output = Number(usage.output_tokens ?? usage.completion_tokens);
  const details = [];
  if (Number.isFinite(input)) {
    details.push(`input ${input}`);
  }
  if (Number.isFinite(output)) {
    details.push(`output ${output}`);
  }
  if (Number.isFinite(total)) {
    details.push(`total ${total}`);
  }
  return details.length ? details.join(" · ") : "尚無紀錄";
}

function setPillTone(element, tone) {
  if (!element) {
    return;
  }
  element.classList.remove("is-success", "is-warning", "is-danger");
  if (tone) {
    element.classList.add(`is-${tone}`);
  }
}

function normalizeOpenAIRuntime(status = {}) {
  const runtime = status.openai_runtime && typeof status.openai_runtime === "object" ? { ...status.openai_runtime } : {};
  const hasOpenAIKey = Boolean(status.has_openai_key);
  runtime.enabled = hasOpenAIKey || Boolean(runtime.enabled);
  if (runtime.enabled && runtime.state === "disabled") {
    runtime.state = "idle";
  }
  return runtime;
}

function renderOpenAIRuntime(runtime = {}) {
  if (!openaiHealthPill || !openaiHealthMessage || !openaiLastKind || !openaiLastSuccess || !openaiLastUsage || !openaiLastError) {
    return;
  }

  openaiLastKind.textContent = formatRequestKind(runtime.last_request_kind);
  openaiLastSuccess.textContent = formatTimestamp(runtime.last_success_at);
  openaiLastUsage.textContent = formatUsage(runtime.last_usage);

  const errorBits = [];
  if (runtime.last_error_code) {
    errorBits.push(runtime.last_error_code);
  }
  if (runtime.last_error_message) {
    errorBits.push(runtime.last_error_message);
  }
  openaiLastError.textContent = errorBits.length ? errorBits.join(" · ") : "目前沒有錯誤";

  if (runtime.state === "backend_unavailable") {
    openaiHealthPill.textContent = "後端離線";
    setPillTone(openaiHealthPill, "warning");
    openaiHealthMessage.textContent = "目前無法連到後端，因此也拿不到 OpenAI runtime 狀態。請先確認 server 是否正在運行。";
    return;
  }

  if (!runtime.enabled) {
    openaiHealthPill.textContent = "未啟用";
    setPillTone(openaiHealthPill, "");
    openaiHealthMessage.textContent = "目前尚未設定 OPENAI_API_KEY，因此系統會改走本地 fallback，不會消耗 OpenAI 額度。";
    return;
  }

  if (runtime.state === "quota_exhausted" || runtime.quota_exhausted) {
    openaiHealthPill.textContent = "額度不足";
    setPillTone(openaiHealthPill, "danger");
    openaiHealthMessage.textContent = "最近一次 OpenAI 請求疑似因額度或帳務限制失敗。建議到 OpenAI Billing 檢查 credit、付款方式或 hard limit。";
    return;
  }

  if (runtime.state === "error") {
    openaiHealthPill.textContent = "異常";
    setPillTone(openaiHealthPill, "warning");
    openaiHealthMessage.textContent = "最近一次 OpenAI 請求失敗，顧客端可能會自動退回 fallback 回覆。可以先查看下方錯誤內容。";
    return;
  }

  if (runtime.state === "ok") {
    openaiHealthPill.textContent = "正常";
    setPillTone(openaiHealthPill, "success");
    openaiHealthMessage.textContent = "最近一次 OpenAI 請求已成功完成。若之後額度不足或 API 失敗，這裡會立即顯示提醒。";
    return;
  }

  openaiHealthPill.textContent = "待使用";
  setPillTone(openaiHealthPill, "");
  openaiHealthMessage.textContent = "OpenAI 已啟用，但目前還沒有可判讀的請求紀錄。等顧客發問或重建向量索引後，這裡會更新狀態。";
}

async function readJson(response) {
  try {
    return await response.json();
  } catch (_error) {
    return {};
  }
}

async function adminFetch(url, options = {}) {
  const response = await fetch(url, options);
  const data = await readJson(response);
  if (response.status === 401) {
    const next = encodeURIComponent(window.location.pathname);
    window.location.href = `/login.html?next=${next}&reason=session_expired`;
    throw new Error(data.error || "需要先登入後台");
  }
  return { response, data };
}

function renderSessionHistory(items) {
  if (!sessionHistory) {
    return;
  }
  if (!items.length) {
    sessionHistory.innerHTML = `<p class="empty-state">這個 session 目前還沒有可顯示的聊天紀錄。</p>`;
    return;
  }
  sessionHistory.innerHTML = items
    .map(
      (item) => `
        <article class="history-item">
          <div class="history-top">
            <strong>${escapeHtml(item.id)}</strong>
            <span>${escapeHtml(item.created_at.replace("T", " "))}</span>
          </div>
          <p><strong>顧客：</strong>${escapeHtml(item.customer_message)}</p>
          <p><strong>AI：</strong>${escapeHtml(item.response)}</p>
        </article>
      `,
    )
    .join("");
}

async function loadSessionHistory(sessionId) {
  if (!sessionId || !sessionHistory) {
    return;
  }
  selectedSessionId = sessionId;
  sessionHistory.innerHTML = `<p class="empty-state">載入中...</p>`;
  const { response, data } = await adminFetch(`/api/conversations?session_id=${encodeURIComponent(sessionId)}`);
  if (!response.ok) {
    renderSessionHistory([]);
    return;
  }
  renderSessionHistory(data.items || []);
}

function renderTicketAssistance(payload) {
  if (!assistantSummary || !assistantReply || !assistantProvider) {
    return;
  }
  if (!payload) {
    assistantSummary.innerHTML = "從上方待處理案件選擇一筆工單後，這裡會顯示 AI 協助整理的案件摘要。";
    assistantReply.innerHTML = "選擇工單後，系統會提供一段可交給客服人員參考的回覆草稿。";
    assistantProvider.textContent = "尚未選擇工單";
    return;
  }
  assistantSummary.textContent = payload.summary || "目前沒有可用摘要。";
  assistantReply.textContent = payload.suggested_reply || "目前沒有可用建議回覆。";
  assistantProvider.textContent = `${payload.provider || "local"} · ${payload.ticket_id}`;
}

async function loadTicketAssistance(ticketId) {
  if (!ticketId || !assistantSummary || !assistantReply || !assistantProvider) {
    return;
  }
  selectedTicketId = ticketId;
  assistantSummary.textContent = "整理中...";
  assistantReply.textContent = "產生建議回覆中...";
  assistantProvider.textContent = "AI Assist";
  const { response, data } = await adminFetch(`/api/tickets/assistance?ticket_id=${encodeURIComponent(ticketId)}`);
  if (!response.ok) {
    renderTicketAssistance(null);
    return;
  }
  renderTicketAssistance(data);
}

function fallbackCopyText(text) {
  const textarea = document.createElement("textarea");
  textarea.value = text;
  textarea.setAttribute("readonly", "");
  textarea.style.position = "absolute";
  textarea.style.left = "-9999px";
  document.body.appendChild(textarea);
  textarea.select();
  const success = document.execCommand("copy");
  document.body.removeChild(textarea);
  return success;
}

async function copyAssistantReply() {
  if (!assistantReply) {
    return;
  }
  const text = assistantReply.textContent.trim();
  if (!text || text.includes("選擇工單後") || text.includes("產生建議回覆中")) {
    alert("目前還沒有可複製的 AI 建議回覆。");
    return;
  }
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text);
    } else {
      const copied = fallbackCopyText(text);
      if (!copied) {
        throw new Error("clipboard unavailable");
      }
    }
    if (copyAssistantReplyButton) {
      const originalLabel = copyAssistantReplyButton.textContent;
      copyAssistantReplyButton.textContent = "已複製";
      window.setTimeout(() => {
        copyAssistantReplyButton.textContent = originalLabel;
      }, 1200);
    }
  } catch (_error) {
    alert("複製失敗，請手動選取建議回覆內容。");
  }
}

async function updateWorkflow(ticketId, payload) {
  const { response, data } = await adminFetch("/api/conversations/workflow", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ticket_id: ticketId, ...payload }),
  });
  if (!response.ok) {
    throw new Error(data.error || "更新工單失敗");
  }
  return data;
}

function renderTickets(items) {
  if (!handoffList) {
    return;
  }
  if (!items.length) {
    handoffList.innerHTML = `<p class="empty-state">目前沒有待人工處理案件，代表這批 FAQ 已經能覆蓋大部分情境。</p>`;
    renderTicketAssistance(null);
    return;
  }

  const template = document.getElementById("ticket-template");
  handoffList.innerHTML = "";

  items.forEach((item) => {
    const clone = template.content.cloneNode(true);
    const container = clone.querySelector(".ticket-card");
    if (item.id === selectedTicketId) {
      container.classList.add("active");
    }
    clone.querySelector(".ticket-id").textContent = item.id;
    clone.querySelector(".ticket-time").textContent = item.created_at.replace("T", " ");
    clone.querySelector(".ticket-message").textContent = `顧客問題：${item.customer_message}`;
    clone.querySelector(".ticket-response").textContent = `AI 回覆：${item.response}`;
    clone.querySelector(".ticket-meta").textContent = `session：${item.session_id} · 狀態：${item.handoff_status || "pending"}`;
    clone.querySelector(".ticket-assigned").value = item.assigned_to || "";
    clone.querySelector(".ticket-status").value = item.handoff_status || "pending";
    clone.querySelector(".ticket-notes").value = item.handoff_notes || "";
    clone.querySelector(".ticket-ai-btn").addEventListener("click", async () => {
      await loadTicketAssistance(item.id);
      await loadSessionHistory(item.session_id);
      renderTickets(items);
    });
    clone.querySelector(".ticket-history-btn").addEventListener("click", () => {
      loadSessionHistory(item.session_id);
    });
    clone.querySelector(".ticket-save-btn").addEventListener("click", async () => {
      const assignedTo = container.querySelector(".ticket-assigned").value.trim();
      const handoffStatus = container.querySelector(".ticket-status").value;
      const handoffNotes = container.querySelector(".ticket-notes").value.trim();
      try {
        await updateWorkflow(item.id, {
          assigned_to: assignedTo,
          handoff_status: handoffStatus,
          handoff_notes: handoffNotes,
        });
        await refreshDashboard();
      } catch (error) {
        alert(error.message || "更新工單失敗");
      }
    });
    handoffList.appendChild(clone);
  });
}

function renderConversationList(items) {
  if (!conversationList) {
    return;
  }
  if (!items.length) {
    conversationList.innerHTML = `<p class="empty-state">目前還沒有聊天紀錄。</p>`;
    return;
  }
  conversationList.innerHTML = items
    .map(
      (item) => `
        <button type="button" class="conversation-item${item.session_id === selectedSessionId ? " active" : ""}" data-session-id="${escapeHtml(item.session_id)}">
          <strong>${escapeHtml(item.session_id)}</strong>
          <span>${escapeHtml(item.customer_message)}</span>
          <small>${escapeHtml(item.created_at.replace("T", " "))}</small>
        </button>
      `,
    )
    .join("");

  conversationList.querySelectorAll(".conversation-item").forEach((button) => {
    button.addEventListener("click", () => {
      loadSessionHistory(button.dataset.sessionId);
    });
  });
}

function renderFaq(items) {
  if (!faqList || !faqCount) {
    return;
  }
  faqCount.textContent = items.length;
  faqList.innerHTML = items
    .map(
      (item) => `
      <article class="faq-item">
        <h4>${escapeHtml(item.question)}</h4>
        <p>${escapeHtml(item.answer)}</p>
        <div class="faq-meta">
          <span class="pill">${escapeHtml(item.id)}</span>
          <span class="pill">${escapeHtml(item.category)}</span>
          ${(item.keywords || []).map((keyword) => `<span class="pill">${escapeHtml(keyword)}</span>`).join("")}
        </div>
      </article>
    `,
    )
    .join("");
}

function renderFaqGaps(items) {
  if (!faqGapList) {
    return;
  }
  if (faqGapCount) {
    faqGapCount.textContent = `${items.length} 個缺口`;
  }
  if (!items.length) {
    faqGapList.innerHTML = `<p class="empty-state">目前 FAQ 覆蓋率不錯，還沒有明顯缺口。</p>`;
    return;
  }
  faqGapList.innerHTML = items
    .map(
      (item, index) => `
        <article class="gap-item">
          <div class="demo-order-top">
            <strong>${escapeHtml(item.topic)}</strong>
            <span>${escapeHtml(String(item.count))} 次</span>
          </div>
          <p><span class="gap-reason">${escapeHtml(item.reason)}</span> · ${escapeHtml(item.intent)}</p>
          <small>${escapeHtml(item.latest_message)}</small>
          <button
            type="button"
            class="secondary-btn gap-fill-btn"
            data-topic="${escapeHtml(item.topic)}"
            data-latest-message="${escapeHtml(item.latest_message)}"
            data-intent="${escapeHtml(item.intent)}"
            data-index="${index + 1}"
          >
            帶入 FAQ 表單
          </button>
        </article>
      `,
    )
    .join("");

  faqGapList.querySelectorAll(".gap-fill-btn").forEach((button) => {
    button.addEventListener("click", () => {
      const faqIdInput = document.getElementById("faq-id");
      const faqCategoryInput = document.getElementById("faq-category");
      const faqQuestionInput = document.getElementById("faq-question");
      const faqAnswerInput = document.getElementById("faq-answer");
      const faqKeywordsInput = document.getElementById("faq-keywords");
      const topic = button.dataset.topic || "";
      const latestMessage = button.dataset.latestMessage || "";
      const intent = button.dataset.intent || "general";
      const index = button.dataset.index || "1";

      if (faqIdInput && !faqIdInput.value.trim()) {
        faqIdInput.value = `FAQ-GAP-${String(index).padStart(2, "0")}`;
      }
      if (faqCategoryInput && !faqCategoryInput.value.trim()) {
        faqCategoryInput.value = intent;
      }
      if (faqQuestionInput) {
        faqQuestionInput.value = latestMessage || topic;
      }
      if (faqAnswerInput && !faqAnswerInput.value.trim()) {
        faqAnswerInput.value = "請補上這題的標準客服回答。";
      }
      if (faqKeywordsInput && !faqKeywordsInput.value.trim()) {
        faqKeywordsInput.value = `${topic},${intent}`;
      }
      faqQuestionInput?.focus();
    });
  });
}

async function loadFaqGapAnalysis() {
  if (!faqGapList) {
    return;
  }
  const { response, data } = await adminFetch("/api/analysis/faq-gaps");
  if (!response.ok) {
    faqGapList.innerHTML = `<p class="empty-state">暫時無法取得 FAQ 缺口分析。</p>`;
    return;
  }
  renderFaqGaps(data.items || []);
}

function renderOrders(items) {
  if (!ordersList) {
    return;
  }
  if (!items.length) {
    selectedOrderId = "";
    ordersList.innerHTML = `<p class="empty-state">目前沒有符合條件的訂單資料。</p>`;
    return;
  }
  if (!selectedOrderId || !items.some((item) => item.order_id === selectedOrderId)) {
    selectedOrderId = items[0].order_id;
  }
  ordersList.innerHTML = items
    .map(
      (item) => `
        <article class="demo-order-item order-card${item.order_id === selectedOrderId ? " expanded" : ""}" data-order-id="${escapeHtml(item.order_id)}">
          <div class="demo-order-top">
            <strong>${escapeHtml(item.order_id)}</strong>
            <span>${escapeHtml(item.shipping_status)}</span>
          </div>
          <p>${escapeHtml(item.customer_name)} · 手機末四碼 ${escapeHtml(item.customer_phone_last4)}</p>
          <small>訂單狀態：${escapeHtml(item.status)} · 付款：${escapeHtml(item.payment_status)}</small>
          <div class="order-detail">
            <div class="order-detail-grid">
              <div><span>訂單狀態</span><strong>${escapeHtml(item.status)}</strong></div>
              <div><span>出貨狀態</span><strong>${escapeHtml(item.shipping_status)}</strong></div>
              <div><span>付款狀態</span><strong>${escapeHtml(item.payment_status)}</strong></div>
              <div><span>發票類型</span><strong>${escapeHtml(item.invoice_type)}</strong></div>
              <div><span>物流單號</span><strong>${escapeHtml(item.tracking_number || "尚未產生")}</strong></div>
              <div><span>訂單金額</span><strong>NT$${escapeHtml(String(item.amount))}</strong></div>
            </div>
            <div class="order-items">
              <span>商品內容</span>
              <p>${(item.items || []).map((product) => escapeHtml(product)).join("、") || "未提供"}</p>
            </div>
          </div>
        </article>
      `,
    )
    .join("");

  ordersList.querySelectorAll(".order-card").forEach((card) => {
    card.addEventListener("click", () => {
      selectedOrderId = card.dataset.orderId || "";
      renderOrders(items);
    });
  });
}

async function loadOrders(query = "") {
  if (!ordersList) {
    return;
  }
  const suffix = query ? `?q=${encodeURIComponent(query)}` : "";
  const { response, data } = await adminFetch(`/api/orders${suffix}`);
  if (!response.ok) {
    ordersList.innerHTML = `<p class="empty-state">暫時無法取得訂單資料。</p>`;
    return;
  }
  renderOrders(data.items || []);
}

async function refreshDashboard() {
  try {
    if (window.location.protocol === "file:") {
      return;
    }
    const [faqResult, conversationsResult, handoffResult] = await Promise.all([
      adminFetch("/api/faq"),
      adminFetch("/api/conversations"),
      adminFetch("/api/conversations?needs_handoff=true"),
    ]);

    allConversationsCache = conversationsResult.data.items || [];
    renderFaq(faqResult.data.items || []);
    const handoffItems = handoffResult.data.items || [];
    renderTickets(handoffItems);
    renderConversationList(allConversationsCache);
    if (conversationCount) {
      conversationCount.textContent = allConversationsCache.length;
    }
    if (handoffCount) {
      handoffCount.textContent = handoffItems.length;
    }

    await Promise.all([loadFaqGapAnalysis(), loadOrders(ordersSearchInput ? ordersSearchInput.value.trim() : "")]);

    if (!selectedTicketId && handoffItems.length) {
      selectedTicketId = handoffItems[0].id;
      selectedSessionId = handoffItems[0].session_id;
      renderTickets(handoffItems);
      await Promise.all([
        loadTicketAssistance(handoffItems[0].id),
        loadSessionHistory(handoffItems[0].session_id),
      ]);
    }

    if (selectedSessionId) {
      await loadSessionHistory(selectedSessionId);
    }
    if (selectedTicketId) {
      await loadTicketAssistance(selectedTicketId);
    }
  } catch (_error) {
    if (handoffList) {
      handoffList.innerHTML = `<p class="empty-state">目前無法取得後台資料，請確認 server 是否已啟動。</p>`;
    }
  }
}

async function loadStatus() {
  if (!runtimeEndpoint || !runtimeMode || !vectorMode) {
    return;
  }
  if (window.location.protocol === "file:") {
    runtimeEndpoint.textContent = "static preview";
    runtimeMode.textContent = "需要後端 server 才能對話";
    vectorMode.textContent = "API unavailable in file mode";
    renderOpenAIRuntime();
    return;
  }
  try {
    const response = await fetch("/api/status");
    const data = await readJson(response);
    runtimeEndpoint.textContent = window.location.host;
    runtimeMode.textContent = data.has_openai_key ? `OpenAI Responses API · ${data.model}` : "local fallback mode";
    vectorMode.textContent = data.vector_index_ready
      ? `vector db ready · ${data.vector_backend} · ${data.embedding_model} · ${data.vector_entries} entries`
      : `vector db not ready · ${data.vector_backend} · ${data.embedding_model}${data.vector_status_error ? ` · ${data.vector_status_error}` : ""}`;
    renderOpenAIRuntime(normalizeOpenAIRuntime(data));
  } catch (_error) {
    runtimeEndpoint.textContent = window.location.host || "unknown";
    runtimeMode.textContent = "後端未連線";
    vectorMode.textContent = "請確認 server 已啟動";
    renderOpenAIRuntime({
      enabled: false,
      state: "backend_unavailable",
      last_error_code: "backend_unavailable",
      last_error_message: "後端未連線，無法取得 OpenAI runtime 狀態。",
    });
  }
}

async function ensureAdminSession() {
  const response = await fetch("/api/admin/session");
  const data = await readJson(response);
  if (!data.authenticated) {
    const next = encodeURIComponent(window.location.pathname);
    window.location.href = `/login.html?next=${next}&reason=session_expired`;
    return false;
  }
  if (adminUser) {
    adminUser.textContent = data.username ? `已登入：${data.username}` : "Staff Only";
  }
  return true;
}

async function logoutAdmin() {
  await fetch("/api/admin/logout", { method: "POST" });
  window.location.href = "/login.html";
}

async function initAdminPage() {
  if (window.location.protocol === "file:") {
    return;
  }
  const ok = await ensureAdminSession();
  if (!ok) {
    return;
  }
  renderTicketAssistance(null);
  await loadStatus();
  await refreshDashboard();
}

if (faqForm) {
  faqForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const payload = {
      id: document.getElementById("faq-id").value.trim(),
      category: document.getElementById("faq-category").value.trim(),
      question: document.getElementById("faq-question").value.trim(),
      answer: document.getElementById("faq-answer").value.trim(),
      keywords: document
        .getElementById("faq-keywords")
        .value.split(",")
        .map((item) => item.trim())
        .filter(Boolean),
    };

    const { response, data } = await adminFetch("/api/faq", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      alert(data.error || "新增 FAQ 失敗");
      return;
    }
    faqForm.reset();
    await refreshDashboard();
  });
}

if (refreshButton) {
  refreshButton.addEventListener("click", refreshDashboard);
}

if (reindexButton) {
  reindexButton.addEventListener("click", async () => {
    if (window.location.protocol === "file:") {
      alert("目前是靜態預覽模式，請先啟動 python3 server.py");
      return;
    }
    reindexButton.disabled = true;
    reindexButton.textContent = "建立中...";
    const { response, data } = await adminFetch("/api/reindex", { method: "POST" });
    if (!response.ok) {
      alert(data.error || "重建向量索引失敗");
    } else {
      alert(`向量索引完成：${data.count} 筆，model=${data.model}`);
    }
    reindexButton.disabled = false;
    reindexButton.textContent = "重建向量索引";
    await loadStatus();
    await refreshDashboard();
  });
}

if (ordersSearchInput) {
  ordersSearchInput.addEventListener("input", () => {
    clearTimeout(orderSearchTimer);
    orderSearchTimer = window.setTimeout(() => {
      loadOrders(ordersSearchInput.value.trim());
    }, 180);
  });
}

if (logoutButton) {
  logoutButton.addEventListener("click", logoutAdmin);
}

if (copyAssistantReplyButton) {
  copyAssistantReplyButton.addEventListener("click", copyAssistantReply);
}

initAdminPage();
