from automacao_web import Navegador

with Navegador(tipo_navegador="edge", sem_interface=False, anonimo=True, tamanho_janela=(1366, 768)) as bot:
    bot.navegar("https://example.com")
    print(bot.titulo)
    print(bot.obter_texto(tag="h1"))
    bot.clicar(css="a")
    print(bot.url_atual)
    input("Pressione Enter para sair...")
