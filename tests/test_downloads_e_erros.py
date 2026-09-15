"""Testes que precisam de uma ConfiguracaoNavegador própria (pasta_download /
pasta_screenshot_erro), então não usam o `bot` compartilhado de conftest.py.
"""

from pathlib import Path

import pytest

from webot import ErroElementoNaoEncontrado, Navegador


def test_baixar_arquivo(tmp_path: Path, pagina_teste_url: str) -> None:
    with Navegador(sem_interface=True, pasta_download=tmp_path) as bot:
        bot.navegar(pagina_teste_url)
        caminho = bot.baixar_arquivo(lambda: bot.clicar(id="link-download"), timeout=10)

    assert caminho.exists()
    assert caminho.read_text(encoding="utf-8") == "conteudo de teste"


def test_baixar_arquivo_sem_pasta_configurada_da_erro(pagina_teste_url: str) -> None:
    with Navegador(sem_interface=True) as bot:
        bot.navegar(pagina_teste_url)
        with pytest.raises(ValueError):
            bot.baixar_arquivo(lambda: bot.clicar(id="link-download"))


def test_screenshot_automatico_em_erro(tmp_path: Path, pagina_teste_url: str) -> None:
    pasta_erro = tmp_path / "erros"
    with Navegador(sem_interface=True, pasta_screenshot_erro=pasta_erro) as bot:
        bot.navegar(pagina_teste_url)
        with pytest.raises(ErroElementoNaoEncontrado):
            bot.encontrar(id="isso-nunca-existe", timeout=1)

    capturas = list(pasta_erro.glob("erro_*.png"))
    assert len(capturas) == 1


def test_sem_pasta_screenshot_erro_nao_tira_nada(tmp_path: Path, pagina_teste_url: str) -> None:
    with Navegador(sem_interface=True) as bot:
        bot.navegar(pagina_teste_url)
        with pytest.raises(ErroElementoNaoEncontrado):
            bot.encontrar(id="isso-nunca-existe", timeout=1)

    assert list(tmp_path.glob("*.png")) == []
