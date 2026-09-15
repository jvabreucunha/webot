"""`Fluxo`: uma automação nomeada e reutilizável, montada independente de
qualquer `Navegador` e executada contra um depois.

    fluxo = Fluxo("Cadastro de cliente")
    fluxo.navegar("https://exemplo.com/cadastro")
    fluxo.preencher_formulario({"#nome": "Maria", "#pais": "Brasil"})
    fluxo.clicar(texto="Salvar")

    with Navegador() as bot:
        resultado = fluxo.executar(bot)
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .etapa import ResultadoEtapa
from .excecoes import ErroAutomacao
from .formulario import Campo

if TYPE_CHECKING:
    from .navegador import Navegador

logger = logging.getLogger(__name__)

_Passo = Callable[["Navegador"], None]


@dataclass
class ResultadoFluxo:
    """O resultado de rodar um `Fluxo`: quanto tempo levou, e o `ResultadoEtapa`
    de cada passo (na ordem em que rodaram)."""

    nome: str
    etapas: list[ResultadoEtapa] = field(default_factory=list)
    duracao_segundos: float = 0.0

    @property
    def sucesso(self) -> bool:
        return all(etapa.sucesso for etapa in self.etapas)

    @property
    def total_acoes(self) -> int:
        return sum(etapa.acoes for etapa in self.etapas)

    @property
    def total_retries(self) -> int:
        return sum(etapa.retries for etapa in self.etapas)

    @property
    def total_falhas(self) -> int:
        return sum(1 for etapa in self.etapas if not etapa.sucesso)

    @property
    def taxa_sucesso(self) -> float:
        if not self.etapas:
            return 1.0
        return sum(1 for etapa in self.etapas if etapa.sucesso) / len(self.etapas)


class ErroFluxo(ErroAutomacao):
    """Uma etapa do fluxo falhou. `.resultado` tem o que rodou até ali
    (etapas concluídas, métricas parciais), pra quem quiser inspecionar o
    que deu certo antes da falha."""

    def __init__(self, mensagem: str, *, resultado: ResultadoFluxo) -> None:
        super().__init__(mensagem)
        self.resultado = resultado


class Fluxo:
    """Uma automação nomeada, montada uma vez e reaproveitável em várias
    execuções/navegadores. Cada passo adicionado (via `.adicionar()` ou pelos
    atalhos `.navegar()`/`.clicar()`/`.digitar()`/`.preencher_formulario()`)
    vira uma `Etapa` própria quando o fluxo roda — dá pra ver exatamente qual
    passo falhou em `resultado.etapas`.
    """

    def __init__(self, nome: str) -> None:
        """Cria um fluxo vazio, sem passos ainda — use `.adicionar()` ou os
        atalhos (`.navegar()`, `.clicar()`, ...) pra montá-lo.

        Args:
            nome: identifica o fluxo nos logs e na mensagem de `ErroFluxo`.
        """
        self.nome = nome
        self._passos: list[tuple[str, _Passo]] = []

    def adicionar(self, passo: _Passo, *, nome: str | None = None) -> Fluxo:
        """Adiciona um passo customizado: uma função que recebe o `Navegador`
        em execução. Use isso pra qualquer lógica que os atalhos
        (`.navegar()`, `.clicar()`, ...) não cobrirem."""
        nome_final: str = nome or str(getattr(passo, "__name__", "passo"))
        self._passos.append((nome_final, passo))
        return self

    def navegar(self, url: str) -> Fluxo:
        """Adiciona um passo que chama `Navegador.navegar(url)` quando o fluxo rodar."""
        return self.adicionar(lambda bot: bot.navegar(url), nome=f"navegar {url}")

    def clicar(self, **seletor: Any) -> Fluxo:
        """Adiciona um passo que chama `Navegador.clicar(**seletor)` quando o
        fluxo rodar (mesmas chaves de seletor de sempre: `id=`, `css=`,
        `texto=`, ...; também aceita `timeout=`)."""
        return self.adicionar(lambda bot: bot.clicar(**seletor), nome=f"clicar {seletor}")

    def digitar(self, texto: str, **seletor: Any) -> Fluxo:
        """Adiciona um passo que chama `Navegador.digitar(texto, **seletor)`
        quando o fluxo rodar."""
        return self.adicionar(lambda bot: bot.digitar(texto, **seletor), nome=f"digitar {seletor}")

    def preencher_formulario(self, campos: dict[str, str | bool] | list[Campo]) -> Fluxo:
        """Adiciona um passo que chama `Navegador.preencher_formulario(campos)`
        quando o fluxo rodar."""
        return self.adicionar(lambda bot: bot.preencher_formulario(campos), nome="preencher formulário")

    def executar(self, bot: Navegador) -> ResultadoFluxo:
        """Roda todos os passos, em ordem, contra `bot`. Cada passo roda
        dentro da sua própria `Etapa` (ver `Navegador.etapa`).

        Raises:
            ErroFluxo: um passo falhou — a exceção original fica em `__cause__`,
                e `erro.resultado` tem as etapas concluídas até ali.
        """
        inicio = time.monotonic()
        resultado = ResultadoFluxo(nome=self.nome)
        logger.info("Fluxo %r iniciado (%d passo(s))", self.nome, len(self._passos))

        for nome_passo, passo in self._passos:
            etapa = bot.etapa(nome_passo)
            try:
                with etapa:
                    passo(bot)
            except Exception as erro:
                resultado.etapas.append(etapa.resultado)
                resultado.duracao_segundos = time.monotonic() - inicio
                raise ErroFluxo(
                    f"Fluxo {self.nome!r} falhou na etapa {nome_passo!r}: {erro}",
                    resultado=resultado,
                ) from erro
            resultado.etapas.append(etapa.resultado)

        resultado.duracao_segundos = time.monotonic() - inicio
        logger.info(
            "Fluxo %r concluído em %.2fs (%d etapa(s), taxa de sucesso: %.0f%%)",
            self.nome,
            resultado.duracao_segundos,
            len(resultado.etapas),
            resultado.taxa_sucesso * 100,
        )
        return resultado
