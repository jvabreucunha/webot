"""Testes da introspecção usada por scripts/gerar_referencia_ia.py."""

from scripts import introspeccao


def test_lista_todas_as_classes_publicas_esperadas() -> None:
    nomes = {d.nome for d in introspeccao.listar_classes()}
    esperado = {
        "Navegador",
        "Elemento",
        "ConfiguracaoNavegador",
        "InfoElemento",
        "TipoNavegador",
        "ErroAutomacao",
        "ErroAoIniciarNavegador",
        "ErroElementoNaoEncontrado",
        "ErroNavegadorNaoIniciado",
        "ErroSeletorInvalido",
    }
    assert esperado <= nomes


def test_toda_classe_tem_docstring_propria() -> None:
    """Regressão: TipoNavegador(str, Enum) sem docstring própria herdava a
    docstring de `str` via inspect.getdoc(). Toda classe pública precisa ter
    a sua, ou REFERENCIA_IA.md sai com lixo."""
    for descricao in introspeccao.listar_classes():
        assert descricao.docstring, f"{descricao.nome} está sem docstring própria"
        assert "object=" not in descricao.docstring, (
            f"{descricao.nome} parece ter herdado a docstring de `str`/`object`"
        )


def test_todo_metodo_publico_tem_docstring() -> None:
    """Regressão: Elemento.__init__ não tinha docstring própria e
    `inspect.getdoc()` devolvia a genérica de `object.__init__`
    ("Initialize self. ..."), passando batido por um check ingênuo de
    "tem docstring ou não". Por isso também rejeitamos esse texto especificamente."""
    generica = "Initialize self."
    faltando = []
    for descricao in introspeccao.listar_classes():
        if descricao.tipo != "classe":
            continue
        for membro in descricao.membros:
            if membro.tipo != "metodo":
                continue
            if not membro.docstring or membro.docstring.startswith(generica):
                faltando.append(f"{descricao.nome}.{membro.nome}")
    assert not faltando, f"Métodos públicos sem docstring própria: {faltando}"


def test_descrever_classe_navegador() -> None:
    descricao = introspeccao.descrever_classe("Navegador")
    assert descricao is not None
    nomes_membros = {m.nome for m in descricao.membros}
    assert {"clicar", "digitar", "encontrar", "encontrar_todos", "aba", "baixar_arquivo"} <= nomes_membros


def test_descrever_classe_inexistente_devolve_none() -> None:
    assert introspeccao.descrever_classe("NaoExiste") is None


def test_descrever_membro_clicar() -> None:
    membro = introspeccao.descrever_membro("Navegador", "clicar")
    assert membro is not None
    assert membro.tipo == "metodo"
    assert "elemento" in membro.assinatura
    assert "timeout" in membro.assinatura


def test_descrever_membro_inexistente_devolve_none() -> None:
    assert introspeccao.descrever_membro("Navegador", "nao_existe") is None
    assert introspeccao.descrever_membro("NaoExiste", "clicar") is None


def test_configuracao_navegador_expoe_campos_com_descricao() -> None:
    descricao = introspeccao.descrever_classe("ConfiguracaoNavegador")
    assert descricao is not None
    assert descricao.tipo == "modelo_pydantic"
    campos = {m.nome: m for m in descricao.membros}
    assert "tipo_navegador" in campos
    assert campos["tipo_navegador"].docstring  # tem description= no Field


def test_tipo_navegador_lista_os_tres_valores() -> None:
    descricao = introspeccao.descrever_classe("TipoNavegador")
    assert descricao is not None
    assert descricao.tipo == "enum"
    nomes = {m.nome for m in descricao.membros}
    assert nomes == {"CHROME", "EDGE", "FIREFOX"}


def test_buscar_encontra_por_nome_e_por_docstring() -> None:
    achados = introspeccao.buscar("download")
    membros_achados = {(classe, m.nome) for classe, m in achados}
    assert ("Navegador", "baixar_arquivo") in membros_achados
    assert ("ConfiguracaoNavegador", "pasta_download") in membros_achados


def test_buscar_sem_resultado_devolve_lista_vazia() -> None:
    assert introspeccao.buscar("xyzabc_termo_que_nao_existe") == []


def test_assinatura_nao_tem_aspas_ao_redor_dos_tipos() -> None:
    """Regressão: `from __future__ import annotations` faz inspect.signature()
    devolver anotações como string (ex.: "elemento: 'Elemento | None' = None");
    a assinatura mostrada pra IA deve estar limpa disso."""
    membro = introspeccao.descrever_membro("Navegador", "clicar")
    assert membro is not None
    assert "'" not in membro.assinatura
