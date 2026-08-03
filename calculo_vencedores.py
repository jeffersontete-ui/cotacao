import pandas as pd

def aplicar_fornecedor_escolhido(df_comparativo, cols_fornecedores):
    """
    Garante que, para cada item, apenas o fornecedor vencedor/escolhido mantenha o preço,
    enquanto todos os concorrentes perdedores fiquem zerados (0.0), recalculando o subtotal.
    """
    if df_comparativo is None or df_comparativo.empty:
        return df_comparativo

    df_final = df_comparativo.copy()

    # Identifica a coluna de escolha do vencedor
    coluna_escolha = "Fornecedor Escolhido" if "Fornecedor Escolhido" in df_final.columns else "Fornecedor Vencedor"

    for med, linha in df_final.iterrows():
        vencedor_final = str(linha.get(coluna_escolha, ""))
        
        # Se for um empate bruto pendente de escolha na interface, pula o zeramento individual temporário
        if not vencedor_final or vencedor_final.startswith("EMPATE"):
            continue

        # Zera os concorrentes e valida o preço do vencedor
        for col in cols_fornecedores:
            if col in df_final.columns:
                if col != vencedor_final:
                    df_final.loc[med, col] = 0.0
                else:
                    # Se o valor do vencedor estiver vazio ou zero, recupera do menor preço
                    val_atual = df_final.loc[med, col]
                    if pd.isna(val_atual) or val_atual == 0:
                        df_final.loc[med, col] = linha.get("Menor Preço (R$)", 0.0)

    # Recalcula o Subtotal Otimizado estritamente baseado no fornecedor escolhido x quantidade
    if "Qtd" in df_final.columns:
        subtotais = []
        for med, linha in df_final.iterrows():
            vencedor_final = str(linha.get(coluna_escolha, ""))
            qtd = linha.get("Qtd", 1)
            
            if vencedor_final in cols_fornecedores:
                preco_unit = linha.get(vencedor_final, 0.0)
                subtotais.append((preco_unit if pd.notna(preco_unit) else 0.0) * qtd)
            else:
                subtotais.append(0.0)
        
        df_final["Subtotal Otimizado (R$)"] = subtotais

    return df_final
