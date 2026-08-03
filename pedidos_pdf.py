import io
import zipfile
from datetime import datetime

from fpdf import FPDF

from database import carregar_fornecedores
from pedidos import preparar_pedidos

# Larguras (mm) — soma 190
W_ITEM, W_DESC, W_QTD, W_UNIT, W_TOTAL = 10, 100, 18, 31, 31
MARGEM_INF = 22


def brl(v):
    return f"{v:,.2f}".replace(",", "@").replace(".", ",").replace("@", ".")


def _lat(s):
    return str(s).encode("latin-1", "replace").decode("latin-1")


class PDFPedido(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 14)
        self.set_text_color(31, 78, 120)
        self.cell(0, 8, "PEDIDO DE COMPRA", new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "", 9)
        self.set_text_color(100, 100, 100)
        self.cell(0, 5, "Sistema Integrado de Cotacoes", new_x="LMARGIN", new_y="NEXT")
        self.ln(2)
        self.set_draw_color(31, 78, 120)
        self.set_line_width(0.6)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f"Gerado em {datetime.now():%d/%m/%Y %H:%M}  -  Pagina {self.page_no()}",
                  align="C")


def _quebrar(pdf, texto, larg, max_linhas=3):
    palavras = _lat(texto).split()
    linhas, atual = [], ""
    for p in palavras:
        teste = f"{atual} {p}".strip()
        if pdf.get_string_width(teste) <= larg - 2:
            atual = teste
        else:
            if atual:
                linhas.append(atual)
            atual = p
    if atual:
        linhas.append(atual)
    return linhas[:max_linhas] or [""]


def _cab_tabela(pdf):
    pdf.set_fill_color(31, 78, 120)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(W_ITEM, 7, "#", align="C", fill=True)
    pdf.cell(W_DESC, 7, "Medicamento", fill=True)
    pdf.cell(W_QTD, 7, "Qtd", align="C", fill=True)
    pdf.cell(W_UNIT, 7, "Valor (R$)", align="R", fill=True)
    pdf.cell(W_TOTAL, 7, "Subtotal (R$)", align="R", fill=True)
    pdf.ln()
    pdf.set_text_color(50, 50, 50)
    pdf.set_font("Helvetica", "", 8)


def _bloco_forn(pdf, nome, info):
    pdf.set_fill_color(245, 247, 250)
    pdf.rect(10, pdf.get_y(), 190, 22, style="F")
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(40, 40, 40)
    y = pdf.get_y() + 3
    pdf.set_xy(12, y)
    pdf.cell(92, 5, _lat(f"Fornecedor: {nome}"))
    pdf.cell(92, 5, _lat(f"CNPJ: {info.get('cnpj') or 'N/A'}"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(12)
    pdf.cell(92, 5, _lat(f"Representante: {info.get('representante') or 'N/A'}"))
    tel = info.get("telefone") or info.get("whatsapp") or "N/A"
    pdf.cell(92, 5, _lat(f"Telefone: {tel}"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(12)
    pdf.cell(184, 5, _lat(f"E-mail: {info.get('email') or 'N/A'}"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)


def gerar_zip_pedidos_pdf(df_comparativo):
    buffer_zip = io.BytesIO()
    fornecedores = {str(f["nome"]).lower().strip(): f for f in carregar_fornecedores()}
    df_fechados, df_pendentes = preparar_pedidos(df_comparativo)

    with zipfile.ZipFile(buffer_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for forn, itens in df_fechados.groupby("_forn"):
            info = fornecedores.get(str(forn).lower().strip(), {})
            pdf = PDFPedido()
            pdf.set_auto_page_break(auto=False)
            pdf.add_page()
            _bloco_forn(pdf, forn, info)
            _cab_tabela(pdf)

            total = 0.0
            for idx, (_, row) in enumerate(itens.iterrows(), start=1):
                qtd = int(row.get("Qtd", 1) or 1)
                preco = float(row["Menor Preço (R$)"])
                sub = float(row.get("Subtotal Otimizado (R$)") or preco * qtd)
                total += sub

                linhas = _quebrar(pdf, row["Medicamento"], W_DESC)
                altura = 6 * len(linhas)
                if pdf.get_y() + altura > pdf.h - MARGEM_INF:
                    pdf.add_page()
                    _cab_tabela(pdf)

                y0, x0 = pdf.get_y(), pdf.l_margin
                pdf.cell(W_ITEM, altura, str(idx), align="C")
                for i, ln in enumerate(linhas):
                    pdf.set_xy(x0 + W_ITEM, y0 + i * 6)
                    pdf.cell(W_DESC, 6, ln)
                pdf.set_xy(x0 + W_ITEM + W_DESC, y0)
                pdf.cell(W_QTD, altura, str(qtd), align="C")
                pdf.cell(W_UNIT, altura, brl(preco), align="R")
                pdf.cell(W_TOTAL, altura, brl(sub), align="R")
                pdf.set_xy(x0, y0 + altura)

            if pdf.get_y() > pdf.h - MARGEM_INF - 12:
                pdf.add_page()
            pdf.ln(4)
            pdf.set_font("Helvetica", "B", 11)
            pdf.set_text_color(31, 78, 120)
            pdf.cell(0, 8, _lat(f"TOTAL DO PEDIDO ({len(itens)} itens): R$ {brl(total)}"),
                     align="R", new_x="LMARGIN", new_y="NEXT")

            zf.writestr(f"Pedido_{str(forn).replace(' ', '_')}.pdf", bytes(pdf.output()))

        if not df_pendentes.empty:
            zf.writestr("ITENS_PENDENTES.pdf", bytes(_pdf_pendentes(df_pendentes).output()))

    buffer_zip.seek(0)
    return buffer_zip


def _cab_pendentes(pdf):
    pdf.set_fill_color(180, 50, 50)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(110, 7, "Medicamento", fill=True)
    pdf.cell(25, 7, "Preco (R$)", align="R", fill=True)
    pdf.cell(55, 7, "Situacao", fill=True)
    pdf.ln()
    pdf.set_text_color(50, 50, 50)
    pdf.set_font("Helvetica", "", 8)


def _pdf_pendentes(df):
    pdf = PDFPedido()
    pdf.set_auto_page_break(auto=False)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(180, 50, 50)
    pdf.cell(0, 8, "ITENS SEM FORNECEDOR DEFINIDO", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(0, 5, "Empates nao resolvidos e itens que ninguem cotou.", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    _cab_pendentes(pdf)

    for _, row in df.iterrows():
        preco = row.get("Menor Preço (R$)")
        preco_fmt = "-" if preco is None or preco != preco else brl(float(preco))
        situacao = str(row["_forn"]).replace("EMPATE (", "Empate: ").replace(")", "")
        linhas = _quebrar(pdf, row["Medicamento"], 110, max_linhas=2)
        altura = 6 * len(linhas)
        if pdf.get_y() + altura > pdf.h - MARGEM_INF:
            pdf.add_page()
            _cab_pendentes(pdf)
        y0, x0 = pdf.get_y(), pdf.l_margin
        for i, ln in enumerate(linhas):
            pdf.set_xy(x0, y0 + i * 6)
            pdf.cell(110, 6, ln)
        pdf.set_xy(x0 + 110, y0)
        pdf.cell(25, altura, preco_fmt, align="R")
        pdf.cell(55, altura, _lat(situacao[:42]))
        pdf.set_xy(x0, y0 + altura)

    return pdf
