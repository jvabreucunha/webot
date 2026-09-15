"""CLI do webot: `python -m webot <comando>`.

Comandos:
    empacotar <script.py>   compila um script de automação num executável
                            standalone (não precisa de Python instalado na
                            máquina que for rodar — só o navegador em si)
"""

from __future__ import annotations

import sys


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0 if argv else 1

    comando, *resto = argv
    if comando == "empacotar":
        from .empacotar import empacotar_cli

        return empacotar_cli(resto)

    print(f"Comando desconhecido: {comando!r}. Comandos disponíveis: empacotar", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
