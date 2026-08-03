import io
import zipfile

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Protection, Side


def gerar_zip_cotacoes(medicamentos, fornecedores_selecionados):
    buffer_zip = io.BytesIO()

    with zipfile.ZipFile(buffer_zip, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for forn in fornecedores_selecionados:
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Cotação"

            # ATIVAR PROTEÇÃO DA PLANILHA
            ws.protection.sheet = True

            # Estilos do cabeçalho
            fill_header = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
            font_header = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
            border_thin = Border(
                left=Side(style='thin', color='D9D9D9'),
                right=Side(style='thin', color='D9D9D9'),
                top=Side(style='thin', color='D9D9D9'),
                bottom=Side(style='thin', color='D9D9D9'),
            )

            # Título do Documento
            ws['A1'] = f"COTAÇÃO DE PREÇOS - FORNECEDOR: {forn.upper()}"
            ws['A1'].font = Font(name="Calibri", size=14, bold=True, color="1F4E78")

            # Cabeçalho da Tabela - APENAS 3 COLUNAS
            headers = ["Item", "Descrição do Medicamento", "Preço Unitário (R$)"]
            ws.append([])
            ws.append(headers)

            for col_num, header in enumerate(headers, 1):
                cell = ws.cell(row=3, column=col_num)
                cell.fill = fill_header
                cell.font = font_header
                cell.alignment = Alignment(horizontal="center", vertical="center")
                cell.protection = Protection(locked=True)

            for idx, med in enumerate(medicamentos, start=1):
                row_idx = idx + 3

                c1 = ws.cell(row=row_idx, column=1, value=idx)
                c2 = ws.cell(row=row_idx, column=2, value=med.strip())
                c3 = ws.cell(row=row_idx, column=3, value=None)

                c1.alignment = Alignment(horizontal="center")
                c2.alignment = Alignment(horizontal="left")
                c3.alignment = Alignment(horizontal="right")
                c3.number_format = 'R$ #,##0.00'

                c1.protection = Protection(locked=True)
                c2.protection = Protection(locked=True)
                c3.protection = Protection(locked=False)

                for c in (c1, c2, c3):
                    c.border = border_thin

            ws.column_dimensions['A'].width = 10
            ws.column_dimensions['B'].width = 50
            ws.column_dimensions['C'].width = 25

            excel_buffer = io.BytesIO()
            wb.save(excel_buffer)
            excel_buffer.seek(0)

            nome_arquivo = f"Cotacao_{forn.replace(' ', '_')}.xlsx"
            zip_file.writestr(nome_arquivo, excel_buffer.getvalue())

    buffer_zip.seek(0)
    return buffer_zip
