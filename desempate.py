import streamlit as st
import pandas as pd

def tratar_empates_interface(df_comparativo):
    """
    Verifica se há empates no DataFrame comparativo, renderiza a interface
    de escolha manual e retorna o DataFrame com o vencedor definido pelo usuário.
    """
    if df_comparativo is None or 'Fornecedor Vencedor' not in df_comparativo.columns:
        return df_comparativo

    # Inicializa session state para escolhas de desempate
    if 'escolhas_desempate' not in st.session_state:
        st.session_state['escolhas_desempate'] = {}

    # Identifica itens com empate
    mask_empate = df_comparativo['Fornecedor Vencedor'].str.startswith('EMPATE', na=False)
    itens_empatados = df_comparativo[mask_empate]

    if not itens_empatados.empty:
        st.warning(f"⚠️ Atenção: Há {len(itens_empatados)} item(ns) com empate de menor preço. Defina o vencedor manualmente abaixo:")
        
        for idx, row in itens_empatados.iterrows():
            med_nome = idx if isinstance(idx, str) else row.get('Medicamento', str(idx))
            texto_empate = row['Fornecedor Vencedor'] # Ex: EMPATE (TESTE / TESTE 02)
            
            # Extrai os nomes dos fornecedores envolvidos no empate
            fornecedores_envolvidos = texto_empate.replace("EMPATE (", "").replace(")", "").split(" / ")
            
            col_info, col_sel = st.columns([2, 1])
            with col_info:
                preco_val = row.get('Menor Preço (R$)', 0.0)
                preco_str = f"R$ {preco_val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                st.markdown(f"**Item:** `{med_nome}` | **Preço Unit.:** {preco_str}")
            with col_sel:
                escolha_atual = st.session_state['escolhas_desempate'].get(med_nome, fornecedores_envolvidos[0])
                vencedor_escolhido = st.selectbox(
                    f"Desempatar: {med_nome[:15]}...",
                    options=fornecedores_envolvidos,
                    index=fornecedores_envolvidos.index(escolha_atual) if escolha_atual in fornecedores_envolvidos else 0,
                    key=f"desempate_mod_{med_nome}"
                )
                st.session_state['escolhas_desempate'][med_nome] = vencedor_escolhido

        # Aplica as escolhas manuais no DataFrame principal
        for med, forn in st.session_state['escolhas_desempate'].items():
            if med in df_comparativo.index:
                df_comparativo.loc[med, 'Fornecedor Vencedor'] = forn

    return df_comparativo
