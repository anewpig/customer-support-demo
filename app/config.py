import os #操作環境變數
from dataclasses import dataclass #讓class自動擁有初始化等功能
from pathlib import Path #用物件的方式處理路徑，較安全也好讀


def load_dotenv_file(dotenv_path: Path): #讀取.env
    if not dotenv_path.exists(): #如果檔案不存在，就直接結束
        return

    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines(): #用UTF-8編碼讀取檔案，然後逐行處理
        line = raw_line.strip() #去掉行首行尾的空白
        if not line or line.startswith("#") or "=" not in line: #如果是空行、註解行（以#開頭）或不包含=的行，就跳過
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
