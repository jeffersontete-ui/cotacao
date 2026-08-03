import io
import zipfile

from weasyprint import HTML
from database import carregar_fornecedores


def gerar_zip_pedidos_pdf(df_comparativo):
    """
    Gera um arquivo ZIP contendo as Ordens de Pedido em PDF formatadas
    para cada distribuidora vencedora.
    """
    buffer_zip = io.BytesIO()

    fornecedores_lista = carregar_fornecedores()
    dict_fornecedores = {f['nome'].lower().strip(): f for f in fornecedores_lista}

    if df_comparativo.index.name == 'Medicamento':
        df_reset = df_comparativo.reset_index()
    else:
        df_reset = df_comparativo.copy()

    df_vencedores = df_reset[['Medicamento', 'Menor Preço (R$)', 'Fornecedor Vencedor']].dropna(subset=['Fornecedor Vencedor'])
    grupos_fornecedores = df_vencedores.groupby('Fornecedor Vencedor')

    with zipfile.ZipFile(buffer_zip, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for forn_vencedor, df_itens in grupos_fornecedores:
            info = dict_fornecedores.get(str(forn_vencedor).lower().strip(), {})
            vendedor = info.get('vendedor', 'Não informado')
            telefone = info.get('telefone', 'Não informado')
            email = info.get('email', 'Não informado')
            cnpj = info.get('cnpj', 'Não informado')

            total_pedido = float(df_itens['Menor Preço (R$)'].sum())

            rows_html = ""
            for idx, (_, row) in enumerate(df_itens.iterrows(), start=1):
                med = row['Medicamento']
                preco = float(row['Menor Preço (R$)'])
                preco_fmt = f"R$ {preco:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

                rows_html += f"""
                <tr>
                    <td style="text-align: center;">{idx}</td>
                    <td>{med}</td>
                    <td style="text-align: right;">{preco_fmt}</td>
                </tr>
                """

            total_fmt = f"R$ {total_pedido:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>Pedido de Compra - {forn_vencedor}</title>
                <style>
                    @page {{
                        size: A4;
                        margin: 15mm 12mm;
                        background-color: #ffffff;
                    }}
                    body {{
                        font-family: Arial, sans-serif;
                        color: #333333;
                        margin: 0;
                        padding: 0;
                        font-size: 11pt;
                    }}
                    .header {{
                        border-bottom: 2px solid #1F4E78;
                        padding-bottom: 10px;
                        margin-bottom: 20px;
                    }}
                    .header h1 {{
                        color: #1F4E78;
                        margin: 0 0 5px 0;
                        font-size: 18pt;
                        text-transform: uppercase;
                    }}
                    .header p {{
                        margin: 0;
                        color: #666666;
                        font-size: 10pt;
                    }}
                    .info-block {{
                        background-color: #f8f9fa;
                        border-left: 4px solid #1F4E78;
                        padding: 12px;
                        margin-bottom: 20px;
                        border-radius: 4px;
                    }}
                    .info-block table {{
                        width: 100%;
                        border-collapse: collapse;
                    }}
                    .info-block td {{
                        padding: 4px 0;
                        font-size: 10pt;
                    }}
                    table.items {{
                        width: 100%;
                        border-collapse: collapse;
                        margin-bottom: 20px;
                    }}
                    table.items th {{
                        background-color: #1F4E78;
                        color: white;
                        text-align: left;
                        padding: 8px 10px;
                        font-size: 10pt;
                        font-weight: bold;
                    }}
                    table.items td {{
                        border-bottom: 1px solid #e0e0e0;
                        padding: 8px 10px;
                        font-size: 10pt;
                    }}
                    table.items tr:nth-child(even) {{
                        background-color: #f9f9f9;
                    }}
                    .total-box {{
                        text-align: right;
                        margin-top: 15px;
                        font-size: 12pt;
                        font-weight: bold;
                        color: #1F4E78;
                    }}
                    .footer {{
                        margin-top: 40px;
                        border-top: 1px solid #e0e0e0;
                        padding-top: 15px;
                        font-size: 9pt;
                        color: #777777;
                        text-align: center;
                    }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>ORDEM DE PEDIDO DE COMPRA</h1>
                    <p>Sistema Integrado de Cotações &bull; Farmácia & Saúde</p>
                </div>

                <div class="info-block">
                    <table>
                        <tr>
                            <td><strong>Fornecedor:</strong> {forn_vencedor}</td>
                            <td><strong>CNPJ:</strong> {cnpj}</td>
                        </tr>
                        <tr>
                            <td><strong>Contato/Vendedor:</strong> {vendedor}</td>
                            <td><strong>Telefone:</strong> {telefone}</td>
                        </tr>
                        <tr>
                            <td><strong>E-mail:</strong> {email}</td>
                            <td><strong>Status:</strong> Itens Vencedores (Menor Preço)</td>
                        </tr>
                    </table>
                </div>

                <table class="items">
                    <thead>
                        <tr>
                            <th style="width: 8%; text-align: center;">Item</th>
                            <th>Descrição do Medicamento</th>
                            <th style="width: 25%; text-align: right;">Preço Unitário</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows_html}
                    </tbody>
                </table>

                <div class="total-box">
                    VALOR TOTAL DO PEDIDO: {total_fmt}
                </div>

                <div class="footer">
                    Este pedido de compra foi gerado automaticamente com base no mapa comparativo de menor preço.
                </div>
            </body>
            </html>
            """

            pdf_bytes = HTML(string=html_content).write_pdf()
            nome_arq_pdf = f"Pedido_Compra_{str(forn_vencedor).replace(' ', '_')}.pdf"
            zip_file.writestr(nome_arq_pdf, pdf_bytes)

    buffer_zip.seek(0)
    return buffer_zip
