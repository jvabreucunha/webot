import pytest

from webot import ErroElementoNaoEncontrado, Navegador


def test_etapa_sucesso_registra_resultado(pagina_teste_url: str) -> None:
    with Navegador(sem_interface=True) as bot:
        bot.navegar(pagina_teste_url)
        with bot.etapa("Preencher e clicar") as etapa:
            bot.digitar("joao", id="campo-texto")
            bot.clicar(id="botao-clicar")

        assert etapa.resultado.status == "sucesso"
        assert etapa.resultado.sucesso is True
        assert etapa.resultado.acoes == 2
        assert etapa.resultado.duracao_segundos > 0
        assert etapa.resultado.erro is None
        assert etapa.resultado.tentativas == 1


def test_etapa_falha_propaga_excecao_e_registra_resultado(pagina_teste_url: str) -> None:
    with Navegador(sem_interface=True) as bot:
        bot.navegar(pagina_teste_url)
        with pytest.raises(ErroElementoNaoEncontrado):
            with bot.etapa("Falha") as etapa:
                bot.encontrar(id="nao-existe", timeout=1)

        assert etapa.resultado.status == "falha"
        assert etapa.resultado.sucesso is False
        assert etapa.resultado.erro is not None
        assert bot.metricas.falhas == 1


def test_etapa_nao_suprime_excecao_no_with(pagina_teste_url: str) -> None:
    with Navegador(sem_interface=True) as bot:
        bot.navegar(pagina_teste_url)
        with pytest.raises(ValueError):
            with bot.etapa("Etapa qualquer"):
                raise ValueError("algo deu errado, nada a ver com Selenium")


def test_etapa_como_decorator(pagina_teste_url: str) -> None:
    with Navegador(sem_interface=True) as bot:
        bot.navegar(pagina_teste_url)

        @bot.etapa("Login via decorator")
        def fazer_login(b: Navegador) -> None:
            b.digitar("usuario", id="campo-texto")

        fazer_login(bot)
        assert bot.obter_atributo("value", id="campo-texto") == "usuario"


def test_etapa_decorator_com_retry_reexecuta_ate_dar_certo(pagina_teste_url: str) -> None:
    with Navegador(sem_interface=True) as bot:
        bot.navegar(pagina_teste_url)
        chamadas = {"n": 0}

        @bot.etapa("Instável", tentativas=3)
        def instavel(b: Navegador) -> None:
            chamadas["n"] += 1
            if chamadas["n"] < 2:
                raise ValueError("falha de propósito")

        instavel(bot)
        assert chamadas["n"] == 2


def test_etapa_decorator_desiste_apos_esgotar_tentativas(pagina_teste_url: str) -> None:
    with Navegador(sem_interface=True) as bot:
        bot.navegar(pagina_teste_url)
        chamadas = {"n": 0}

        @bot.etapa("Sempre falha", tentativas=2)
        def sempre_falha(b: Navegador) -> None:
            chamadas["n"] += 1
            raise ValueError("sempre falha")

        with pytest.raises(ValueError):
            sempre_falha(bot)
        assert chamadas["n"] == 2  # tentou as 2 vezes configuradas, depois desistiu


def test_etapa_aninhada_mantem_nome_da_etapa_mais_interna(pagina_teste_url: str) -> None:
    """Uma etapa externa não pode sobrescrever o nome, mais específico, que a
    etapa interna já atribuiu à evidência da falha."""
    with Navegador(sem_interface=True) as bot:
        bot.navegar(pagina_teste_url)
        with pytest.raises(ErroElementoNaoEncontrado):
            with bot.etapa("Etapa externa"):
                with bot.etapa("Etapa interna"):
                    bot.encontrar(id="nao-existe", timeout=1)

        assert len(bot.evidencias) == 1
        assert bot.evidencias[-1].etapa == "Etapa interna"


def test_etapa_com_with_sempre_roda_uma_vez_so(pagina_teste_url: str) -> None:
    """`tentativas=` só tem efeito quando a etapa é usada como decorator —
    usada como `with`, não há como reexecutar o bloco."""
    with Navegador(sem_interface=True) as bot:
        bot.navegar(pagina_teste_url)
        with pytest.raises(ValueError):
            with bot.etapa("Etapa com tentativas, mas via with", tentativas=5) as etapa:
                raise ValueError("falha")
        assert etapa.resultado.tentativas == 1
