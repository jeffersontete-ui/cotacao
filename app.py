import io

import pandas as pd
import streamlit as st

import database
from dashboard import calcular_dashboard
from database import (
    adicionar_fornecedor, atualizar_fornecedor, carregar_fornecedores,
    excluir_fornecedor, salvar_fornecedores,
)
from gerador_excel import gerar_zip_cotacoes
from leitor_excel import (
    aplicar_escolhas, colunas_de_fornecedores, listar_empates, processar_comparativo,
)
from pedidos import gerar_zip_pedidos
from pedidos_pdf import gerar_zip_pedidos_pdf

st.set_page_config(page_title="Sistema Integrado de Cotações", page_icon="💊", layout="wide")


def brl(v):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "R$ 0,00"
    return f"R$ {v:,.2f}".replace(",", "@").replace(".", ",").replace("@", ".")


def itens_vazios():
    return pd.DataFrame({"Medicamento": ["", "", ""], "Qtd": [1, 1, 1]})


st.title("💊 Sistema Integrado de Cotações")

tab1, tab2, tab3 = st.tabs([
    "📝 1. Criar Cotação",
    "📊 2. Comparar e Decidir",
    "🏢 3. Fornecedores",
])

# ════════════════════════════════════════════════════ 1. CRIAR COTAÇÃO
with tab1:
    col_topo, col_btn = st.columns([4, 1])
    col_topo.header("Criar Nova Cotação")
    if col_btn.button("🗑️ Limpar", help="Começar uma cotação em branco"):
        st.session_state.itens_cotacao = itens_vazios()
        st.session_state.pop("zip_cotacao", None)
        st.rerun()

    st.caption(
        "A quantidade é sua: viaja oculta na planilha e volta com o arquivo preenchido. "
        "O fornecedor vê apenas o medicamento e o campo de valor."
    )

    if "itens_cotacao" not in st.session_state:
        st.session_state.itens_cotacao = itens_vazios()

    col_itens, col_forn = st.columns([3, 2])

    with col_itens:
        st.write("**Itens** — digite ou cole; use ➕ para novas linhas.")
        itens_editados = st.data_editor(
            st.session_state.itens_cotacao,
            num_rows="dynamic", width="stretch", height=340,
            column_config={
                "Medicamento": st.column_config.TextColumn("Medicamento", width="large"),
                "Qtd": st.column_config.NumberColumn("Qtd", min_value=1, step=1, default=1),
            },
            key="editor_itens",
        )
        with st.expander("📋 Colar lista pronta (um medicamento por linha)"):
            texto = st.text_area("Lista:", height=140, key="texto_colado")
            if st.button("Adicionar itens colados"):
                novos = [m.strip() for m in texto.split("\n") if m.strip()]
                if novos:
                    base = itens_editados[itens_editados["Medicamento"].astype(str).str.strip() != ""]
                    df_novos = pd.DataFrame({"Medicamento": novos, "Qtd": [1] * len(novos)})
                    st.session_state.itens_cotacao = pd.concat([base, df_novos], ignore_index=True)
                    st.rerun()

    with col_forn:
        fornecedores = carregar_fornecedores()
        nomes = [f["nome"] for f in fornecedores if f.get("nome")]
        ativos = [f["nome"] for f in fornecedores if f.get("ativo", True) and f.get("nome")]
        forn_sel = st.multiselect("Fornecedores desta cotação:", options=nomes, default=ativos,
                                  help="Os ativos já vêm marcados.")
        descricao = st.text_input("Identificação (opcional)", placeholder="Ex.: Compra semanal 04/08")

    if st.button("⚙️ Gerar Planilhas de Cotação", width="stretch", type="primary"):
        itens = []
        for _, l in itens_editados.iterrows():
            med = str(l.get("Medicamento", "")).strip()
            if not med:
                continue
            try:
                qtd = max(1, int(l.get("Qtd", 1)))
            except (TypeError, ValueError):
                qtd = 1
            itens.append({"medicamento": med, "qtd": qtd})

        if not itens:
            st.warning("⚠️ Insira pelo menos um medicamento.")
        elif not forn_sel:
            st.warning("⚠️ Selecione pelo menos um fornecedor.")
        else:
            reps = pd.Series([i["medicamento"].upper() for i in itens])
            dup = reps[reps.duplicated()].unique().tolist()
            if dup:
                st.warning(f"⚠️ Itens repetidos: {', '.join(dup[:5])}")
            cid = database.salvar_cotacao(itens, forn_sel, descricao)
            st.session_state.zip_cotacao = gerar_zip_cotacoes(itens, forn_sel, cid)
            st.session_state.cotacao_id = cid
            st.session_state.itens_cotacao = itens_editados

    if st.session_state.get("zip_cotacao"):
        st.success(f"✅ Cotação #{st.session_state.cotacao_id} salva e planilhas geradas.")
        st.download_button("📥 Baixar Planilhas (.zip)", data=st.session_state.zip_cotacao,
                           file_name=f"Cotacao_{st.session_state.cotacao_id}.zip",
                           mime="application/zip", width="stretch")

