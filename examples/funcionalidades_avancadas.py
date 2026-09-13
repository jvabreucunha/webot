"""Exemplo mais completo, cobrindo boa parte das funcionalidades do Navegador.

Usa o site público https://the-internet.herokuapp.com, feito justamente para
testes de automação, então é seguro rodar contra ele.
"""

from pathlib import Path

from automacao_web import ConfiguracaoNavegador, Navegador, TipoNavegador

config = ConfiguracaoNavegador(
    tipo_navegador=TipoNavegador.CHROME,
    sem_interface=False,
    tempo_espera_padrao=8,
)

with Navegador(config) as bot:
    # ---- dropdown + retrato tipado do elemento (pydantic) ----
    bot.navegar("https://the-internet.herokuapp.com/dropdown")
    bot.selecionar_por_valor("2", id="dropdown")
    info = bot.obter_info(id="dropdown")
    print(f"dropdown -> texto={info.texto!r} habilitado={info.habilitado} atributos={info.atributos}")

    # ---- esperar um tempinho (fixo) entre ações, como num fluxo de RPA ----
    bot.aguardar(0.5)

    # ---- alerta de JavaScript ----
    bot.navegar("https://the-internet.herokuapp.com/javascript_alerts")
    bot.clicar(xpath="//button[text()='Click for JS Alert']")
    print("texto do alerta:", bot.obter_texto_alerta())
    bot.aceitar_alerta()
    print("resultado:", bot.obter_texto(id="result"))

    # ---- espera aleatória (simula ritmo humano) ----
    bot.aguardar((0.3, 0.8))

    # ---- nova aba ----
    bot.nova_aba("https://example.com")
    print("título na nova aba:", bot.titulo)
    bot.fechar_aba_atual()

    # ---- upload de arquivo ----
    arquivo = Path("arquivo_teste.txt").resolve()
    arquivo.write_text("conteúdo de teste gerado pelo exemplo")
    try:
        bot.navegar("https://the-internet.herokuapp.com/upload")
        bot.enviar_arquivo(str(arquivo), id="file-upload")
        bot.clicar(id="file-submit")
        print("arquivo enviado:", bot.obter_texto(id="uploaded-files"))
    finally:
        arquivo.unlink(missing_ok=True)

    # ---- checar presença sem lançar exceção ----
    if bot.esta_presente(id="nao-existe", timeout=1):
        print("nunca deveria cair aqui")
    else:
        print("elemento inexistente detectado corretamente")

    # ---- captura de tela ----
    bot.capturar_tela("captura_final.png")
    print("screenshot salvo em captura_final.png")
