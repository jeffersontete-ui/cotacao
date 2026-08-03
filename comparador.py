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
