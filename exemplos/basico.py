"""Primeiro contato com o webot: abrir o navegador, navegar, ler e clicar.

Para usar outro navegador, troque só a linha `tipo_navegador` abaixo — o
resto do código não muda nada.
"""

from webot import Navegador

tipo_navegador = "chrome"  # troque para "edge" ou "firefox"

with Navegador(tipo_navegador=tipo_navegador, sem_interface=False, anonimo=True, tamanho_janela=(1366, 768)) as bot:
    bot.navegar("https://example.com")
    print("título:", bot.titulo)
    print("url atual:", bot.url_atual)
    print("texto do <h1>:", bot.obter_texto(tag="h1"))

    bot.clicar(css="a")
    print("depois do clique:", bot.url_atual)
