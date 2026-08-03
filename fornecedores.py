import database


def carregar_fornecedores():
    return database.carregar_fornecedores()


def adicionar_fornecedor(nome, cnpj="", telefone="", email="", vendedor=""):
    return database.adicionar_fornecedor(nome, cnpj, telefone, email, vendedor)


def excluir_fornecedor(nome):
    return database.excluir_fornecedor(nome)


def salvar_fornecedores(lista_fornecedores):
    return database.salvar_fornecedores(lista_fornecedores)


def atualizar_fornecedor(nome_original, novos_dados):
    return database.atualizar_fornecedor(nome_original, novos_dados)
