import pandas as pd

from leitor_excel import colunas_de_fornecedores


def _forn_final(row):
    """Fornecedor que efetivamente leva o item (usa a escolha do desempate)."""
    for chave in ("Fornecedor Escolhido", "Fornecedor Vencedor"):
        val = str(row.get(chave, "")).strip()
        if val and not val.startswith("EMPATE") and val not in ("Nenhum", "nan", ""):
            return val
    return None


def calcular_dashboard(df):
    """
    Retorna um dicionário com todos os números do painel:
      total_otimizado, total_caro, economia, economia_pct,
      itens, itens_decididos, itens_pendentes, itens_sem_preco,
      por_fornecedor (DataFrame), ranking (DataFrame).
    """
    vazio = {
        "total_otimizado": 0.0, "total_caro": 0.0, "economia": 0.0, "economia_pct": 0.0,
        "itens": 0, "itens_decididos": 0, "itens_pendentes": 0, "itens_sem_preco": 0,
        "por_fornecedor": pd.DataFrame(), "ranking": pd.DataFrame(),
    }
    if df is None or df.empty:
        return vazio

    cols_forn = colunas_de_fornecedores(df)
    total_otimizado = 0.0
    total_caro = 0.0
    itens_decididos = itens_pendentes = itens_sem_preco = 0
    gasto_por_forn = {c: 0.0 for c in cols_forn}
    itens_por_forn = {c: 0 for c in cols_forn}

    for _, row in df.iterrows():
        qtd = int(row.get("Qtd", 1) or 1)
        menor = row.get("Menor Preço (R$)")

        precos_linha = []
        for c in cols_forn:
            v = row.get(c)
            if v is not None and not pd.isna(v):
                try:
                    precos_linha.append(float(v))
                except (TypeError, ValueError):
                    pass

        if not precos_linha or menor is None or pd.isna(menor):
            itens_sem_preco += 1
            continue

        # Pior cenário: comprar tudo do fornecedor mais caro de cada item.
        total_caro += max(precos_linha) * qtd
        total_otimizado += float(menor) * qtd

        forn = _forn_final(row)
        if forn and forn in gasto_por_forn:
            gasto_por_forn[forn] += float(menor) * qtd
            itens_por_forn[forn] += 1
            itens_decididos += 1
        else:
            itens_pendentes += 1

    economia = total_caro - total_otimizado
    economia_pct = (economia / total_caro * 100) if total_caro > 0 else 0.0

    por_forn = pd.DataFrame({
        "Fornecedor": list(gasto_por_forn.keys()),
        "Itens ganhos": [itens_por_forn[c] for c in gasto_por_forn],
        "Valor (R$)": [round(gasto_por_forn[c], 2) for c in gasto_por_forn],
    })
    ranking = (por_forn[por_forn["Valor (R$)"] > 0]
               .sort_values("Valor (R$)", ascending=False)
               .reset_index(drop=True))
    ranking.index = ranking.index + 1

    return {
        "total_otimizado": round(total_otimizado, 2),
        "total_caro": round(total_caro, 2),
        "economia": round(economia, 2),
        "economia_pct": round(economia_pct, 1),
        "itens": len(df),
        "itens_decididos": itens_decididos,
        "itens_pendentes": itens_pendentes,
        "itens_sem_preco": itens_sem_preco,
        "por_fornecedor": por_forn,
        "ranking": ranking,
    }
