class ErroAutomacao(Exception):
    """Erro base para a camada de automação web."""


class ErroAoIniciarNavegador(ErroAutomacao):
    """Falha ao iniciar o navegador."""


class ErroNavegadorNaoIniciado(ErroAutomacao):
    """O navegador foi usado antes de iniciar() ser chamado."""


class ErroElementoNaoEncontrado(ErroAutomacao):
    """Elemento ou condição não satisfeita dentro do tempo de espera configurado."""


class ErroSeletorInvalido(ErroAutomacao):
    """Nenhum seletor (ou mais de um) foi informado numa chamada que exige exatamente um."""
