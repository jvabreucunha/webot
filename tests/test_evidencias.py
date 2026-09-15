from pathlib import Path

import pytest

from webot import ErroElementoNaoEncontrado, Navegador


def test_evidencia_registrada_sem_pasta_configurada(pagina_teste_url: str) -> None:
    with Navegador(sem_interface=True) as bot:
        bot.navegar(pagina_teste_url)
        with pytest.raises(ErroElementoNaoEncontrado):
            bot.encontrar(id="nao-existe", timeout=1)

        assert len(bot.evidencias) == 1
        evidencia = bot.evidencias[0]
        assert evidencia.erro
        assert evidencia.url == pagina_teste_url
        assert evidencia.caminho_screenshot is None
        assert evidencia.caminho_html is None


def test_evidencia_com_pasta_salva_screenshot_e_html(tmp_path: Path, pagina_teste_url: str) -> None:
    pasta = tmp_path / "evidencias"
    with Navegador(sem_interface=True, pasta_screenshot_erro=pasta) as bot:
        bot.navegar(pagina_teste_url)
        with pytest.raises(ErroElementoNaoEncontrado):
            bot.encontrar(id="nao-existe", timeout=1)

    evidencia = bot.evidencias[0]
    assert evidencia.caminho_screenshot is not None
    assert evidencia.caminho_screenshot.exists()
    assert evidencia.caminho_html is not None
    assert evidencia.caminho_html.exists()
    assert "<html" in evidencia.caminho_html.read_text(encoding="utf-8").lower()


def test_evidencia_nao_duplica_quando_etapa_propaga(pagina_teste_url: str) -> None:
    with Navegador(sem_interface=True) as bot:
        bot.navegar(pagina_teste_url)
        with pytest.raises(ErroElementoNaoEncontrado):
            with bot.etapa("Falha"):
                bot.encontrar(id="nao-existe", timeout=1)

        assert len(bot.evidencias) == 1
        assert bot.evidencias[0].etapa == "Falha"


def test_evidencia_registrada_mesmo_se_capturada_dentro_da_etapa(pagina_teste_url: str) -> None:
    """Se o código do usuário captura a exceção dentro do `with etapa:`, a
    etapa nunca vê a falha (termina com sucesso) — mas a evidência ainda
    precisa existir, porque o erro aconteceu de verdade."""
    with Navegador(sem_interface=True) as bot:
        bot.navegar(pagina_teste_url)
        with bot.etapa("Etapa que trata o próprio erro") as etapa:
            try:
                bot.encontrar(id="nao-existe", timeout=1)
            except ErroElementoNaoEncontrado:
                pass

        assert etapa.resultado.status == "sucesso"
        assert len(bot.evidencias) == 1
        assert bot.evidencias[0].etapa is None
