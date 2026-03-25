import os
from dataclasses import dataclass
from pathlib import Path


def load_dotenv_file(dotenv_path: Path):
    if not dotenv_path.exists():
        return

    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


@dataclass(frozen=True)
class AppConfig:
    base_dir: Path
    static_dir: Path
    data_dir: Path
    sqlite_path: Path
    faq_path: Path
    orders_path: Path
    conversations_path: Path
    sessions_path: Path
    vector_store_path: Path
    chroma_dir: Path
    openai_api_key: str
    openai_model: str
    openai_base_url: str
    embedding_model: str
    admin_username: str
    admin_password: str
    admin_cookie_name: str
    host: str
    port: int


def load_config() -> AppConfig:
    base_dir = Path(__file__).resolve().parent.parent
    load_dotenv_file(base_dir / ".env")
    data_dir = base_dir / "data"
    return AppConfig(
        base_dir=base_dir,
        static_dir=base_dir / "static",
        data_dir=data_dir,
        sqlite_path=data_dir / "app.db",
        faq_path=data_dir / "faq.json",
        orders_path=data_dir / "orders.json",
        conversations_path=data_dir / "conversations.json",
        sessions_path=data_dir / "sessions.json",
        vector_store_path=data_dir / "vector_store.json",
        chroma_dir=data_dir / "chroma_db",
        openai_api_key=os.environ.get("OPENAI_API_KEY", ""),
        openai_model=os.environ.get("OPENAI_MODEL", "gpt-4.1-mini"),
        openai_base_url=os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        embedding_model=os.environ.get("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
        admin_username=os.environ.get("ADMIN_USERNAME", "admin"),
        admin_password=os.environ.get("ADMIN_PASSWORD", "supportos123"),
        admin_cookie_name=os.environ.get("ADMIN_COOKIE_NAME", "supportos_admin_session"),
        host=os.environ.get("HOST", "0.0.0.0"),
        port=int(os.environ.get("PORT", "8000")),
    )
