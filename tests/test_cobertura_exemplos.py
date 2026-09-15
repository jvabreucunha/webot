"""Garante que todo método/propriedade público de Navegador/Elemento e todo
campo de ConfiguracaoNavegador aparece em pelo menos um arquivo de
exemplos/ — trava a documentação por exemplo de ficar pra trás conforme a
API cresce (não roda nenhum navegador; só confere o texto dos arquivos).
"""

import re
from pathlib import Path

from scripts import introspeccao

_RAIZ_PROJETO = Path(__file__).resolve().parent.parent
_TEXTO_EXEMPLOS = "\n".join(
    arquivo.read_text(encoding="utf-8") for arquivo in sorted((_RAIZ_PROJETO / "exemplos").glob("*.py"))
)


def test_todo_metodo_publico_aparece_em_algum_exemplo() -> None:
    faltando = []
    for descricao in introspeccao.listar_classes():
        if descricao.tipo != "classe":
            continue
        for membro in descricao.membros:
            if membro.tipo not in ("metodo", "propriedade") or membro.nome.startswith("__"):
                continue
            padrao = rf"\.{re.escape(membro.nome)}\b|\b{re.escape(membro.nome)}="
            if not re.search(padrao, _TEXTO_EXEMPLOS):
                faltando.append(f"{descricao.nome}.{membro.nome}")
    assert not faltando, f"Sem exemplo em exemplos/: {faltando}"


def test_todo_campo_de_configuracao_aparece_em_algum_exemplo() -> None:
    descricao = introspeccao.descrever_classe("ConfiguracaoNavegador")
    assert descricao is not None
    faltando = [
        campo.nome
        for campo in descricao.membros
        if not re.search(rf"\b{re.escape(campo.nome)}\s*=", _TEXTO_EXEMPLOS)
    ]
    assert not faltando, f"Campo(s) de ConfiguracaoNavegador sem exemplo: {faltando}"
