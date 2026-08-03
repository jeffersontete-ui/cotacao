import pandas as pd


def limpar_valor_monetario(val):
    """Converte valores para float mesmo que venham como 'R$ 3,00', '3.00' ou 1.000,00."""
    if pd.isna(val):
        return None
    if isinstance(val, (int, float)):
        return float(val)

    val_str = str(val).upper().replace("R$", "").replace(" ", "").strip()
    if not val_str:
        return None

    # Trata padrão brasileiro (1.000,00) e também o americano (1,000.00)
    if "," in val_str and "." in val_str:
        if val_str.rfind(",") > val_str.rfind("."):
            val_str = val_str.replace(".", "").replace(",", ".")
        else:
            val_str = val_str.replace(",", "")
    elif "," in val_str:
        val_str = val_str.replace(",", ".")

    try:
        return float(val_str)
    except ValueError:
        return None


def identificar_vencedor(row, cols_fornecedores):
    """Retorna o fornecedor com menor preço, ou EMPATE quando há mais de um."""
    menor_valor = row.get('Menor Preço (R$)')
    if menor_valor is None or pd.isna(menor_valor):
        return "Nenhum"

    vencedores = []
    for col in cols_fornecedores:
        val = row.get(col)
        if val is None or pd.isna(val):
            continue
        try:
            if abs(float(val) - float(menor_valor)) < 0.001:
                vencedores.append(col)
        except (TypeError, ValueError):
            continue

    if len(vencedores) > 1:
        return f"EMPATE ({' / '.join(vencedores)})"
    if len(vencedores) == 1:
        return vencedores[0]
    return "Nenhum"


def processar_comparativo(arquivos_enviados):
    """Lê as planilhas devolvidas pelos fornecedores e monta o mapa comparativo."""
    if not arquivos_enviados:
        return None

    dados_medicamentos = {}
    quantidades = {}

    for arquivo in arquivos_enviados:
        try:
            nome_fornecedor = (
                arquivo.name
                .replace("Cotacao_", "")
                .replace(".xlsx", "")
                .replace(".xls", "")
                .replace("_", " ")
                .strip()
            )

            # A planilha gerada tem título na linha 1 e cabeçalho na linha 3
            df = pd.read_excel(arquivo, header=2)

            col_map = {str(c).strip().lower(): c for c in df.columns}

            col_med_orig = next(
                (v for k, v in col_map.items()
                 if any(x in k for x in ['medicamento', 'descri', 'produto'])),
                None,
            )
            col_preco_orig = next(
                (v for k, v in col_map.items()
                 if any(x in k for x in ['preço', 'preco', 'valor', 'unitario', 'unitário'])),
                None,
            )
            col_qtd_orig = next(
                (v for k, v in col_map.items()
                 if any(x in k for x in ['qtd', 'quant'])),
                None,
            )

            if not (col_med_orig and col_preco_orig):
                continue

            for _, row in df.iterrows():
                med = str(row[col_med_orig]).strip().upper()
                if not med or med == 'NAN':
                    continue

                preco = limpar_valor_monetario(row[col_preco_orig])

                dados_medicamentos.setdefault(med, {})
                dados_medicamentos[med][nome_fornecedor] = preco

                if col_qtd_orig is not None and not pd.isna(row[col_qtd_orig]):
                    try:
                        quantidades[med] = int(row[col_qtd_orig])
                    except (TypeError, ValueError):
                        quantidades[med] = 1
                elif med not in quantidades:
                    quantidades[med] = 1

        except Exception:
            continue

    if not dados_medicamentos:
        return None

    df_resultado = pd.DataFrame.from_dict(dados_medicamentos, orient='index')
    df_resultado.index.name = "Medicamento"

    cols_fornecedores = list(df_resultado.columns)

    df_resultado['Menor Preço (R$)'] = df_resultado[cols_fornecedores].min(axis=1)

    df_resultado['Fornecedor Vencedor'] = df_resultado.apply(
        lambda row: identificar_vencedor(row, cols_fornecedores), axis=1
    )

    df_resultado['Qtd'] = [quantidades.get(m, 1) for m in df_resultado.index]
    df_resultado['Subtotal Otimizado (R$)'] = (
        df_resultado['Menor Preço (R$)'] * df_resultado['Qtd']
    )

    cols_finais = (
        ['Qtd'] + cols_fornecedores
        + ['Menor Preço (R$)', 'Subtotal Otimizado (R$)', 'Fornecedor Vencedor']
    )
    return df_resultado[cols_finais]
