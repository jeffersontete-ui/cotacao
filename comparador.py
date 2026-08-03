import pandas as pd


def identificar_vencedor(row, cols_fornecedores):
    menor_valor = row['Menor Preço (R$)']
    if pd.isna(menor_valor):
        return "Nenhum"
    
    # Encontra todos os fornecedores que oferecem o menor preço exatamente
    vencedores = [col for col in cols_fornecedores if row.get(col) == menor_valor]
    
    if len(vencedores) > 1:
        return f"EMPATE ({' / '.join(vencedores)})"
    elif len(vencedores) == 1:
        return vencedores[0]
    return "Nenhum"


def processar_comparativo(arquivos_enviados):
    if not arquivos_enviados:
        return None

    dados_combinados = {}
    
    for arquivo in arquivos_enviados:
        try:
            # Extrai nome do fornecedor do arquivo
            nome_fornecedor = arquivo.name.replace("Cotacao_", "").replace(".xlsx", "").replace("_", " ").strip()
            
            df = pd.read_excel(arquivo)
            df.columns = [str(c).strip().title() for c in df.columns]
            
            col_med = next((c for c in df.columns if 'Medicamento' in c or 'Descrição' in c or 'Item' in c), None)
            col_preco = next((c for c in df.columns if 'Preço' in c or 'Preco' in c or 'Valor' in c), None)
            
            if col_med and col_preco:
                for _, row in df.iterrows():
                    med = str(row[col_med]).strip().upper()
                    try:
                        preco = float(row[col_preco])
                    except (ValueError, TypeError):
                        preco = None
                        
                    if med not in dados_combinados:
                        dados_combinados[med] = {}
                        
                    dados_combinados[med][nome_fornecedor] = preco
        except Exception:
            continue

    if not dados_combinados:
        return None

    df_resultado = pd.DataFrame.from_dict(dados_combinados, orient='index')
    df_resultado.index.name = "Medicamento"
    
    cols_fornecedores = list(df_resultado.columns)
    
    # Calcula Menor Preço
    df_resultado['Menor Preço (R$)'] = df_resultado[cols_fornecedores].min(axis=1)
    
    # Identifica Vencedor (com suporte a Empate)
    df_resultado['Fornecedor Vencedor'] = df_resultado.apply(
        lambda row: identificar_vencedor(row, cols_fornecedores), axis=1
    )
    
    return df_resultado
