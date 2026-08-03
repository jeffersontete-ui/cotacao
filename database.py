import json
import os
import sqlite3
from datetime import datetime

# Caminho absoluto: garante o mesmo banco independente da pasta de onde o app é iniciado.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(BASE_DIR, "cotacao.db")


def get_connection():
    """Conecta ao banco de dados SQLite."""
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Cria as tabelas se elas ainda não existirem."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fornecedores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT UNIQUE NOT NULL,
                cnpj TEXT,
                vendedor TEXT,
                telefone TEXT,
                email TEXT,
                ativo INTEGER DEFAULT 1
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cotacoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                criada_em TEXT NOT NULL,
                descricao TEXT,
                itens_json TEXT NOT NULL,
                fornecedores_json TEXT
            )
        """)
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------- fornecedores

def carregar_fornecedores():
    """Retorna todos os fornecedores cadastrados."""
    init_db()
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM fornecedores ORDER BY nome ASC")
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def adicionar_fornecedor(nome, cnpj="", telefone="", email="", vendedor=""):
    """Insere um novo fornecedor no banco de dados."""
    init_db()
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO fornecedores (nome, cnpj, vendedor, telefone, email) VALUES (?, ?, ?, ?, ?)",
            (nome.strip(), cnpj.strip(), vendedor.strip(), telefone.strip(), email.strip()),
        )
        conn.commit()
        return True, "Fornecedor cadastrado com sucesso!"
    except sqlite3.IntegrityError:
        return False, "Fornecedor já cadastrado!"
    except Exception as e:
        return False, f"Erro ao salvar no banco de dados: {str(e)}"
    finally:
        conn.close()


def excluir_fornecedor(nome):
    """Exclui um fornecedor pelo nome."""
    init_db()
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM fornecedores WHERE LOWER(nome) = LOWER(?)",
            (nome.strip(),),
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def atualizar_fornecedor(nome_original, novos_dados):
    """Atualiza os dados de um fornecedor existente."""
    init_db()
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE fornecedores SET nome = ?, cnpj = ?, vendedor = ?, telefone = ?, "
            "email = ?, ativo = ? WHERE LOWER(nome) = LOWER(?)",
            (
                novos_dados.get("nome", nome_original).strip(),
                novos_dados.get("cnpj", "").strip(),
                novos_dados.get("vendedor", "").strip(),
                novos_dados.get("telefone", "").strip(),
                novos_dados.get("email", "").strip(),
                1 if novos_dados.get("ativo", True) else 0,
                nome_original.strip(),
            ),
        )
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def salvar_fornecedores(lista_fornecedores):
    """Regrava a lista inteira de fornecedores (usado na importação de CSV)."""
    init_db()
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM fornecedores")
        for f in lista_fornecedores:
            nome = str(f.get("nome", "")).strip()
            if not nome:
                continue
            cursor.execute(
                "INSERT OR REPLACE INTO fornecedores (nome, cnpj, vendedor, telefone, email, ativo) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    nome,
                    str(f.get("cnpj", "")).strip(),
                    str(f.get("vendedor", "")).strip(),
                    str(f.get("telefone", "")).strip(),
                    str(f.get("email", "")).strip(),
                    1 if f.get("ativo", True) in (1, True, "1", "True", "Sim", "sim") else 0,
                ),
            )
        conn.commit()
        return True
    finally:
        conn.close()


# ------------------------------------------------------------------- cotações

def salvar_cotacao(itens, fornecedores, descricao=""):
    """
    Guarda a cotação enviada aos fornecedores.

    itens: lista de dicts {"medicamento": str, "qtd": int}
    Retorna o id da cotação, usado depois para recuperar as quantidades.
    """
    init_db()
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO cotacoes (criada_em, descricao, itens_json, fornecedores_json) "
            "VALUES (?, ?, ?, ?)",
            (
                datetime.now().strftime("%Y-%m-%d %H:%M"),
                descricao.strip(),
                json.dumps(itens, ensure_ascii=False),
                json.dumps(fornecedores, ensure_ascii=False),
            ),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def listar_cotacoes(limite=30):
    """Lista as cotações mais recentes (sem carregar os itens)."""
    init_db()
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, criada_em, descricao, itens_json FROM cotacoes "
            "ORDER BY id DESC LIMIT ?",
            (limite,),
        )
        resultado = []
        for row in cursor.fetchall():
            try:
                total_itens = len(json.loads(row["itens_json"]))
            except Exception:
                total_itens = 0
            resultado.append({
                "id": row["id"],
                "criada_em": row["criada_em"],
                "descricao": row["descricao"] or "",
                "total_itens": total_itens,
            })
        return resultado
    finally:
        conn.close()


def carregar_cotacao(cotacao_id):
    """Retorna os itens de uma cotação salva, ou lista vazia se não existir."""
    init_db()
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT itens_json FROM cotacoes WHERE id = ?", (cotacao_id,))
        row = cursor.fetchone()
        if not row:
            return []
        try:
            return json.loads(row["itens_json"])
        except Exception:
            return []
    finally:
        conn.close()


def quantidades_da_cotacao(cotacao_id):
    """Retorna {MEDICAMENTO_EM_MAIUSCULO: qtd} para uma cotação salva."""
    itens = carregar_cotacao(cotacao_id)
    quantidades = {}
    for item in itens:
        med = str(item.get("medicamento", "")).strip().upper()
        if not med:
            continue
        try:
            quantidades[med] = max(1, int(item.get("qtd", 1)))
        except (TypeError, ValueError):
            quantidades[med] = 1
    return quantidades
