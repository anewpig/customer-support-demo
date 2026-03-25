const loginForm = document.getElementById("admin-login-form");
const loginUsername = document.getElementById("login-username");
const loginPassword = document.getElementById("login-password");
const loginError = document.getElementById("login-error");

async function readJson(response) {
  try {
    return await response.json();
  } catch (_error) {
    return {};
  }
}

async function initLoginPage() {
  if (!loginForm || window.location.protocol === "file:") {
    return;
  }

  const params = new URLSearchParams(window.location.search);
  const reason = params.get("reason");
  if (reason === "session_expired" && loginError) {
    loginError.hidden = false;
    loginError.textContent = "登入狀態已過期，請重新登入後再繼續操作。";
  }

  const sessionResponse = await fetch("/api/admin/session");
  const sessionData = await readJson(sessionResponse);
  if (sessionData.authenticated) {
    window.location.href = "/admin.html";
    return;
  }

  loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (loginError) {
      loginError.hidden = true;
      loginError.textContent = "";
    }

    const response = await fetch("/api/admin/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        username: loginUsername ? loginUsername.value.trim() : "",
        password: loginPassword ? loginPassword.value : "",
      }),
    });
    const data = await readJson(response);
    if (!response.ok) {
      if (loginError) {
        loginError.hidden = false;
        if (data.error_code === "invalid_username") {
          loginError.textContent = "帳號錯誤，請重新確認你輸入的帳號。";
        } else if (data.error_code === "invalid_password") {
          loginError.textContent = "密碼錯誤，請重新確認你輸入的密碼。";
        } else {
          loginError.textContent = data.error || "登入失敗";
        }
      }
      return;
    }

    const next = new URLSearchParams(window.location.search).get("next") || "/admin.html";
    window.location.href = next;
  });
}

initLoginPage();
