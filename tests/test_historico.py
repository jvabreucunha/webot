"""Testes do histórico de ações (`Navegador.historico` / `RegistroAcao`)."""

import json
from pathlib import Path

from webot import Navegador
from webot.historico import RegistroAcao


def test_registro_acao_para_dict_serializa_timestamp() -> None:
    from datetime import datetime

    registro = RegistroAcao(timestamp=datetime(2026, 1, 1, 10, 0, 0), acao="clicar", detalhes={"seletor": {"id": "x"}})
    dado = registro.para_dict()
    assert dado["timestamp"] == "2026-01-01T10:00:00"
    assert dado["acao"] == "clicar"
    assert dado["detalhes"] == {"seletor": {"id": "x"}}
    assert dado["etapa"] is None
    json.dumps(dado)  # não levanta TypeError


def test_historico_registra_navegar_encontrar_clicar_digitar_em_ordem(pagina_teste_url: str) -> None:
    with Navegador(sem_interface=True) as bot:
        bot.navegar(pagina_teste_url)
        bot.encontrar(id="titulo")
        bot.clicar(id="botao-clicar")
        bot.digitar("x", id="campo-texto")

        acoes = [registro.acao for registro in bot.historico]
        assert acoes == ["navegar", "encontrar", "clicar", "digitar"]
        assert bot.historico[0].detalhes == {"url": pagina_teste_url}
        assert bot.historico[2].detalhes == {"seletor": {"id": "botao-clicar"}}


def test_historico_de_digitar_nunca_inclui_o_texto_digitado(pagina_teste_url: str) -> None:
    """Regressão de segurança: senha/dado sensível digitado não pode acabar
    gravado em historico (nem, por consequência, num relatório exportado)."""
    with Navegador(sem_interface=True) as bot:
        bot.navegar(pagina_teste_url)
        bot.digitar("senha-super-secreta", id="campo-texto")

        registro_digitar = next(r for r in bot.historico if r.acao == "digitar")
        assert "senha-super-secreta" not in json.dumps(registro_digitar.para_dict())


def test_historico_de_acoes_via_elemento_ja_encontrado(pagina_teste_url: str) -> None:
    with Navegador(sem_interface=True) as bot:
        bot.navegar(pagina_teste_url)
        botao = bot.encontrar(id="botao-clicar")
        botao.clicar()

        registro_clicar = next(r for r in bot.historico if r.acao == "clicar")
        assert registro_clicar.detalhes == {"elemento": "<button>"}


def test_historico_marca_a_etapa_ativa(pagina_teste_url: str) -> None:
    with Navegador(sem_interface=True) as bot:
        bot.navegar(pagina_teste_url)
        with bot.etapa("Login"):
            bot.clicar(id="botao-clicar")

        registro_navegar = next(r for r in bot.historico if r.acao == "navegar")
        registro_clicar = next(r for r in bot.historico if r.acao == "clicar")
        assert registro_navegar.etapa is None
        assert registro_clicar.etapa == "Login"


def test_salvar_relatorio_json_inclui_historico(tmp_path: Path, pagina_teste_url: str) -> None:
    caminho_relatorio = tmp_path / "relatorio.json"
    with Navegador(sem_interface=True) as bot:
        bot.navegar(pagina_teste_url)
        bot.clicar(id="botao-clicar")
        bot.salvar_relatorio_json(caminho_relatorio)

    relatorio = json.loads(caminho_relatorio.read_text(encoding="utf-8"))
    assert [item["acao"] for item in relatorio["historico"]] == ["navegar", "clicar"]
