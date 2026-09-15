"""Gera `REFERENCIA_IA.md` na raiz do projeto: um único arquivo Markdown com
toda a API pública do webot, pra jogar em qualquer projeto/conversa e uma IA
entender como usar a biblioteca sem precisar ler o código-fonte.

Todo o conteúdo vem de `scripts.introspeccao` (assinatura + docstring reais,
via `inspect`) — nada aqui é escrito à mão sobre "o que cada método faz".
Rode de novo depois de qualquer mudança na API pública:

    python scripts/gerar_referencia_ia.py
"""

from __future__ import annotations

from pathlib import Path

from scripts import introspeccao

_RAIZ_PROJETO = Path(__file__).resolve().parent.parent
_ARQUIVO_SAIDA = _RAIZ_PROJETO / "REFERENCIA_IA.md"

_VISAO_GERAL = """\
webot é uma abstração em pt-br sobre o Selenium para automação/RPA web.

Fundamentos:
- `Navegador` é a classe principal: controla o ciclo de vida do navegador
  (Chrome/Edge/Firefox) e expõe métodos em português (navegar, clicar,
  digitar, encontrar, ...). Use como context manager:
  `with Navegador(tipo_navegador="chrome") as bot: ...` — isso abre o
  navegador e garante que ele feche sozinho ao final.
- Localizar elementos é sempre por palavra-chave — `id=`, `css=`, `xpath=`,
  `nome=`, `classe=`, `tag=`, `texto_link=`, `texto_link_parcial=` —
  exatamente uma por chamada. Nunca um objeto `By` do Selenium.
- `bot.encontrar(**seletor)` / `bot.encontrar_todos(**seletor)` NÃO devolvem
  o WebElement puro do Selenium: devolvem um `Elemento` (ou lista deles), um
  envelope com os MESMOS métodos de interação (`.clicar()`, `.digitar()`,
  `.obter_texto()`, `.obter_atributo()`, ...) já mirados naquele elemento
  específico — não precisa de seletor de novo. `Elemento` também tem busca
  ANINHADA: `elemento.encontrar(**seletor)` procura só dentro dele (ótimo
  para tabelas/listas).
- Todo método de interação do `Navegador` (clicar, digitar, obter_texto, ...)
  também aceita `elemento=` (um `Elemento` já encontrado) como alternativa ao
  seletor — nunca os dois juntos.
- Configuração via `ConfiguracaoNavegador` (modelo pydantic, validado — nome
  ou tipo errado falha na hora) ou parâmetros soltos direto em
  `Navegador(...)`, nunca os dois juntos.
- Toda exceção da biblioteca herda de `ErroAutomacao`.
- Retry automático em erros transitórios do Selenium (elemento "stale",
  ainda não interagível), configurável.

Exemplo mínimo:

```python
from webot import Navegador

with Navegador(tipo_navegador="chrome", sem_interface=True) as bot:
    bot.navegar("https://exemplo.com")
    bot.clicar(css="button.enviar")
    itens = bot.encontrar_todos(css=".item")
    itens[2].clicar()
```
"""


def _linha_lista(membro: introspeccao.MembroAPI) -> str:
    """Uma linha de bullet list compacta, para campo/valor_enum."""
    marcador = "—" if membro.tipo == "campo" else "="
    linha = f"- **`{membro.nome}`** {marcador} `{membro.assinatura}`"
    if membro.docstring:
        linha += f" — {membro.docstring}"
    return linha


def _secao_membro(membro: introspeccao.MembroAPI) -> str:
    """Um bloco `#### nome(...)` + docstring, para metodo/propriedade."""
    titulo = (
        f"#### `{membro.nome}{membro.assinatura or '(...)'}`"
        if membro.tipo == "metodo"
        else f"#### `{membro.nome}` (propriedade)"
    )
    linhas = [titulo, ""]
    if membro.docstring:
        linhas.append(membro.docstring)
    linhas.append("")
    return "\n".join(linhas)


def _secao_classe(descricao: introspeccao.DescricaoClasse) -> str:
    linhas = [f"## `{descricao.nome}`", ""]
    if descricao.docstring:
        linhas.append(descricao.docstring)
        linhas.append("")

    metodos = [m for m in descricao.membros if m.tipo == "metodo"]
    propriedades = [m for m in descricao.membros if m.tipo == "propriedade"]
    campos_ou_valores = [m for m in descricao.membros if m.tipo in ("campo", "valor_enum")]

    if propriedades:
        linhas.append("### Propriedades")
        linhas.append("")
        for membro in propriedades:
            linhas.append(_secao_membro(membro))
    if metodos:
        linhas.append("### Métodos")
        linhas.append("")
        for membro in metodos:
            linhas.append(_secao_membro(membro))
    if campos_ou_valores:
        rotulo = "Campos" if descricao.tipo in ("modelo_pydantic", "dataclass") else "Valores"
        linhas.append(f"### {rotulo}")
        linhas.append("")
        for membro in campos_ou_valores:
            linhas.append(_linha_lista(membro))
        linhas.append("")

    return "\n".join(linhas)


def gerar_markdown() -> str:
    partes = [
        "# Referência da API do webot (para IA)",
        "",
        "> Gerado automaticamente por `scripts/gerar_referencia_ia.py` a partir "
        "do código-fonte — não edite à mão. Rode o script de novo depois de "
        "qualquer mudança na API pública para atualizar este arquivo.",
        "",
        "## Visão geral",
        "",
        _VISAO_GERAL,
    ]

    classes = introspeccao.listar_classes()
    for tipo, titulo in (
        ("classe", "Classes principais"),
        ("modelo_pydantic", "Modelos de configuração e retorno"),
        ("dataclass", "Resultados e estruturas de dados"),
        ("enum", "Enums"),
        ("excecao", "Exceções"),
    ):
        do_tipo = [d for d in classes if d.tipo == tipo]
        if not do_tipo:
            continue
        partes.append(f"# {titulo}")
        partes.append("")
        for descricao in do_tipo:
            partes.append(_secao_classe(descricao))

    return "\n".join(partes).rstrip() + "\n"


def main() -> None:
    conteudo = gerar_markdown()
    _ARQUIVO_SAIDA.write_text(conteudo, encoding="utf-8")
    print(f"Gerado {_ARQUIVO_SAIDA} ({len(conteudo)} caracteres).")


if __name__ == "__main__":
    main()
