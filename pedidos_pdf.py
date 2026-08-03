import io
import zipfile
from fpdf import FPDF
from database import carregar_fornecedores


class PDFPedido(FPDF):
    def header(self):
        self.set_font('Helvetica', 'B', 14)
        self.set_text_color(31, 78, 120)
        self.cell(0, 8, 'ORDEM DE PEDIDO DE COMPRA', ln=True)
        self.set_font('Helvetica', '', 9)
        self.set_text_color(100, 100, 100)
        self.cell(0, 5, 'Sistema Integrado de Cotacoes - Farmacia', ln=True)
        self.ln(2)
        self.set_draw_color(31, 78, 120)
        self.set_line_width(0.6)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, 'Gerado automaticamente pelo Sistema Integrado de Cotacoes.', align='C')


def gerar_zip_pedidos_pdf(df_comparativo):
    buffer_zip = io.BytesIO()
    
    fornecedores_lista = carregar_fornecedores()
    dict_fornecedores = {f['nome'].lower().strip(): f for f in fornecedores_lista}
    
    df_reset = df_comparativo.reset_index() if df_comparativo.index.name == 'Medicamento' else df_comparativo.copy()
    
    with zipfile.ZipFile(buffer_zip, "w", zipfile.ZIP_DEFLATED) as zip_file:
        
        # 1. PEDIDOS PARA VENCEDORES ÚNICOS
        df_unicos = df_reset[~df_reset['Fornecedor Vencedor'].str.startswith('EMPATE', na=False) & (df_reset['Fornecedor Vencedor'] != 'Nenhum')]
        grupos = df_unicos.groupby('Fornecedor Vencedor')
        
        for forn_vencedor, df_itens in grupos:
            info = dict_fornecedores.get(str(forn_vencedor).lower().strip(), {})
            
            pdf = PDFPedido()
            pdf.add_page()
            
            # Dados do Fornecedor
            pdf.set_fill_color(245, 247, 250)
            pdf.rect(10, pdf.get_y(), 190, 22, style='F')
            pdf.set_font('Helvetica', 'B', 9)
            pdf.set_text_color(40, 40, 40)
            
            y_curr = pdf.get_y() + 3
            pdf.set_xy(12, y_curr)
            pdf.cell(92, 5, f"Fornecedor: {forn_vencedor}")
            pdf.cell(92, 5, f"CNPJ: {info.get('cnpj', 'N/A')}", ln=True)
            pdf.set_x(12)
            pdf.cell(92, 5, f"Contato: {info.get('vendedor', 'N/A')}")
            pdf.cell(92, 5, f"Telefone: {info.get('telefone', 'N/A')}", ln=True)
            
            pdf.ln(6)
            
            # Tabela
            pdf.set_fill_color(31, 78, 120)
            pdf.set_text_color(255, 255, 255)
            pdf.set_font('Helvetica', 'B', 9)
            pdf.cell(12, 7, 'Item', border=0, align='C', fill=True)
            pdf.cell(110, 7, 'Descricao do Medicamento', border=0, fill=True)
            pdf.cell(18, 7, 'Qtd', border=0, align='C', fill=True)
            pdf.cell(25, 7, 'P. Unit (R$)', border=0, align='R', fill=True)
            pdf.cell(25, 7, 'Total (R$)', border=0, align='R', fill=True)
            pdf.ln()
            
            pdf.set_text_color(50, 50, 50)
            pdf.set_font('Helvetica', '', 8)
            total_pedido = 0.0
            
            for idx, (_, row) in enumerate(df_itens.iterrows(), start=1):
                med = str(row['Medicamento'])
                qtd = int(row.get('Qtd', 1))
                preco = float(row['Menor Preço (R$)'])
                subtot = float(row.get('Subtotal Otimizado (R$)', preco * qtd))
                total_pedido += subtot
                
                pdf.cell(12, 6, str(idx), align='C')
                pdf.cell(110, 6, med[:60])
                pdf.cell(18, 6, str(qtd), align='C')
                pdf.cell(25, 6, f"{preco:,.2f}", align='R')
                pdf.cell(25, 6, f"{subtot:,.2f}", align='R')
                pdf.ln()
                
            pdf.ln(4)
            pdf.set_font('Helvetica', 'B', 10)
            pdf.set_text_color(31, 78, 120)
            pdf.cell(0, 8, f"TOTAL DO PEDIDO: R$ {total_pedido:,.2f}", align='R', ln=True)
            
            zip_file.writestr(f"Pedido_{str(forn_vencedor).replace(' ', '_')}.pdf", bytes(pdf.output()))

        # 2. RELATÓRIO DE ITENS EMPATADOS (SE HOUVER)
        df_empates = df_reset[df_reset['Fornecedor Vencedor'].str.startswith('EMPATE', na=False)]
        if not df_empates.empty:
            pdf_emp = PDFPedido()
            pdf_emp.add_page()
            pdf_emp.set_font('Helvetica', 'B', 12)
            pdf_emp.set_text_color(180, 50, 50)
            pdf_emp.cell(0, 8, 'RELATORIO DE ITENS COM EMPATE DE PRECO', ln=True)
            pdf_emp.set_font('Helvetica', '', 9)
            pdf_emp.set_text_color(80, 80, 80)
            pdf_emp.cell(0, 5, 'Escolha manualmente para qual fornecedor enviar estes itens:', ln=True)
            pdf_emp.ln(4)
            
            pdf_emp.set_fill_color(180, 50, 50)
            pdf_emp.set_text_color(255, 255, 255)
            pdf_emp.set_font('Helvetica', 'B', 9)
            pdf_emp.cell(110, 7, 'Medicamento', fill=True)
            pdf_emp.cell(25, 7, 'Preco (R$)', align='R', fill=True)
            pdf_emp.cell(55, 7, 'Fornecedores Empatados', fill=True)
            pdf_emp.ln()
            
            pdf_emp.set_text_color(50, 50, 50)
            pdf_emp.set_font('Helvetica', '', 8)
            for _, row in df_empates.iterrows():
                pdf_emp.cell(110, 6, str(row['Medicamento'])[:60])
                pdf_emp.cell(25, 6, f"{float(row['Menor Preço (R$)']):,.2f}", align='R')
                pdf_emp.cell(55, 6, str(row['Fornecedor Vencedor']).replace('EMPATE (', '').replace(')', ''))
                pdf_emp.ln()
                
            zip_file.writestr("ITENS_EM_EMPATE_DECISAO.pdf", bytes(pdf_emp.output()))

    buffer_zip.seek(0)
    return buffer_zip
