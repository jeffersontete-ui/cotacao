import pandas as pd

def aplicar_fornecedor_escolhido(df_comparativo, cols_fornecedores):
    """
    Garante que para cada item, o fornecedor definido em 'Fornecedor Escolhido' 
    mantenha o seu preço e todos os concorrentes sejam zerados (0.0).
    """
    if df_comparativo is None or df_comparativo.empty:
        return df_comparativo

    df_final = df_comparativo.copy()

    # Garante que a coluna de escolha existe
    if "Fornecedor Escolhido" not in df_final.columns:
        df_final["Fornecedor Escolhido"] = df_final["Fornecedor Vencedor"]

    subtotais = []

    for med, linha in df_final.iterrows():
        # Pega especificamente o fornecedor escolhido para ESTE medicamento
        vencedor_final = str(linha.get("Fornecedor Escolhido", ""))
        
        # Se ainda for um empate bruto pendente, mantém os preços originais temporariamente
        if not vencedor_final or vencedor_final.startswith("EMPATE"):
            subtotais.append(0.0)
            continue

        # Zera os concorrentes na linha e mantém apenas o escolhido
        for col in cols_fornecedores:
            if col in df_final.columns:
                if col != vencedor_final:
                    df_final.loc[med, col] = 0.0
                else:
                    # Se o valor do escolhido estiver vazio/zero, usa o menor preço da linha
                    val_atual = df_final.loc[med, col]
                    if pd.isna(val_atual) or val_atual == 0:
                        df_final.loc[med, col] = linha.get("Menor Preço (R$)", 0.0)

        # Calcula o subtotal otimizado individual (Preço Unitário x Quantidade)
        qtd = linha.get("Qtd", 1)
        preco_unit = df_final.loc[med, vencedor_final] if vencedor_final in cols_fornecedores else 0.0
        subtotais.append((preco_unit if pd.notna(preco_unit) else 0.0) * qtd)

    df_final["Subtotal Otimizado (R$)"] = subtotais
    return df_final
