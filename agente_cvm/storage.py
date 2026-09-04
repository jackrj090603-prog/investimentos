import sqlite3
import os
from config import DB_PATH

def get_connection():
    """Retorna uma conexão aberta com o banco SQLite."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Inicializa as tabelas do banco de dados se não existirem."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Tabela de documentos CVM processados
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS documentos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cvm_code TEXT,
        company_name TEXT,
        ticker TEXT,
        category TEXT,
        doc_type TEXT,
        description TEXT,
        ref_date TEXT,
        delivery_date TEXT,
        link TEXT UNIQUE,
        resumo_ia TEXT,
        data_processamento TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Tabela de estado global (como carimbo de última busca CVM)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS estado (
        chave TEXT PRIMARY KEY,
        valor TEXT
    )
    """)
    
    # Tabela de conversas de chat (histórico)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS conversas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id TEXT,
        role TEXT,
        message TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    conn.commit()
    conn.close()

def doc_existe(link):
    """Verifica se um documento com o link fornecido já existe no banco (dedup)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM documentos WHERE link = ?", (link,))
    exists = cursor.fetchone() is not None
    conn.close()
    return exists

def salvar_documento(doc):
    """Salva um documento CVM no banco de dados."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
        INSERT INTO documentos (
            cvm_code, company_name, ticker, category, doc_type, description, ref_date, delivery_date, link, resumo_ia
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            doc.get("cvm_code"),
            doc.get("company_name"),
            doc.get("ticker"),
            doc.get("category"),
            doc.get("doc_type"),
            doc.get("description"),
            doc.get("ref_date"),
            doc.get("delivery_date"),
            doc.get("link"),
            doc.get("resumo_ia", "")
        ))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        # Documento duplicado pelo link
        return False
    finally:
        conn.close()

def atualizar_resumo(link, resumo_ia):
    """Atualiza o resumo gerado por IA para um documento."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE documentos SET resumo_ia = ? WHERE link = ?", (resumo_ia, link))
    conn.commit()
    conn.close()

def get_ultimo_timestamp():
    """Retorna o timestamp da última busca realizada com sucesso."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT valor FROM estado WHERE chave = 'ultima_busca'")
    row = cursor.fetchone()
    conn.close()
    return row["valor"] if row else None

def set_ultimo_timestamp(ts_str):
    """Salva o timestamp da última busca realizada com sucesso."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO estado (chave, valor) VALUES ('ultima_busca', ?)", (ts_str,))
    conn.commit()
    conn.close()

def salvar_mensagem(chat_id, role, message):
    """Salva uma mensagem do chat no histórico do banco de dados."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO conversas (chat_id, role, message) VALUES (?, ?, ?)", (str(chat_id), role, message))
    conn.commit()
    conn.close()

def get_historico_chat(chat_id, limit=15):
    """Retorna o histórico recente de conversas para um determinado chat."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT role, message FROM conversas 
    WHERE chat_id = ? 
    ORDER BY id DESC LIMIT ?
    """, (str(chat_id), limit))
    rows = cursor.fetchall()
    conn.close()
    
    # Inverter para obter ordem cronológica
    messages = [{"role": row["role"], "message": row["message"]} for row in reversed(rows)]
    return messages

def get_todos_documentos(limit=100):
    """Retorna a lista de todos os documentos cadastrados no banco."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM documentos ORDER BY id DESC LIMIT ?", (limit,))
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows

def buscar_documentos_por_termo(query, limit=100):
    """Busca documentos no banco de dados que casam com o termo da busca."""
    conn = get_connection()
    cursor = conn.cursor()
    search = f"%{query}%"
    cursor.execute("""
        SELECT * FROM documentos 
        WHERE ticker LIKE ? OR company_name LIKE ? OR category LIKE ? OR description LIKE ? OR resumo_ia LIKE ?
        ORDER BY id DESC LIMIT ?
    """, (search, search, search, search, search, limit))
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows

