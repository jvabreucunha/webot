"""Preenchimento de formulários em lote — reaproveita os seletores e as
interações (`digitar`, `clicar`, `selecionar_por_texto`) que já existem em
`Elemento`, só decidindo qual usar de acordo com a tag/tipo do campo.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .elemento import Elemento


@dataclass
class Campo:
    """Um campo de formulário a preencher: o valor, mais um seletor (as
    mesmas palavras-chave de sempre — exatamente uma delas).

        Campo(valor="joao", id="usuario")
        Campo(valor=True, css="#aceite-termos")        # checkbox
        Campo(valor="Brasil", css="#pais")              # <select>, por texto visível

    `texto=`/`texto_link=` acham elementos pelo texto visível deles mesmos —
    ótimos pra botões/links, mas a maioria dos `<input>`/`<textarea>` não tem
    texto próprio (o texto fica no `<label>`, que é outro elemento). Pra
    campos de formulário de verdade, prefira `id=`/`css=`/`nome=`.
    """

    valor: str | bool
    id: str | None = None
    css: str | None = None
    xpath: str | None = None
    nome: str | None = None
    classe: str | None = None
    tag: str | None = None
    texto: str | None = None
    texto_link: str | None = None
    texto_link_parcial: str | None = None

    def seletor(self) -> dict[str, str]:
        """As chaves de seletor não vazias, prontas pra `**desempacotar` em
        `encontrar()`/`clicar()`/etc."""
        bruto = {
            "id": self.id,
            "css": self.css,
            "xpath": self.xpath,
            "nome": self.nome,
            "classe": self.classe,
            "tag": self.tag,
            "texto": self.texto,
            "texto_link": self.texto_link,
            "texto_link_parcial": self.texto_link_parcial,
        }
        return {chave: valor for chave, valor in bruto.items() if valor is not None}


def normalizar_campos(campos: dict[str, str | bool] | list[Campo]) -> list[Campo]:
    """Aceita tanto o formato simples (dict, chave = seletor CSS) quanto uma
    lista de `Campo` (seletor flexível) e devolve sempre uma lista de `Campo`."""
    if isinstance(campos, dict):
        return [Campo(valor=valor, css=chave) for chave, valor in campos.items()]
    return list(campos)


def preencher_campo(elemento: Elemento, valor: str | bool) -> None:
    """Preenche um único elemento já encontrado, de acordo com a tag/tipo dele:
    `<select>` seleciona por texto visível, checkbox/radio marca conforme o
    booleano (só clica se o estado atual for diferente do desejado), e o
    resto (input, textarea, ...) digita o valor como texto."""
    tag = elemento.tag
    tipo = (elemento.obter_atributo("type") or "").lower()

    if tag == "select":
        elemento.selecionar_por_texto(str(valor))
    elif tipo in ("checkbox", "radio"):
        if elemento.selecionado != bool(valor):
            elemento.clicar()
    else:
        elemento.digitar(str(valor))
