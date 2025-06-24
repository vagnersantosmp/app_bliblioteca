# routes/livro_routes.py
from flask import Blueprint, request, jsonify, current_app
import mysql.connector
import requests
from datetime import datetime

# Importa as funções utilitárias e o decorador de autenticação
from utils.db_utils import get_db_connection
from utils.auth_utils import token_required
from config import Config # Para acessar GOOGLE_BOOKS_API_URL

livro_bp = Blueprint('livro_bp', __name__)

# --- Buscar dados do livro por ISBN na Google Books API (NÃO PROTEGIDA) ---
@livro_bp.route('/livros/buscar-isbn', methods=['GET'])
def buscar_livro_por_isbn():
    isbn = request.args.get('isbn')

    if not isbn:
        return jsonify({"status": "erro", "mensagem": "ISBN é obrigatório para a busca."}), 400

    try:
        search_url = f"{Config.GOOGLE_BOOKS_API_URL}?q=isbn:{isbn}"
        response = requests.get(search_url)
        response.raise_for_status()
        google_data = response.json()

        if google_data and 'items' in google_data and len(google_data['items']) > 0:
            volume_info = google_data['items'][0]['volumeInfo']
            
            book_data_preview = {
                'isbn': isbn,
                'titulo': volume_info.get('title', 'Título Desconhecido'),
                'autores': ", ".join(volume_info.get('authors', ['Autor Desconhecido'])) if volume_info.get('authors') else 'Autor Desconhecido',
                'genero': volume_info.get('categories', ['Gênero Desconhecido'])[0] if volume_info.get('categories') else 'Gênero Desconhecido',
                'editora': volume_info.get('publisher', 'Editora Desconhecida'),
                'ano_publicacao': int(volume_info.get('publishedDate', '0000')[:4]) if volume_info.get('publishedDate') and volume_info.get('publishedDate')[:4].isdigit() else None,
                'numero_paginas': volume_info.get('pageCount', None),
                'capa_url': volume_info['imageLinks']['thumbnail'] if 'imageLinks' in volume_info and 'thumbnail' in volume_info['imageLinks'] else None,
                'idioma': volume_info.get('language', 'pt')[:2] if volume_info.get('language') else 'pt',
                'localizacao_fisica': None,
                'notas_pessoais': None,
                'data_inicio_leitura': None,
                'data_fim_leitura': None,
                'id_usuario': None # Não podemos definir aqui, pois a busca é pública
            }
            return jsonify({"status": "sucesso", "mensagem": "Dados do livro encontrados.", "livro": book_data_preview})
        else:
            return jsonify({
                "status": "sucesso",
                "mensagem": f"Livro com ISBN {isbn} não encontrado na Google Books API. Por favor, insira os dados manualmente.",
                "livro": {'isbn': isbn, 'titulo': 'Título Desconhecido', 'autores': 'Autor Desconhecido', 'genero': None, 'editora': None, 'ano_publicacao': None, 'numero_paginas': None, 'capa_url': None, 'idioma': 'pt', 'localizacao_fisica': None, 'notas_pessoais': None, 'data_inicio_leitura': None, 'data_fim_leitura': None, 'id_usuario': None}
            })
    except requests.exceptions.RequestException as e:
        print(f"Erro na requisição à Google Books API: {e}")
        return jsonify({"status": "erro", "mensagem": f"Erro ao comunicar com a API do Google Books: {e}"}), 500

