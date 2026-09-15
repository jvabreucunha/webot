"""Testes de `Empacotador`.

A maior parte mocka `subprocess.run`/`shutil.which` (compilar de verdade leva
minutos, e não precisa disso pra verificar os caminhos de erro e a montagem
do comando). As classes marcadas como integração no final rodam o PyInstaller
de verdade e são puladas automaticamente se ele não estiver instalado.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from webot.empacotar import Empacotador, empacotar_cli


def test_empacotar_script_inexistente_da_erro(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        Empacotador(tmp_path / "nao_existe.py").empacotar()


def test_empacotar_sem_pyinstaller_instalado_da_erro(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    script = tmp_path / "automacao.py"
    script.write_text("print('oi')")
    monkeypatch.setattr("webot.empacotar.shutil.which", lambda _: None)

    with pytest.raises(RuntimeError, match="PyInstaller"):
        Empacotador(script).empacotar()


def test_empacotar_cli_script_inexistente_retorna_codigo_1(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    codigo = empacotar_cli([str(tmp_path / "nao_existe.py")])
    assert codigo == 1
    assert "Erro" in capsys.readouterr().err


class _ResultadoFalso:
    returncode = 0


def _capturar_comando(monkeypatch: pytest.MonkeyPatch) -> list[list[str]]:
    comandos_chamados: list[list[str]] = []

    def _run_falso(comando: list[str], cwd: Path) -> _ResultadoFalso:
        comandos_chamados.append(comando)
        return _ResultadoFalso()

    monkeypatch.setattr("webot.empacotar.shutil.which", lambda _: "/usr/bin/pyinstaller")
    monkeypatch.setattr("webot.empacotar.subprocess.run", _run_falso)
    return comandos_chamados


def test_empacotar_monta_comando_pyinstaller_padrao(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    script = tmp_path / "automacao.py"
    script.write_text("print('oi')")
    comandos_chamados = _capturar_comando(monkeypatch)

    caminho = Empacotador(script, nome="minha_automacao").empacotar()

    assert len(comandos_chamados) == 1
    comando = comandos_chamados[0]
    assert "--onefile" in comando
    assert "--collect-all" in comando and "selenium" in comando
    assert "--name" in comando and "minha_automacao" in comando
    assert "--windowed" not in comando
    assert caminho.name.startswith("minha_automacao")
    assert caminho.parent.name == "dist"


def test_empacotar_repassa_todas_as_opcoes_para_o_comando(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    script = tmp_path / "automacao.py"
    script.write_text("print('oi')")
    icone = tmp_path / "logo.ico"
    icone.write_text("")
    pasta_saida = tmp_path / "saida"
    comandos_chamados = _capturar_comando(monkeypatch)

    caminho = Empacotador(
        script,
        nome="robo",
        icone=icone,
        sem_console=True,
        onedir=True,
        pasta_saida=pasta_saida,
        imports_ocultos=["pkg_oculto"],
        arquivos_adicionais=["modelo.xlsx;."],
        argumentos_extras=["--clean"],
    ).empacotar()

    comando = comandos_chamados[0]
    assert "--onedir" in comando and "--onefile" not in comando
    assert "--windowed" in comando
    assert "--icon" in comando and str(icone) in comando
    assert "--distpath" in comando and str(pasta_saida) in comando
    assert "--hidden-import" in comando and "pkg_oculto" in comando
    assert "--add-data" in comando
    assert "--clean" in comando
    assert caminho == pasta_saida / "robo"


def test_empacotar_add_data_converte_separador_fora_do_windows(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`arquivos_adicionais` é documentado no formato 'origem;destino'
    (sempre com ';'); fora do Windows o --add-data do PyInstaller espera
    ':', então o Empacotador converte antes de montar o comando."""
    script = tmp_path / "automacao.py"
    script.write_text("print('oi')")
    monkeypatch.setattr("webot.empacotar.sys.platform", "linux")
    comandos_chamados = _capturar_comando(monkeypatch)

    Empacotador(script, arquivos_adicionais=["modelo.xlsx;."]).empacotar()

    comando = comandos_chamados[0]
    indice = comando.index("--add-data")
    assert comando[indice + 1] == "modelo.xlsx:."


def test_empacotar_pyinstaller_falhando_da_erro(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    script = tmp_path / "automacao.py"
    script.write_text("print('oi')")

    class _ResultadoComFalha:
        returncode = 1

    monkeypatch.setattr("webot.empacotar.shutil.which", lambda _: "/usr/bin/pyinstaller")
    monkeypatch.setattr("webot.empacotar.subprocess.run", lambda comando, cwd: _ResultadoComFalha())

    with pytest.raises(RuntimeError, match="falhou"):
        Empacotador(script).empacotar()


def test_empacotar_cli_repassa_flags_para_empacotador(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    script = tmp_path / "automacao.py"
    script.write_text("print('oi')")
    comandos_chamados = _capturar_comando(monkeypatch)

    codigo = empacotar_cli(
        [str(script), "--nome", "robo_cli", "--onedir", "--sem-console", "--hidden-import", "pkg_x"]
    )

    assert codigo == 0
    comando = comandos_chamados[0]
    assert "--onedir" in comando
    assert "--windowed" in comando
    assert "--hidden-import" in comando and "pkg_x" in comando
    assert "robo_cli" in comando


# ---- integração: roda o PyInstaller de verdade (pulado se não instalado) ----

pytestmark_integracao = pytest.mark.skipif(
    shutil.which("pyinstaller") is None, reason="PyInstaller não instalado neste ambiente"
)


@pytestmark_integracao
def test_integracao_empacotar_onefile_gera_executavel_funcional(tmp_path: Path) -> None:
    script = tmp_path / "ola.py"
    script.write_text("print('ola do executavel empacotado')")

    caminho = Empacotador(script, nome="ola_onefile").empacotar()

    assert caminho.is_file()
    resultado = subprocess.run([str(caminho)], capture_output=True, text=True, timeout=60)
    assert resultado.returncode == 0
    assert "ola do executavel empacotado" in resultado.stdout


@pytestmark_integracao
def test_integracao_empacotar_onedir_gera_pasta_com_executavel(tmp_path: Path) -> None:
    script = tmp_path / "ola.py"
    script.write_text("print('ola da pasta empacotada')")

    caminho = Empacotador(script, nome="ola_onedir", onedir=True).empacotar()

    assert caminho.is_dir()
    sufixo = ".exe" if sys.platform == "win32" else ""
    executavel = caminho / f"ola_onedir{sufixo}"
    assert executavel.is_file()
    resultado = subprocess.run([str(executavel)], capture_output=True, text=True, timeout=60)
    assert resultado.returncode == 0
    assert "ola da pasta empacotada" in resultado.stdout
