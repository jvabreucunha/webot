"""Trilha de auditoria em memória: um registro de cada ação bem-sucedida
realizada pelo `Navegador` (e pelos `Elemento`s dele), na ordem em que
aconteceram — o passo a passo completo de uma execução.

Diferente de `Metricas` (só contadores agregados) e de `Evidencia` (só o
estado no momento de uma falha), `RegistroAcao` cobre toda ação relevante,
com ou sem falha em volta. Por segurança, `detalhes` nunca inclui o valor
digitado em `digitar()` — só o seletor/elemento alvo — pra não acabar
gravando senhas/dados sensíveis em `Navegador.historico` ou num relatório
exportado.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class RegistroAcao:
    """Um item do histórico: uma ação, quando aconteceu, com que detalhes
    (seletor, URL, ...) e dentro de qual etapa nomeada (se houver)."""

    timestamp: datetime
    acao: str
    detalhes: dict[str, Any] = field(default_factory=dict)
    etapa: str | None = None

    def para_dict(self) -> dict[str, Any]:
        """Um dict serializável em JSON (`timestamp` em ISO 8601)."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "acao": self.acao,
            "detalhes": self.detalhes,
            "etapa": self.etapa,
        }
