from fornecedores import (
    carregar_fornecedores,
    salvar_fornecedores,
    adicionar_fornecedor,
    excluir_fornecedor,
    atualizar_fornecedor,
)

import pandas as pd
import streamlit as st
from gerador_excel import gerar_zip_cotacoes
from pedidos import gerar_zip_pedidos
from comparador import processar_comparativo

# Configuração da página
st.set_page_config(page_title="Sistema Integrado de Cotações", layout="wide")


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
        todos_nomes = [f["nome"] for f in fornecedores if f.get("nome")]
        ativos_nomes = [
            f["nome"]
            for f in fornecedores
            if f.get("ativo", True) and f.get("nome")
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

            zip_pedidos = gerar_zip_pedidos(df_comparativo)
            st.download_button(
                label="📥 Baixar ZIP de Pedidos de Compra",
                data=zip_pedidos,
                file_name="Pedidos_de_Compra.zip",
                mime="application/zip",
                use_container_width=True,
            )
        else:
            st.warning("Nenhum dado válido foi encontrado nos arquivos carregados.")

with tab3:
    st.header("🏢 Gestão e Cadastro de Fornecedores")

    col_cad, col_list = st.columns([1, 1.5])

    with col_cad:
        st.subheader("➕ Novo Fornecedor")
        with st.form("form_cad_fornecedor", clear_on_submit=True):
            nome = st.text_input("Nome Fantasia / Distribuidora *")
            cnpj = st.text_input("CNPJ (Opcional)")
            vendedor = st.text_input("Nome do Vendedor / Contato")
            telefone = st.text_input("Telefone / WhatsApp")
            email = st.text_input("E-mail")

            submeter = st.form_submit_button("💾 Salvar Fornecedor", use_container_width=True)

            if submeter:
                if not nome:
                    st.warning("⚠️ O nome do fornecedor é obrigatório.")
                else:
                    sucesso, msg = adicionar_fornecedor(nome, cnpj, telefone, email, vendedor)
                    if sucesso:
                        st.success(f"✅ {msg}")
                        rerun()
                    else:
                        st.error(f"❌ {msg}")

    with col_list:
        st.subheader("📋 Fornecedores Cadastrados")
        lista_forn = carregar_fornecedores()

        if not lista_forn:
            st.info("Nenhum fornecedor cadastrado até o momento.")
        else:
            busca = st.text_input("🔍 Buscar fornecedor por nome:", "")
            if busca:
                lista_filtrada = [
                    f for f in lista_forn if busca.lower() in f["nome"].lower()
                ]
            else:
                lista_filtrada = lista_forn

            st.metric("Total de Fornecedores", len(lista_filtrada))

            for i, f in enumerate(lista_filtrada):
                with st.expander(f"🏢 **{f['nome']}**"):
                    col_info, col_acoes = st.columns([3, 1])

                    with col_info:
                        if f.get('vendedor'):
                            st.write(f"👤 **Vendedor:** {f['vendedor']}")
                        if f.get('telefone'):
                            st.write(f"📞 **Telefone:** {f['telefone']}")
                        if f.get('email'):
                            st.write(f"✉️ **E-mail:** {f['email']}")
                        if f.get('cnpj'):
                            st.write(f"📄 **CNPJ:** {f['cnpj']}")
                        st.write(f"🔔 **Ativo:** {'Sim' if f.get('ativo', True) else 'Não'}")

                    with col_acoes:
                        if st.button("🗑️ Excluir", key=f"del_{f['nome']}_{i}", use_container_width=True):
                            excluir_fornecedor(f['nome'])
                            st.success("Fornecedor removido com sucesso!")
                            st.experimental_rerun()
