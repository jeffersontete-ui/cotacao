import io

import pandas as pd
import streamlit as st

import database
from calculo_vencedores import aplicar_fornecedor_escolhido
from comparador import processar_comparativo
from desempate import tratar_empates_interface
from fornecedores import (
    adicionar_fornecedor,
    atualizar_fornecedor,
    carregar_fornecedores,
    excluir_fornecedor,
    salvar_fornecedores,
)
from gerador_excel import gerar_zip_cotacoes
from pedidos import gerar_zip_pedidos
from pedidos_pdf import gerar_zip_pedidos_pdf

COLS_CALCULADAS = [
    "Qtd", "Menor Preço (R$)", "Subtotal Otimizado (R$)",
    "Fornecedor Vencedor", "Fornecedor Escolhido", "Alerta",
]

st.set_page_config(page_title="Sistema Integrado de Cotações", layout="wide")
st.title("💊 Sistema Integrado de Cotações e Fornecedores")


def formata_reais(valor):
    if pd.isna(valor):
        return "R$ 0,00"
    return f"R$ {valor:,.2f}".replace(",", "@").replace(".", ",").replace("@", ".")


tab1, tab2, tab3 = st.tabs([
    "📝 1. Criar Cotação",
    "📊 2. Comparar Preços",
    "🏢 3. Cadastro de Fornecedores",
])

# ─────────────────────────────────────────────────────────── 1. Criar cotação
with tab1:
    st.header("Gerar Nova Cotação")
    st.caption(
        "A quantidade fica só com você: ela viaja oculta na planilha e volta junto "
        "com o arquivo preenchido. O fornecedor vê apenas o produto e o campo de preço."
    )

    col1, col2 = st.columns([3, 2])

    with col1:
        if "itens_cotacao" not in st.session_state:
            st.session_state.itens_cotacao = pd.DataFrame(
                {"Medicamento": ["", "", ""], "Qtd": [1, 1, 1]}
            )

        st.write("**Itens da cotação** — cole a lista ou digite; use o ➕ para novas linhas.")
        itens_editados = st.data_editor(
            st.session_state.itens_cotacao,
            num_rows="dynamic",
            use_container_width=True,
            height=320,
            column_config={
                "Medicamento": st.column_config.TextColumn("Medicamento", width="large"),
                "Qtd": st.column_config.NumberColumn("Qtd", min_value=1, step=1, default=1),
            },
            key="editor_itens",
        )

        with st.expander("📋 Colar uma lista pronta (um medicamento por linha)"):
            texto_colado = st.text_area("Lista:", height=150, key="texto_colado")
            if st.button("Adicionar itens colados"):
                novos = [m.strip() for m in texto_colado.split("\n") if m.strip()]
                if novos:
                    df_novos = pd.DataFrame({"Medicamento": novos, "Qtd": [1] * len(novos)})
                    base = itens_editados[itens_editados["Medicamento"].astype(str).str.strip() != ""]
                    st.session_state.itens_cotacao = pd.concat([base, df_novos], ignore_index=True)
                    st.rerun()

    with col2:
        fornecedores = carregar_fornecedores()
        todos_nomes = [f["nome"] for f in fornecedores if f.get("nome")]
        ativos_nomes = [f["nome"] for f in fornecedores if f.get("ativo", True) and f.get("nome")]

        fornecedores_sel = st.multiselect(
            "Fornecedores desta cotação:",
            options=todos_nomes,
            default=ativos_nomes,
            help="Os marcados como Ativos no cadastro já vêm selecionados.",
        )
        descricao = st.text_input("Identificação da cotação (opcional)",
                                  placeholder="Ex.: Compra semanal 04/08")

    if st.button("⚙️ Gerar Planilhas de Cotação", use_container_width=True, type="primary"):
        itens = []
        for _, linha in itens_editados.iterrows():
            med = str(linha.get("Medicamento", "")).strip()
            if not med:
                continue
            try:
                qtd = max(1, int(linha.get("Qtd", 1)))
            except (TypeError, ValueError):
                qtd = 1
            itens.append({"medicamento": med, "qtd": qtd})

        if not itens:
            st.warning("⚠️ Insira pelo menos um medicamento.")
        elif not fornecedores_sel:
            st.warning("⚠️ Selecione pelo menos um fornecedor.")
        else:
            duplicados = pd.Series([i["medicamento"].upper() for i in itens])
            repetidos = duplicados[duplicados.duplicated()].unique().tolist()
            if repetidos:
                st.warning(f"⚠️ Itens repetidos na lista: {', '.join(repetidos[:5])}")

            cotacao_id = database.salvar_cotacao(itens, fornecedores_sel, descricao)
            st.session_state.zip_cotacao = gerar_zip_cotacoes(itens, fornecedores_sel, cotacao_id)
            st.session_state.cotacao_id = cotacao_id
            st.session_state.itens_cotacao = itens_editados

    if st.session_state.get("zip_cotacao"):
        st.success(
            f"✅ Cotação #{st.session_state.cotacao_id} salva e planilhas geradas."
        )
        st.download_button(
            "📥 Baixar Arquivos de Cotação (.zip)",
            data=st.session_state.zip_cotacao,
            file_name=f"Cotacao_{st.session_state.cotacao_id}.zip",
            mime="application/zip",
            use_container_width=True,
        )

