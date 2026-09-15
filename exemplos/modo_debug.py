"""Modo debug: liga um log estruturado no console de cada ação do bot, sem
precisar configurar o `logging` do Python na mão. Útil pra entender o que a
automação está fazendo de verdade, passo a passo, durante o desenvolvimento.
"""

from webot import Navegador

with Navegador(sem_interface=True) as bot:
    bot.navegar("https://example.com")  # nada é logado ainda (modo debug desligado)

    bot.debug()  # a partir daqui, cada ação aparece no console
    bot.clicar(css="a")
    print("título depois do clique:", bot.titulo)

    bot.debug(False)  # desliga — bot.debug() de novo (sem argumento) ligaria outra vez
    bot.navegar("https://example.com")  # essa navegação não gera log
