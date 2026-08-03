import pandas as pd


def processar_comparativo(arquivos_enviados):
    """
    Recebe a lista de arquivos .xlsx enviados pelos fornecedores,
    consolida os preços em uma tabela e identifica o menor valor e vencedor por item.
    """
    if not arquivos_enviados:
        return None

    dados_combinados = {}
    
    for arquivo in arquivos_enviados:
        try:
            # Obtém o nome do fornecedor a partir do nome do arquivo (ex: Cotacao_DistribuidoraA.xlsx)
            nome_fornecedor = arquivo.name.replace("Cotacao_", "").replace(".xlsx", "").replace("_", " ").strip()
            
            df = pd.read_excel(arquivo)
            
            # Padroniza nomes das colunas
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

    # Monta DataFrame consolidado
    df_resultado = pd.DataFrame.from_dict(dados_combinados, orient='index')
    df_resultado.index.name = "Medicamento"
    
    # Identifica o menor preço e o fornecedor vencedor por linha
    fornecedores_cols = list(df_resultado.columns)
    
    df_resultado['Menor Preço (R$)'] = df_resultado[fornecedores_cols].min(axis=1)
    df_resultado['Fornecedor Vencedor'] = df_resultado[fornecedores_cols].idxmin(axis=1)
    
    return df_resultado
import pandas as pd
import openpyxl
import streamlit as st


def processar_comparativo(arquivos_carregados):
    """
    Lê os arquivos Excel enviados pelos fornecedores e retorna
    uma DataFrame pivoteada com a comparação de preços.
    """
    dados = []

    for arq in arquivos_carregados:
        try:
            # 1. Abre com openpyxl para ler o nome do fornecedor no cabeçalho (célula A1)
            wb = openpyxl.load_workbook(arq, data_only=True)
            ws = wb.active

            titulo_a1 = str(ws['A1'].value or '')
            if "FORNECEDOR:" in titulo_a1:
                nome_fornecedor = titulo_a1.split("FORNECEDOR:")[-1].strip()
            else:
                nome_fornecedor = arq.name.replace(".xlsx", "").replace("Cotacao_", "").replace("_", " ")

            # 2. Lê os dados com Pandas pulando as 2 primeiras linhas do cabeçalho
            arq.seek(0)
            df = pd.read_excel(arq, skiprows=2)
            df.columns = [str(c).strip() for c in df.columns]

            # Localiza colunas automaticamente
            col_med = [c for c in df.columns if "Descrição" in c or "Medicamento" in c][0]
            col_prc = [c for c in df.columns if "Preço" in c or "Unitário" in c][0]

            df_temp = df[[col_med, col_prc]].copy()
            df_temp.columns = ['Medicamento', 'Preço Unitário']
            df_temp['Fornecedor'] = nome_fornecedor

            # Formata o preço para número booleano/float
            df_temp['Preço Unitário'] = pd.to_numeric(df_temp['Preço Unitário'], errors='coerce')
            df_temp = df_temp.dropna(subset=['Medicamento'])

            dados.append(df_temp)
        except Exception as e:
            st.error(f"Erro ao processar o arquivo {arq.name}: {e}")

    if not dados:
        return None

    # Unifica todas as tabelas lidas
    df_todos = pd.concat(dados, ignore_index=True)

    # Monta a matriz comparativa
    matriz = df_todos.pivot_table(
        index='Medicamento',
        columns='Fornecedor',
        values='Preço Unitário',
        aggfunc='first'
    )

    # Descobre o menor preço e quem ganhou por linha
    matriz['Menor Preço (R$)'] = matriz.min(axis=1)
    matriz['Fornecedor Vencedor'] = matriz.drop(columns=['Menor Preço (R$)']).idxmin(axis=1)

    return matriz