# ───────────────────────────────────────────────────────── 2. Comparar preços
with tab2:
    st.header("📊 Comparativo de Preços")

    cotacoes = database.listar_cotacoes()
    quantidades_padrao = {}
    if cotacoes:
        opcoes = {
            f"#{c['id']} — {c['criada_em']} — {c['total_itens']} itens"
            + (f" — {c['descricao']}" if c["descricao"] else ""): c["id"]
            for c in cotacoes
        }
        escolha = st.selectbox(
            "Cotação de referência (de onde vêm as quantidades, caso a planilha volte sem elas):",
            options=list(opcoes.keys()),
        )
        quantidades_padrao = database.quantidades_da_cotacao(opcoes[escolha])

    arquivos_enviados = st.file_uploader(
        "Planilhas .xlsx devolvidas pelos fornecedores",
        type=["xlsx"],
        accept_multiple_files=True,
    )

    if arquivos_enviados:
        df_comparativo, relatorio = processar_comparativo(arquivos_enviados, quantidades_padrao)

        for erro in relatorio["erros"]:
            st.error(f"❌ {erro}")
        for aviso in relatorio["avisos"]:
            st.warning(f"⚠️ {aviso}")

        if relatorio["lidos"]:
            st.success(
                "✅ Entraram na comparação: "
                + " · ".join(
                    f"**{l['fornecedor']}** ({l['precos']}/{l['itens']} preços)"
                    for l in relatorio["lidos"]
                )
            )

        if df_comparativo is None:
            st.error("Nenhum arquivo pôde ser usado. Verifique as mensagens acima.")
        else:
            cols_fornecedores = [c for c in df_comparativo.columns if c not in COLS_CALCULADAS]

            alertas = df_comparativo[df_comparativo["Alerta"].astype(str).str.len() > 0]
            if not alertas.empty:
                with st.expander(f"🔍 {len(alertas)} item(ns) merecem conferência", expanded=True):
                    st.dataframe(
                        alertas[["Menor Preço (R$)", "Fornecedor Vencedor", "Alerta"]],
                        use_container_width=True,
                    )

            st.dataframe(
                df_comparativo.style
                .highlight_min(axis=1, color="lightgreen", subset=cols_fornecedores)
                .format(precision=2, na_rep="-", subset=cols_fornecedores +
                        ["Menor Preço (R$)", "Subtotal Otimizado (R$)"]),
                use_container_width=True,
            )

            # ── Desempate na tela (isolado no módulo desempate.py)
            df_final = df_comparativo.copy()
            df_final["Fornecedor Escolhido"] = df_final["Fornecedor Vencedor"]
            df_final = tratar_empates_interface(df_final)

            # 🛠️ Aplica o recálculo que zera os concorrentes e ajusta os subtotais
            df_final = aplicar_fornecedor_escolhido(df_final, cols_fornecedores)

            col_a, col_b, col_c = st.columns(3)
            col_a.metric("💰 Custo Total Otimizado",
                         formata_reais(df_final["Subtotal Otimizado (R$)"].sum(skipna=True)))
            col_b.metric("📦 Itens comparados", len(df_final))
            sem_preco = int(df_final["Menor Preço (R$)"].isna().sum())
            col_c.metric("🚫 Itens sem nenhum preço", sem_preco)

            st.divider()
            st.subheader("🧾 Gerar Pedidos de Compra")

            col_pdf, col_xls = st.columns(2)
            with col_pdf:
                st.download_button(
                    "📦 Pedidos em PDF (.zip)",
                    data=gerar_zip_pedidos_pdf(df_final),
                    file_name="Pedidos_de_Compra_PDF.zip",
                    mime="application/zip",
                    use_container_width=True,
                )
            with col_xls:
                st.download_button(
                    "📊 Pedidos em Excel (.zip)",
                    data=gerar_zip_pedidos(df_final),
                    file_name="Pedidos_de_Compra_XLSX.zip",
                    mime="application/zip",
                    use_container_width=True,
                )

