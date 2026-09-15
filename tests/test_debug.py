import logging

from webot import Navegador


def test_debug_liga_e_desliga_log_estruturado(pagina_teste_url: str) -> None:
    logger_pacote = logging.getLogger("webot")
    registros: list[logging.LogRecord] = []
    coletor = logging.Handler()
    coletor.emit = registros.append  # type: ignore[method-assign]
    logger_pacote.addHandler(coletor)
    try:
        with Navegador(sem_interface=True) as bot:
            bot.navegar(pagina_teste_url)
            assert not registros  # desligado por padrão: nada logado ainda

            bot.debug()
            bot.clicar(id="botao-clicar")
            assert registros  # ligado: as ações passam a gerar log

            registros.clear()
            bot.debug(False)
            bot.clicar(id="botao-clicar")
            assert not registros  # desligado: log para nesse instante em diante
    finally:
        logger_pacote.removeHandler(coletor)
        bot.debug(False)  # garante que não vaza estado pros outros testes


def test_debug_chamado_duas_vezes_nao_duplica_handler() -> None:
    logger_pacote = logging.getLogger("webot")
    with Navegador(sem_interface=True) as bot:
        try:
            bot.debug()
            handlers_depois_de_ligar = len(logger_pacote.handlers)
            bot.debug()
            assert len(logger_pacote.handlers) == handlers_depois_de_ligar
        finally:
            bot.debug(False)
