"""Observabilidade para automações maiores que um script avulso: agrupar
ações sob um nome (`etapa`), medir a execução inteira (`métricas`), e montar
uma automação reaproveitável e testável (`Fluxo`).
"""

from pathlib import Path

from webot import ErroFluxo, Fluxo, Navegador

_PAGINA_TESTE = (Path(__file__).resolve().parent.parent / "tests/fixtures/pagina_teste.html").as_uri()

with Navegador(sem_interface=True) as bot:
    bot.navegar(_PAGINA_TESTE)

    # ---- etapa(): agrupa ações sob um nome, pra rastrear status/duração/erro ----
    with bot.etapa("Login") as etapa_login:
        bot.digitar("usuario_teste", id="campo-texto")
        bot.clicar(id="botao-clicar")
    r = etapa_login.resultado
    print(f"etapa {r.nome!r}: status={r.status} duração={r.duracao_segundos:.3f}s ações={r.acoes}")

    # também funciona como decorator — aí `tentativas=` reexecuta a função
    # inteira se ela falhar (usada como `with`, uma etapa roda no máximo uma vez)
    @bot.etapa("Confirmar cadastro", tentativas=2)
    def confirmar_cadastro(navegador: Navegador) -> None:
        navegador.clicar(id="botao-clicar")

    confirmar_cadastro(bot)

    # ---- Elemento.metricas: as mesmas métricas do bot, vistas de um elemento ----
    campo = bot.encontrar(id="campo-texto")
    print("mesmas métricas do bot, via elemento?", campo.metricas is bot.metricas)

    # ---- métricas da sessão inteira: ações, retries e falhas acumulados ----
    print("métricas da sessão:", bot.metricas)

    # ---- historico: o passo a passo de cada ação bem-sucedida, na ordem em
    # que aconteceu — inclusive de qual etapa nomeada fazia parte ----
    for registro in bot.historico:
        print(f"  [{registro.etapa or '-'}] {registro.acao} {registro.detalhes}")

# ---- Fluxo: uma automação nomeada, montada sem navegador e executada depois ----
fluxo = Fluxo("Cadastro de cliente")
fluxo.navegar(_PAGINA_TESTE)
fluxo.preencher_formulario({"#campo-texto": "Cliente via Fluxo"})
fluxo.clicar(texto="Clique aqui")
fluxo.adicionar(lambda _bot: print("  (passo customizado rodando)"), nome="passo customizado")

with Navegador(sem_interface=True) as bot:
    resultado = fluxo.executar(bot)

print(f"\nFluxo {resultado.nome!r}: sucesso={resultado.sucesso} taxa_sucesso={resultado.taxa_sucesso:.0%}")
for etapa_resultado in resultado.etapas:
    print(f"  - {etapa_resultado.nome}: {etapa_resultado.status}")

# ---- Fluxo que falha: ErroFluxo carrega o resultado parcial ----
fluxo_com_falha = Fluxo("Fluxo com passo inválido")
fluxo_com_falha.navegar(_PAGINA_TESTE)
fluxo_com_falha.clicar(id="isso-nao-existe", timeout=1)

with Navegador(sem_interface=True) as bot:
    try:
        fluxo_com_falha.executar(bot)
    except ErroFluxo as erro:
        print(f"\nErroFluxo (esperado): {erro}")
        print(f"etapas concluídas antes da falha: {[e.nome for e in erro.resultado.etapas]}")
