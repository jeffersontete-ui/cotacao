import json
import os
import pandas as pd
import streamlit as st

# Configuração da página (Modo amplo para facilitar visualização)
st.set_page_config(
    page_title="Gestão de Cotações", page_icon="💊", layout="wide"
)

# -----------------------------------------------------------------------------
# FUNÇÕES DE PERSISTÊNCIA EM JSON
# -----------------------------------------------------------------------------
ARQUIVO_JSON = "fornecedores.json"


def carregar_fornecedores():
  """Lê os fornecedores salvos no arquivo JSON."""
  if os.path.exists(ARQUIVO_JSON):
    try:
      with open(ARQUIVO_JSON, "r", encoding="utf-8") as f:
        return json.load(f)
    except Exception:
      return []
  return []


def salvar_fornecedores(dados):
  """Salva a lista de fornecedores no arquivo JSON."""
  with open(ARQUIVO_JSON, "w", encoding="utf-8") as f:
    json.dump(dados, f, indent=2, ensure_ascii=False)


# -----------------------------------------------------------------------------
# NAVEGAÇÃO POR ABAS
# -----------------------------------------------------------------------------
st.title("💊 Sistema Integrado de Cotações e Fornecedores")

aba_cotacao, aba_cadastro = st.tabs(
    ["📝 1. Criar Cotação", "👥 2. Cadastro de Fornecedores"]
)

# -----------------------------------------------------------------------------
# ABA 1: CRIAR COTAÇÃO
# -----------------------------------------------------------------------------
with aba_cotacao:
  st.header("Gerar Nova Cotação")

  # 1. Criamos a divisão em duas colunas (60% e 40%)
  col1, col2 = st.columns([3, 2])

  # 2. Tudo dentro de 'with col1:' vai para a esquerda
  with col1:
    lista_padrao = (
        "ACEBROFILINA 25 MG XPE PED 120 ML\nACECLOFENACO 100 MG C/ 12 CPR"
    )
    lista_meds = st.text_area(
        "Lista de Medicamentos (um por linha):",
        value=lista_padrao,
        height=220,
        help="Digite ou cole um medicamento por linha.",
    )

  # 3. Tudo dentro de 'with col2:' vai para a direita
  with col2:
    fornecedores = carregar_fornecedores()
    todos_nomes = [f["distribuidora"] for f in fornecedores if "distribuidora" in f]
    ativos_nomes = [
        f["distribuidora"]
        for f in fornecedores
        if f.get("ativo") and "distribuidora" in f
    ]

    fornecedores_sel = st.multiselect(
        "Selecione os fornecedores para esta cotação:",
        options=todos_nomes,
        default=ativos_nomes,
        help="Fornecedores marcados como Ativos no cadastro vêm pré-selecionados automaticamente.",
    )

  # 3. Botão para Gerar Planilhas
  if st.button("⚙️ Gerar Planilhas de Cotação", type="primary"):
    lista_meds = [
        m.strip() for m in lista_meds.split("\n") if m.strip()
    ]

    if not lista_meds:
      st.error("⚠️ Insira pelo menos um medicamento para continuar.")
    elif not fornecedores_sel:
      st.warning("⚠️ Selecione ao menos um fornecedor para a cotação.")
    else:
      st.success(
          f"✅ Cotação gerada com {len(lista_meds)} medicamentos para"
          f" {len(fornecedores_sel)} fornecedor(es)!"
      )
      # Aqui entra a chamada da função do seu gerador_excel.py

# -----------------------------------------------------------------------------
# ABA 2: CADASTRO DE FORNECEDORES
# -----------------------------------------------------------------------------
with aba_cadastro:
  st.header("Cadastro e Status dos Fornecedores")
  st.caption(
      "Edite diretamente na tabela abaixo. Marque/desmarque a opção 'ativo' e"
      " clique em Salvar."
  )

  # Carrega dados atuais em um DataFrame
  dados_fornecedores = carregar_fornecedores()

  if not dados_fornecedores:
    df_inicial = pd.DataFrame([{
        "distribuidora": "DISTRIBUIDORA EXEMPLO",
        "representante": "Nome do Rep",
        "telefone": "(00) 00000-0000",
        "ativo": True,
    }])
  else:
    df_inicial = pd.DataFrame(dados_fornecedores)

  # Tabela interativa leve e rápida
  df_editado = st.data_editor(
      df_inicial,
      num_rows="dynamic",  # Permite adicionar ➕ ou excluir 🗑️ linhas
      use_container_width=True,
      column_config={
          "distribuidora": st.column_config.TextColumn(
              "Distribuidora", required=True
          ),
          "representante": st.column_config.TextColumn("Representante"),
          "telefone": st.column_config.TextColumn("Telefone"),
          "ativo": st.column_config.CheckboxColumn("Ativo?", default=True),
      },
  )

  # Botão de Salvamento
  if st.button("💾 Salvar Alterações de Fornecedores", type="primary"):
    novos_dados = df_editado.to_dict(orient="records")
    salvar_fornecedores(novos_dados)
    st.success("✅ Cadastro atualizado e salvo com sucesso no arquivo JSON!")