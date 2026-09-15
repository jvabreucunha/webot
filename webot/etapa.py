"""Agrupa um bloco de ações do `Navegador` sob um nome, pra rastrear
status/duração/erro/ações/retries de cada parte de uma automação — e
identificar claramente qual etapa falhou quando algo dá errado.
"""

from __future__ import annotations

import logging
import time
from contextlib import ContextDecorator
from dataclasses import dataclass
from functools import wraps
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from .navegador import Navegador

logger = logging.getLogger(__name__)


@dataclass
class ResultadoEtapa:
    """O que aconteceu durante uma etapa (`Navegador.etapa(...)`).

    `acoes`/`retries` são a soma do que aconteceu com o `Navegador` (e
    `Elemento`s dele) enquanto a etapa estava ativa — não são contados por
    fora, são a diferença de `Navegador.metricas` entre o início e o fim.
    `tentativas` só é maior que 1 quando a etapa é usada como decorator com
    `tentativas=N` (ver docstring de `Etapa`); usada como `with`, uma etapa
    roda no máximo uma vez.
    """

    nome: str
    status: str = "em_andamento"  # "sucesso" | "falha" | "em_andamento"
    duracao_segundos: float = 0.0
    erro: str | None = None
    acoes: int = 0
    retries: int = 0
    tentativas: int = 1

    @property
    def sucesso(self) -> bool:
        return self.status == "sucesso"


class Etapa(ContextDecorator):
    """Uso como `with` (roda uma vez, sem retry no nível da etapa):

        with bot.etapa("Login"):
            bot.digitar("usuario", id="usuario")
            bot.clicar(texto="Entrar")

    Uso como decorator (por herdar de `ContextDecorator`) — aqui sim
    `tentativas=` reexecuta a função inteira do zero se ela falhar:

        @bot.etapa("Login", tentativas=3)
        def fazer_login(bot):
            bot.digitar("usuario", id="usuario")
            bot.clicar(texto="Entrar")

        fazer_login(bot)

    Em nenhum dos dois casos a exceção original é suprimida — ela sempre se
    propaga (ou, na última tentativa esgotada, é relançada) depois de a
    etapa registrar o que aconteceu em `.resultado` e capturar evidência.
    """

    def __init__(self, bot: Navegador, nome: str, *, tentativas: int = 1) -> None:
        """Normalmente não construído diretamente — vem de `Navegador.etapa(nome, tentativas=...)`.

        Args:
            bot: o `Navegador` cujas ações serão rastreadas.
            nome: identifica a etapa nos logs/métricas/evidências.
            tentativas: só tem efeito no uso como decorator (ver docstring
                da classe) — quantas vezes reexecutar a função inteira se
                ela falhar.
        """
        self.nome = nome
        self.tentativas_maximas = max(1, tentativas)
        self._bot = bot
        self.resultado = ResultadoEtapa(nome=nome)
        self._inicio = 0.0
        self._metricas_iniciais = bot.metricas.copia()
        self._evidencias_antes = len(bot.evidencias)
        self._etapa_anterior: Etapa | None = None

    def __enter__(self) -> Etapa:
        self._inicio = time.monotonic()
        self._metricas_iniciais = self._bot.metricas.copia()
        self._evidencias_antes = len(self._bot.evidencias)
        self._etapa_anterior = self._bot._etapa_atual
        self._bot._etapa_atual = self
        logger.info("Etapa %r iniciada", self.nome)
        return self

    def __exit__(self, tipo_exc, valor_exc, traceback_exc) -> Literal[False]:
        self.resultado.duracao_segundos = time.monotonic() - self._inicio
        delta = self._bot.metricas - self._metricas_iniciais
        self.resultado.acoes = delta.acoes
        self.resultado.retries = delta.retries
        self._bot._etapa_atual = self._etapa_anterior

        if tipo_exc is None:
            self.resultado.status = "sucesso"
            logger.info(
                "Etapa %r concluída em %.2fs (%d ação(ões), %d retry(s))",
                self.nome,
                self.resultado.duracao_segundos,
                self.resultado.acoes,
                self.resultado.retries,
            )
        else:
            self.resultado.status = "falha"
            self.resultado.erro = str(valor_exc)
            self._bot.metricas.falhas += 1
            logger.error("Etapa %r falhou após %.2fs: %s", self.nome, self.resultado.duracao_segundos, valor_exc)
            if len(self._bot.evidencias) > self._evidencias_antes:
                # já foi registrada uma evidência de baixo nível (ex.: um
                # esperar_ate() que estourou) durante esta etapa — só marca
                # de qual etapa ela é, em vez de duplicar a captura. Se uma
                # etapa aninhada mais interna já preencheu `.etapa`, deixa
                # como está — o nome mais específico é mais útil que o da
                # etapa externa.
                ultima_evidencia = self._bot.evidencias[-1]
                if ultima_evidencia.etapa is None:
                    ultima_evidencia.etapa = self.nome
            else:
                self._bot._registrar_evidencia(etapa=self.nome, erro=valor_exc)
        return False  # nunca suprime a exceção

    def __call__(self, func):
        @wraps(func)
        def envoltorio(*args, **kwargs):
            ultimo_erro: BaseException | None = None
            for tentativa in range(1, self.tentativas_maximas + 1):
                self.resultado = ResultadoEtapa(nome=self.nome, tentativas=tentativa)
                try:
                    with self:
                        return func(*args, **kwargs)
                except Exception as erro:  # a etapa não suprime, então cai aqui
                    ultimo_erro = erro
                    if tentativa == self.tentativas_maximas:
                        raise
                    logger.warning(
                        "Etapa %r falhou (tentativa %s/%s), tentando de novo",
                        self.nome,
                        tentativa,
                        self.tentativas_maximas,
                    )
            raise ultimo_erro  # pragma: no cover — inatingível, só pra satisfazer o type checker

        return envoltorio