# --- Salvar Livro no Banco de Dados (PROTEGIDA) ---
@livro_bp.route('/livros', methods=['POST'])
@token_required # Aplica o decorador de proteção
def adicionar_livro(current_user_id): # Recebe o ID do usuário logado
    data = request.get_json()

    required_fields = ['isbn', 'titulo', 'autores']
    for field in required_fields:
        if field not in data or not data[field]:
            return jsonify({"status": "erro", "mensagem": f"Campo '{field}' é obrigatório."}), 400

    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            sql = """
            INSERT INTO livros (
                isbn, titulo, autores, genero, editora, ano_publicacao,
                numero_paginas, capa_url, localizacao_fisica, notas_pessoais,
                idioma, data_inicio_leitura, data_fim_leitura, data_cadastro, id_usuario
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), %s)
            """
            values = (
                data.get('isbn'),
                data.get('titulo'),
                data.get('autores'),
                data.get('genero', None), # Garante que seja None se não vier
                data.get('editora', None), # Garante que seja None se não vier
                data.get('ano_publicacao', None), # Garante que seja None se não vier
                data.get('numero_paginas', None), # Garante que seja None se não vier
                data.get('capa_url', None), # Garante que seja None se não vier
                data.get('localizacao_fisica', None), # Garante que seja None se não vier
                data.get('notas_pessoais', None), # Garante que seja None se não vier
                data.get('idioma', None), # Garante que seja None se não vier
                data.get('data_inicio_leitura', None), # Garante que seja None se não vier
                data.get('data_fim_leitura', None), # Garante que seja None se não vier
                current_user_id # Usa o ID do usuário logado
            )
            cursor.execute(sql, values)
            conn.commit()

            book_id = cursor.lastrowid
            return jsonify({
                "status": "sucesso",
                "mensagem": f"Livro com ISBN {data.get('isbn')} adicionado com sucesso.",
                "livro_cadastrado": {**data, "id": book_id}
            }), 201
        except mysql.connector.Error as err:
            conn.rollback()
            print(f"Erro ao inserir livro no DB: {err}")
            if "Duplicate entry" in str(err) and "isbn" in str(err).lower():
                 return jsonify({"status": "erro", "mensagem": f"Livro com ISBN {isbn} já existe no catálogo."}), 409
            
            # Tratamento específico para o erro 1048 (NOT NULL)
            if err.errno == 1048: # Código de erro MySQL para "Column cannot be null"
                # Exemplo de mensagem de erro do MySQL: "Column 'genero' cannot be null"
                # Usamos split("'")[1] para extrair o nome da coluna ('genero')
                return jsonify({
                    "status": "erro", 
                    "mensagem": f"Erro: O campo '{err.msg.split("'")[1]}' não pode ser nulo. Por favor, forneça um valor."
                }), 400
            
            return jsonify({"status": "erro", "mensagem": f"Erro interno ao adicionar livro: {err}"}), 500
        finally:
            cursor.close()
            conn.close()
    else:
        return jsonify({"status": "erro", "mensagem": "Falha ao processar dados do livro ou conectar ao banco de dados."}), 500

# --- ROTAS DE LIVROS (PROTEGIDAS E FILTRADAS POR USUÁRIO) ---

@livro_bp.route('/livros', methods=['GET'])
@token_required # Protege a rota
def get_all_livros(current_user_id): # Recebe o ID do usuário logado
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        try:
            categoria_id = request.args.get('categoria_id', type=int)
            termo_busca = request.args.get('busca') # Para título/autor
            genero = request.args.get('genero')
            editora = request.args.get('editora')
            idioma = request.args.get('idioma')

            ordenar_por = request.args.get('ordenar_por', 'titulo')
            ordem = request.args.get('ordem', 'ASC').upper()

            sql = "SELECT DISTINCT l.* FROM livros l"
            values = []
            where_clauses = ["l.id_usuario = %s"] # **FILTRO POR USUÁRIO SEMPRE**
            values.append(current_user_id) # Adiciona o ID do usuário logado aos valores

            if categoria_id is not None:
                sql += " JOIN livro_categoria lc ON l.id = lc.id_livro"
                where_clauses.append("lc.id_categoria = %s")
                values.append(categoria_id)

            if termo_busca:
                where_clauses.append("(l.titulo LIKE %s OR l.autores LIKE %s)")
                values.append(f"%{termo_busca}%")
                values.append(f"%{termo_busca}%")
            
            if genero:
                where_clauses.append("l.genero = %s")
                values.append(genero)
            if editora:
                where_clauses.append("l.editora = %s")
                values.append(editora)
            if idioma:
                where_clauses.append("l.idioma = %s")
                values.append(idioma)

            if where_clauses:
                sql += " WHERE " + " AND ".join(where_clauses)
            
            valid_order_fields = ['titulo', 'autores', 'ano_publicacao', 'data_cadastro', 'id']
            if ordenar_por not in valid_order_fields:
                ordenar_por = 'titulo'

            if ordem not in ['ASC', 'DESC']:
                ordem = 'ASC'

            sql += f" ORDER BY {ordenar_por} {ordem}"

            cursor.execute(sql, tuple(values))
            livros = cursor.fetchall()

            for livro in livros:
                for key in ['data_inicio_leitura', 'data_fim_leitura', 'data_cadastro']:
                    if isinstance(livro.get(key), (type(None),)):
                        livro[key] = None
                    else:
                        livro[key] = str(livro[key])

            return jsonify({"status": "sucesso", "total": len(livros), "livros": livros})
        except mysql.connector.Error as err:
            print(f"Erro ao buscar livros: {err}")
            return jsonify({"status": "erro", "mensagem": f"Erro ao buscar livros: {err}"}), 500
        finally:
            cursor.close()
            conn.close()
    else:
        return jsonify({"status": "erro", "mensagem": "Falha ao conectar ao banco de dados para buscar livros."}), 500


