"""Introspecção da API pública do `webot`.

Fonte única de verdade para `scripts/gerar_referencia_ia.py`: nada aqui é
escrito à mão sobre "o que cada método faz" — tudo vem de `inspect` sobre as
classes reais (assinatura, docstring, tipos), então esta descrição nunca fica
desatualizada em relação ao código. Se um método for adicionado, renomeado ou
tiver a assinatura alterada em `webot`, a próxima geração já reflete isso
automaticamente, sem precisar editar nada aqui.
"""

from __future__ import annotations

import dataclasses
import inspect
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from pydantic import BaseModel

import webot
from webot.configuracao import ConfiguracaoNavegador
from webot.etapa import Etapa, ResultadoEtapa
from webot.evidencias import Evidencia
from webot.fluxo import Fluxo, ResultadoFluxo
from webot.formulario import Campo
from webot.historico import RegistroAcao
from webot.metricas import Metricas
from webot.resultados import InfoElemento

_CLASSES_COM_METODOS: dict[str, type] = {
    "Navegador": webot.Navegador,
    "Elemento": webot.Elemento,
    "Fluxo": Fluxo,
    "Etapa": Etapa,
    "Empacotador": webot.Empacotador,
}
_MODELOS_PYDANTIC: dict[str, type[BaseModel]] = {
    "ConfiguracaoNavegador": ConfiguracaoNavegador,
    "InfoElemento": InfoElemento,
}
_DATACLASSES: dict[str, type] = {
    "ResultadoEtapa": ResultadoEtapa,
    "ResultadoFluxo": ResultadoFluxo,
    "Metricas": Metricas,
    "Evidencia": Evidencia,
    "RegistroAcao": RegistroAcao,
    "Campo": Campo,
}
_ENUMS: dict[str, type[Enum]] = {
    "TipoNavegador": webot.TipoNavegador,
}
_EXCECOES: dict[str, type] = {
    nome: getattr(webot, nome) for nome in webot.__all__ if nome.startswith("Erro")
}


@dataclass
class MembroAPI:
    """Um método, propriedade, campo de config ou valor de enum."""

    nome: str
    tipo: str  # "metodo" | "propriedade" | "campo" | "valor_enum"
    assinatura: str | None
    docstring: str | None


@dataclass
class DescricaoClasse:
    """Uma classe/modelo/enum/exceção pública do webot, com seus membros."""

    nome: str
    tipo: str  # "classe" | "modelo_pydantic" | "enum" | "excecao"
    docstring: str | None
    membros: list[MembroAPI] = field(default_factory=list)


def _docstring(obj: Any) -> str | None:
    doc = inspect.getdoc(obj)
    return doc.strip() if doc else None


def _nome_tipo(anotacao: Any) -> str:
    if isinstance(anotacao, type):
        return anotacao.__name__
    return str(anotacao)


# `from __future__ import annotations` faz `inspect.signature()` devolver as
# anotações como string (ex.: "elemento: 'Elemento | None' = None"). Resolver
# essas strings de volta pro tipo real (`eval_str=True`) quebraria para
# anotações que só existem sob `TYPE_CHECKING` (import quebra-ciclo, comum
# entre navegador.py/elemento.py) — então só limpamos as aspas do texto.
_RE_ANOTACAO_ENTRE_ASPAS = re.compile(r"(:\s*|->\s*)'([^']*)'")


def _assinatura_sem_self(func: Any) -> str | None:
    try:
        assinatura = inspect.signature(func)
    except (TypeError, ValueError):
        return None
    parametros = [p for nome, p in assinatura.parameters.items() if nome != "self"]
    texto = str(assinatura.replace(parameters=parametros))
    return _RE_ANOTACAO_ENTRE_ASPAS.sub(r"\1\2", texto)


def _membros_de_classe(cls: type) -> list[MembroAPI]:
    membros: list[MembroAPI] = []
    for nome, valor in sorted(vars(cls).items()):
        if nome.startswith("_") and nome != "__init__":
            continue
        if isinstance(valor, property):
            membros.append(
                MembroAPI(
                    nome=nome,
                    tipo="propriedade",
                    assinatura=None,
                    docstring=_docstring(valor.fget),
                )
            )
        elif inspect.isfunction(valor):
            membros.append(
                MembroAPI(
                    nome=nome,
                    tipo="metodo",
                    assinatura=_assinatura_sem_self(valor),
                    docstring=_docstring(valor),
                )
            )
    return membros


