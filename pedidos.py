import io
import zipfile

import openpyxl
import pandas as pd
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

FONTE = "Arial"
COL_ESCOLHIDO = "Fornecedor Escolhido"


def preparar_pedidos(df_comparativo):
    """
    Separa itens fechados (com fornecedor definido) dos pendentes.
    Usa 'Fornecedor Escolhido' quando existir; senão 'Fornecedor Vencedor'.
    """
    df = df_comparativo.reset_index() if df_comparativo.index.name == "Medicamento" else df_comparativo.copy()
    coluna = COL_ESCOLHIDO if COL_ESCOLHIDO in df.columns else "Fornecedor Vencedor"
    df["_forn"] = df[coluna].astype(str)

    pendente = (
        df["_forn"].str.startswith("EMPATE", na=False)
        | df["_forn"].isin(["Nenhum", "nan", "None", ""])
        | df["Menor Preço (R$)"].isna()
    )
    if "Qtd" not in df.columns:
        df["Qtd"] = 1
    if "Subtotal Otimizado (R$)" not in df.columns:
        df["Subtotal Otimizado (R$)"] = df["Menor Preço (R$)"] * df["Qtd"]
    return df[~pendente].copy(), df[pendente].copy()


def gerar_zip_pedidos(df_comparativo):
    """Um .xlsx de pedido por fornecedor: Medicamento, Quantidade, Valor, Subtotal, Total."""
    buffer_zip = io.BytesIO()
    df_fechados, _ = preparar_pedidos(df_comparativo)

    fill_header = PatternFill("solid", fgColor="1F4E78")
    font_header = Font(name=FONTE, size=11, bold=True, color="FFFFFF")
    borda = Border(*[Side(style="thin", color="D9D9D9")] * 4)

    with zipfile.ZipFile(buffer_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for forn, itens in df_fechados.groupby("_forn"):
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Pedido"

            ws["A1"] = f"PEDIDO DE COMPRA — {str(forn).upper()}"
            ws["A1"].font = Font(name=FONTE, size=14, bold=True, color="1F4E78")

            headers = ["Medicamento", "Quantidade", "Valor (R$)", "Subtotal (R$)"]
            for col, titulo in enumerate(headers, 1):
                c = ws.cell(row=3, column=col, value=titulo)
                c.fill = fill_header
                c.font = font_header
                c.alignment = Alignment(horizontal="center", vertical="center")

            primeira = 4
            for i, (_, row) in enumerate(itens.iterrows(), start=1):
                r = i + 3
                qtd = int(row.get("Qtd", 1) or 1)
                preco = float(row["Menor Preço (R$)"])

                ws.cell(row=r, column=1, value=str(row["Medicamento"]))
                ws.cell(row=r, column=2, value=qtd).alignment = Alignment(horizontal="center")
                cp = ws.cell(row=r, column=3, value=preco)
                cp.number_format = "R$ #,##0.00"
                cs = ws.cell(row=r, column=4, value=f"=B{r}*C{r}")
                cs.number_format = "R$ #,##0.00"
                for col in range(1, 5):
                    cel = ws.cell(row=r, column=col)
                    cel.border = borda
                    if cel.font.name != FONTE:
                        cel.font = Font(name=FONTE, size=10)

            ultima = len(itens) + 3
            r_total = ultima + 1
            lbl = ws.cell(row=r_total, column=3, value="TOTAL:")
            lbl.font = Font(name=FONTE, size=11, bold=True)
            lbl.alignment = Alignment(horizontal="right")
            tot = ws.cell(row=r_total, column=4, value=f"=SUM(D{primeira}:D{ultima})")
            tot.font = Font(name=FONTE, size=11, bold=True, color="1F4E78")
            tot.number_format = "R$ #,##0.00"

            ws.column_dimensions["A"].width = 52
            ws.column_dimensions["B"].width = 12
            ws.column_dimensions["C"].width = 16
            ws.column_dimensions["D"].width = 16

            buf = io.BytesIO()
            wb.save(buf)
            zf.writestr(f"Pedido_Compra_{str(forn).replace(' ', '_')}.xlsx", buf.getvalue())

    buffer_zip.seek(0)
    return buffer_zip
