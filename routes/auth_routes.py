# routes/auth_routes.py
from flask import Blueprint, request, jsonify, current_app
import mysql.connector
import jwt
import uuid
from datetime import datetime, timedelta
from functools import wraps # Importa wraps para o decorador

# Importa as funções utilitárias e o decorador de autenticação
from utils.db_utils import get_db_connection
from utils.auth_utils import token_required # Não precisamos mais da importação Bcrypt aqui
from config import Config # Importa as configurações do seu config.py

auth_bp = Blueprint('auth_bp', __name__)

# NOTA: Bcrypt NÃO é inicializado aqui. Ele é inicializado em app.py
# e acessado via current_app.bcrypt.

@auth_bp.route('/registrar', methods=['POST'])
def registrar_usuario():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    email = data.get('email')

    if not username or not password:
        return jsonify({"status": "erro", "mensagem": "Nome de usuário e senha são obrigatórios."}), 400

    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT id FROM usuarios WHERE username = %s", (username,))
            if cursor.fetchone():
                return jsonify({"status": "erro", "mensagem": "Nome de usuário já existe."}), 409

            if email:
                cursor.execute("SELECT id FROM usuarios WHERE email = %s", (email,))
                if cursor.fetchone():
                    return jsonify({"status": "erro", "mensagem": "E-mail já está em uso."}), 409

            # Acessa o bcrypt que foi inicializado em app.py através de current_app
            hashed_password = current_app.bcrypt.generate_password_hash(password).decode('utf-8')
            user_id = str(uuid.uuid4())

            sql = "INSERT INTO usuarios (id, username, password_hash, email) VALUES (%s, %s, %s, %s)"
            cursor.execute(sql, (user_id, username, hashed_password, email))
            conn.commit()

            return jsonify({"status": "sucesso", "mensagem": "Usuário registrado com sucesso.", "user_id": user_id}), 201
        except mysql.connector.Error as err:
            conn.rollback()
            print(f"Erro ao registrar usuário: {err}")
            return jsonify({"status": "erro", "mensagem": f"Erro interno ao registrar usuário: {err}"}), 500
        finally:
            cursor.close()
            conn.close()
    else:
        return jsonify({"status": "erro", "mensagem": "Falha ao conectar ao banco de dados para registrar usuário."}), 500

@auth_bp.route('/login', methods=['POST'])
def login_usuario():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({"status": "erro", "mensagem": "Nome de usuário e senha são obrigatórios."}), 400

    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        try:
            sql = "SELECT id, username, password_hash FROM usuarios WHERE username = %s"
            cursor.execute(sql, (username,))
            user = cursor.fetchone()

            # Acessa o bcrypt que foi inicializado em app.py através de current_app
            if user and current_app.bcrypt.check_password_hash(user['password_hash'], password):
                token_payload = {
                    'user_id': user['id'],
                    # Acessa TOKEN_EXPIRATION_HOURS diretamente de Config
                    'exp': datetime.utcnow() + timedelta(hours=Config.TOKEN_EXPIRATION_HOURS)
                }
                token = jwt.encode(token_payload, current_app.config['SECRET_KEY'], algorithm="HS256")
                
                return jsonify({
                    "status": "sucesso",
                    "mensagem": "Login realizado com sucesso.",
                    "token": token,
                    "user_id": user['id']
                }), 200
            else:
                return jsonify({"status": "erro", "mensagem": "Nome de usuário ou senha inválidos."}), 401
        except mysql.connector.Error as err:
            print(f"Erro ao fazer login: {err}")
            return jsonify({"status": "erro", "mensagem": f"Erro interno ao fazer login: {err}"}), 500
        finally:
            cursor.close()
            conn.close()
    else:
        return jsonify({"status": "erro", "mensagem": "Falha ao conectar ao banco de dados para login."}), 500 