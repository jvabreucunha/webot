from pathlib import Path

import pytest

from webot import Navegador


@pytest.fixture(scope="session")
def pagina_teste_url() -> str:
    caminho = Path(__file__).parent / "fixtures" / "pagina_teste.html"
    return caminho.resolve().as_uri()


@pytest.fixture(scope="session")
def _navegador_sessao():
    with Navegador(sem_interface=True, tempo_espera_padrao=5) as navegador:
        yield navegador


@pytest.fixture
def bot(_navegador_sessao: Navegador, pagina_teste_url: str) -> Navegador:
    """Um `Navegador` já na página de teste, com a página recarregada a cada teste
    (isolamento entre testes), mas reaproveitando o mesmo browser (rapidez)."""
    _navegador_sessao.navegar(pagina_teste_url)
    return _navegador_sessao
