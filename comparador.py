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
        import pandas as pd
        import re


        def limpar_valor_monetario(val):
            """ Converte valores para float mesmo que venham como string ex: 'R$ 3,00' ou '3.00' """
            if pd.isna(val):
                return None
            if isinstance(val, (int, float)):
                return float(val)
    
            # Se for string, remove R$, espaços e converte vírgula para ponto
            val_str = str(val).upper().replace("R$", "").replace(" ", "").strip()
            val_str = val_str.replace(".", "").replace(",", ".") # Trata padrão brasileiro 1.000,00
    
            try:
                return float(val_str)
            except ValueError:
                return None


        def identificar_vencedor(row, cols_fornecedores):
            menor_valor = row['Menor Preço (R$)']
            if pd.isna(menor_valor) or menor_valor is None:
                return "Nenhum"
    
            # Procura quais fornecedores empataram no menor valor
            vencedores = []
            for col in cols_fornecedores:
                val = row.get(col)
                if val is not None and not pd.isna(val):
                    try:
                        if abs(float(val) - float(menor_valor)) < 0.001:
                            vencedores.append(col)
                    except Exception:
                        continue
    
            if len(vencedores) > 1:
                return f"EMPATE ({' / '.join(vencedores)})"
            elif len(vencedores) == 1:
                return vencedores[0]
            return "Nenhum"


        def processar_comparativo(arquivos_enviados):
            if not arquivos_enviados:
                return None

            dados_medicamentos = {}
            quantidades = {}

            for arquivo in arquivos_enviados:
                try:
                    # Nome limpo do fornecedor extraído do arquivo
                    nome_fornecedor = arquivo.name.replace("Cotacao_", "").replace(".xlsx", "").replace(".xls", "").replace("_", " ").strip()
            
                    df = pd.read_excel(arquivo)
            
                    # Normaliza os nomes das colunas para busca sem case/acentos
                    col_map = {str(c).strip().lower(): c for c in df.columns}
            
                    # Identifica colunas flexíveis
                    col_med_orig = next((v for k, v in col_map.items() if any(x in k for x in ['medicamento', 'descri', 'item', 'produto'])), None)
                    col_preco_orig = next((v for k, v in col_map.items() if any(x in k for x in ['preço', 'preco', 'valor', 'unitario', 'unitário'])), None)
                    col_qtd_orig = next((v for k, v in col_map.items() if any(x in k for x in ['qtd', 'quant', 'quantidade'])), None)
            
                    if col_med_orig and col_preco_orig:
                        for _, row in df.iterrows():
                            med = str(row[col_med_orig]).strip().upper()
                            if not med or med == 'NAN':
                                continue
                        
                            preco = limpar_valor_monetario(row[col_preco_orig])
                    
                            if med not in dados_medicamentos:
                                dados_medicamentos[med] = {}
                        
                            dados_medicamentos[med][nome_fornecedor] = preco
                    
                            # Guarda a quantidade se existir na planilha
                            if col_qtd_orig and not pd.isna(row[col_qtd_orig]):
                                try:
                                    quantidades[med] = int(row[col_qtd_orig])
                                except Exception:
                                    quantidades[med] = 1
                            elif med not in quantidades:
                                quantidades[med] = 1

                except Exception:
                    continue

            if not dados_medicamentos:
                return None

            # Monta Tabela Comparativa
            df_resultado = pd.DataFrame.from_dict(dados_medicamentos, orient='index')
            df_resultado.index.name = "Medicamento"
    
            cols_fornecedores = list(df_resultado.columns)
    
            # 1. Menor preço unitário
            df_resultado['Menor Preço (R$)'] = df_resultado[cols_fornecedores].min(axis=1)
    
            # 2. Identifica Fornecedor Vencedor ou EMPATE
            df_resultado['Fornecedor Vencedor'] = df_resultado.apply(
                lambda row: identificar_vencedor(row, cols_fornecedores), axis=1
            )
    
            # 3. Adiciona Quantidade e Custo Total do Item se disponível
            df_resultado['Qtd'] = [quantidades.get(m, 1) for m in df_resultado.index]
            df_resultado['Subtotal Otimizado (R$)'] = df_resultado['Menor Preço (R$)'] * df_resultado['Qtd']
    
            # Reorganiza colunas
            cols_finais = ['Qtd'] + cols_fornecedores + ['Menor Preço (R$)', 'Subtotal Otimizado (R$)', 'Fornecedor Vencedor']
            return df_resultado[cols_finais]
