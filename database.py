import json
import os
import sqlite3
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(BASE_DIR, "cotacao.db")

# Campos do cadastro de fornecedor, na ordem em que aparecem/exportam.
CAMPOS_FORNECEDOR = [
    "distribuidora", "representante", "telefone", "whatsapp",
    "email", "cnpj", "ativo", "observacoes",
]


def get_connection():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _colunas(cursor, tabela):
    cursor.execute(f"PRAGMA table_info({tabela})")
    return {row["name"] for row in cursor.fetchall()}


def init_db():
    """Cria as tabelas e aplica migrações leves em bancos antigos."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS fornecedores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                distribuidora TEXT UNIQUE NOT NULL,
                representante TEXT,
                telefone TEXT,
                whatsapp TEXT,
                email TEXT,
                cnpj TEXT,
                ativo INTEGER DEFAULT 1,
                observacoes TEXT
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS cotacoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                criada_em TEXT NOT NULL,
                descricao TEXT,
                itens_json TEXT NOT NULL,
                fornecedores_json TEXT
            )
        """)
        conn.commit()

        # --- Migração de bancos que ainda usavam "nome"/"vendedor" ---
        cols = _colunas(cur, "fornecedores")
        if "nome" in cols and "distribuidora" not in cols:
            cur.execute("ALTER TABLE fornecedores RENAME COLUMN nome TO distribuidora")
            cols = _colunas(cur, "fornecedores")
        if "vendedor" in cols and "representante" not in cols:
            cur.execute("ALTER TABLE fornecedores RENAME COLUMN vendedor TO representante")
            cols = _colunas(cur, "fornecedores")
        for nova in ("whatsapp", "observacoes", "representante", "cnpj"):
            if nova not in cols:
                cur.execute(f"ALTER TABLE fornecedores ADD COLUMN {nova} TEXT")
        if "ativo" not in _colunas(cur, "fornecedores"):
            cur.execute("ALTER TABLE fornecedores ADD COLUMN ativo INTEGER DEFAULT 1")
        conn.commit()
    finally:
        conn.close()


# ------------------------------------------------------------- fornecedores

def _linha_para_dict(row):
    d = dict(row)
    # "nome" continua disponível como apelido de "distribuidora" para o resto do código.
    d["nome"] = d.get("distribuidora", "")
    return d


def carregar_fornecedores():
    init_db()
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM fornecedores ORDER BY distribuidora ASC")
        return [_linha_para_dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def adicionar_fornecedor(distribuidora, cnpj="", telefone="", email="",
                         representante="", whatsapp="", observacoes="", ativo=True):
    init_db()
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO fornecedores "
            "(distribuidora, representante, telefone, whatsapp, email, cnpj, ativo, observacoes) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (distribuidora.strip(), representante.strip(), telefone.strip(),
             whatsapp.strip(), email.strip(), cnpj.strip(),
             1 if ativo else 0, observacoes.strip()),
        )
        conn.commit()
        return True, "Fornecedor cadastrado com sucesso!"
    except sqlite3.IntegrityError:
        return False, "Já existe um fornecedor com essa distribuidora!"
    except Exception as e:
        return False, f"Erro ao salvar: {e}"
    finally:
        conn.close()


def excluir_fornecedor(distribuidora):
    init_db()
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM fornecedores WHERE LOWER(distribuidora) = LOWER(?)",
                    (distribuidora.strip(),))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def atualizar_fornecedor(nome_original, novos_dados):
    init_db()
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE fornecedores SET distribuidora=?, representante=?, telefone=?, "
            "whatsapp=?, email=?, cnpj=?, ativo=?, observacoes=? "
            "WHERE LOWER(distribuidora) = LOWER(?)",
            (
                novos_dados.get("distribuidora", nome_original).strip(),
                novos_dados.get("representante", "").strip(),
                novos_dados.get("telefone", "").strip(),
                novos_dados.get("whatsapp", "").strip(),
                novos_dados.get("email", "").strip(),
                novos_dados.get("cnpj", "").strip(),
                1 if novos_dados.get("ativo", True) else 0,
                novos_dados.get("observacoes", "").strip(),
                nome_original.strip(),
            ),
        )
        conn.commit()
        return cur.rowcount > 0
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def salvar_fornecedores(lista):
    """Regrava toda a lista (usado na importação de CSV)."""
    init_db()
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM fornecedores")
        for f in lista:
            dist = str(f.get("distribuidora") or f.get("nome") or "").strip()
            if not dist:
                continue
            bruto = f.get("ativo", True)
            ativo = 1 if (bruto in (1, True) or str(bruto).strip().lower()
                          in ("1", "true", "sim", "ativo", "s")) else 0
            cur.execute(
                "INSERT OR REPLACE INTO fornecedores "
                "(distribuidora, representante, telefone, whatsapp, email, cnpj, ativo, observacoes) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (dist,
                 str(f.get("representante") or f.get("vendedor") or "").strip(),
                 str(f.get("telefone", "")).strip(),
                 str(f.get("whatsapp", "")).strip(),
                 str(f.get("email", "")).strip(),
                 str(f.get("cnpj", "")).strip(),
                 ativo,
                 str(f.get("observacoes", "")).strip()),
            )
        conn.commit()
        return True
    finally:
        conn.close()


# ---------------------------------------------------------------- cotações

def salvar_cotacao(itens, fornecedores, descricao=""):
    init_db()
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO cotacoes (criada_em, descricao, itens_json, fornecedores_json) "
            "VALUES (?, ?, ?, ?)",
            (datetime.now().strftime("%Y-%m-%d %H:%M"), descricao.strip(),
             json.dumps(itens, ensure_ascii=False),
             json.dumps(fornecedores, ensure_ascii=False)),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def listar_cotacoes(limite=30):
    init_db()
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, criada_em, descricao, itens_json FROM cotacoes ORDER BY id DESC LIMIT ?",
            (limite,),
        )
        out = []
        for row in cur.fetchall():
            try:
                total = len(json.loads(row["itens_json"]))
            except Exception:
                total = 0
            out.append({"id": row["id"], "criada_em": row["criada_em"],
                        "descricao": row["descricao"] or "", "total_itens": total})
        return out
    finally:
        conn.close()


def carregar_cotacao(cotacao_id):
    init_db()
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT itens_json FROM cotacoes WHERE id = ?", (cotacao_id,))
        row = cur.fetchone()
        if not row:
            return []
        try:
            return json.loads(row["itens_json"])
        except Exception:
            return []
    finally:
        conn.close()


def quantidades_da_cotacao(cotacao_id):
    quantidades = {}
    for item in carregar_cotacao(cotacao_id):
        med = str(item.get("medicamento", "")).strip().upper()
        if not med:
            continue
        try:
            quantidades[med] = max(1, int(item.get("qtd", 1)))
        except (TypeError, ValueError):
            quantidades[med] = 1
    return quantidades
