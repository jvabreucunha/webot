"""Registro do que aconteceu no momento de uma falha, pra facilitar auditoria
e debugging depois: screenshot, HTML da página, URL, timestamp, etapa e ação.

A captura em si (quem sabe tirar screenshot, ler `driver.page_source`, etc.)
é responsabilidade do `Navegador` (`_registrar_evidencia`) — aqui só mora o
formato do registro.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class Evidencia:
    """Um retrato do estado da automação no momento de uma falha.

    `caminho_screenshot`/`caminho_html` só vêm preenchidos se
    `ConfiguracaoNavegador.pasta_screenshot_erro` estiver configurada — sem
    isso, a evidência ainda é registrada (em `Navegador.evidencias`), só sem
    os arquivos.
    """

    timestamp: datetime
    erro: str
    etapa: str | None = None
    acao: str | None = None
    url: str | None = None
    caminho_screenshot: Path | None = None
    caminho_html: Path | None = None

    def para_dict(self) -> dict[str, Any]:
        """Um dict serializável em JSON com os mesmos campos (`timestamp`
        em ISO 8601, caminhos como texto) — útil pra exportar um relatório
        da execução."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "erro": self.erro,
            "etapa": self.etapa,
            "acao": self.acao,
            "url": self.url,
            "caminho_screenshot": str(self.caminho_screenshot) if self.caminho_screenshot else None,
            "caminho_html": str(self.caminho_html) if self.caminho_html else None,
        }