# ──────────────────────────────────────────────────────── 3. Fornecedores
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

            if st.form_submit_button("💾 Salvar Fornecedor", use_container_width=True):
                if not nome.strip():
                    st.warning("⚠️ O nome do fornecedor é obrigatório.")
                else:
                    sucesso, msg = adicionar_fornecedor(nome, cnpj, telefone, email, vendedor)
                    if sucesso:
                        st.success(f"✅ {msg}")
                        st.rerun()
                    else:
                        st.error(f"❌ {msg}")

        st.divider()
        st.subheader("💾 Backup do cadastro")
        lista_atual = carregar_fornecedores()
        if lista_atual:
            csv_buffer = io.StringIO()
            pd.DataFrame(lista_atual).to_csv(csv_buffer, index=False)
            st.download_button(
                "⬇️ Exportar fornecedores (.csv)",
                data=csv_buffer.getvalue().encode("utf-8-sig"),
                file_name="fornecedores.csv",
                mime="text/csv",
                use_container_width=True,
            )

        arquivo_csv = st.file_uploader("⬆️ Importar fornecedores (.csv)", type=["csv"],
                                       key="import_forn")
        if arquivo_csv is not None:
            df_import = pd.read_csv(arquivo_csv)
            st.dataframe(df_import, use_container_width=True)
            st.warning("A importação substitui todo o cadastro atual.")
            if st.button("Confirmar importação", key="confirma_import"):
                salvar_fornecedores(df_import.to_dict("records"))
                st.success("Cadastro importado.")
                st.rerun()

    with col_list:
        st.subheader("📋 Fornecedores Cadastrados")
        lista_forn = carregar_fornecedores()

        if not lista_forn:
            st.info("Nenhum fornecedor cadastrado até o momento.")
        else:
            busca = st.text_input("🔍 Buscar fornecedor por nome:", "")
            lista_filtrada = [
                f for f in lista_forn if busca.lower() in f["nome"].lower()
            ] if busca else lista_forn

            st.metric("Total de Fornecedores", len(lista_filtrada))

            for f in lista_filtrada:
                marca = "🟢" if f.get("ativo", True) else "⚪"
                with st.expander(f"{marca} **{f['nome']}**"):
                    with st.form(f"form_edit_{f['id']}"):
                        novo_nome = st.text_input("Nome", value=f["nome"] or "")
                        novo_cnpj = st.text_input("CNPJ", value=f.get("cnpj") or "")
                        novo_vend = st.text_input("Vendedor", value=f.get("vendedor") or "")
                        novo_tel = st.text_input("Telefone", value=f.get("telefone") or "")
                        novo_mail = st.text_input("E-mail", value=f.get("email") or "")
                        novo_ativo = st.checkbox("Ativo", value=bool(f.get("ativo", True)))

                        if st.form_submit_button("💾 Salvar alterações", use_container_width=True):
                            ok = atualizar_fornecedor(f["nome"], {
                                "nome": novo_nome, "cnpj": novo_cnpj, "vendedor": novo_vend,
                                "telefone": novo_tel, "email": novo_mail, "ativo": novo_ativo,
                            })
                            if ok:
                                st.success("Atualizado.")
                                st.rerun()
                            else:
                                st.error("Não foi possível atualizar (nome já usado?).")

                    confirmar = st.checkbox(
                        "Confirmo que quero excluir este fornecedor",
                        key=f"conf_del_{f['id']}",
                    )
                    if st.button("🗑️ Excluir", key=f"del_{f['id']}",
                                 disabled=not confirmar, use_container_width=True):
                        excluir_fornecedor(f["nome"])
                        st.success("Fornecedor removido.")
                        st.rerun()
