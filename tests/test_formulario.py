from webot import Campo, Navegador
from webot.formulario import normalizar_campos


def test_normalizar_campos_aceita_dict() -> None:
    campos = normalizar_campos({"#a": "1", "#b": True})
    assert [(c.css, c.valor) for c in campos] == [("#a", "1"), ("#b", True)]


def test_normalizar_campos_aceita_lista_de_campo() -> None:
    lista = [Campo(valor="x", id="y")]
    assert normalizar_campos(lista) == lista


def test_campo_seletor_devolve_so_as_chaves_preenchidas() -> None:
    campo = Campo(valor="joao", id="usuario")
    assert campo.seletor() == {"id": "usuario"}


def test_preencher_formulario_dict_simples(bot: Navegador) -> None:
    bot.preencher_formulario(
        {
            "#campo-texto": "ola",
            "#comentario": "um comentario",
            "#select-teste": "Dois",
            "#aceite": True,
            "#opcao-b": True,
        }
    )
    assert bot.obter_atributo("value", id="campo-texto") == "ola"
    assert bot.obter_atributo("value", id="comentario") == "um comentario"
    assert bot.executar_script("return document.getElementById('select-teste').value") == "2"
    assert bot.encontrar(id="aceite").selecionado is True
    assert bot.encontrar(id="opcao-b").selecionado is True
    assert bot.encontrar(id="opcao-a").selecionado is False


def test_preencher_formulario_lista_de_campo(bot: Navegador) -> None:
    bot.preencher_formulario([Campo(valor="via campo", id="campo-texto")])
    assert bot.obter_atributo("value", id="campo-texto") == "via campo"


def test_preencher_formulario_checkbox_e_idempotente(bot: Navegador) -> None:
    bot.preencher_formulario({"#aceite": True})
    bot.preencher_formulario({"#aceite": True})  # marcar de novo não desmarca
    assert bot.encontrar(id="aceite").selecionado is True

    bot.preencher_formulario({"#aceite": False})
    assert bot.encontrar(id="aceite").selecionado is False


def test_elemento_preencher_formulario_busca_aninhada(bot: Navegador) -> None:
    formulario = bot.encontrar(id="formulario-teste")
    formulario.preencher_formulario({"#comentario": "aninhado"})
    assert bot.obter_atributo("value", id="comentario") == "aninhado"
