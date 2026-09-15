"""Empacota um script de automação feito com webot num executável standalone
via PyInstaller — não precisa de Python instalado na máquina que for rodar,
só o navegador (Chrome/Edge/Firefox) em si.

Não é compilação nativa de verdade (o Python continua interpretado por
dentro); é o interpretador + o script + as dependências, tudo dentro de um
único arquivo (ou pasta, com `onedir=True`). `selenium-manager` (o binário
que o Selenium usa pra resolver o driver certo sozinho) não é um `.py` — o
PyInstaller não pega ele automaticamente, por isso o `--collect-all selenium`
abaixo em vez de deixar os padrões de detecção do PyInstaller adivinhar.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


class Empacotador:
    """Compila um script de automação feito com webot num executável
    standalone via PyInstaller — quem for rodar não precisa de Python
    instalado, só o navegador (Chrome/Edge/Firefox) em si.

        Empacotador("meu_script.py", nome="MinhaAutomacao").empacotar()
    """

    def __init__(
        self,
        script: str | Path,
        *,
        nome: str | None = None,
        icone: str | Path | None = None,
        sem_console: bool = False,
        onedir: bool = False,
        pasta_saida: str | Path | None = None,
        imports_ocultos: list[str] | None = None,
        arquivos_adicionais: list[str] | None = None,
        argumentos_extras: list[str] | None = None,
    ) -> None:
        """Configura a compilação; nada roda até chamar `empacotar()`.

        Args:
            script: caminho do script Python de automação (feito com webot).
            nome: nome do executável gerado. Padrão: nome do script (sem `.py`).
            icone: caminho de um `.ico` para o executável. Padrão: ícone
                padrão do PyInstaller.
            sem_console: `True` gera o executável sem janela de console
                (`--windowed`). Nesse modo `print()`/`input()` não
                funcionam — use logging em arquivo. Padrão: `False`.
            onedir: `True` gera uma pasta com vários arquivos (`--onedir`)
                em vez de um único `.exe` (`--onefile`, padrão). `--onedir`
                inicia mais rápido, pois `--onefile` descompacta tudo numa
                pasta temporária a cada execução. Padrão: `False`.
            pasta_saida: pasta onde o executável é gerado. Padrão: `dist/`
                na pasta do script.
            imports_ocultos: módulos que o PyInstaller não detecta sozinho
                (`--hidden-import`).
            arquivos_adicionais: arquivos/pastas extras a incluir no
                executável, no formato `'origem;destino'` do `--add-data`
                (ex.: `'modelo.xlsx;.'`).
            argumentos_extras: flags adicionais repassadas cruas ao
                PyInstaller, para casos não cobertos acima.
        """
        self.script = Path(script)
        self.nome = nome
        self.icone = Path(icone) if icone else None
        self.sem_console = sem_console
        self.onedir = onedir
        self.pasta_saida = Path(pasta_saida) if pasta_saida else None
        self.imports_ocultos = imports_ocultos or []
        self.arquivos_adicionais = arquivos_adicionais or []
        self.argumentos_extras = argumentos_extras or []

    def empacotar(self) -> Path:
        """Compila o script configurado num executável standalone.

        Returns:
            Caminho do executável gerado (ou da pasta, se `onedir=True`).

        Raises:
            FileNotFoundError: o script configurado não existe.
            RuntimeError: PyInstaller não está instalado, ou a compilação falhou.
        """
        if not self.script.is_file():
            raise FileNotFoundError(f"Script não encontrado: {self.script}")
        if shutil.which("pyinstaller") is None:
            raise RuntimeError("PyInstaller não encontrado. Instale com: pip install webot[empacotar]")

        nome_final = self.nome or self.script.stem
        separador_add_data = ";" if sys.platform == "win32" else ":"

        comando = [
            "pyinstaller",
            "--onedir" if self.onedir else "--onefile",
            "--name",
            nome_final,
            "--collect-all",
            "selenium",
            "--noconfirm",
        ]
        if self.sem_console:
            comando.append("--windowed")
        if self.icone:
            comando += ["--icon", str(self.icone)]
        if self.pasta_saida:
            comando += ["--distpath", str(self.pasta_saida)]
        for modulo in self.imports_ocultos:
            comando += ["--hidden-import", modulo]
        for item in self.arquivos_adicionais:
            comando += ["--add-data", item.replace(";", separador_add_data)]
        comando += self.argumentos_extras
        comando.append(str(self.script.resolve()))

        resultado = subprocess.run(comando, cwd=self.script.resolve().parent)
        if resultado.returncode != 0:
            raise RuntimeError(f"PyInstaller falhou (código {resultado.returncode})")

        pasta_dist = self.pasta_saida or (self.script.resolve().parent / "dist")
        if self.onedir:
            return pasta_dist / nome_final
        sufixo = ".exe" if sys.platform == "win32" else ""
        return pasta_dist / f"{nome_final}{sufixo}"


def empacotar_cli(argv: list[str]) -> int:
    """Ponto de entrada de `python -m webot empacotar` — lê os argumentos,
    monta um `Empacotador` e chama `.empacotar()`, traduzindo erro em
    mensagem de saída (código 1) em vez de deixar a exceção subir crua."""
    parser = argparse.ArgumentParser(prog="python -m webot empacotar")
    parser.add_argument("script", type=Path, help="script Python da automação")
    parser.add_argument("--nome", default=None, help="nome do executável gerado (padrão: nome do script)")
    parser.add_argument("--icone", type=Path, default=None, help="caminho de um .ico para o executável")
    parser.add_argument(
        "--sem-console", action="store_true", help="gera sem janela de console (print()/input() param de funcionar)"
    )
    parser.add_argument(
        "--onedir", action="store_true", help="gera uma pasta em vez de um único .exe (inicia mais rápido)"
    )
    parser.add_argument(
        "--pasta-saida", type=Path, default=None, help="pasta onde o executável é gerado (padrão: dist/)"
    )
    parser.add_argument(
        "--hidden-import",
        dest="imports_ocultos",
        action="append",
        default=[],
        help="módulo que o PyInstaller não detecta sozinho (repetível)",
    )
    parser.add_argument(
        "--add-data",
        dest="arquivos_adicionais",
        action="append",
        default=[],
        help="arquivo/pasta extra no formato 'origem;destino' (repetível)",
    )
    args = parser.parse_args(argv)

    try:
        caminho = Empacotador(
            args.script,
            nome=args.nome,
            icone=args.icone,
            sem_console=args.sem_console,
            onedir=args.onedir,
            pasta_saida=args.pasta_saida,
            imports_ocultos=args.imports_ocultos,
            arquivos_adicionais=args.arquivos_adicionais,
        ).empacotar()
    except (FileNotFoundError, RuntimeError) as erro:
        print(f"Erro: {erro}", file=sys.stderr)
        return 1

    print(f"Executável gerado em: {caminho}")
    return 0