@livro_bp.route('/livros/<int:livro_id>', methods=['GET'])
@token_required # Protege a rota
def get_livro_by_id(current_user_id, livro_id): # Recebe o ID do usuário
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        try:
            # Filtra por ID do livro E ID do usuário para garantir que o usuário só veja seus próprios livros
            sql = "SELECT * FROM livros WHERE id = %s AND id_usuario = %s"
            cursor.execute(sql, (livro_id, current_user_id))
            livro = cursor.fetchone()

            if livro:
                for key in ['data_inicio_leitura', 'data_fim_leitura', 'data_cadastro']:
                    if isinstance(livro.get(key), (type(None),)):
                        livro[key] = None
                    else:
                        livro[key] = str(livro[key])
                return jsonify({"status": "sucesso", "livro": livro})
            else:
                return jsonify({"status": "erro", "mensagem": "Livro não encontrado ou você não tem permissão para acessá-lo."}), 404
        except mysql.connector.Error as err:
            print(f"Erro ao buscar livro por ID: {err}")
            return jsonify({"status": "erro", "mensagem": f"Erro ao buscar livro: {err}"}), 500
        finally:
            cursor.close()
            conn.close()
    else:
        return jsonify({"status": "erro", "mensagem": "Falha ao conectar ao banco de dados para buscar livro."}), 500

@livro_bp.route('/livros/<int:livro_id>', methods=['PUT'])
@token_required # Protege a rota
def update_livro(current_user_id, livro_id): # Recebe o ID do usuário
    data = request.get_json()

    if not data:
        return jsonify({"status": "erro", "mensagem": "Nenhum dado fornecido para atualização."}), 400

    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            set_clauses = []
            values = []
            
            updatable_fields = [
                'isbn', 'titulo', 'autores', 'genero', 'editora', 'ano_publicacao',
                'numero_paginas', 'capa_url', 'localizacao_fisica', 'notas_pessoais',
                'idioma', 'data_inicio_leitura', 'data_fim_leitura'
            ]

            for field in updatable_fields:
                if field in data:
                    set_clauses.append(f"{field} = %s")
                    values.append(data[field])
            
            if not set_clauses:
                return jsonify({"status": "erro", "mensagem": "Nenhum campo válido fornecido para atualização."}), 400

            # Garante que só o próprio usuário possa atualizar seus livros
            sql = f"UPDATE livros SET {', '.join(set_clauses)} WHERE id = %s AND id_usuario = %s"
            values.append(livro_id)
            values.append(current_user_id)

            cursor.execute(sql, tuple(values))
            conn.commit()

            if cursor.rowcount == 0:
                return jsonify({"status": "erro", "mensagem": "Livro não encontrado ou você não tem permissão para atualizá-lo."}), 404
            else:
                return jsonify({"status": "sucesso", "mensagem": f"Livro com ID {livro_id} atualizado com sucesso."}), 200

        except mysql.connector.Error as err:
            conn.rollback()
            print(f"Erro ao atualizar livro: {err}")
            if "Duplicate entry" in str(err) and "isbn" in str(err).lower():
                return jsonify({"status": "erro", "mensagem": f"ISBN '{data.get('isbn')}' já existe em outro livro."}), 409
            return jsonify({"status": "erro", "mensagem": f"Erro interno ao atualizar livro: {err}"}), 500
        finally:
            cursor.close()
            conn.close()
    else:
        return jsonify({"status": "erro", "mensagem": "Falha ao conectar ao banco de dados para atualizar livro."}), 500

