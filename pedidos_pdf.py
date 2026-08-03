import io
import zipfile
from fpdf import FPDF
from database import carregar_fornecedores


class PDFPedido(FPDF):
    def header(self):
        self.set_font('Helvetica', 'B', 16)
        self.set_text_color(31, 78, 120)
        self.cell(0, 8, 'ORDEM DE PEDIDO DE COMPRA', ln=True)
        self.set_font('Helvetica', '', 9)
        self.set_text_color(100, 100, 100)
        self.cell(0, 5, 'Sistema Integrado de Cotacoes - Farmacia & Saude', ln=True)
        self.ln(3)
        self.set_draw_color(31, 78, 120)
        self.set_line_width(0.8)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(6)

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, 'Este pedido de compra foi gerado automaticamente com base no mapa comparativo.', align='C')


def gerar_zip_pedidos_pdf(df_comparativo):
    """
    Gera um arquivo ZIP com os PDFs dos Pedidos de Compra usando fpdf2.
    """
    buffer_zip = io.BytesIO()

    # Busca contatos dos fornecedores no banco de dados SQLite
    fornecedores_lista = carregar_fornecedores()
    dict_fornecedores = {f['nome'].lower().strip(): f for f in fornecedores_lista}

    if df_comparativo.index.name == 'Medicamento':
        df_reset = df_comparativo.reset_index()
    else:
        df_reset = df_comparativo.copy()
        
    df_vencedores = df_reset[['Medicamento', 'Menor Preço (R$)', 'Fornecedor Vencedor']].dropna(subset=['Fornecedor Vencedor'])

    # Filtra itens sem empate e itens em empate
    df_sem_empate = df_vencedores[~df_vencedores['Fornecedor Vencedor'].str.startswith('EMPATE', na=False)]
    df_empates = df_vencedores[df_vencedores['Fornecedor Vencedor'].str.startswith('EMPATE', na=False)]

    grupos_fornecedores = df_sem_empate.groupby('Fornecedor Vencedor')

    with zipfile.ZipFile(buffer_zip, "w", zipfile.ZIP_DEFLATED) as zip_file:
        # Gera PDF por fornecedor vencedor (sem empates)
        for forn_vencedor, df_itens in grupos_fornecedores:
            info = dict_fornecedores.get(str(forn_vencedor).lower().strip(), {})
            
            vendedor = info.get('vendedor', 'Nao informado')
            telefone = info.get('telefone', 'Nao informado')
            email = info.get('email', 'Nao informado')
            cnpj = info.get('cnpj', 'Nao informado')
            
            pdf = PDFPedido()
            pdf.add_page()
            pdf.set_auto_page_break(auto=True, margin=15)
            
            # Bloco de Informações do Fornecedor
            pdf.set_fill_color(248, 249, 250)
            pdf.rect(10, pdf.get_y(), 190, 24, style='F')
            
            pdf.set_font('Helvetica', 'B', 9)
            pdf.set_text_color(50, 50, 50)
            
            y_curr = pdf.get_y() + 3
            pdf.set_xy(12, y_curr)
            pdf.cell(92, 5, f"Fornecedor: {forn_vencedor}")
            pdf.cell(92, 5, f"CNPJ: {cnpj}", ln=True)
            
            pdf.set_x(12)
            pdf.cell(92, 5, f"Contato/Vendedor: {vendedor}")
            pdf.cell(92, 5, f"Telefone: {telefone}", ln=True)
            
            pdf.set_x(12)
            pdf.cell(92, 5, f"E-mail: {email}")
            pdf.cell(92, 5, "Status: Itens Vencedores (Menor Preco)", ln=True)
            
            pdf.ln(8)
            
            # Cabeçalho da Tabela
            pdf.set_fill_color(31, 78, 120)
            pdf.set_text_color(255, 255, 255)
            pdf.set_font('Helvetica', 'B', 9)
            pdf.cell(15, 7, 'Item', border=0, align='C', fill=True)
            pdf.cell(130, 7, 'Descricao do Medicamento', border=0, fill=True)
            pdf.cell(45, 7, 'Preco Unitario', border=0, align='R', fill=True)
            pdf.ln()
            
            # Linhas dos Itens
            pdf.set_text_color(50, 50, 50)
            pdf.set_font('Helvetica', '', 9)
            
            total_pedido = 0.0
            fill = False
            
            for idx, (_, row) in enumerate(df_itens.iterrows(), start=1):
                med = str(row['Medicamento'])
                preco = float(row['Menor Preço (R$)'])
                total_pedido += preco
                
                if fill:
                    pdf.set_fill_color(245, 245, 245)
                else:
                    pdf.set_fill_color(255, 255, 255)
                preco_fmt = f"R$ {preco:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                
                pdf.cell(15, 6, str(idx), align='C', fill=True)
                pdf.cell(130, 6, med, fill=True)
                pdf.cell(45, 6, preco_fmt, align='R', fill=True)
                pdf.ln()
                fill = not fill
                
            pdf.ln(4)
            pdf.set_font('Helvetica', 'B', 11)
            pdf.set_text_color(31, 78, 120)
            total_fmt = f"R$ {total_pedido:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
            pdf.cell(0, 8, f"VALOR TOTAL DO PEDIDO: {total_fmt}", align='R', ln=True)
            
            nome_pdf = f"Pedido_Compra_{str(forn_vencedor).replace(' ', '_')}.pdf"
            # Use dest='S' to get PDF as bytes from fpdf2
            zip_file.writestr(nome_pdf, pdf.output(dest='S'))

        # Se houver empates, gera um PDF consolidado com os itens empatados
        if not df_empates.empty:
            pdf_emp = PDFPedido()
            pdf_emp.add_page()
            pdf_emp.set_auto_page_break(auto=True, margin=15)

            pdf_emp.set_font('Helvetica', 'B', 12)
            pdf_emp.set_text_color(31, 78, 120)
            pdf_emp.cell(0, 8, 'Itens em Empate', ln=True)
            pdf_emp.ln(6)

            # Cabeçalho
            pdf_emp.set_fill_color(31, 78, 120)
            pdf_emp.set_text_color(255, 255, 255)
            pdf_emp.set_font('Helvetica', 'B', 9)
            pdf_emp.cell(15, 7, 'Item', border=0, align='C', fill=True)
            pdf_emp.cell(110, 7, 'Descricao do Medicamento', border=0, fill=True)
            pdf_emp.cell(35, 7, 'Menor Preco', border=0, align='R', fill=True)
            pdf_emp.cell(30, 7, 'Fornecedores', border=0, align='C', fill=True)
            pdf_emp.ln()

            pdf_emp.set_text_color(50, 50, 50)
            pdf_emp.set_font('Helvetica', '', 9)
            fill = False
            for idx, (_, row) in enumerate(df_empates.iterrows(), start=1):
                med = str(row['Medicamento'])
                preco = float(row['Menor Preço (R$)'])
                fornecedores_text = str(row['Fornecedor Vencedor'])

                if fill:
                    pdf_emp.set_fill_color(245, 245, 245)
                else:
                    pdf_emp.set_fill_color(255, 255, 255)

                preco_fmt = f"R$ {preco:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                pdf_emp.cell(15, 6, str(idx), align='C', fill=True)
                pdf_emp.cell(110, 6, med, fill=True)
                pdf_emp.cell(35, 6, preco_fmt, align='R', fill=True)
                pdf_emp.cell(30, 6, fornecedores_text, align='C', fill=True)
                pdf_emp.ln()
                fill = not fill

            zip_file.writestr('Itens_em_Empate.pdf', pdf_emp.output(dest='S'))
            
    buffer_zip.seek(0)
    return buffer_zip
