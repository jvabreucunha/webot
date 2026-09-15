"""Abas, iframes e alertas de JavaScript: o que fazer quando o conteúdo que
você quer não está na janela/documento principal, ou quando o navegador
abre um diálogo nativo.
"""

from webot import Navegador

with Navegador(sem_interface=False) as bot:
    # ---- aba() como context manager: abre, executa, fecha sozinha ----
    bot.navegar("https://the-internet.herokuapp.com")
    titulo_original = bot.titulo
    with bot.aba("https://example.com") as nova:
        print("na aba nova, título:", nova.titulo)  # 'nova' é o próprio bot, focado na aba nova
    print("de volta na aba original:", bot.titulo == titulo_original)

    # ---- nova_aba()/mudar_para_janela()/fechar_aba_atual(): controle manual ----
    # Use em vez de aba() quando quiser manter várias abas abertas ao mesmo tempo.
    bot.nova_aba("https://the-internet.herokuapp.com/windows")
    bot.clicar(css="a[href='/windows/new']")  # abre mais uma aba
    bot.mudar_para_janela(-1)  # foca na aba mais recente
    print("título da 3a aba:", bot.titulo)
    bot.fechar_aba_atual()  # fecha e volta pra aba anterior sozinha
    bot.fechar_aba_atual()

    # ---- mudar_para_frame(): agir dentro de um <iframe> ----
    bot.navegar("https://the-internet.herokuapp.com/iframe")
    frame = bot.encontrar(id="mce_0_ifr")
    bot.mudar_para_frame(frame)
    bot.clicar(id="tinymce")  # clicar/digitar/etc. já funcionam normalmente aqui dentro
    bot.mudar_para_conteudo_padrao()  # sai do iframe, volta pro documento principal

    # ---- alertas de JavaScript ----
    bot.navegar("https://the-internet.herokuapp.com/javascript_alerts")
    bot.clicar(xpath="//button[text()='Click for JS Alert']")
    print("texto do alerta:", bot.obter_texto_alerta())
    bot.aceitar_alerta()

    bot.clicar(xpath="//button[text()='Click for JS Confirm']")
    bot.recusar_alerta()
    print("resultado ao recusar o confirm:", bot.obter_texto(id="result"))
