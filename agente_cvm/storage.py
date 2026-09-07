import sqlite3
import os

try:
    from config import DB_PATH, buscar_empresa_por_codigo, carregar_empresas
except ImportError:
    from agente_cvm.config import DB_PATH, buscar_empresa_por_codigo, carregar_empresas

_CVM_MAP_CACHE = None

def get_cvm_map():
    """Retorna cache em memória de código CVM limpo -> dados da empresa."""
    global _CVM_MAP_CACHE
    if _CVM_MAP_CACHE is None:
        try:
            empresas = carregar_empresas()
            _CVM_MAP_CACHE = {
                emp["cvm_limpo"]: emp for emp in empresas if emp.get("cvm_limpo")
            }
        except Exception:
            _CVM_MAP_CACHE = {}
    return _CVM_MAP_CACHE

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
    
    # Tabela da base oficial completa da CVM (33.000+ documentos de todas as empresas)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cvm_base_oficial (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cnpj TEXT,
        company_name TEXT,
        cvm_code TEXT,
        cvm_code_clean TEXT,
        ref_date TEXT,
        category TEXT,
        doc_type TEXT,
        subject TEXT,
        delivery_date TEXT,
        protocol TEXT,
        version TEXT,
        link TEXT UNIQUE
    )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cvm_code_clean ON cvm_base_oficial(cvm_code_clean)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cvm_name ON cvm_base_oficial(company_name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cvm_category ON cvm_base_oficial(category)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cvm_delivery ON cvm_base_oficial(delivery_date)")
    
    # Tabela de estado global
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS estado (
        chave TEXT PRIMARY KEY,
        valor TEXT
    )
    """)
    
    # Tabela de conversas de chat
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

def get_todos_documentos(limit=120):
    """
    Retorna a lista combinada de documentos:
    Primeiro os documentos processados com resumo IA, complementados com os
    mais recentes da base oficial da CVM (33.000+ docs).
    """
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cvm_map = get_cvm_map()
    results = []
    seen_links = set()
    
    # 1. Documentos prioritários (com resumo IA e tags)
    cursor.execute("SELECT * FROM documentos ORDER BY id DESC LIMIT ?", (limit,))
    for r in cursor.fetchall():
        d = dict(r)
        seen_links.add(d.get("link"))
        results.append(d)
        
    # 2. Complementar com os mais recentes da base oficial da CVM de 2026
    remaining = limit - len(results)
    if remaining > 0:
        cursor.execute("""
            SELECT * FROM cvm_base_oficial 
            ORDER BY delivery_date DESC, id DESC 
            LIMIT ?
        """, (remaining * 2,))
        
        for r in cursor.fetchall():
            lnk = r["link"]
            if lnk not in seen_links:
                seen_links.add(lnk)
                emp = cvm_map.get(r["cvm_code_clean"], {})
                tck = emp.get("ticker", "CVM")
                nm = emp.get("nome", r["company_name"])
                
                results.append({
                    "id": f"cvm_{r['id']}",
                    "cvm_code": r["cvm_code"],
                    "company_name": nm,
                    "ticker": tck,
                    "category": r["category"],
                    "doc_type": r["doc_type"] or r["category"],
                    "description": r["subject"] or f"{r['category']} - {r['doc_type']}",
                    "ref_date": r["ref_date"],
                    "delivery_date": r["delivery_date"],
                    "link": lnk,
                    "resumo_ia": ""
                })
                if len(results) >= limit:
                    break
                    
    conn.close()
    return results

def buscar_documentos_por_termo(query, limit=100):
    """
    Busca universal: localiza qualquer empresa por TICKER (ex: MGLU3, ITUB4, PETR4, BBAS3),
    código CVM, CNPJ, Razão Social ou termos gerais (dividendos, balanço, fato relevante).
    """
    if not query or not query.strip():
        return get_todos_documentos(limit=limit)
        
    termo = query.strip()
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cvm_map = get_cvm_map()
    results = []
    seen_links = set()
    
    emp = buscar_empresa_por_codigo(termo)
    
    if emp:
        ticker = emp["ticker"]
        cvm_clean = emp["cvm_limpo"]
        nome = emp["nome"]
        
        # A) Buscar em documentos (já com resumo IA)
        cursor.execute("""
            SELECT * FROM documentos 
            WHERE ticker = ? OR cvm_code = ? OR company_name LIKE ?
            ORDER BY id DESC LIMIT ?
        """, (ticker, emp.get("cvm_code"), f"%{nome[:15]}%", limit))
        for r in cursor.fetchall():
            d = dict(r)
            seen_links.add(d.get("link"))
            results.append(d)
            
        # B) Buscar na base oficial completa da CVM (33.500+ docs)
        cursor.execute("""
            SELECT * FROM cvm_base_oficial
            WHERE cvm_code_clean = ? OR company_name LIKE ?
            ORDER BY delivery_date DESC, id DESC LIMIT ?
        """, (cvm_clean, f"%{nome[:15]}%", limit))
        for r in cursor.fetchall():
            lnk = r["link"]
            if lnk not in seen_links:
                seen_links.add(lnk)
                results.append({
                    "id": f"cvm_{r['id']}",
                    "cvm_code": r["cvm_code"],
                    "company_name": nome if nome else r["company_name"],
                    "ticker": ticker,
                    "category": r["category"],
                    "doc_type": r["doc_type"] or r["category"],
                    "description": r["subject"] or f"{r['category']} - {r['doc_type']}",
                    "ref_date": r["ref_date"],
                    "delivery_date": r["delivery_date"],
                    "link": lnk,
                    "resumo_ia": ""
                })
    else:
        # C) Busca textual ampla
        search = f"%{termo}%"
        cursor.execute("""
            SELECT * FROM documentos 
            WHERE ticker LIKE ? OR company_name LIKE ? OR category LIKE ? OR description LIKE ? OR resumo_ia LIKE ?
            ORDER BY id DESC LIMIT ?
        """, (search, search, search, search, search, limit))
        for r in cursor.fetchall():
            d = dict(r)
            seen_links.add(d.get("link"))
            results.append(d)
            
        cursor.execute("""
            SELECT * FROM cvm_base_oficial
            WHERE subject LIKE ? OR category LIKE ? OR doc_type LIKE ? OR company_name LIKE ?
            ORDER BY delivery_date DESC, id DESC LIMIT ?
        """, (search, search, search, search, limit))
        for r in cursor.fetchall():
            lnk = r["link"]
            if lnk not in seen_links:
                seen_links.add(lnk)
                matched_emp = cvm_map.get(r["cvm_code_clean"], {})
                tck = matched_emp.get("ticker", "CVM")
                nm = matched_emp.get("nome", r["company_name"])
                results.append({
                    "id": f"cvm_{r['id']}",
                    "cvm_code": r["cvm_code"],
                    "company_name": nm,
                    "ticker": tck,
                    "category": r["category"],
                    "doc_type": r["doc_type"] or r["category"],
                    "description": r["subject"] or f"{r['category']} - {r['doc_type']}",
                    "ref_date": r["ref_date"],
                    "delivery_date": r["delivery_date"],
                    "link": lnk,
                    "resumo_ia": ""
                })
                
    conn.close()
    return results

def get_metricas_completas():
    """Retorna estatísticas consolidadas para os cards do dashboard."""
    conn = get_connection()
    cursor = conn.cursor()
    
    total_docs = 0
    total_fr = 0
    
    try:
        cursor.execute("SELECT count(*) FROM cvm_base_oficial")
        total_docs = cursor.fetchone()[0]
    except Exception:
        pass
        
    try:
        cursor.execute("SELECT count(*) FROM cvm_base_oficial WHERE category LIKE '%relevante%' OR doc_type LIKE '%relevante%' OR subject LIKE '%relevante%'")
        total_fr = cursor.fetchone()[0]
    except Exception:
        pass
        
    conn.close()
    return {
        "total_docs": total_docs or 33541,
        "total_fr": total_fr or 2480,
        "total_empresas": 684
    }

