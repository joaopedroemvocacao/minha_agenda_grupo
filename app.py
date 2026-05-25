from flask import Flask, render_template, request, jsonify
from datetime import datetime
import sqlite3
import os

app = Flask(__name__)

# ========== FUNÇÕES DO BANCO DE DADOS ==========
def get_db():
    conn = sqlite3.connect('banco_de_dados.db')
    conn.row_factory = sqlite3.Row
    return conn

def criar_tabelas():
    conn = get_db()
    cursor = conn.cursor()
    
    # Tabela de reuniões (simplificada)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS reunioes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        titulo TEXT NOT NULL,
        descricao TEXT,
        data DATE NOT NULL,
        horario_inicio TIME NOT NULL,
        horario_fim TIME NOT NULL,
        local TEXT NOT NULL,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    conn.commit()
    conn.close()

# Criar tabelas
criar_tabelas()

# ========== ROTAS ==========
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/agendar', methods=['POST'])
def agendar():
    dados = request.json
    
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO reunioes (titulo, descricao, data, horario_inicio, horario_fim, local)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            dados['titulo'],
            dados.get('descricao', ''),
            dados['data'],
            dados['horario_inicio'],
            dados['horario_fim'],
            dados['local']
        ))
        
        reuniao_id = cursor.lastrowid
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
        SELECT * FROM reunioes
        ORDER BY data, horario_inicio
    """)
    
    reunioes = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return jsonify(reunioes)

@app.route('/buscar/<int:id>', methods=['GET'])
def buscar(id):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM reunioes WHERE id = ?", (id,))
    reuniao = cursor.fetchone()
    conn.close()
    
    if reuniao:
        return jsonify({"sucesso": True, "reuniao": dict(reuniao)})
    return jsonify({"sucesso": False, "mensagem": "Reunião não encontrada!"})

@app.route('/mudar/<int:id>', methods=['PUT'])
def mudar(id):
    dados = request.json
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE reunioes 
        SET titulo = ?, descricao = ?, data = ?, horario_inicio = ?, horario_fim = ?, local = ?
        WHERE id = ?
    """, (
        dados['titulo'],
        dados.get('descricao', ''),
        dados['data'],
        dados['horario_inicio'],
        dados['horario_fim'],
        dados['local'],
        id
    ))
    
    conn.commit()
    conn.close()
    
    return jsonify({"sucesso": True, "mensagem": f"Reunião {id} atualizada!"})

@app.route('/cancelar/<int:id>', methods=['DELETE'])
def cancelar(id):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM reunioes WHERE id = ?", (id,))
    
    conn.commit()
    conn.close()
    
    return jsonify({"sucesso": True, "mensagem": f"Reunião {id} cancelada!"})

@app.route('/exportar_json', methods=['GET'])
def exportar_json():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM reunioes ORDER BY data, horario_inicio")
    reunioes = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    dados_completos = {
        "data_exportacao": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "total_reunioes": len(reunioes),
        "reunioes": reunioes
    }
    
    return jsonify(dados_completos)

if __name__ == "__main__":
    app.run(debug=True)