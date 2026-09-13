from .configuracao import ConfiguracaoNavegador, TipoNavegador
from .excecoes import (
    ErroAutomacao,
    ErroAoIniciarNavegador,
    ErroElementoNaoEncontrado,
    ErroNavegadorNaoIniciado,
    ErroSeletorInvalido,
)
from .navegador import Navegador
from .resultados import InfoElemento

__all__ = [
    "Navegador",
    "ConfiguracaoNavegador",
    "TipoNavegador",
    "InfoElemento",
    "ErroAutomacao",
    "ErroAoIniciarNavegador",
    "ErroElementoNaoEncontrado",
    "ErroNavegadorNaoIniciado",
    "ErroSeletorInvalido",
]
