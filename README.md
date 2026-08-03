# Sistema Integrado de Cotações

App em Streamlit para cotação de medicamentos entre fornecedores.

## Como funciona

1. **Criar Cotação** — você monta a lista de medicamentos com a quantidade de cada um.
   O sistema gera uma planilha `.xlsx` por fornecedor. O fornecedor vê apenas
   *Item / Descrição / Preço Unitário*; a quantidade e a identificação do fornecedor
   viajam numa coluna oculta e protegida, e voltam junto com o arquivo preenchido.
2. **Comparar Preços** — você sobe os arquivos devolvidos. O sistema monta o mapa
   comparativo, aponta o menor preço de cada item, sinaliza empates e preços fora
   da curva, e mostra exatamente quais arquivos entraram e quais falharam.
3. **Cadastro de Fornecedores** — cadastro, edição, exportação e importação em CSV.

Cada cotação criada fica salva no banco local, então as quantidades são recuperadas
mesmo que o fornecedor devolva o arquivo em outro formato.

## Rodando

```bash
pip install -r requirements.txt
streamlit run app.py
```

O banco `cotacao.db` é criado na pasta do projeto na primeira execução e **não é
versionado** — ele contém dados de fornecedores. Use o botão de exportar CSV na
aba 3 para ter backup.
