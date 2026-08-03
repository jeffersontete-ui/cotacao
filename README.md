# Sistema Integrado de Cotações

App em Streamlit para cotação de medicamentos entre fornecedores: monta a lista uma
vez, gera uma planilha por fornecedor, compara os preços que voltam, resolve empates
e emite os pedidos de compra.

## Fluxo

1. **Criar Cotação** — lista de medicamentos com quantidade. Sai um `.xlsx` por
   fornecedor mostrando **apenas Medicamento e Valor**. A quantidade e a identificação
   do fornecedor viajam ocultas e voltam no arquivo preenchido. Botão *Limpar* começa
   uma cotação em branco.
2. **Comparar e Decidir** — suba os arquivos devolvidos. Se houver empate de menor
   preço, abre a **tela de desempate**: mostra só os itens empatados, só os fornecedores
   empatados, e **bloqueia o restante da tela até você escolher um vencedor para cada um**.
   Resolvido isso, tudo é recalculado automaticamente — tabela, painel, pedidos, PDF e
   Excel.
3. **Fornecedores** — cadastro com Distribuidora, Representante, Telefone, WhatsApp,
   E-mail, CNPJ, Ativo/Inativo e Observações. Exporta e importa em CSV.

## Painel

Total otimizado, economia (contra comprar tudo do fornecedor mais caro de cada item),
quantidade de itens, itens pendentes/sem preço, valor por fornecedor e ranking.

## Leitura de preços

Aceita célula vazia, texto, vírgula, ponto, `R$` e espaços — tudo convertido
corretamente (`R$ 10,50` → `10.50`; `1.234,56` → `1234.56`).

## Rodando

```bash
pip install -r requirements.txt
streamlit run app.py
```

O banco `cotacao.db` é criado na pasta do projeto na primeira execução e **não é
versionado** — contém os fornecedores e o histórico de cotações. Use *Exportar CSV*
na aba de fornecedores para backup.

## Arquivos

| Arquivo | Papel |
|---|---|
| `app.py` | Interface, fluxo e tela de empate |
| `leitor_excel.py` | Leitura das planilhas, comparação e detecção de empates |
| `gerador_excel.py` | Geração das planilhas dos fornecedores |
| `dashboard.py` | Cálculo das métricas do painel |
| `pedidos.py` | Pedidos de compra em Excel |
| `pedidos_pdf.py` | Pedidos de compra em PDF |
| `database.py` | Banco SQLite: fornecedores e cotações |
