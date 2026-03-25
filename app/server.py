from http.server import ThreadingHTTPServer

from app.config import load_config
from app.repositories import json_repository
from app.repositories.sqlite_repository import SQLiteRepository
from app.services.chat_service import ChatService
from app.services.auth_service import AuthService
from app.services.cleaning_service import FAQCleaningService
from app.services.openai_service import OpenAIService
from app.services.vector_store_service import VectorStoreService
from app.web.handler import create_app_handler


def create_app():
    config = load_config()
    cleaning_service = FAQCleaningService(config.faq_path)
    openai_service = OpenAIService(config)
    auth_service = AuthService(config)
    vector_store_service = VectorStoreService(config, openai_service, json_repository)
    sqlite_repository = SQLiteRepository(config.sqlite_path)
    chat_service = ChatService(config, cleaning_service, openai_service, vector_store_service, sqlite_repository)
    handler = create_app_handler(chat_service, auth_service, config)
    return config, handler


def run():
    config, handler = create_app()
    server = ThreadingHTTPServer((config.host, config.port), handler)
    print(f"Customer support MVP is running on http://{config.host}:{config.port}")
    server.serve_forever()