# ════════════════════════════════════════════════ 2. COMPARAR E DECIDIR
with tab2:
    st.header("📊 Comparar Preços e Decidir")

    cotacoes = database.listar_cotacoes()
    quantidades_padrao = {}
    if cotacoes:
        opcoes = {f"#{c['id']} — {c['criada_em']} — {c['total_itens']} itens"
                  + (f" — {c['descricao']}" if c["descricao"] else ""): c["id"] for c in cotacoes}
        escolha = st.selectbox("Cotação de referência (de onde vêm as quantidades):",
                               options=list(opcoes.keys()))
        quantidades_padrao = database.quantidades_da_cotacao(opcoes[escolha])

    arquivos = st.file_uploader("Planilhas .xlsx devolvidas pelos fornecedores",
                                type=["xlsx"], accept_multiple_files=True)

    if not arquivos:
        st.info("Envie os arquivos preenchidos para começar a comparação.")
    else:
        df_base, relatorio = processar_comparativo(arquivos, quantidades_padrao)

        for e in relatorio["erros"]:
            st.error(f"❌ {e}")
        for a in relatorio["avisos"]:
            st.warning(f"⚠️ {a}")
        if relatorio["lidos"]:
            st.success("✅ Lidos: " + " · ".join(
                f"**{l['fornecedor']}** ({l['precos']}/{l['itens']})" for l in relatorio["lidos"]))

        if df_base is None:
            st.error("Nenhum arquivo pôde ser usado.")
            st.stop()

        empates = listar_empates(df_base)

        # chave de identidade desta comparação: se os arquivos mudarem, as escolhas zeram
        assinatura = tuple(sorted(e["medicamento"] for e in empates))
        if st.session_state.get("assinatura_empates") != assinatura:
            st.session_state.escolhas_empate = {}
            st.session_state.assinatura_empates = assinatura

        pendentes = [e for e in empates
                     if e["medicamento"] not in st.session_state.get("escolhas_empate", {})]

        # ───────────────── TELA DE EMPATE (bloqueante) — requisito 1
        if pendentes:
            st.divider()
            st.subheader("⚖️ Resolver Empates")
            st.error(
                f"Há **{len(pendentes)}** item(ns) empatado(s) sem vencedor. "
                "Escolha um fornecedor para cada um — o restante da tela fica bloqueado até terminar."
            )
            with st.form("form_empates"):
                escolhas_form = {}
                for e in pendentes:
                    escolhas_form[e["medicamento"]] = st.radio(
                        f"**{e['medicamento']}** — {brl(e['preco'])}",
                        options=e["candidatos"],
                        horizontal=True,
                        index=None,
                        key=f"radio_{e['medicamento']}",
                    )
                enviado = st.form_submit_button("✅ Confirmar vencedores", width="stretch", type="primary")

            if enviado:
                faltou = [m for m, v in escolhas_form.items() if not v]
                if faltou:
                    st.warning(f"⚠️ Ainda faltam {len(faltou)} item(ns) sem escolha.")
                else:
                    st.session_state.escolhas_empate.update(escolhas_form)
                    st.rerun()
            st.stop()   # nada abaixo aparece enquanto houver empate pendente

        # ───────────────── daqui pra baixo, tudo já recalculado com as escolhas
        df = aplicar_escolhas(df_base, st.session_state.get("escolhas_empate", {}))
        cols_forn = colunas_de_fornecedores(df)

        if empates:
            st.success(f"✅ {len(empates)} empate(s) resolvido(s).")
            if st.button("↩️ Refazer escolhas de empate"):
                st.session_state.escolhas_empate = {}
                st.rerun()

        # ---- Dashboard (requisito 7)
        painel = calcular_dashboard(df)
        st.subheader("📈 Painel")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("💰 Total otimizado", brl(painel["total_otimizado"]))
        c2.metric("💚 Economia", brl(painel["economia"]), f"{painel['economia_pct']}%")
        c3.metric("📦 Itens", painel["itens"],
                  f"{painel['itens_pendentes']} pendentes" if painel["itens_pendentes"] else "todos decididos")
        c4.metric("🚫 Sem preço", painel["itens_sem_preco"])

        col_rank, col_val = st.columns(2)
        with col_rank:
            st.caption("🏆 Ranking por valor de compra")
            if not painel["ranking"].empty:
                st.dataframe(painel["ranking"].style.format({"Valor (R$)": brl}), width="stretch")
            else:
                st.write("—")
        with col_val:
            st.caption("💵 Valor por fornecedor")
            pf = painel["por_fornecedor"]
            if not pf.empty:
                st.bar_chart(pf.set_index("Fornecedor")["Valor (R$)"])

        # ---- Alertas
        alertas = df[df["Alerta"].astype(str).str.len() > 0]
        if not alertas.empty:
            with st.expander(f"🔍 {len(alertas)} item(ns) para conferir", expanded=False):
                st.dataframe(alertas[["Menor Preço (R$)", "Fornecedor Escolhido", "Alerta"]],
                             width="stretch")

        # ---- Tabela comparativa (preços dos perdedores permanecem visíveis)
        st.subheader("🧾 Comparativo")
        num_cols = cols_forn + ["Menor Preço (R$)", "Subtotal Otimizado (R$)"]
        st.dataframe(
            df.style
            .highlight_min(axis=1, color="#D7F0E3", subset=cols_forn)
            .format(brl, subset=num_cols, na_rep="—"),
            width="stretch",
        )

        # ---- Pedidos (requisitos 8) — recalculados automaticamente
        st.divider()
        st.subheader("📤 Gerar Pedidos de Compra")
        cpdf, cxls = st.columns(2)
        cpdf.download_button("📦 Pedidos em PDF (.zip)", data=gerar_zip_pedidos_pdf(df),
                             file_name="Pedidos_PDF.zip", mime="application/zip", width="stretch")
        cxls.download_button("📊 Pedidos em Excel (.zip)", data=gerar_zip_pedidos(df),
                             file_name="Pedidos_XLSX.zip", mime="application/zip", width="stretch")

