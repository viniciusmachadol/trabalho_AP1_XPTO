"""Executa o notebook do início ao fim (ambiente limpo) e grava as saídas no próprio arquivo."""
import os
import sys

import nbformat
from nbclient import NotebookClient

PASTA_PROJETO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARQUIVO = os.path.join(PASTA_PROJETO, "XPTO_Preparacao_Dados_Vinicius_Machado.ipynb")

nb = nbformat.read(ARQUIVO, as_version=4)
try:
    # Executa com a pasta do projeto como diretório de trabalho (onde o CSV final é gravado)
    NotebookClient(nb, timeout=900, kernel_name="python3",
                   resources={"metadata": {"path": PASTA_PROJETO}}).execute()
finally:
    nbformat.write(nb, ARQUIVO)

erros = [(i, o.ename, o.evalue) for i, c in enumerate(nb.cells) if c.cell_type == "code"
         for o in c.outputs if o.output_type == "error"]
print(f"Células: {len(nb.cells)} | erros: {len(erros)}")
for e in erros:
    print(e)
sys.exit(1 if erros else 0)
