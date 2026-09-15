"""Esperas em pt-br (sem tocar em expected_conditions do Selenium), e o
escape hatch para condições customizadas quando os métodos prontos não
bastarem.
"""

from selenium.webdriver.support import expected_conditions as EC

from webot import Navegador

with Navegador(sem_interface=False) as bot:
    # ---- esperar_url_conter(): útil depois de um clique que navega ----
    bot.navegar("https://the-internet.herokuapp.com/redirector")
    bot.clicar(id="redirect")
    bot.esperar_url_conter("/status_codes", timeout=5)
    print("url depois do redirect:", bot.url_atual)

    # ---- esperar_titulo_conter(): espera o <title> mudar ----
    bot.executar_script("setTimeout(() => { document.title = 'Carregado!'; }, 300);")
    bot.esperar_titulo_conter("Carregado", timeout=2)
    print("título mudou:", bot.titulo)

    # ---- esperar_texto_conter(): espera o texto de um elemento existente mudar ----
    bot.navegar("https://the-internet.herokuapp.com/dynamic_loading/2")
    bot.clicar(css="#start button")
    bot.esperar_texto_conter("Hello World!", id="finish", timeout=10)
    print("texto carregado (via AJAX):", bot.obter_texto(id="finish"))

    # ---- esperar_rede_ociosa(): espera o DOM parar de mudar ----
    # Heurística por MutationObserver (não é detecção real de rede — isso
    # exigiria CDP, só em Chromium); funciona nos 3 navegadores.
    bot.executar_script(
        """
        window.__contador__ = 0;
        var intervalo = setInterval(function () {
            document.body.appendChild(document.createElement('div'));
            window.__contador__++;
            if (window.__contador__ >= 5) clearInterval(intervalo);
        }, 200);
        """
    )
    bot.esperar_rede_ociosa(tempo_estavel=0.4, timeout=5)
    print("rede ficou ociosa depois de", bot.executar_script("return window.__contador__;"), "inserções")

    # ---- esperar_ate(): escape hatch pra qualquer condição do Selenium ----
    bot.nova_aba("https://example.com")
    bot.esperar_ate(EC.number_of_windows_to_be(2), timeout=3, descricao="2 janelas abertas")
    print("esperar_ate confirmou 2 janelas abertas")
    bot.fechar_aba_atual()
