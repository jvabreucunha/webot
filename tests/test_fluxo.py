import pytest

from webot import ErroFluxo, Fluxo, Navegador


def test_fluxo_executa_passos_em_ordem(pagina_teste_url: str) -> None:
    fluxo = Fluxo("Fluxo de teste")
    fluxo.navegar(pagina_teste_url)
    fluxo.digitar("joao", id="campo-texto")
    fluxo.clicar(id="botao-clicar")

    with Navegador(sem_interface=True) as bot:
        resultado = fluxo.executar(bot)
        assert bot.obter_texto(id="resultado-clique") == "clicado"

    assert resultado.sucesso is True
    assert len(resultado.etapas) == 3
    assert resultado.total_falhas == 0
    assert resultado.taxa_sucesso == 1.0
    assert resultado.duracao_segundos > 0


def test_fluxo_com_preencher_formulario(pagina_teste_url: str) -> None:
    fluxo = Fluxo("Formulário")
    fluxo.navegar(pagina_teste_url)
    fluxo.preencher_formulario({"#comentario": "via fluxo"})

    with Navegador(sem_interface=True) as bot:
        fluxo.executar(bot)
        assert bot.obter_atributo("value", id="comentario") == "via fluxo"


def test_fluxo_falha_levanta_errofluxo_com_resultado_parcial(pagina_teste_url: str) -> None:
    fluxo = Fluxo("Fluxo com falha")
    fluxo.navegar(pagina_teste_url)
    fluxo.clicar(id="nao-existe-no-fluxo", timeout=1)
    fluxo.clicar(id="nunca-executa")

    with Navegador(sem_interface=True) as bot:
        with pytest.raises(ErroFluxo) as exc_info:
            fluxo.executar(bot)

    resultado = exc_info.value.resultado
    assert resultado.sucesso is False
    # só as duas primeiras etapas rodaram; a 3a (clicar em "nunca-executa")
    # nunca chegou a executar, porque a 2a já interrompeu o fluxo
    assert len(resultado.etapas) == 2
    assert resultado.etapas[0].sucesso is True  # navegar
    assert resultado.etapas[1].sucesso is False  # o clicar que falhou
    assert "nao-existe-no-fluxo" in str(exc_info.value)


def test_fluxo_adicionar_passo_customizado(pagina_teste_url: str) -> None:
    fluxo = Fluxo("Customizado")
    fluxo.adicionar(lambda bot: bot.navegar(pagina_teste_url), nome="ir pra página")
    fluxo.adicionar(lambda bot: bot.clicar(id="botao-clicar"), nome="clicar")

    with Navegador(sem_interface=True) as bot:
        resultado = fluxo.executar(bot)

    assert [etapa.nome for etapa in resultado.etapas] == ["ir pra página", "clicar"]


def test_fluxo_reutilizavel_em_navegadores_diferentes(pagina_teste_url: str) -> None:
    """O mesmo Fluxo, montado uma vez, pode rodar contra bots diferentes."""
    fluxo = Fluxo("Reutilizável")
    fluxo.navegar(pagina_teste_url)
    fluxo.clicar(id="botao-clicar")

    with Navegador(sem_interface=True) as bot1:
        resultado1 = fluxo.executar(bot1)
    with Navegador(sem_interface=True) as bot2:
        resultado2 = fluxo.executar(bot2)

    assert resultado1.sucesso is True
    assert resultado2.sucesso is True
