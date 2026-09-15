"""Empacota um script de automação num executável standalone (via
PyInstaller) — quem for rodar não precisa de Python, só o navegador
(Chrome/Edge/Firefox) em si.

Requer: pip install webot[empacotar]
"""

from pathlib import Path

from webot import Empacotador

_SCRIPT_EXEMPLO = Path(__file__).resolve().parent / "basico.py"

# ---- uso simples: opções soltas direto no construtor. empacotar() de
# verdade roda o PyInstaller e leva alguns minutos (--collect-all selenium
# copia a lib inteira), então só chamamos uma vez aqui ----
executavel = Empacotador(_SCRIPT_EXEMPLO, nome="RoboBasico").empacotar()
print(f"executável (--onefile) gerado em: {executavel}")

# ---- onedir=True: gera uma pasta em vez de um único .exe (inicia mais
# rápido, pois --onefile descompacta tudo numa pasta temporária a cada
# execução) — só mostrando a configuração, sem rodar de novo ----
empacotador_pasta = Empacotador(_SCRIPT_EXEMPLO, nome="RoboBasico_Pasta", onedir=True)
print(f"\nempacotaria como pasta (onedir): {empacotador_pasta.onedir}")

# ---- sem_console=True: roda "invisível", sem janela de cmd — nesse modo
# print()/input() não funcionam, então esse script precisaria trocar
# print() por logging em arquivo antes de valer a pena empacotar assim ----
empacotador_sem_console = Empacotador(_SCRIPT_EXEMPLO, nome="RoboBasico_SemConsole", sem_console=True)
print(f"empacotaria sem console: {empacotador_sem_console.sem_console}")

# ---- script inexistente falha antes de chamar o PyInstaller ----
try:
    Empacotador("nao_existe.py").empacotar()
except FileNotFoundError as erro:
    print(f"\nErro esperado: {erro}")
