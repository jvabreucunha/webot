"""Interagir com o que já foi encontrado: clicar, digitar, ler estado, e
preencher um formulário inteiro de uma vez. Veja seletores_e_busca.py para
como achar os elementos primeiro.
"""

from pathlib import Path

from webot import Campo, Navegador

_PAGINA_TESTE = (Path(__file__).resolve().parent.parent / "tests/fixtures/pagina_teste.html").as_uri()

with Navegador(sem_interface=True) as bot:
    # ---- clicar/digitar num Elemento já achado (mesmo efeito de bot.clicar/digitar) ----
    bot.navegar("https://the-internet.herokuapp.com/login")
    usuario = bot.encontrar(id="username")
    print("campo visível:", usuario.visivel, "| habilitado:", usuario.habilitado)
    print("timeout padrão via elemento.config:", usuario.config.tempo_espera_padrao)
    usuario.digitar("tomsmith")
    bot.encontrar(id="password").digitar("SuperSecretPassword!")
    bot.clicar(css="button[type='submit']")
    print("resultado do login:", bot.obter_texto(id="flash").strip())

    # ---- obter_atributo/obter_info: ler o elemento sem interagir ----
    bot.navegar("https://the-internet.herokuapp.com/dropdown")
    print("atributo id do dropdown:", bot.obter_atributo("id", id="dropdown"))
    info = bot.obter_info(id="dropdown")
    print(f"obter_info -> tag={info.tag} habilitado={info.habilitado} atributos={list(info.atributos)}")

    # ---- selecionar_por_texto/selecionar_por_valor: <select>, via bot ou via elemento ----
    bot.selecionar_por_texto("Option 1", id="dropdown")
    dropdown = bot.encontrar(id="dropdown")
    dropdown.selecionar_por_valor("2")

    # ---- rolar_para_baixo/rolar_para_elemento/Elemento.rolar_ate ----
    bot.rolar_para_baixo()
    titulo = bot.encontrar(tag="h3")
    bot.rolar_para_elemento(titulo)
    titulo.rolar_ate()

    # ---- enviar_arquivo: input type="file" ----
    arquivo = Path("arquivo_teste.txt").resolve()
    arquivo.write_text("conteúdo de teste gerado pelo exemplo")
    try:
        bot.navegar("https://the-internet.herokuapp.com/upload")
        campo_upload = bot.encontrar(id="file-upload")
        campo_upload.enviar_arquivo(str(arquivo))
        bot.clicar(id="file-submit")
        print("arquivo enviado:", bot.obter_texto(id="uploaded-files"))
    finally:
        arquivo.unlink(missing_ok=True)

    # ---- aguardar(): pausa fixa ou aleatória (simula ritmo humano) ----
    bot.aguardar(0.3)
    bot.aguardar((0.2, 0.5))

    # ---- preencher_formulario(): vários campos de um formulário de uma vez ----
    bot.navegar(_PAGINA_TESTE)
    bot.preencher_formulario(
        {
            "#campo-texto": "Maria",
            "#comentario": "Cadastro via webot",
            "#select-teste": "Dois",  # <select>: seleciona por texto visível
            "#aceite": True,  # checkbox: marca só se ainda não estiver marcado
            "#opcao-b": True,  # radio: idem
        }
    )
    print("checkbox marcado?", bot.encontrar(id="aceite").selecionado)

    # Campo dá seletor flexível (id=, xpath=, nome=, ...) quando um CSS simples não basta:
    bot.preencher_formulario([Campo(valor="Silva", id="campo-texto")])

    # Elemento.preencher_formulario(): mesma coisa, mas escopada — útil
    # quando o formulário está dentro de um modal/seção já encontrada
    formulario = bot.encontrar(id="formulario-teste")
    formulario.preencher_formulario({"#comentario": "preenchido de dentro do form"})
