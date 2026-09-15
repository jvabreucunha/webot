"""Testes unitários (sem browser) para as utilidades internas."""


import pytest
from selenium.common.exceptions import StaleElementReferenceException

from webot import Elemento, Navegador
from webot._utilitarios import repetir_se_transitorio
from webot.metricas import Metricas


class _ConfigFalsa:
    def __init__(self, tentativas: int, espera: float) -> None:
        self.tentativas_retry_transitorio = tentativas
        self.espera_entre_tentativas = espera


class _ObjetoFalso:
    """Simula um Navegador/Elemento: só precisa expor `.config` e `.metricas`."""

    def __init__(self, tentativas: int, falhas_antes_de_sucesso: int, espera: float = 0.0) -> None:
        self.config = _ConfigFalsa(tentativas, espera)
        self.metricas = Metricas()
        self.chamadas = 0
        self._falhas_antes_de_sucesso = falhas_antes_de_sucesso

    @repetir_se_transitorio
    def acao(self) -> str:
        self.chamadas += 1
        if self.chamadas <= self._falhas_antes_de_sucesso:
            raise StaleElementReferenceException("elemento stale de propósito")
        return "ok"


def test_retry_reexecuta_ate_dar_certo_dentro_do_limite() -> None:
    objeto = _ObjetoFalso(tentativas=3, falhas_antes_de_sucesso=2)
    assert objeto.acao() == "ok"
    assert objeto.chamadas == 3  # 2 falhas + 1 sucesso


def test_retry_desiste_apos_esgotar_tentativas_configuradas() -> None:
    objeto = _ObjetoFalso(tentativas=1, falhas_antes_de_sucesso=99)
    with pytest.raises(StaleElementReferenceException):
        objeto.acao()
    assert objeto.chamadas == 2  # tentativa inicial + 1 retry, depois desiste
    # a tentativa final (sem mais retry depois dela) não conta como retry:
    # só houve 1 retry de verdade (a 2ª chamada).
    assert objeto.metricas.retries == 1


def test_retry_com_zero_tentativas_nao_reexecuta() -> None:
    objeto = _ObjetoFalso(tentativas=0, falhas_antes_de_sucesso=1)
    with pytest.raises(StaleElementReferenceException):
        objeto.acao()
    assert objeto.chamadas == 1


def test_todos_os_metodos_de_interacao_tem_retry() -> None:
    """Regressão: selecionar_por_texto/selecionar_por_valor/enviar_arquivo
    mexem no elemento (podem pegar StaleElementReferenceException) igual
    clicar/digitar/obter_texto, mas ficaram sem @repetir_se_transitorio até
    essa checagem existir. `__wrapped__` é o que `functools.wraps` deixa no
    método decorado, então dá pra verificar isso sem precisar de um browser."""
    metodos_de_interacao = [
        "clicar",
        "digitar",
        "obter_texto",
        "obter_atributo",
        "obter_info",
        "selecionar_por_texto",
        "selecionar_por_valor",
        "enviar_arquivo",
    ]
    sem_retry = []
    for classe in (Navegador, Elemento):
        for nome in metodos_de_interacao:
            metodo = getattr(classe, nome, None)
            if metodo is None:
                continue  # nem todo método existe nas duas classes (ex.: Navegador aceita elemento=)
            if not hasattr(metodo, "__wrapped__"):
                sem_retry.append(f"{classe.__name__}.{nome}")
    assert not sem_retry, f"Métodos de interação sem retry configurável: {sem_retry}"
