"""Download de arquivo, captura de tela, e o que fica registrado
automaticamente quando algo dá errado (screenshot + retry configurável).
"""

import tempfile
from pathlib import Path

from webot import ErroElementoNaoEncontrado, Navegador

with tempfile.TemporaryDirectory() as pasta_temporaria:
    pasta_download = Path(pasta_temporaria) / "downloads"
    pasta_erro = Path(pasta_temporaria) / "screenshots_erro"

    # ---- baixar_arquivo(): dispara um download e espera terminar ----
    # `tentativas_retry_transitorio`/`espera_entre_tentativas` controlam
    # quantas vezes e com que intervalo o webot reexecuta uma ação (clicar,
    # digitar, ...) se ela falhar por um erro transitório do Selenium
    # (elemento "stale", ainda não interagível) — aqui mais tolerante que o
    # padrão (2 tentativas/0.3s) só para ilustrar.
    with Navegador(
        sem_interface=True,
        pasta_download=pasta_download,
        tentativas_retry_transitorio=4,
        espera_entre_tentativas=0.2,
    ) as bot:
        bot.navegar("https://the-internet.herokuapp.com/download")
        link = bot.encontrar(css="a[href$='.txt']")
        caminho = bot.baixar_arquivo(lambda: link.clicar())
        print(f"baixado: {caminho.name} em {pasta_download}")

        # ---- capturar_tela(): screenshot manual, a qualquer momento ----
        bot.capturar_tela(str(Path(pasta_temporaria) / "manual.png"))

    # ---- pasta_screenshot_erro: screenshot + HTML automáticos quando uma espera expira ----
    # Desligado por padrão (None). Cada falha também fica em `bot.evidencias`
    # (lista de `Evidencia`), com ou sem essa pasta configurada.
    with Navegador(sem_interface=True, pasta_screenshot_erro=pasta_erro) as bot:
        bot.navegar("https://the-internet.herokuapp.com")
        try:
            bot.encontrar(id="isso-nao-existe-nesta-pagina", timeout=1)
        except ErroElementoNaoEncontrado:
            pass

        evidencia = bot.evidencias[-1]
        print(f"evidência: url={evidencia.url}")
        print(f"  screenshot: {evidencia.caminho_screenshot}")
        print(f"  html: {evidencia.caminho_html}")
