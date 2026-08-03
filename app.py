import json
import os

import pandas as pd
import streamlit as st
from gerador_excel import gerar_zip_cotacoes
from comparador import processar_comparativo

# Configuração da página
st.set_page_config(page_title="Sistema Integrado de Cotações", layout="wide")

# Persistência de fornecedores
ARQUIVO_JSON = "fornecedores.json"


def carregar_fornecedores():
    if os.path.exists(ARQUIVO_JSON):
        try:
            with open(ARQUIVO_JSON, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def salvar_fornecedores(dados):
    with open(ARQUIVO_JSON, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=2, ensure_ascii=False)


st.title("💊 Sistema Integrado de Cotações e Fornecedores")

# Criação das Abas principais
tab1, tab2, tab3 = st.tabs([
    "📝 1. Criar Cotação",
    "📊 2. Comparar Preços",
    "🏢 3. Cadastro de Fornecedores",
])

with tab1:
    st.header("Gerar Nova Cotação")

    col1, col2 = st.columns([3, 2])

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

    if st.button("⚙️ Gerar Planilhas de Cotação", use_container_width=True):
        lista_meds_limpa = [m for m in lista_meds.split("\n") if m.strip()]

        if not lista_meds_limpa:
            st.warning("⚠️ Por favor, insira pelo menos um medicamento.")
        elif not fornecedores_sel:
            st.warning("⚠️ Por favor, selecione pelo menos um fornecedor.")
        else:
            zip_data = gerar_zip_cotacoes(lista_meds_limpa, fornecedores_sel)
            st.success("✅ Planilhas geradas com sucesso!")
            st.download_button(
                label="📥 Baixar Arquivos de Cotação (.zip)",
                data=zip_data,
                file_name="Cotacoes_Fornecedores.zip",
                mime="application/zip",
                use_container_width=True,
            )

with tab2:
    st.header("📊 Comparativo de Preços das Cotações")
    st.write(
        "Faça o upload dos arquivos `.xlsx` preenchidos pelos fornecedores para gerar o mapa comparativo:"
    )

    arquivos_enviados = st.file_uploader(
        "Selecione as planilhas dos fornecedores",
        type=["xlsx"],
        accept_multiple_files=True,
    )

    if arquivos_enviados:
        df_comparativo = processar_comparativo(arquivos_enviados)

        if df_comparativo is not None:
            st.success(f"✅ {len(arquivos_enviados)} planilha(s) analisada(s) com sucesso!")

            st.dataframe(df_comparativo, use_container_width=True)

            total_otimizado = df_comparativo['Menor Preço (R$)'].sum()
            st.metric(
                label="💰 Custo Total Otimizado",
                value=f"R$ {total_otimizado:,.2f}",
            )
        else:
            st.warning("Nenhum dado válido foi encontrado nos arquivos carregados.")

with tab3:
    st.header("Cadastro e Status dos Fornecedores")
    st.caption(
        "Edite diretamente na tabela abaixo. Marque/desmarque a opção 'ativo' e clique em Salvar."
    )

    dados_fornecedores = carregar_fornecedores()

    if not dados_fornecedores:
        df_inicial = pd.DataFrame([
            {
                "distribuidora": "DISTRIBUIDORA EXEMPLO",
                "representante": "Nome do Rep",
                "telefone": "(00) 00000-0000",
                "ativo": True,
            }
        ])
    else:
        df_inicial = pd.DataFrame(dados_fornecedores)

    df_editado = st.data_editor(
        df_inicial,
        num_rows="dynamic",
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

    if st.button("💾 Salvar Alterações de Fornecedores", type="primary"):
        novos_dados = df_editado.to_dict(orient="records")
        salvar_fornecedores(novos_dados)
        st.success("✅ Cadastro atualizado e salvo com sucesso no arquivo JSON!")
