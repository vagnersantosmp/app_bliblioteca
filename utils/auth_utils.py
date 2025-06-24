# utils/auth_utils.py
from flask import request, jsonify, current_app
import jwt
from functools import wraps # Importa wraps para manter metadados da função original

def token_required(f):
    @wraps(f) # Adicionado @wraps para preservar metadados da função original
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            token = request.headers['Authorization'].split(" ")[1]

        if not token:
            return jsonify({"status": "erro", "mensagem": "Token de autenticação ausente!"}), 401

        try:
            # Tenta decodificar o token usando a SECRET_KEY do app Flask
            data = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user_id = data['user_id']
        except jwt.ExpiredSignatureError:
            return jsonify({"status": "erro", "mensagem": "Token de autenticação expirado!"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"status": "erro", "mensagem": "Token de autenticação inválido!"}), 401

        return f(current_user_id, *args, **kwargs)
    return decorated