# utils/db_utils.py
import mysql.connector
from flask import jsonify # Usamos jsonify aqui para retornar erros formatados
from config import Config # Importa as configurações

def get_db_connection():
    """Cria e retorna uma conexão com o banco de dados MySQL."""
    try:
        conn = mysql.connector.connect(
            host=Config.DB_HOST,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME
        )
        return conn
    except mysql.connector.Error as err:
        print(f"Erro ao conectar ao MySQL: {err}")
        # Não retorna jsonify aqui, pois isso é uma função utilitária
        return None