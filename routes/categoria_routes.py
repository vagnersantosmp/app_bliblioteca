# routes/categoria_routes.py
from flask import Blueprint, request, jsonify
import mysql.connector

# Importa as funções utilitárias e o decorador de autenticação
from utils.db_utils import get_db_connection
from utils.auth_utils import token_required

categoria_bp = Blueprint('categoria_bp', __name__)

@categoria_bp.route('/categorias', methods=['POST'])
@token_required
def create_categoria(current_user_id):
    data = request.get_json()
    if not data or 'nome' not in data or not data['nome']:
        return jsonify({"status": "erro", "mensagem": "Nome da categoria é obrigatório."}), 400

    nome = data['nome']
    descricao = data.get('descricao')

    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            sql = "INSERT INTO categorias (nome, descricao, id_usuario) VALUES (%s, %s, %s)"
            cursor.execute(sql, (nome, descricao, current_user_id))
            conn.commit()
            categoria_id = cursor.lastrowid
            return jsonify({"status": "sucesso", "mensagem": "Categoria criada com sucesso.", "categoria": {"id": categoria_id, "nome": nome, "descricao": descricao}}), 201
        except mysql.connector.Error as err:
            conn.rollback()
            print(f"Erro ao criar categoria: {err}")
            if "Duplicate entry" in str(err) and "nome" in str(err).lower():
                cursor.execute("SELECT id FROM categorias WHERE nome = %s AND id_usuario = %s", (nome, current_user_id))
                if cursor.fetchone():
                    return jsonify({"status": "erro", "mensagem": f"Categoria com o nome '{nome}' já existe para este usuário."}), 409
                else:
                    return jsonify({"status": "erro", "mensagem": f"Erro interno: Duplicidade de entrada genérica. {err}"}), 500
            return jsonify({"status": "erro", "mensagem": f"Erro interno ao criar categoria: {err}"}), 500
        finally:
            cursor.close()
            conn.close()
    else:
        return jsonify({"status": "erro", "mensagem": "Falha ao conectar ao banco de dados para criar categoria."}), 500

@categoria_bp.route('/categorias', methods=['GET'])
@token_required
def get_all_categorias(current_user_id):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        try:
            sql = "SELECT id, nome, descricao FROM categorias WHERE id_usuario = %s"
            cursor.execute(sql, (current_user_id,))
            categorias = cursor.fetchall()
            return jsonify({"status": "sucesso", "total": len(categorias), "categorias": categorias})
        except mysql.connector.Error as err:
            print(f"Erro ao buscar categorias: {err}")
            return jsonify({"status": "erro", "mensagem": f"Erro ao buscar categorias: {err}"}), 500
        finally:
            cursor.close()
            conn.close()
    else:
        return jsonify({"status": "erro", "mensagem": "Falha ao conectar ao banco de dados para buscar categorias."}), 500

@categoria_bp.route('/categorias/<int:categoria_id>', methods=['PUT'])
@token_required
def update_categoria(current_user_id, categoria_id):
    data = request.get_json()
    if not data:
        return jsonify({"status": "erro", "mensagem": "Nenhum dado fornecido para atualização."}), 400

    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            set_clauses = []
            values = []

            if 'nome' in data and data['nome']:
                set_clauses.append("nome = %s")
                values.append(data['nome'])
            if 'descricao' in data:
                set_clauses.append("descricao = %s")
                values.append(data['descricao'])

            if not set_clauses:
                return jsonify({"status": "erro", "mensagem": "Nenhum campo válido (nome ou descricao) fornecido para atualização."}), 400

            sql = f"UPDATE categorias SET {', '.join(set_clauses)} WHERE id = %s AND id_usuario = %s"
            values.append(categoria_id)
            values.append(current_user_id)

            cursor.execute(sql, tuple(values))
            conn.commit()

            if cursor.rowcount == 0:
                return jsonify({"status": "erro", "mensagem": "Categoria não encontrada ou você não tem permissão para atualizá-la."}), 404
            else:
                return jsonify({"status": "sucesso", "mensagem": f"Categoria com ID {categoria_id} atualizada com sucesso."}), 200
        except mysql.connector.Error as err:
            conn.rollback()
            print(f"Erro ao atualizar categoria: {err}")
            if "Duplicate entry" in str(err) and "nome" in str(err).lower():
                cursor.execute("SELECT id FROM categorias WHERE nome = %s AND id_usuario = %s", (data.get('nome'), current_user_id))
                if cursor.fetchone():
                    return jsonify({"status": "erro", "mensagem": f"Categoria com o nome '{data.get('nome')}' já existe para este usuário."}), 409
                else:
                    return jsonify({"status": "erro", "mensagem": f"Erro interno: Duplicidade de entrada genérica. {err}"}), 500
            return jsonify({"status": "erro", "mensagem": f"Erro interno ao atualizar categoria: {err}"}), 500
        finally:
            cursor.close()
            conn.close()
    else:
        return jsonify({"status": "erro", "mensagem": "Falha ao conectar ao banco de dados para atualizar categoria."}), 500

@categoria_bp.route('/categorias/<int:categoria_id>', methods=['DELETE'])
@token_required
def delete_categoria(current_user_id, categoria_id):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            sql = "DELETE FROM categorias WHERE id = %s AND id_usuario = %s"
            cursor.execute(sql, (categoria_id, current_user_id))
            conn.commit()

            if cursor.rowcount == 0:
                return jsonify({"status": "erro", "mensagem": "Categoria não encontrada ou você não tem permissão para excluí-la."}), 404
            else:
                return jsonify({"status": "sucesso", "mensagem": f"Categoria com ID {categoria_id} excluída com sucesso."}), 200
        except mysql.connector.Error as err:
            conn.rollback()
            print(f"Erro ao excluir categoria: {err}")
            return jsonify({"status": "erro", "mensagem": f"Erro interno ao excluir categoria: {err}"}), 500
        finally:
            cursor.close()
            conn.close()
    else:
        return jsonify({"status": "erro", "mensagem": "Falha ao conectar ao banco de dados para excluir categoria."}), 500