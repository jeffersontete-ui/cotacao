import pandas as pd

def aplicar_fornecedor_escolhido(df_comparativo, cols_fornecedores):
    """
    Garante que, para cada item, apenas o fornecedor escolhido mantenha o preço,
    os concorrentes fiquem zerados, e o Subtotal Otimizado seja recalculado com precisão.
    """
    if df_comparativo is None or df_comparativo.empty:
        return df_comparativo

    df_final = df_comparativo.copy()

    # Se a coluna de escolha não existir ainda, inicia com o vencedor padrão
    if "Fornecedor Escolhido" not in df_final.columns:
        df_final["Fornecedor Escolhido"] = df_final["Fornecedor Vencedor"]

    # 1. Zera o preço dos concorrentes e mantém apenas do escolhido
    for med, linha in df_final.iterrows():
        vencedor_final = str(linha.get("Fornecedor Escolhido", ""))
        preco_menor = linha.get("Menor Preço (R$)", 0.0)

        # Ignora se for um empate genérico pendente de escolha
        if vencedor_final and not vencedor_final.startswith("EMPATE"):
            for col in cols_fornecedores:
                if col in df_final.columns:
                    if col != vencedor_final:
                        df_final.loc[med, col] = 0.0
                    else:
                        val_atual = df_final.loc[med, col]
                        if pd.isna(val_atual) or val_atual == 0:
                            df_final.loc[med, col] = preco_menor

    # 2. Recalcula o Subtotal Otimizado baseado no fornecedor escolhido x quantidade
    if "Qtd" in df_final.columns:
        subtotais = []
        for med, linha in df_final.iterrows():
            vencedor_final = str(linha.get("Fornecedor Escolhido", ""))
            qtd = linha.get("Qtd", 1)
            
            if vencedor_final in cols_fornecedores:
                preco_unit = linha.get(vencedor_final, 0.0)
                subtotais.append((preco_unit if pd.notna(preco_unit) else 0.0) * qtd)
            else:
                subtotais.append(0.0)
        
        df_final["Subtotal Otimizado (R$)"] = subtotais

    return df_final
