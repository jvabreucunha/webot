from webot import Navegador
from webot.metricas import Metricas


def test_metricas_copia_e_independente() -> None:
    original = Metricas(acoes=1, falhas=2, retries=3)
    copia = original.copia()
    copia.acoes = 99
    assert original.acoes == 1


def test_metricas_subtracao() -> None:
    depois = Metricas(acoes=5, falhas=2, retries=1)
    antes = Metricas(acoes=2, falhas=1, retries=0)
    delta = depois - antes
    assert delta == Metricas(acoes=3, falhas=1, retries=1)


def test_navegador_conta_acoes_principais(pagina_teste_url: str) -> None:
    with Navegador(sem_interface=True) as bot:
        assert bot.metricas.acoes == 0
        bot.navegar(pagina_teste_url)
        bot.encontrar(id="titulo")
        bot.clicar(id="botao-clicar")
        bot.digitar("x", id="campo-texto")
        assert bot.metricas.acoes == 4


def test_navegador_conta_retries(pagina_teste_url: str) -> None:
    """Não força uma StaleElementReferenceException de verdade aqui (isso já
    é testado isoladamente, sem browser, em test_utilitarios.py) — só
    confirma que a contagem começa em zero e não conta retries que não
    aconteceram."""
    with Navegador(sem_interface=True) as bot:
        bot.navegar(pagina_teste_url)
        bot.clicar(id="botao-clicar")
        assert bot.metricas.retries == 0
