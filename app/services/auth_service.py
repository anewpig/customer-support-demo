import secrets


class AuthService:
    def __init__(self, config):
        self.config = config
        self.sessions = {}

    def login(self, username, password):
        if username != self.config.admin_username:
            return {"ok": False, "error_code": "invalid_username", "message": "帳號錯誤，請重新確認 ADMIN_USERNAME。"}
        if password != self.config.admin_password:
            return {"ok": False, "error_code": "invalid_password", "message": "密碼錯誤，請重新確認 ADMIN_PASSWORD。"}
        token = secrets.token_urlsafe(24)
        self.sessions[token] = {"username": username}
        return {"ok": True, "token": token, "username": username}

    def get_session(self, token):
        if not token:
            return None
        return self.sessions.get(token)

    def is_authorized(self, token):
        return self.get_session(token) is not None

    def logout(self, token):
        if token in self.sessions:
            self.sessions.pop(token, None)
