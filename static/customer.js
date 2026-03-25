const chatLog = document.getElementById("chat-log");
const chatForm = document.getElementById("chat-form");
const messageInput = document.getElementById("message-input");
const customerNameInput = document.getElementById("customer-name");
const customerPhoneLast4Input = document.getElementById("customer-phone-last4");
const quickShortcutButtons = Array.from(document.querySelectorAll(".quick-shortcut"));

const SESSION_KEY = "customer-support-session-id";

function getSessionId() {
  let value = window.localStorage.getItem(SESSION_KEY);
  if (!value) {
    value = `session-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    window.localStorage.setItem(SESSION_KEY, value);
  }
  return value;
}

function escapeHtml(text) {
  return String(text ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function formatMessageTime(value) {
  const date = value ? new Date(value) : new Date();
  if (Number.isNaN(date.getTime())) {
    return "";
  }
  return new Intl.DateTimeFormat("zh-TW", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(date);
}

async function readJson(response) {
  try {
    return await response.json();
  } catch (_error) {
    return {};
  }
}

function appendMessage(role, html) {
  if (!chatLog) {
    return;
  }
  const article = document.createElement("article");
  article.className = `message ${role}`;
  article.innerHTML = html;
  chatLog.appendChild(article);
  chatLog.scrollTop = chatLog.scrollHeight;
}

function renderSystemNotice(message) {
  appendMessage(
    "assistant",
    `
      <span class="badge">系統提示</span>
      <p>${escapeHtml(message).replaceAll("\n", "<br />")}</p>
      <div class="message-time">${formatMessageTime()}</div>
    `,
  );
}

function renderAssistantReply(ticket) {
  appendMessage(
    "assistant",
    `
      <span class="badge">AI 客服</span>
      <p>${escapeHtml(ticket.response).replaceAll("\n", "<br />")}</p>
      <div class="message-time">${formatMessageTime(ticket.created_at)}</div>
    `,
  );
}

async function sendMessage(message) {
  appendMessage(
    "user",
    `
      <span class="badge">顧客</span>
      <p>${escapeHtml(message)}</p>
      <div class="message-time">${formatMessageTime()}</div>
    `,
  );

  try {
    if (window.location.protocol === "file:") {
      throw new Error("目前是直接打開 HTML 檔，沒有後端 API。請改用 python3 server.py 啟動後再開網頁。");
    }

    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message,
        session_id: getSessionId(),
        customer_name: customerNameInput ? customerNameInput.value.trim() : "",
        customer_phone_last4: customerPhoneLast4Input ? customerPhoneLast4Input.value.trim() : "",
      }),
    });
    const ticket = await readJson(response);
    if (!response.ok) {
      throw new Error(ticket.error || "AI 客服暫時無法回應。");
    }
    renderAssistantReply(ticket);
  } catch (error) {
    renderSystemNotice(error.message || "目前無法連線到後端服務，請確認 server 是否已啟動。");
  }
}

if (chatForm && messageInput) {
  messageInput.addEventListener("keydown", async (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      const message = messageInput.value.trim();
      if (!message) {
        return;
      }
      messageInput.value = "";
      await sendMessage(message);
    }
  });

  chatForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const message = messageInput.value.trim();
    if (!message) {
      return;
    }
    messageInput.value = "";
    await sendMessage(message);
  });
}

if (quickShortcutButtons.length) {
  quickShortcutButtons.forEach((button) => {
    button.addEventListener("click", async () => {
      const shortcutMessage = button.dataset.message || "";
      if (!shortcutMessage) {
        return;
      }
      if (messageInput) {
        messageInput.value = "";
      }
      await sendMessage(shortcutMessage);
    });
  });
}