# ════════════════════════════════════════════════════ 3. FORNECEDORES
with tab3:
    st.header("🏢 Fornecedores")
    col_cad, col_lista = st.columns([1, 1.4])

    with col_cad:
        st.subheader("➕ Novo Fornecedor")
        with st.form("form_novo", clear_on_submit=True):
            distribuidora = st.text_input("Distribuidora *")
            representante = st.text_input("Representante")
            telefone = st.text_input("Telefone")
            whatsapp = st.text_input("WhatsApp")
            email = st.text_input("E-mail")
            cnpj = st.text_input("CNPJ")
            ativo = st.checkbox("Ativo", value=True)
            observacoes = st.text_area("Observações", height=80)
            if st.form_submit_button("💾 Salvar", width="stretch"):
                if not distribuidora.strip():
                    st.warning("⚠️ A distribuidora é obrigatória.")
                else:
                    ok, msg = adicionar_fornecedor(
                        distribuidora, cnpj, telefone, email,
                        representante, whatsapp, observacoes, ativo)
                    (st.success if ok else st.error)(("✅ " if ok else "❌ ") + msg)
                    if ok:
                        st.rerun()

        st.divider()
        st.subheader("💾 Backup")
        lista = carregar_fornecedores()
        if lista:
            buf = io.StringIO()
            pd.DataFrame(lista)[database.CAMPOS_FORNECEDOR].to_csv(buf, index=False)
            st.download_button("⬇️ Exportar (.csv)", data=buf.getvalue().encode("utf-8-sig"),
                               file_name="fornecedores.csv", mime="text/csv", width="stretch")
        up = st.file_uploader("⬆️ Importar (.csv)", type=["csv"], key="imp")
        if up is not None:
            df_imp = pd.read_csv(up)
            st.dataframe(df_imp, width="stretch")
            st.warning("A importação substitui todo o cadastro.")
            if st.button("Confirmar importação"):
                salvar_fornecedores(df_imp.to_dict("records"))
                st.success("Importado.")
                st.rerun()

    with col_lista:
        st.subheader("📋 Cadastrados")
        lista = carregar_fornecedores()
        if not lista:
            st.info("Nenhum fornecedor cadastrado.")
        else:
            busca = st.text_input("🔍 Buscar:", "")
            filtrados = [f for f in lista if busca.lower() in f["nome"].lower()] if busca else lista
            st.metric("Total", len(filtrados))
            for f in filtrados:
                marca = "🟢" if f.get("ativo", True) else "⚪"
                with st.expander(f"{marca} **{f['nome']}**"):
                    with st.form(f"edit_{f['id']}"):
                        d = st.text_input("Distribuidora", value=f.get("distribuidora") or "")
                        r = st.text_input("Representante", value=f.get("representante") or "")
                        t = st.text_input("Telefone", value=f.get("telefone") or "")
                        w = st.text_input("WhatsApp", value=f.get("whatsapp") or "")
                        m = st.text_input("E-mail", value=f.get("email") or "")
                        cj = st.text_input("CNPJ", value=f.get("cnpj") or "")
                        at = st.checkbox("Ativo", value=bool(f.get("ativo", True)))
                        ob = st.text_area("Observações", value=f.get("observacoes") or "", height=70)
                        if st.form_submit_button("💾 Salvar alterações", width="stretch"):
                            ok = atualizar_fornecedor(f["nome"], {
                                "distribuidora": d, "representante": r, "telefone": t,
                                "whatsapp": w, "email": m, "cnpj": cj, "ativo": at, "observacoes": ob})
                            if ok:
                                st.success("Atualizado.")
                                st.rerun()
                            else:
                                st.error("Não foi possível atualizar (distribuidora já usada?).")
                    conf = st.checkbox("Confirmo a exclusão", key=f"cf_{f['id']}")
                    if st.button("🗑️ Excluir", key=f"del_{f['id']}", disabled=not conf, width="stretch"):
                        excluir_fornecedor(f["nome"])
                        st.success("Removido.")
                        st.rerun()
