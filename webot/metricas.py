"""Contadores agregados de uma execução (sessão do `Navegador` inteira, ou o
recorte de uma `Etapa`/`Fluxo`).

`falhas` conta especificamente etapas que terminaram em erro (ver `Etapa`) —
não qualquer exceção solta que aconteça fora de uma etapa.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Metricas:
    """Contadores de uma execução: quantas ações rodaram, quantas etapas
    falharam, e quantos retries de erro transitório aconteceram.

    `Navegador.metricas` acumula isso pra sessão inteira. `Etapa` tira uma
    "foto" no início e no fim pra saber o que aconteceu só durante ela
    (ver `Etapa.resultado`).
    """

    acoes: int = 0
    falhas: int = 0
    retries: int = 0

    def copia(self) -> Metricas:
        """Uma cópia independente (pra comparar antes/depois sem referência compartilhada)."""
        return Metricas(acoes=self.acoes, falhas=self.falhas, retries=self.retries)

    def __sub__(self, outra: Metricas) -> Metricas:
        return Metricas(
            acoes=self.acoes - outra.acoes,
            falhas=self.falhas - outra.falhas,
            retries=self.retries - outra.retries,
        )
