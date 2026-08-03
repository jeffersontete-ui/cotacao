import io
import zipfile

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side


def gerar_zip_pedidos(df_comparativo):
    """
    Recebe o DataFrame do mapa comparativo e gera um arquivo ZIP
    contendo as planilhas de pedido de compra para cada fornecedor vencedor.
    """
    buffer_zip = io.BytesIO()

    if df_comparativo.index.name == 'Medicamento':
        df_reset = df_comparativo.reset_index()
    else:
        df_reset = df_comparativo.copy()

    df_vencedores = df_reset[
        ['Medicamento', 'Menor Preço (R$)', 'Fornecedor Vencedor']
    ].dropna(subset=['Fornecedor Vencedor'])
    grupos_fornecedores = df_vencedores.groupby('Fornecedor Vencedor')

    with zipfile.ZipFile(buffer_zip, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for forn_vencedor, df_itens in grupos_fornecedores:
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Pedido de Compra"

            fill_header = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
            font_header = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
            border_thin = Border(
                left=Side(style='thin', color='D9D9D9'),
                right=Side(style='thin', color='D9D9D9'),
                top=Side(style='thin', color='D9D9D9'),
                bottom=Side(style='thin', color='D9D9D9')
            )

            ws['A1'] = f"PEDIDO DE COMPRA - FORNECEDOR: {str(forn_vencedor).upper()}"
            ws['A1'].font = Font(name="Calibri", size=14, bold=True, color="1F4E78")

            headers = ["Item", "Descrição do Medicamento", "Preço Unitário (R$)"]
            ws.append([])
            ws.append(headers)

            for col_num, header in enumerate(headers, 1):
                cell = ws.cell(row=3, column=col_num)
                cell.fill = fill_header
                cell.font = font_header
                cell.alignment = Alignment(horizontal="center", vertical="center")

            total_pedido = 0.0

            for idx, (_, row) in enumerate(df_itens.iterrows(), start=1):
                row_idx = idx + 3
                med = row['Medicamento']
                preco = float(row['Menor Preço (R$)'])
                total_pedido += preco

                c1 = ws.cell(row=row_idx, column=1, value=idx)
                c2 = ws.cell(row=row_idx, column=2, value=med)
                c3 = ws.cell(row=row_idx, column=3, value=preco)

                c1.alignment = Alignment(horizontal="center")
                c2.alignment = Alignment(horizontal="left")
                c3.alignment = Alignment(horizontal="right")
                c3.number_format = 'R$ #,##0.00'

                for c in (c1, c2, c3):
                    c.border = border_thin

            last_row = len(df_itens) + 4
            cell_lbl = ws.cell(row=last_row, column=2, value="TOTAL DO PEDIDO:")
            cell_lbl.font = Font(name="Calibri", size=11, bold=True)
            cell_lbl.alignment = Alignment(horizontal="right")

            cell_tot = ws.cell(row=last_row, column=3, value=total_pedido)
            cell_tot.font = Font(name="Calibri", size=11, bold=True, color="1F4E78")
            cell_tot.number_format = 'R$ #,##0.00'
            cell_tot.alignment = Alignment(horizontal="right")

            ws.column_dimensions['A'].width = 10
            ws.column_dimensions['B'].width = 50
            ws.column_dimensions['C'].width = 25

            excel_buffer = io.BytesIO()
            wb.save(excel_buffer)
            excel_buffer.seek(0)

            nome_arq = f"Pedido_Compra_{str(forn_vencedor).replace(' ', '_')}.xlsx"
            zip_file.writestr(nome_arq, excel_buffer.getvalue())

    buffer_zip.seek(0)
    return buffer_zip
