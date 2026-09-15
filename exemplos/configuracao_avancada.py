"""Ciclo de vida manual (sem `with`), escape hatch pro WebDriver puro, e os
campos mais avançados de `ConfiguracaoNavegador`.
"""

from selenium.common.exceptions import TimeoutException

from webot import ConfiguracaoNavegador, ErroAoIniciarNavegador, Navegador

# ---- ciclo de vida manual: iniciar()/encerrar() sem `with` ----
# `with Navegador(...) as bot:` é o jeito recomendado (fecha sozinho mesmo se
# der exceção) — isso aqui mostra que dá pra controlar na mão, caso seu fluxo
# precise manter o navegador aberto entre chamadas de funções diferentes.
bot = Navegador(sem_interface=True)
bot.iniciar()
try:
    bot.navegar("https://the-internet.herokuapp.com")
    bot.clicar(css="a[href='/dropdown']")
    bot.voltar()
    bot.avancar()
    bot.atualizar()

    # driver_bruto: escape hatch pro WebDriver puro do Selenium, para quando
    # a abstração realmente não cobrir o que você precisa
    cookies = bot.driver_bruto.get_cookies()
    print(f"driver_bruto.get_cookies() -> {len(cookies)} cookie(s)")
finally:
    bot.encerrar()

# ---- ConfiguracaoNavegador: campos mais avançados ----
config = ConfiguracaoNavegador(
    maximizar_janela=True,
    espera_implicita=0,  # recomendado manter em 0 — ver descrição do campo
    tempo_espera_padrao=8,  # timeout padrão de encontrar/clicar/etc., em segundos
    agente_usuario="webot-exemplo/1.0",
    argumentos_extras=["--window-position=50,50"],
)
with Navegador(config) as bot:
    bot.navegar("https://example.com")
    agente = bot.executar_script("return navigator.userAgent;")
    print("User-Agent customizado aplicado:", agente)

# ---- tempo_carregamento_pagina baixo demais: propaga TimeoutException do Selenium ----
# É o único caso documentado onde uma exceção "crua" do Selenium escapa. Com
# um valor tão baixo, o estouro às vezes já acontece na própria inicialização
# do navegador (não só dentro de navegar()) — por isso o try envolve os dois.
try:
    with Navegador(tempo_carregamento_pagina=0.001) as bot:
        bot.navegar("https://the-internet.herokuapp.com")
except TimeoutException:
    print("TimeoutException do Selenium propagou, como documentado")

# ---- caminho_binario inválido: falha ao iniciar, de forma clara ----
config_invalida = ConfiguracaoNavegador(caminho_binario="/caminho/que/nao/existe")
try:
    with Navegador(config_invalida):
        pass
except ErroAoIniciarNavegador as erro:
    print("ErroAoIniciarNavegador (esperado):", erro)