@livro_bp.route('/livros/<int:livro_id>', methods=['DELETE'])
@token_required # Protege a rota
def delete_livro(current_user_id, livro_id): # Recebe o ID do usuário
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            # Garante que só o próprio usuário possa excluir seus livros
            sql = "DELETE FROM livros WHERE id = %s AND id_usuario = %s"
            cursor.execute(sql, (livro_id, current_user_id))
            conn.commit()

            if cursor.rowcount == 0:
                return jsonify({"status": "erro", "mensagem": "Livro não encontrado ou você não tem permissão para excluí-lo."}), 404
            else:
                return jsonify({"status": "sucesso", "mensagem": f"Livro com ID {livro_id} excluído com sucesso."}), 200
        except mysql.connector.Error as err:
            conn.rollback()
            print(f"Erro ao excluir livro: {err}")
            return jsonify({"status": "erro", "mensagem": f"Erro interno ao excluir livro: {err}"}), 500
        finally:
            cursor.close()
            conn.close()
    else:
        return jsonify({"status": "erro", "mensagem": "Falha ao conectar ao banco de dados para exclusão."}), 500

# --- ROTAS DE ASSOCIAÇÃO LIVRO-CATEGORIA (PROTEGIDAS) ---
@livro_bp.route('/livros/<int:livro_id>/categorias/<int:categoria_id>', methods=['POST'])
@token_required
def add_livro_to_categoria(current_user_id, livro_id, categoria_id):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT id FROM livros WHERE id = %s AND id_usuario = %s", (livro_id, current_user_id))
            livro_existe = cursor.fetchone()
            if not livro_existe:
                return jsonify({"status": "erro", "mensagem": "Livro não encontrado ou você não tem permissão para acessá-lo."}), 404

            cursor.execute("SELECT id FROM categorias WHERE id = %s AND id_usuario = %s", (categoria_id, current_user_id))
            categoria_existe = cursor.fetchone()
            if not categoria_existe:
                return jsonify({"status": "erro", "mensagem": "Categoria não encontrada ou você não tem permissão para acessá-la."}), 404

            sql = "INSERT INTO livro_categoria (id_livro, id_categoria) VALUES (%s, %s)"
            cursor.execute(sql, (livro_id, categoria_id))
            conn.commit()
            return jsonify({"status": "sucesso", "mensagem": f"Livro {livro_id} associado à categoria {categoria_id} com sucesso."}), 201
        except mysql.connector.Error as err:
            conn.rollback()
            print(f"Erro ao associar livro à categoria: {err}")
            if "Duplicate entry" in str(err) and "PRIMARY" in str(err):
                return jsonify({"status": "erro", "mensagem": "Livro já está associado a esta categoria."}), 409
            return jsonify({"status": "erro", "mensagem": f"Erro interno ao associar livro à categoria: {err}"}), 500
        finally:
            cursor.close()
            conn.close()
    else:
        return jsonify({"status": "erro", "mensagem": "Falha ao conectar ao banco de dados para associar livro à categoria."}), 500

@livro_bp.route('/livros/<int:livro_id>/categorias/<int:categoria_id>', methods=['DELETE'])
@token_required
def remove_livro_from_categoria(current_user_id, livro_id, categoria_id):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT id FROM livros WHERE id = %s AND id_usuario = %s", (livro_id, current_user_id))
            livro_existe = cursor.fetchone()
            if not livro_existe:
                return jsonify({"status": "erro", "mensagem": "Livro não encontrado ou você não tem permissão para acessá-lo."}), 404

            cursor.execute("SELECT id FROM categorias WHERE id = %s AND id_usuario = %s", (categoria_id, current_user_id))
            categoria_existe = cursor.fetchone()
            if not categoria_existe:
                return jsonify({"status": "erro", "mensagem": "Categoria não encontrada ou você não tem permissão para acessá-la."}), 404
            
            sql = "DELETE FROM livro_categoria WHERE id_livro = %s AND id_categoria = %s"
            cursor.execute(sql, (livro_id, categoria_id))
            conn.commit()

            if cursor.rowcount == 0:
                return jsonify({"status": "erro", "mensagem": "Associação de livro e categoria não encontrada."}), 404
            else:
                return jsonify({"status": "sucesso", "mensagem": f"Associação do Livro {livro_id} com a Categoria {categoria_id} removida com sucesso."}), 200
        except mysql.connector.Error as err:
            conn.rollback()
            print(f"Erro ao remover associação livro-categoria: {err}")
            return jsonify({"status": "erro", "mensagem": f"Erro interno ao remover associação: {err}"}), 500
        finally:
            cursor.close()
            conn.close()
    else:
        return jsonify({"status": "erro", "mensagem": "Falha ao conectar ao banco de dados para remover associação."}), 500