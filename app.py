from flask import Flask, render_template, request, jsonify, session
from datetime import datetime
import sqlite3
import hashlib
import os

app = Flask(__name__)
app.secret_key = 'sua_chave_secreta_mude_para_algo_seguro_123'

# ========== FUNÇÕES DO BANCO DE DADOS ==========
def get_db():
    conn = sqlite3.connect('banco_de_dados.db')
    conn.row_factory = sqlite3.Row
    return conn

def criar_tabelas():
    conn = get_db()
    cursor = conn.cursor()
    
    # Tabela de usuários
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        senha TEXT NOT NULL,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Tabela de salas
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS salas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        capacidade INTEGER,
        localizacao TEXT
    )
    """)
    
    # Inserir algumas salas padrão
    cursor.execute("SELECT COUNT(*) FROM salas")
    if cursor.fetchone()[0] == 0:
        salas_padrao = [
            ('Sala de Reuniões A', 10, '2º andar'),
            ('Sala de Reuniões B', 6, '1º andar'),
            ('Sala de Conferências', 20, 'Térreo'),
            ('Meet Virtual', 50, 'Online')
        ]
        cursor.executemany("INSERT INTO salas (nome, capacidade, localizacao) VALUES (?, ?, ?)", salas_padrao)
    
    # Tabela de reuniões
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS reunioes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        titulo TEXT NOT NULL,
        descricao TEXT,
        data DATE NOT NULL,
        horario_inicio TIME NOT NULL,
        horario_fim TIME NOT NULL,
        sala_id INTEGER,
        organizador_id INTEGER,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (sala_id) REFERENCES salas(id),
        FOREIGN KEY (organizador_id) REFERENCES usuarios(id)
    )
    """)
    
    # Tabela de participantes
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS participantes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        reuniao_id INTEGER NOT NULL,
        usuario_id INTEGER NOT NULL,
        FOREIGN KEY (reuniao_id) REFERENCES reunioes(id),
        FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
    )
    """)
    
    conn.commit()
    conn.close()

# Criar tabelas e inserir dados padrão
criar_tabelas()

# ========== ROTAS ==========
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/registrar', methods=['POST'])
def registrar():
    dados = request.json
    senha_hash = hashlib.sha256(dados['senha'].encode()).hexdigest()
    
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute("INSERT INTO usuarios (nome, email, senha) VALUES (?, ?, ?)", 
                      (dados['nome'], dados['email'], senha_hash))
        conn.commit()
        return jsonify({"sucesso": True, "mensagem": "Usuário registrado com sucesso!"})
    except sqlite3.IntegrityError:
        return jsonify({"sucesso": False, "mensagem": "Email já cadastrado!"})
    finally:
        conn.close()

@app.route('/login', methods=['POST'])
def login():
    dados = request.json
    senha_hash = hashlib.sha256(dados['senha'].encode()).hexdigest()
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM usuarios WHERE email = ? AND senha = ?", (dados['email'], senha_hash))
    usuario = cursor.fetchone()
    conn.close()
    
    if usuario:
        session['usuario_id'] = usuario['id']
        session['usuario_nome'] = usuario['nome']
        return jsonify({"sucesso": True, "mensagem": f"Bem-vindo, {usuario['nome']}!"})
    else:
        return jsonify({"sucesso": False, "mensagem": "Email ou senha incorretos!"})

@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({"sucesso": True, "mensagem": "Logout realizado!"})

@app.route('/salas', methods=['GET'])
def listar_salas():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, nome, capacidade, localizacao FROM salas")
    salas = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(salas)

@app.route('/agendar', methods=['POST'])
def agendar():
    if 'usuario_id' not in session:
        return jsonify({"sucesso": False, "mensagem": "Faça login primeiro!"})
    
    dados = request.json
    
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO reunioes (titulo, descricao, data, horario_inicio, horario_fim, sala_id, organizador_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            dados['titulo'],
            dados.get('descricao', ''),
            dados['data'],
            dados['horario_inicio'],
            dados['horario_fim'],
            dados.get('sala_id'),
            session['usuario_id']
        ))
        
        reuniao_id = cursor.lastrowid
        
        # Adicionar organizador como participante
        cursor.execute("INSERT INTO participantes (reuniao_id, usuario_id) VALUES (?, ?)", 
                      (reuniao_id, session['usuario_id']))
        
        conn.commit()
        
        return jsonify({"sucesso": True, "mensagem": f"Reunião '{dados['titulo']}' agendada! ID: {reuniao_id}"})
    except Exception as e:
        return jsonify({"sucesso": False, "mensagem": f"Erro: {str(e)}"})
    finally:
        conn.close()

@app.route('/listar', methods=['GET'])
def listar():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT r.*, s.nome as sala_nome, u.nome as organizador_nome
        FROM reunioes r
        LEFT JOIN salas s ON r.sala_id = s.id
        LEFT JOIN usuarios u ON r.organizador_id = u.id
        ORDER BY r.data, r.horario_inicio
    """)
    
    reunioes = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return jsonify(reunioes)

