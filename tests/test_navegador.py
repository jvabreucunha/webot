import pytest

from webot import ErroElementoNaoEncontrado, ErroSeletorInvalido, Navegador


def test_encontrar_por_id(bot: Navegador) -> None:
    elemento = bot.encontrar(id="titulo")
    assert elemento.texto == "Página de teste"


def test_clicar_atualiza_texto(bot: Navegador) -> None:
    bot.clicar(id="botao-clicar")
    assert bot.obter_texto(id="resultado-clique") == "clicado"


def test_digitar_e_ler_valor(bot: Navegador) -> None:
    bot.digitar("ola mundo", id="campo-texto")
    assert bot.obter_atributo("value", id="campo-texto") == "ola mundo"


def test_selecionar_por_valor(bot: Navegador) -> None:
    bot.selecionar_por_valor("2", id="select-teste")
    valor = bot.executar_script("return document.getElementById('select-teste').value")
    assert valor == "2"


def test_esta_presente_true_false(bot: Navegador) -> None:
    assert bot.esta_presente(id="titulo") is True
    assert bot.esta_presente(id="isso-nao-existe", timeout=1) is False


def test_elemento_visivel_e_habilitado(bot: Navegador) -> None:
    titulo = bot.encontrar(id="titulo")
    assert titulo.visivel is True

    botao_desabilitado = bot.encontrar(id="botao-desabilitado")
    assert botao_desabilitado.habilitado is False


def test_elemento_oculto_nao_visivel(bot: Navegador) -> None:
    oculto = bot.encontrar(id="oculto")
    assert oculto.visivel is False


def test_seletor_sem_chave_da_erro(bot: Navegador) -> None:
    with pytest.raises(ErroSeletorInvalido):
        bot.encontrar()


def test_seletor_com_duas_chaves_da_erro(bot: Navegador) -> None:
    with pytest.raises(ErroSeletorInvalido):
        bot.encontrar(id="titulo", css="#titulo")


def test_seletor_desconhecido_da_erro(bot: Navegador) -> None:
    with pytest.raises(ErroSeletorInvalido):
        bot.encontrar(seletor_que_nao_existe="titulo")


def test_elemento_e_seletor_juntos_da_erro(bot: Navegador) -> None:
    elemento = bot.encontrar(id="titulo")
    with pytest.raises(ErroSeletorInvalido):
        bot.clicar(elemento=elemento, id="titulo")


def test_timeout_da_erro_com_contexto_do_seletor(bot: Navegador) -> None:
    with pytest.raises(ErroElementoNaoEncontrado) as exc_info:
        bot.encontrar(id="isso-nao-existe-de-jeito-nenhum", timeout=1)
    assert "isso-nao-existe-de-jeito-nenhum" in str(exc_info.value)


def test_busca_aninhada_dentro_de_linha(bot: Navegador) -> None:
    linhas = bot.encontrar_todos(css="#tabela tr.linha")
    assert len(linhas) == 2
    assert linhas[1].encontrar(css=".celula-nome").obter_texto() == "Bruno"


def test_clicar_dentro_de_linha_aninhada(bot: Navegador) -> None:
    linhas = bot.encontrar_todos(css="#tabela tr.linha")
    linhas[0].encontrar(css=".botao-linha").clicar()
    assert linhas[0].encontrar(css=".status").obter_texto() == "clicado na linha"


def test_esta_presente_aninhado(bot: Navegador) -> None:
    linha = bot.encontrar(css="#tabela tr.linha")
    assert linha.esta_presente(css=".celula-nome") is True
    assert linha.esta_presente(css=".coluna-que-nao-existe", timeout=1) is False


def test_obter_info_retorna_atributos(bot: Navegador) -> None:
    info = bot.obter_info(id="link-teste")
    assert info.tag == "a"
    assert info.atributos["href"].endswith("#ancora")


def test_link_por_texto(bot: Navegador) -> None:
    elemento = bot.encontrar(texto_link="Ir para âncora")
    assert elemento.obter_atributo("id") == "link-teste"


def test_link_por_texto_parcial(bot: Navegador) -> None:
    elemento = bot.encontrar(texto_link_parcial="âncora")
    assert elemento.obter_atributo("id") == "link-teste"


def test_esperar_url_conter(bot: Navegador) -> None:
    bot.clicar(id="link-teste")
    bot.esperar_url_conter("#ancora", timeout=3)


def test_esperar_titulo_conter(bot: Navegador) -> None:
    bot.executar_script("document.title = 'Titulo Mudou De Verdade';")
    bot.esperar_titulo_conter("Mudou De Verdade", timeout=3)


def test_esperar_texto_conter(bot: Navegador) -> None:
    bot.clicar(id="botao-clicar")
    bot.esperar_texto_conter("clicado", id="resultado-clique", timeout=3)


def test_esperar_rede_ociosa_aguarda_dom_parar_de_mudar(bot: Navegador) -> None:
    bot.executar_script(
        """
        window.__teste_mutacoes__ = 0;
        var intervalo = setInterval(function () {
            document.body.appendChild(document.createElement('div'));
            window.__teste_mutacoes__++;
            if (window.__teste_mutacoes__ >= 3) { clearInterval(intervalo); }
        }, 150);
        """
    )
    bot.esperar_rede_ociosa(tempo_estavel=0.3, timeout=5)
    assert bot.executar_script("return window.__teste_mutacoes__;") == 3


def test_aba_abre_executa_e_fecha_sozinha(bot: Navegador, pagina_teste_url: str) -> None:
    handles_antes = set(bot.driver_bruto.window_handles)
    with bot.aba(pagina_teste_url) as nova:
        assert len(bot.driver_bruto.window_handles) == len(handles_antes) + 1
        assert nova.obter_texto(id="titulo") == "Página de teste"
    assert set(bot.driver_bruto.window_handles) == handles_antes
