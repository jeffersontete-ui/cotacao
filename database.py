import sqlite3

DB_NAME = "cotacao.db"


def get_connection():
    """Conecta ao banco de dados SQLite."""
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Cria a tabela de fornecedores se ela ainda não existir."""
    with get_connection() as conn:
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
        conn.commit()


def carregar_fornecedores():
    """Retorna todos os fornecedores cadastrados."""
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM fornecedores ORDER BY nome ASC")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def adicionar_fornecedor(nome, cnpj="", telefone="", email="", vendedor=""):
    """Insere um novo fornecedor no banco de dados."""
    init_db()
    try:
        with get_connection() as conn:
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


def excluir_fornecedor(nome):
    """Exclui um fornecedor pelo nome."""
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM fornecedores WHERE LOWER(nome) = LOWER(?)",
            (nome.strip(),),
        )
        conn.commit()
        return cursor.rowcount > 0


def atualizar_fornecedor(nome_original, novos_dados):
    """Atualiza os dados de um fornecedor existente."""
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE fornecedores SET nome = ?, cnpj = ?, vendedor = ?, telefone = ?, email = ?, ativo = ? WHERE LOWER(nome) = LOWER(?)",
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
