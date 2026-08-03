import json
import os

ARQUIVO_JSON = "fornecedores.json"


def _normalizar_fornecedor(fornecedor):
    fornecedor_normalizado = {
        "id": fornecedor.get("id"),
        "nome": fornecedor.get("nome") or fornecedor.get("distribuidora") or "",
        "cnpj": fornecedor.get("cnpj", "").strip(),
        "telefone": fornecedor.get("telefone", "").strip(),
        "email": fornecedor.get("email", "").strip(),
        "vendedor": fornecedor.get("vendedor") or fornecedor.get("representante") or "",
        "ativo": fornecedor.get("ativo", True),
    }

    if fornecedor_normalizado["id"] is None:
        fornecedor_normalizado["id"] = 0

    return fornecedor_normalizado


def carregar_fornecedores():
    """Lê a lista de fornecedores salva no JSON."""
    if not os.path.exists(ARQUIVO_JSON):
        return []

    try:
        with open(ARQUIVO_JSON, "r", encoding="utf-8") as f:
            fornecedores = json.load(f)
    except Exception:
        return []

    fornecedores_normalizados = []
    for f in fornecedores:
        if isinstance(f, dict):
            fornecedores_normalizados.append(_normalizar_fornecedor(f))

    for index, fornecedor in enumerate(fornecedores_normalizados, start=1):
        fornecedor["id"] = index

    return fornecedores_normalizados


def salvar_fornecedores(lista_fornecedores):
    """Salva a lista atualizada no arquivo JSON."""
    with open(ARQUIVO_JSON, "w", encoding="utf-8") as f:
        json.dump(lista_fornecedores, f, ensure_ascii=False, indent=4)


def adicionar_fornecedor(nome, cnpj="", telefone="", email="", vendedor=""):
    """Adiciona um novo fornecedor à lista se não existir duplicado."""
    fornecedores = carregar_fornecedores()

    if any(f["nome"].strip().lower() == nome.strip().lower() for f in fornecedores):
        return False, "Fornecedor já cadastrado!"

    novo = {
        "id": len(fornecedores) + 1,
        "nome": nome.strip(),
        "cnpj": cnpj.strip(),
        "telefone": telefone.strip(),
        "email": email.strip(),
        "vendedor": vendedor.strip(),
        "ativo": True,
    }

    fornecedores.append(novo)
    salvar_fornecedores(fornecedores)
    return True, "Fornecedor cadastrado com sucesso!"


def excluir_fornecedor(nome):
    """Remove um fornecedor pelo nome."""
    fornecedores = carregar_fornecedores()
    nova_lista = [
        f for f in fornecedores if f["nome"].strip().lower() != nome.strip().lower()
    ]

    if len(nova_lista) < len(fornecedores):
        salvar_fornecedores(nova_lista)
        return True
    return False


def atualizar_fornecedor(nome_original, novos_dados):
    """Atualiza os dados de um fornecedor existente."""
    fornecedores = carregar_fornecedores()
    for f in fornecedores:
        if f["nome"].strip().lower() == nome_original.strip().lower():
            f.update(novos_dados)
            salvar_fornecedores(fornecedores)
            return True
    return False
