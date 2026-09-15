from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _version

from .configuracao import ConfiguracaoNavegador, TipoNavegador
from .elemento import Elemento
from .empacotar import Empacotador
from .etapa import Etapa, ResultadoEtapa
from .evidencias import Evidencia
from .excecoes import (
    ErroAoIniciarNavegador,
    ErroAutomacao,
    ErroElementoNaoEncontrado,
    ErroNavegadorNaoIniciado,
    ErroSeletorInvalido,
)
from .fluxo import ErroFluxo, Fluxo, ResultadoFluxo
from .formulario import Campo
from .metricas import Metricas
from .navegador import Navegador
from .resultados import InfoElemento

try:
    __version__ = _version("webot")
except PackageNotFoundError:
    __version__ = "0.0.0+local"

__all__ = [
    "__version__",
    "Navegador",
    "Elemento",
    "ConfiguracaoNavegador",
    "TipoNavegador",
    "InfoElemento",
    "Campo",
    "Etapa",
    "ResultadoEtapa",
    "Fluxo",
    "ResultadoFluxo",
    "Metricas",
    "Evidencia",
    "Empacotador",
    "ErroAutomacao",
    "ErroAoIniciarNavegador",
    "ErroElementoNaoEncontrado",
    "ErroNavegadorNaoIniciado",
    "ErroSeletorInvalido",
    "ErroFluxo",
]
