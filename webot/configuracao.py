from enum import Enum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class TipoNavegador(str, Enum):
    """Navegadores suportados pelo `Navegador` (campo `tipo_navegador`)."""

    CHROME = "chrome"
    EDGE = "edge"
    FIREFOX = "firefox"


class ConfiguracaoNavegador(BaseModel):
    """Configuração de como o navegador deve subir.

    Por ser um modelo pydantic, um parâmetro com nome errado ou valor de
    tipo/valor inválido já falha na criação, com uma mensagem clara indicando
    qual campo está errado e quais valores são aceitos.

    Selenium 4.6+ resolve o driver correto automaticamente (Selenium Manager),
    então não é preciso apontar caminho de chromedriver/msedgedriver.
    """

    model_config = ConfigDict(extra="forbid")

    tipo_navegador: TipoNavegador = Field(
        default=TipoNavegador.CHROME,
        description="Qual navegador abrir: 'chrome', 'edge' ou 'firefox' (ou TipoNavegador.CHROME/EDGE/FIREFOX).",
    )
    sem_interface: bool = Field(
        default=False,
        description="Modo headless: True roda sem abrir janela nenhuma (útil em servidor/CI).",
    )
    anonimo: bool = Field(
        default=True,
        description=(
            "True abre em modo anônimo/privado (--incognito no Chrome, "
            "--inprivate no Edge, -private no Firefox)."
        ),
    )
    tamanho_janela: tuple[int, int] | None = Field(
        default=(1920, 1080),
        description="(largura, altura) em pixels da janela. None deixa o navegador decidir sozinho.",
    )
    maximizar_janela: bool = Field(
        default=False,
        description="True maximiza a janela ao iniciar; tem prioridade sobre tamanho_janela.",
    )
    pasta_download: Path | None = Field(
        default=None,
        description="Pasta onde os downloads feitos pelo navegador serão salvos. None usa o padrão do sistema.",
    )
    espera_implicita: float = Field(
        default=0,
        ge=0,
        description="Espera implícita (segundos) aplicada globalmente pelo Selenium antes de cada busca. "
        "Recomendado manter em 0 e usar os timeouts explícitos dos métodos (encontrar, clicar, etc.).",
    )
    tempo_espera_padrao: float = Field(
        default=10,
        gt=0,
        description="Timeout padrão (segundos) das esperas explícitas quando `timeout=` não é informado na chamada.",
    )
    tempo_carregamento_pagina: float = Field(
        default=30,
        gt=0,
        description="Tempo máximo (segundos) que navegar() espera o carregamento de uma página antes de falhar.",
    )
    agente_usuario: str | None = Field(
        default=None,
        description="User-Agent customizado a enviar nas requisições. None usa o padrão do navegador.",
    )
    caminho_binario: str | None = Field(
        default=None,
        description="Caminho do executável do navegador, se não estiver no local padrão do sistema.",
    )
    argumentos_extras: list[str] = Field(
        default_factory=list,
        description="Flags de linha de comando adicionais para o navegador (ex.: '--proxy-server=...').",
    )
    pasta_screenshot_erro: Path | None = Field(
        default=None,
        description=(
            "Se definida, tira um screenshot automático nessa pasta sempre que uma "
            "espera expirar (ErroElementoNaoEncontrado). None desativa (padrão)."
        ),
    )
    tentativas_retry_transitorio: int = Field(
        default=2,
        ge=0,
        description=(
            "Quantas vezes reexecutar uma ação (clicar, digitar, ...) se ela falhar "
            "por um erro transitório do Selenium (elemento 'stale', ainda não "
            "interagível, etc.) antes de desistir."
        ),
    )
    espera_entre_tentativas: float = Field(
        default=0.3,
        ge=0,
        description="Segundos de espera entre uma tentativa e a próxima, ao reexecutar por erro transitório.",
    )