def _campos_de_modelo(cls: type[BaseModel]) -> list[MembroAPI]:
    membros: list[MembroAPI] = []
    for nome, campo in cls.model_fields.items():
        if campo.default_factory is not None:
            # pydantic tipa default_factory como podendo aceitar os dados já
            # validados, mas os campos do webot só usam fábricas sem argumento.
            padrao = repr(campo.default_factory())  # type: ignore[call-arg]
        elif campo.is_required():
            padrao = "<obrigatório>"
        else:
            padrao = repr(campo.default)
        membros.append(
            MembroAPI(
                nome=nome,
                tipo="campo",
                assinatura=f"{_nome_tipo(campo.annotation)} = {padrao}",
                docstring=campo.description,
            )
        )
    return membros


def _valores_de_enum(cls: type[Enum]) -> list[MembroAPI]:
    return [
        MembroAPI(nome=item.name, tipo="valor_enum", assinatura=repr(item.value), docstring=None)
        for item in cls
    ]


def _campos_de_dataclass(cls: type) -> list[MembroAPI]:
    """Campos de um `@dataclass` comum (não-pydantic), mais as `@property`
    computadas que a classe tiver (ex.: `ResultadoFluxo.taxa_sucesso`)."""
    membros: list[MembroAPI] = []
    for campo in dataclasses.fields(cls):
        # com `from __future__ import annotations`, `campo.type` já vem como
        # string (ex.: "list[ResultadoEtapa]") — não precisa resolver o tipo real.
        if campo.default is not dataclasses.MISSING:
            padrao = repr(campo.default)
        elif campo.default_factory is not dataclasses.MISSING:
            padrao = repr(campo.default_factory())
        else:
            padrao = "<obrigatório>"
        membros.append(
            MembroAPI(nome=campo.name, tipo="campo", assinatura=f"{campo.type} = {padrao}", docstring=None)
        )
    membros.extend(m for m in _membros_de_classe(cls) if m.tipo == "propriedade")
    return membros


def listar_classes() -> list[DescricaoClasse]:
    """Todas as classes/modelos/enums/exceções públicas do webot, com seus membros."""
    resultado: list[DescricaoClasse] = []
    for nome, cls in _CLASSES_COM_METODOS.items():
        resultado.append(
            DescricaoClasse(nome=nome, tipo="classe", docstring=_docstring(cls), membros=_membros_de_classe(cls))
        )
    for nome, cls in _MODELOS_PYDANTIC.items():
        resultado.append(
            DescricaoClasse(
                nome=nome, tipo="modelo_pydantic", docstring=_docstring(cls), membros=_campos_de_modelo(cls)
            )
        )
    for nome, cls in _DATACLASSES.items():
        resultado.append(
            DescricaoClasse(nome=nome, tipo="dataclass", docstring=_docstring(cls), membros=_campos_de_dataclass(cls))
        )
    for nome, cls in _ENUMS.items():
        resultado.append(
            DescricaoClasse(nome=nome, tipo="enum", docstring=_docstring(cls), membros=_valores_de_enum(cls))
        )
    for nome, cls in _EXCECOES.items():
        resultado.append(DescricaoClasse(nome=nome, tipo="excecao", docstring=_docstring(cls), membros=[]))
    return resultado


def descrever_classe(nome_classe: str) -> DescricaoClasse | None:
    """A descrição completa de uma classe (docstring + todos os membros), ou
    `None` se `nome_classe` não existir na API pública do webot."""
    return next((d for d in listar_classes() if d.nome == nome_classe), None)


def descrever_membro(nome_classe: str, nome_membro: str) -> MembroAPI | None:
    """A descrição de um único método/propriedade/campo/valor de enum, ou
    `None` se a classe ou o membro não existirem."""
    descricao = descrever_classe(nome_classe)
    if descricao is None:
        return None
    return next((m for m in descricao.membros if m.nome == nome_membro), None)


def buscar(consulta: str) -> list[tuple[str, MembroAPI]]:
    """Busca por palavra-chave (case-insensitive) no nome e na docstring de
    todos os membros de todas as classes. Devolve pares (nome_da_classe, membro)."""
    alvo = consulta.lower()
    resultados: list[tuple[str, MembroAPI]] = []
    for descricao in listar_classes():
        for membro in descricao.membros:
            texto = f"{membro.nome} {membro.docstring or ''}".lower()
            if alvo in texto:
                resultados.append((descricao.nome, membro))
    return resultados
