# config.py
import os

class Config:
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_NAME = os.getenv("DB_NAME", "catalogo_livros")
    SECRET_KEY = os.getenv("SECRET_KEY", "uma_chave_secreta_padrao_para_desenvolvimento")
    TOKEN_EXPIRATION_HOURS = int(os.getenv("TOKEN_EXPIRATION_HOURS", 24))
    GOOGLE_BOOKS_API_URL = "https://www.googleapis.com/books/v1/volumes"