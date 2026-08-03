import io
import zipfile

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Protection, Side

# Coluna técnica, oculta e protegida, usada só pelo sistema.
# Z1 = distribuidora | Z2 = id da cotação | Z(linha) = quantidade daquele item.
COL_META = "Z"
SENHA_PROTECAO = "cotacao"
FONTE = "Arial"


def gerar_zip_cotacoes(itens, fornecedores_selecionados, cotacao_id=None):
    """
    Gera um .xlsx por fornecedor, todos dentro de um .zip.

    O fornecedor vê SOMENTE duas colunas: Medicamento e Valor (R$).
    Quantidade e identificação viajam na coluna oculta Z e voltam no arquivo.
    """
    itens_norm = _normalizar_itens(itens)
    buffer_zip = io.BytesIO()

    with zipfile.ZipFile(buffer_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for forn in fornecedores_selecionados:
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Cotação"

            fill_header = PatternFill("solid", fgColor="1F4E78")
            font_header = Font(name=FONTE, size=11, bold=True, color="FFFFFF")
            fill_input = PatternFill("solid", fgColor="FFF9DB")
            borda = Border(*[Side(style="thin", color="D9D9D9")] * 4)

            ws["A1"] = f"COTAÇÃO DE PREÇOS — {str(forn).upper()}"
            ws["A1"].font = Font(name=FONTE, size=14, bold=True, color="1F4E78")
            ws["A2"] = ("Preencha somente a coluna Valor (R$), destacada em amarelo. "
                        "Não altere nem reordene as linhas — devolva o arquivo assim mesmo.")
            ws["A2"].font = Font(name=FONTE, size=9, italic=True, color="808080")

            for col_num, titulo in enumerate(["Medicamento", "Valor (R$)"], 1):
                c = ws.cell(row=3, column=col_num, value=titulo)
                c.fill = fill_header
                c.font = font_header
                c.alignment = Alignment(horizontal="center", vertical="center")
                c.protection = Protection(locked=True)

            for idx, item in enumerate(itens_norm, start=1):
                r = idx + 3
                c_med = ws.cell(row=r, column=1, value=item["medicamento"])
                c_val = ws.cell(row=r, column=2, value=None)

                c_med.alignment = Alignment(horizontal="left")
                c_med.protection = Protection(locked=True)
                c_val.alignment = Alignment(horizontal="right")
                c_val.number_format = "R$ #,##0.00"
                c_val.fill = fill_input
                c_val.protection = Protection(locked=False)

                for c in (c_med, c_val):
                    c.font = Font(name=FONTE, size=10)
                    c.border = borda

                ws[f"{COL_META}{r}"] = int(item["qtd"])  # quantidade oculta

            ws[f"{COL_META}1"] = str(forn)
            ws[f"{COL_META}2"] = "" if cotacao_id is None else str(cotacao_id)

            ws.column_dimensions["A"].width = 55
            ws.column_dimensions["B"].width = 18
            ws.column_dimensions[COL_META].hidden = True

            ws.protection.set_password(SENHA_PROTECAO)
            ws.protection.sheet = True

            buf = io.BytesIO()
            wb.save(buf)
            zf.writestr(f"Cotacao_{str(forn).replace(' ', '_')}.xlsx", buf.getvalue())

    buffer_zip.seek(0)
    return buffer_zip


def _normalizar_itens(itens):
    out = []
    for item in itens:
        if isinstance(item, dict):
            med = str(item.get("medicamento", "")).strip()
            try:
                qtd = max(1, int(item.get("qtd", 1)))
            except (TypeError, ValueError):
                qtd = 1
        else:
            med, qtd = str(item).strip(), 1
        if med:
            out.append({"medicamento": med, "qtd": qtd})
    return out