@app.route('/buscar/<int:id>', methods=['GET'])
def buscar(id):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT r.*, s.nome as sala_nome, s.id as sala_id
        FROM reunioes r
        LEFT JOIN salas s ON r.sala_id = s.id
        WHERE r.id = ?
    """, (id,))
    
    reuniao = cursor.fetchone()
    conn.close()
    
    if reuniao:
        return jsonify({"sucesso": True, "reuniao": dict(reuniao)})
    return jsonify({"sucesso": False, "mensagem": "Reunião não encontrada!"})

@app.route('/mudar/<int:id>', methods=['PUT'])
def mudar(id):
    if 'usuario_id' not in session:
        return jsonify({"sucesso": False, "mensagem": "Faça login primeiro!"})
    
    dados = request.json
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE reunioes 
        SET titulo = ?, descricao = ?, data = ?, horario_inicio = ?, horario_fim = ?, sala_id = ?
        WHERE id = ? AND organizador_id = ?
    """, (
        dados['titulo'],
        dados.get('descricao', ''),
        dados['data'],
        dados['horario_inicio'],
        dados['horario_fim'],
        dados.get('sala_id'),
        id,
        session['usuario_id']
    ))
    
    conn.commit()
    conn.close()
    
    return jsonify({"sucesso": True, "mensagem": f"Reunião {id} atualizada!"})

@app.route('/cancelar/<int:id>', methods=['DELETE'])
def cancelar(id):
    if 'usuario_id' not in session:
        return jsonify({"sucesso": False, "mensagem": "Faça login primeiro!"})
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM participantes WHERE reuniao_id = ?", (id,))
    cursor.execute("DELETE FROM reunioes WHERE id = ? AND organizador_id = ?", (id, session['usuario_id']))
    
    conn.commit()
    conn.close()
    
    return jsonify({"sucesso": True, "mensagem": f"Reunião {id} cancelada!"})

@app.route('/exportar_json', methods=['GET'])
def exportar_json():
    conn = get_db()
    cursor = conn.cursor()
    
    # Buscar todas as reuniões com detalhes
    cursor.execute("""
        SELECT 
            r.id,
            r.titulo,
            r.descricao,
            r.data,
            r.horario_inicio,
            r.horario_fim,
            r.criado_em,
            s.nome as sala_nome,
            s.capacidade as sala_capacidade,
            s.localizacao as sala_localizacao,
            u.nome as organizador_nome,
            u.email as organizador_email
        FROM reunioes r
        LEFT JOIN salas s ON r.sala_id = s.id
        LEFT JOIN usuarios u ON r.organizador_id = u.id
        ORDER BY r.data, r.horario_inicio
    """)
    
    reunioes = [dict(row) for row in cursor.fetchall()]
    
    # Buscar todos os usuários
    cursor.execute("SELECT id, nome, email, criado_em FROM usuarios")
    usuarios = [dict(row) for row in cursor.fetchall()]
    
    # Buscar todas as salas
    cursor.execute("SELECT id, nome, capacidade, localizacao FROM salas")
    salas = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    # Montar o JSON completo
    dados_completos = {
        "data_exportacao": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "total_reunioes": len(reunioes),
        "total_usuarios": len(usuarios),
        "total_salas": len(salas),
        "usuarios": usuarios,
        "salas": salas,
        "reunioes": reunioes
    }
    
    return jsonify(dados_completos)

if __name__ == "__main__":
    app.run(debug=True)