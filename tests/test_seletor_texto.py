import pytest

from webot import ErroElementoNaoEncontrado, Navegador


def test_encontrar_por_texto(bot: Navegador) -> None:
    elemento = bot.encontrar(texto="Clique aqui")
    assert elemento.tag == "button"


def test_clicar_por_texto(bot: Navegador) -> None:
    bot.clicar(texto="Clique aqui")
    assert bot.obter_texto(id="resultado-clique") == "clicado"


def test_texto_nao_encontrado_da_erro(bot: Navegador) -> None:
    with pytest.raises(ErroElementoNaoEncontrado):
        bot.encontrar(texto="Isso não existe na página", timeout=1)


def test_texto_com_aspas_simples_e_duplas(bot: Navegador) -> None:
    """Regressão: o seletor "texto" vira um literal XPath — precisa
    funcionar mesmo quando o texto tem aspas simples E duplas juntas
    (nenhum dos dois estilos de aspas do XPath sozinho resolve isso)."""
    conteudo = "ele disse \"oi\" e 'tchau'"
    bot.executar_script(
        "var div = document.createElement('div'); div.id = 'texto-com-aspas'; "
        "div.textContent = arguments[0]; document.body.appendChild(div);",
        conteudo,
    )
    elemento = bot.encontrar(texto=conteudo)
    assert elemento.obter_atributo("id") == "texto-com-aspas"
