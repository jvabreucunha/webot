from scripts.gerar_referencia_ia import gerar_markdown


def test_gerar_markdown_contem_as_secoes_esperadas() -> None:
    conteudo = gerar_markdown()
    assert "# Referência da API do webot" in conteudo
    assert "## Visão geral" in conteudo
    assert "## `Navegador`" in conteudo
    assert "## `Elemento`" in conteudo
    assert "## `ConfiguracaoNavegador`" in conteudo
    assert "## `TipoNavegador`" in conteudo
    assert "## `ErroAutomacao`" in conteudo


def test_gerar_markdown_nao_tem_aspas_nas_assinaturas() -> None:
    conteudo = gerar_markdown()
    assert "'None'" not in conteudo
    assert "'Elemento" not in conteudo


def test_gerar_markdown_nao_tem_docstring_generica_de_object() -> None:
    conteudo = gerar_markdown()
    assert "Initialize self" not in conteudo
