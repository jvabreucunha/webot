"""Seletores: as palavras-chave que localizam elementos (`id=`, `css=`,
`xpath=`, `nome=`, `classe=`, `tag=`, `texto=`, `texto_link=`,
`texto_link_parcial=`) — sempre exatamente uma por chamada, sem precisar
importar `By` do Selenium.
"""

from pathlib import Path

from webot import Navegador

_PAGINA_TESTE = (Path(__file__).resolve().parent.parent / "tests/fixtures/pagina_teste.html").as_uri()

with Navegador(sem_interface=True) as bot:
    bot.navegar("https://the-internet.herokuapp.com/login")
    bot.encontrar(nome="username")  # nome=: pelo atributo name

    bot.navegar("https://the-internet.herokuapp.com")
    bot.encontrar(texto_link="Multiple Windows")  # texto_link=: <a> pelo texto exato
    bot.encontrar(texto_link_parcial="Window")  # idem, só parte do texto

    bot.navegar("https://the-internet.herokuapp.com/tables")
    bot.encontrar(id="table1")
    bot.encontrar(css="#table1 tbody tr")
    bot.encontrar(xpath="//table[@id='table1']")
    bot.encontrar(tag="table")
    bot.encontrar(classe="tablesorter")
    linhas = bot.encontrar_todos(css="#table1 tbody tr")  # lista com todas que casarem
    print(f"{len(linhas)} linha(s) na tabela")

    # esta_presente(): confere sem lançar exceção se não achar
    print("existe #nao-existe?", bot.esta_presente(id="nao-existe", timeout=1))

    # texto=: acha pelo texto visível direto de qualquer elemento (não só
    # links) — veja tests/fixtures/pagina_teste.html
    bot.navegar(_PAGINA_TESTE)
    bot.encontrar(texto="Clique aqui")

    # busca aninhada: Elemento.encontrar()/.encontrar_todos()/.esta_presente()
    # procuram só dentro do elemento já achado, não na página inteira —
    # ótimo pra tabelas/listas, ou (como aqui) pra escopar um formulário
    formulario = bot.encontrar(id="formulario-teste")
    campo = formulario.encontrar(id="comentario")
    print("campo achado dentro do formulário:", campo.tag)
    print("formulário tem #aceite?", formulario.esta_presente(id="aceite"))
    inputs_do_formulario = formulario.encontrar_todos(tag="input")
    print(f"{len(inputs_do_formulario)} <input> dentro do formulário")
