# Referência da API do webot (para IA)

> Gerado automaticamente por `scripts/gerar_referencia_ia.py` a partir do código-fonte — não edite à mão. Rode o script de novo depois de qualquer mudança na API pública para atualizar este arquivo.

## Visão geral

webot é uma abstração em pt-br sobre o Selenium para automação/RPA web.

Fundamentos:
- `Navegador` é a classe principal: controla o ciclo de vida do navegador
  (Chrome/Edge/Firefox) e expõe métodos em português (navegar, clicar,
  digitar, encontrar, ...). Use como context manager:
  `with Navegador(tipo_navegador="chrome") as bot: ...` — isso abre o
  navegador e garante que ele feche sozinho ao final.
- Localizar elementos é sempre por palavra-chave — `id=`, `css=`, `xpath=`,
  `nome=`, `classe=`, `tag=`, `texto_link=`, `texto_link_parcial=` —
  exatamente uma por chamada. Nunca um objeto `By` do Selenium.
- `bot.encontrar(**seletor)` / `bot.encontrar_todos(**seletor)` NÃO devolvem
  o WebElement puro do Selenium: devolvem um `Elemento` (ou lista deles), um
  envelope com os MESMOS métodos de interação (`.clicar()`, `.digitar()`,
  `.obter_texto()`, `.obter_atributo()`, ...) já mirados naquele elemento
  específico — não precisa de seletor de novo. `Elemento` também tem busca
  ANINHADA: `elemento.encontrar(**seletor)` procura só dentro dele (ótimo
  para tabelas/listas).
- Todo método de interação do `Navegador` (clicar, digitar, obter_texto, ...)
  também aceita `elemento=` (um `Elemento` já encontrado) como alternativa ao
  seletor — nunca os dois juntos.
- Configuração via `ConfiguracaoNavegador` (modelo pydantic, validado — nome
  ou tipo errado falha na hora) ou parâmetros soltos direto em
  `Navegador(...)`, nunca os dois juntos.
- Toda exceção da biblioteca herda de `ErroAutomacao`.
- Retry automático em erros transitórios do Selenium (elemento "stale",
  ainda não interagível), configurável.

Exemplo mínimo:

```python
from webot import Navegador

with Navegador(tipo_navegador="chrome", sem_interface=True) as bot:
    bot.navegar("https://exemplo.com")
    bot.clicar(css="button.enviar")
    itens = bot.encontrar_todos(css=".item")
    itens[2].clicar()
```

# Classes principais

## `Navegador`

Abstração em pt-br que encapsula o WebDriver do Selenium.

Uso simples, sem precisar importar nada do Selenium:

    from webot import Navegador

    with Navegador(tipo_navegador="chrome", sem_interface=False) as bot:
        bot.navegar("https://exemplo.com")
        bot.clicar(css="button.enviar")
        bot.digitar("relatorio", nome="busca")
        texto = bot.obter_texto(tag="h1")

Localizar elementos é sempre por palavra-chave: id=, css=, xpath=, nome=,
classe=, tag=, texto=, texto_link= ou texto_link_parcial= (exatamente um
por chamada).

`encontrar()`/`encontrar_todos()` devolvem `Elemento`, um envelope com os
mesmos métodos de interação (`.clicar()`, `.digitar()`, ...) já mirados
naquele elemento específico — útil para filtrar uma lista e agir num item,
ou para buscar um elemento *dentro* de outro (`linha.encontrar(css=".preco")`):

    itens = bot.encontrar_todos(css=".item")
    itens[2].clicar()

### Propriedades

#### `driver_bruto` (propriedade)

Acesso ao WebDriver puro do Selenium, para casos que a abstração não cobre.

#### `titulo` (propriedade)

Título (`<title>`) da página atual.

#### `url_atual` (propriedade)

URL da aba atual.

### Métodos

#### `__init__(config: ConfiguracaoNavegador | None = None, *, tipo_navegador: TipoNavegador | None = None, sem_interface: bool | None = None, anonimo: bool | None = None, tamanho_janela: tuple[int, int] | None = None, maximizar_janela: bool | None = None, pasta_download: str | Path | None = None, espera_implicita: float | None = None, tempo_espera_padrao: float | None = None, tempo_carregamento_pagina: float | None = None, agente_usuario: str | None = None, caminho_binario: str | None = None, argumentos_extras: list[str] | None = None, pasta_screenshot_erro: str | Path | None = None, tentativas_retry_transitorio: int | None = None, espera_entre_tentativas: float | None = None) -> None`

Cria o navegador a partir de opções soltas (uso simples) ou de um
`ConfiguracaoNavegador` pronto (para reaproveitar a mesma config em
vários bots). Não misture os dois.

Args:
    config: uma `ConfiguracaoNavegador` já pronta. Use isso (em vez
        das opções soltas abaixo) quando quiser montar a config uma
        vez e reaproveitar em vários bots.
    tipo_navegador: 'chrome', 'edge' ou 'firefox' (ou
        `TipoNavegador.CHROME`/`EDGE`/`FIREFOX`). Padrão: chrome.
    sem_interface: modo headless — True roda sem abrir janela nenhuma
        (útil em servidor/CI). Padrão: False.
    anonimo: True abre em modo anônimo/privado (--incognito no Chrome,
        --inprivate no Edge, -private no Firefox). Padrão: True.
    tamanho_janela: (largura, altura) em pixels. Padrão: (1920, 1080).
        `None` aqui significa "não informado" (mantém o padrão); para
        abrir sem tamanho fixo de verdade, monte um
        `ConfiguracaoNavegador(tamanho_janela=None)` e passe como `config`.
    maximizar_janela: True maximiza a janela ao iniciar; tem
        prioridade sobre tamanho_janela. Padrão: False.
    pasta_download: pasta onde os downloads serão salvos. Padrão: a
        pasta padrão do navegador.
    espera_implicita: espera implícita (segundos) do Selenium antes de
        cada busca. Recomendado deixar em 0 e usar os `timeout=` dos
        métodos. Padrão: 0.
    tempo_espera_padrao: timeout padrão (segundos) das esperas
        explícitas quando `timeout=` não é passado na chamada.
        Padrão: 10.
    tempo_carregamento_pagina: tempo máximo (segundos) que navegar()
        espera a página carregar antes de falhar. Padrão: 30.
    agente_usuario: User-Agent customizado. Padrão: o do navegador.
    caminho_binario: caminho do executável do navegador, se não
        estiver no local padrão do sistema.
    argumentos_extras: flags de linha de comando adicionais (ex.:
        '--proxy-server=...').
    pasta_screenshot_erro: se definida, tira um screenshot automático
        nessa pasta sempre que uma espera expirar
        (`ErroElementoNaoEncontrado`). Padrão: desativado (None).
    tentativas_retry_transitorio: quantas vezes reexecutar uma ação
        (clicar, digitar, ...) se ela falhar por um erro transitório
        do Selenium (elemento "stale", ainda não interagível) antes de
        desistir. Padrão: 2.
    espera_entre_tentativas: segundos de espera entre uma tentativa e
        a próxima, nesse retry. Padrão: 0.3.

#### `aba(url: str | None = None) -> Generator[Navegador, None, None]`

Abre uma aba nova, roda o bloco `with` nela, e fecha a aba sozinha
ao sair — voltando pra aba original, mesmo se o bloco levantar exceção.

    with bot.aba("https://outro-site.com") as nova:
        nova.clicar(css=".algo")
    # de volta na aba original aqui

#### `aceitar_alerta(timeout: float | None = None) -> None`

Espera um alerta JS (`alert`/`confirm`/`prompt`) aparecer e clica em OK/aceitar.

Args:
    timeout: segundos a esperar; usa `tempo_espera_padrao` se omitido.

#### `aguardar(segundos: float | tuple[float, float]) -> None`

Pausa a execução.

Aceita um tempo fixo (`bot.aguardar(1.5)`) ou um intervalo para uma
pausa aleatória (`bot.aguardar((0.5, 1.5))`), útil para simular um
ritmo mais humano entre ações num fluxo de RPA.

#### `atualizar() -> None`

Recarrega a página atual (equivalente a F5).

#### `avancar() -> None`

Avança uma página no histórico de navegação.

#### `baixar_arquivo(disparar: Callable[[], None], *, timeout: float = 30.0) -> Path`

Dispara um download e aguarda o arquivo terminar de baixar em
`pasta_download` (precisa estar configurado), devolvendo o caminho.

`disparar` é uma função sem argumentos que inicia o download
(tipicamente um `lambda: bot.clicar(css="a.download")`) — chamada só
depois de tirar uma "foto" da pasta, para conseguir identificar qual
arquivo é novo. Ignora arquivos temporários do navegador
(`.crdownload`/`.part`/`.tmp`) até o download terminar de verdade.

#### `capturar_tela(caminho: str) -> None`

Salva um screenshot (PNG) da página atual.

Args:
    caminho: caminho do arquivo a salvar (ex.: `"tela.png"`).

#### `clicar(*, elemento: Elemento | None = None, timeout: float | None = None, **seletor: str | None) -> None`

Clica no elemento. Passe um seletor (`css=`, `id=`, ...) para achar e
clicar em um só passo, ou um `elemento` já obtido antes via `encontrar`/
`encontrar_todos` (por exemplo, para clicar no 3º item de uma lista —
equivalente a chamar `.clicar()` direto no `Elemento`).

#### `debug(ativar: bool = True) -> None`

Liga (ou desliga) log estruturado no console de cada ação
realizada pelo webot a partir deste momento — sem precisar configurar
o `logging` do Python na mão.

    bot.debug()       # liga
    bot.debug(False)  # desliga

Reaproveita os `logger.info`/`.warning`/`.error` que já existem em
cada método (navegar, clicar, etapas, retries, ...); não é por
`Navegador`, e sim por processo — `logging` é global no Python, então
ligar aqui mostra os logs de qualquer `Navegador` ativo.

Args:
    ativar: `True` liga, `False` desliga. Chamar de novo com o mesmo
        valor não faz nada (não duplica o log).

#### `digitar(texto: str, *, elemento: Elemento | None = None, limpar: bool = True, timeout: float | None = None, **seletor: str | None) -> None`

Espera o elemento ficar visível e digita `texto` nele.

Args:
    texto: o que digitar.
    elemento: um `Elemento` já encontrado, como alternativa ao
        seletor (ver "Achar agora, agir depois" no README).
    limpar: se `True` (padrão), limpa o campo antes de digitar.
    timeout: segundos a esperar; usa `tempo_espera_padrao` se omitido.
    **seletor: exatamente uma chave (`id=`, `css=`, ...) — não use
        junto com `elemento=`.

Raises:
    ErroSeletorInvalido: `elemento=` e seletor usados juntos, ou
        seletor ausente/duplicado/desconhecido.
    ErroElementoNaoEncontrado: elemento não ficou visível a tempo.

#### `encerrar() -> None`

Fecha o navegador. Idempotente e seguro de chamar mesmo se o
navegador ainda não tiver sido iniciado ou já estiver fechado.

#### `encontrar(*, timeout: float | None = None, **seletor: str | None) -> Elemento`

Espera um elemento existir no DOM e o devolve.

Args:
    timeout: segundos a esperar; usa `tempo_espera_padrao` (config)
        se omitido.
    **seletor: exatamente uma chave entre `id=`, `css=`, `xpath=`,
        `nome=`, `classe=`, `tag=`, `texto=`, `texto_link=`,
        `texto_link_parcial=`.

Returns:
    O `Elemento` encontrado, já pronto para `.clicar()`, `.digitar()`,
    `.encontrar()` (busca aninhada), etc.

Raises:
    ErroSeletorInvalido: seletor ausente, duplicado ou desconhecido.
    ErroElementoNaoEncontrado: nada casou com o seletor dentro do timeout.

#### `encontrar_todos(*, timeout: float | None = None, **seletor: str | None) -> list[Elemento]`

Como `encontrar()`, mas espera existir pelo menos um elemento e
devolve todos os que casarem com o seletor, na ordem em que aparecem
no DOM.

Args:
    timeout: segundos a esperar; usa `tempo_espera_padrao` se omitido.
    **seletor: mesmas chaves de `encontrar()`.

Returns:
    Lista de `Elemento` (pode ter 1 ou mais itens; nunca vazia — se
    nada casar, levanta `ErroElementoNaoEncontrado` em vez de []).

Raises:
    ErroSeletorInvalido: seletor ausente, duplicado ou desconhecido.
    ErroElementoNaoEncontrado: nada casou com o seletor dentro do timeout.

#### `enviar_arquivo(caminho_arquivo: str, *, elemento: Elemento | None = None, timeout: float | None = None, **seletor: str | None) -> None`

Envia um arquivo para um `<input type="file">`, escrevendo o
caminho absoluto nele (não abre nenhum seletor de arquivo do SO).

Args:
    caminho_arquivo: caminho absoluto do arquivo no disco local.
    elemento: um `Elemento` já encontrado (o próprio `<input>`), como
        alternativa ao seletor.
    timeout: segundos a esperar; usa `tempo_espera_padrao` se omitido.
    **seletor: exatamente uma chave — não use junto com `elemento=`.

#### `esperar_ate(condicao: Callable[[Any], Literal[False] | T], timeout: float | None = None, *, descricao: str | Callable[[], str] | None = None) -> T`

Escape hatch para condições customizadas (selenium.webdriver.support.expected_conditions).

`descricao` (texto fixo ou função sem argumentos) só é avaliada se o
timeout realmente estourar, e aparece na mensagem de erro — útil para
dizer qual seletor/elemento estava sendo esperado.

#### `esperar_rede_ociosa(*, tempo_estavel: float = 0.5, timeout: float | None = None) -> None`

Espera o DOM parar de mudar — uma heurística para "rede ociosa" em
SPAs que carregam dados via AJAX depois do carregamento inicial.

Não é uma detecção real de requisições de rede (isso exigiria CDP,
específico do Chromium); em vez disso, observa mutações no DOM via
`MutationObserver` e considera a página estável quando nenhuma
mutação acontece por `tempo_estavel` segundos seguidos.

#### `esperar_texto_conter(texto: str, *, timeout: float | None = None, **seletor: str | None) -> None`

Espera o texto de um elemento (por seletor) conter `texto` — útil
depois de uma ação que atualiza um elemento já existente via JS/AJAX.

#### `esperar_titulo_conter(trecho: str, *, timeout: float | None = None) -> None`

Espera o título da página conter `trecho`.

#### `esperar_url_conter(trecho: str, *, timeout: float | None = None) -> None`

Espera a URL atual conter `trecho` (útil depois de um clique que navega).

#### `esta_presente(*, timeout: float = 1, **seletor: str | None) -> bool`

Verifica se um elemento existe, sem lançar exceção.

Como o timeout padrão é curto (1s, diferente dos outros métodos que
usam `tempo_espera_padrao`), não é ideal pra confirmar ausência
definitiva de algo que ainda pode demorar a aparecer — nesse caso
aumente `timeout`.

Args:
    timeout: segundos a esperar. Padrão: 1.
    **seletor: mesmas chaves de `encontrar()`.

Returns:
    `True` se achou dentro do timeout, `False` caso contrário.

#### `etapa(nome: str, *, tentativas: int = 1) -> Etapa`

Agrupa um bloco de ações sob um nome, pra rastrear
status/duração/erro/ações/retries — e identificar claramente qual
etapa falhou quando algo dá errado. Funciona como `with` e como
decorator (ver docstring de `Etapa`):

    with bot.etapa("Login"):
        bot.digitar("usuario", id="usuario")
        bot.clicar(texto="Entrar")

Args:
    nome: identifica a etapa nos logs/métricas/evidências.
    tentativas: só tem efeito quando usada como decorator — quantas
        vezes reexecutar a função inteira se ela falhar. Usada como
        `with`, uma etapa sempre roda no máximo uma vez.

Returns:
    Um `Etapa`; `etapa.resultado` (um `ResultadoEtapa`) fica
    disponível depois que o bloco/função termina.

#### `executar_script(script: str, *args: Any) -> Any`

Executa `script` (JavaScript) na página atual e devolve o
resultado (equivalente a `driver.execute_script`).

Args:
    script: código JavaScript. Use `return` nele para obter um valor
        de volta; `arguments[0]`, `arguments[1]`, ... referenciam `*args`.
    *args: valores passados ao script (strings, números, `Elemento.bruto`, ...).

Returns:
    O que o script retornar (convertido pro Selenium/Python correspondente).

#### `fechar_aba_atual() -> None`

Fecha a aba atual e muda o foco para a última aba ainda aberta
(se houver alguma). Para fechar uma aba temporária e voltar
especificamente para a aba original, prefira `aba()`.

#### `iniciar() -> Navegador`

Abre o navegador de acordo com a config. Idempotente — chamar de
novo com o navegador já aberto não faz nada. Normalmente não precisa
ser chamado direto: use `with Navegador(...) as bot:`.

Returns:
    O próprio `Navegador` (para permitir `bot = Navegador(...).iniciar()`).

Raises:
    ErroAoIniciarNavegador: driver/binário do navegador não encontrado
        ou falha ao subir o processo.

#### `mudar_para_conteudo_padrao() -> None`

Sai de qualquer frame e volta o foco para o documento principal.

#### `mudar_para_frame(referencia_frame: Elemento | int | str) -> None`

Muda o foco do navegador para dentro de um `<iframe>`/`<frame>` —
necessário antes de `encontrar`/`clicar`/etc. em elementos que estão
dentro dele.

Args:
    referencia_frame: um `Elemento` já encontrado (tipicamente via
        `bot.encontrar(tag="iframe")`), ou o índice/nome/id do frame.

#### `mudar_para_janela(indice: int = -1) -> None`

Muda o foco para outra janela/aba, pelo índice em que foi aberta.

Args:
    indice: índice na lista de janelas abertas. Padrão `-1` (a mais
        recente).

#### `navegar(url: str) -> None`

Abre `url` na aba atual e espera o carregamento terminar.

Args:
    url: endereço com esquema (ex.: `"https://exemplo.com"`).

Raises:
    selenium.common.exceptions.TimeoutException: a página não carregou
        dentro de `tempo_carregamento_pagina` (config). Essa é uma
        exceção do próprio Selenium, não uma `Erro*` do webot — é o
        único ponto onde isso ainda acontece, porque `navegar()` não
        passa por `esperar_ate()`.

#### `nova_aba(url: str | None = None) -> None`

Abre uma aba nova e já muda o foco para ela.

Args:
    url: se dada, navega direto para ela na aba nova.

#### `obter_atributo(atributo: str, *, elemento: Elemento | None = None, timeout: float | None = None, **seletor: str | None) -> str | None`

Devolve o valor de um atributo HTML do elemento (ex.: `"href"`,
`"value"`, `"class"`).

Args:
    atributo: nome do atributo HTML.
    elemento: um `Elemento` já encontrado, como alternativa ao seletor.
    timeout: segundos a esperar; usa `tempo_espera_padrao` se omitido.
    **seletor: exatamente uma chave — não use junto com `elemento=`.

Returns:
    O valor do atributo, ou `None` se o elemento não tiver esse atributo.

#### `obter_info(*, elemento: Elemento | None = None, timeout: float | None = None, **seletor: str | None) -> InfoElemento`

Retorna um retrato tipado (pydantic) do elemento: `texto`, `tag`,
`visivel`, `habilitado` e `atributos` (dict com todos os atributos
HTML). Útil para logs de auditoria de um fluxo de RPA, já que
(diferente de um `WebElement`/`Elemento`) é serializável.

Args:
    elemento: um `Elemento` já encontrado, como alternativa ao seletor.
    timeout: segundos a esperar; usa `tempo_espera_padrao` se omitido.
    **seletor: exatamente uma chave — não use junto com `elemento=`.

Returns:
    Um `InfoElemento` (`.model_dump()`/`.model_dump_json()` para serializar).

#### `obter_texto(*, elemento: Elemento | None = None, timeout: float | None = None, **seletor: str | None) -> str`

Espera o elemento ficar visível e devolve seu texto visível
(equivalente ao `.text` do Selenium).

Args:
    elemento: um `Elemento` já encontrado, como alternativa ao seletor.
    timeout: segundos a esperar; usa `tempo_espera_padrao` se omitido.
    **seletor: exatamente uma chave — não use junto com `elemento=`.

Returns:
    O texto visível do elemento.

#### `obter_texto_alerta(timeout: float | None = None) -> str`

Espera um alerta JS aparecer e devolve o texto dele, sem fechá-lo.

Args:
    timeout: segundos a esperar; usa `tempo_espera_padrao` se omitido.

Returns:
    O texto exibido no alerta.

#### `preencher_formulario(campos: dict[str, str | bool] | list[Campo], *, timeout: float | None = None) -> None`

Preenche vários campos de um formulário de uma vez, escolhendo
como interagir com cada um pela tag/tipo dele: `<select>` seleciona
por texto visível, checkbox/radio marca conforme um booleano, o
resto (input, textarea, ...) digita como texto.

Args:
    campos: no formato simples, um dict onde a chave é um seletor
        CSS e o valor é o que preencher (`{"#usuario": "joao",
        "#aceite": True}`). Para seletor flexível (id=, xpath=,
        nome=, ...) por campo, passe uma lista de `Campo` no lugar
        (`[Campo(valor="joao", id="usuario")]`).
    timeout: segundos a esperar por cada campo; usa
        `tempo_espera_padrao` se omitido.

Raises:
    ErroSeletorInvalido: um `Campo` sem seletor, ou com mais de um.
    ErroElementoNaoEncontrado: algum campo não foi encontrado a tempo.

#### `recusar_alerta(timeout: float | None = None) -> None`

Espera um alerta JS aparecer e clica em cancelar/dispensar.

Args:
    timeout: segundos a esperar; usa `tempo_espera_padrao` se omitido.

#### `rolar_para_baixo() -> None`

Rola a página até o fim (equivalente a End/Ctrl+End).

#### `rolar_para_elemento(elemento: Elemento) -> None`

Rola a página até `elemento` ficar visível na tela (`scrollIntoView`).

Args:
    elemento: um `Elemento` já encontrado.

#### `salvar_relatorio_json(caminho: str | Path) -> None`

Exporta `metricas`, `historico` e `evidencias` (acumulados desde
que este `Navegador` foi criado) num arquivo JSON — útil pra
auditoria ou dashboard de uma automação rodando desacompanhada, sem
precisar que o código do usuário monte esse relatório na mão.

`historico` é o passo a passo ação por ação (ver `RegistroAcao`);
`metricas` são só os contadores agregados; `evidencias` só registra
o estado no momento de uma falha (ver `Evidencia`).

Args:
    caminho: caminho do arquivo `.json` a salvar.

#### `selecionar_por_texto(texto: str, *, elemento: Elemento | None = None, timeout: float | None = None, **seletor: str | None) -> None`

Num `<select>` HTML, seleciona a opção pelo texto visível.

Args:
    texto: texto visível da `<option>` a selecionar.
    elemento: um `Elemento` já encontrado (o próprio `<select>`), como
        alternativa ao seletor.
    timeout: segundos a esperar; usa `tempo_espera_padrao` se omitido.
    **seletor: exatamente uma chave — não use junto com `elemento=`.

#### `selecionar_por_valor(valor_opcao: str, *, elemento: Elemento | None = None, timeout: float | None = None, **seletor: str | None) -> None`

Num `<select>` HTML, seleciona a opção pelo atributo `value`.

Args:
    valor_opcao: valor (`value=`) da `<option>` a selecionar.
    elemento: um `Elemento` já encontrado (o próprio `<select>`), como
        alternativa ao seletor.
    timeout: segundos a esperar; usa `tempo_espera_padrao` se omitido.
    **seletor: exatamente uma chave — não use junto com `elemento=`.

#### `voltar() -> None`

Volta uma página no histórico de navegação.

## `Elemento`

Envelope em pt-br sobre um elemento já encontrado na página.

Devolvido por `Navegador.encontrar()`/`encontrar_todos()` — e por
`encontrar()`/`encontrar_todos()` deste próprio objeto, para buscas
aninhadas (procurar um elemento *dentro* de outro já encontrado). Tem os
mesmos métodos de interação do `Navegador`, já "mirados" neste elemento —
não precisa de seletor de novo:

    linhas = bot.encontrar_todos(css="table tr")
    preco = linhas[2].encontrar(css=".preco")
    preco.clicar()

O `WebElement` puro do Selenium continua acessível em `.bruto`, para os
casos raros que a abstração não cobre.

### Propriedades

#### `config` (propriedade)

A mesma `ConfiguracaoNavegador` do `Navegador` que encontrou este elemento.

#### `habilitado` (propriedade)

`True` se o elemento está habilitado (não tem o atributo `disabled`).

#### `metricas` (propriedade)

As mesmas `Metricas` do `Navegador` que encontrou este elemento
(usado internamente pelo retry — ver `_utilitarios.repetir_se_transitorio`).

#### `selecionado` (propriedade)

`True` se um checkbox/radio (ou `<option>` dentro de um `<select>`) está selecionado.

#### `tag` (propriedade)

Nome da tag HTML do elemento (ex.: `"a"`, `"button"`, `"input"`), em minúsculas.

#### `texto` (propriedade)

Texto visível do elemento (equivalente ao `.text` do Selenium).
Leitura direta, sem esperar visibilidade — use `obter_texto()` se
precisar esperar.

#### `visivel` (propriedade)

`True` se o elemento está visível na página neste instante
(presente no DOM e com largura/altura maiores que zero).

### Métodos

#### `__init__(bruto: WebElement, bot: Navegador)`

Não construído diretamente pelo código do usuário — vem de
`Navegador.encontrar()`/`encontrar_todos()` ou de `Elemento.encontrar()`/
`encontrar_todos()` (busca aninhada).

Args:
    bruto: o `WebElement` do Selenium já localizado.
    bot: o `Navegador` que localizou este elemento (usado internamente
        para esperas/config compartilhadas).

#### `clicar(*, timeout: float | None = None) -> None`

Espera este elemento ficar clicável (visível e habilitado) e
clica nele; se o clique for interceptado por outro elemento (overlay,
header fixo, etc.), tenta de novo via JavaScript.

Args:
    timeout: segundos a esperar; usa `tempo_espera_padrao` (config
        do `Navegador` original) se omitido.

Raises:
    ErroElementoNaoEncontrado: o elemento não ficou clicável a tempo.

#### `digitar(texto: str, *, limpar: bool = True, timeout: float | None = None) -> None`

Espera este elemento ficar visível e digita `texto` nele.

Args:
    texto: o que digitar.
    limpar: se `True` (padrão), limpa o campo antes de digitar.
    timeout: segundos a esperar; usa `tempo_espera_padrao` se omitido.

Raises:
    ErroElementoNaoEncontrado: o elemento não ficou visível a tempo.

#### `encontrar(*, timeout: float | None = None, **seletor: str | None) -> Elemento`

Espera um elemento existir *dentro* deste (busca aninhada) e o
devolve — não procura na página inteira, só na sub-árvore deste
elemento. Ótimo para tabelas/listas (achar uma célula dentro de uma
linha já encontrada), sem precisar de um seletor único combinando
linha e coluna.

Args:
    timeout: segundos a esperar; usa `tempo_espera_padrao` se omitido.
    **seletor: exatamente uma chave entre `id=`, `css=`, `xpath=`,
        `nome=`, `classe=`, `tag=`, `texto=`, `texto_link=`, `texto_link_parcial=`.

Returns:
    O `Elemento` filho encontrado.

Raises:
    ErroSeletorInvalido: seletor ausente, duplicado ou desconhecido.
    ErroElementoNaoEncontrado: nada casou com o seletor dentro do timeout.

#### `encontrar_todos(*, timeout: float | None = None, **seletor: str | None) -> list[Elemento]`

Como `encontrar()`, mas espera existir pelo menos um elemento
dentro deste e devolve todos os que casarem com o seletor.

Args:
    timeout: segundos a esperar; usa `tempo_espera_padrao` se omitido.
    **seletor: mesmas chaves de `encontrar()`.

Returns:
    Lista de `Elemento` filhos (nunca vazia — se nada casar, levanta
    `ErroElementoNaoEncontrado` em vez de `[]`).

#### `enviar_arquivo(caminho_arquivo: str) -> None`

Se este elemento for um `<input type="file">`, envia um arquivo
escrevendo o caminho absoluto nele (não abre seletor de arquivo do SO).

Args:
    caminho_arquivo: caminho absoluto do arquivo no disco local.

#### `esta_presente(*, timeout: float = 1, **seletor: str | None) -> bool`

Verifica se um elemento existe dentro deste, sem lançar exceção.

Args:
    timeout: segundos a esperar. Padrão: 1.
    **seletor: mesmas chaves de `encontrar()`.

Returns:
    `True` se achou dentro do timeout, `False` caso contrário.

#### `obter_atributo(atributo: str) -> str | None`

Devolve o valor de um atributo HTML do elemento (ex.: `"href"`,
`"value"`, `"class"`).

Args:
    atributo: nome do atributo HTML.

Returns:
    O valor do atributo, ou `None` se o elemento não tiver esse atributo.

#### `obter_info() -> InfoElemento`

Retorna um retrato tipado (pydantic) deste elemento: `texto`,
`tag`, `visivel`, `habilitado` e `atributos` (dict com todos os
atributos HTML). Diferente do `Elemento` em si, é serializável
(`.model_dump()`/`.model_dump_json()`) — útil para logs de auditoria.

Returns:
    Um `InfoElemento`.

#### `obter_texto(*, timeout: float | None = None) -> str`

Espera este elemento ficar visível e devolve seu texto.

Args:
    timeout: segundos a esperar; usa `tempo_espera_padrao` se omitido.

Returns:
    O texto visível do elemento.

#### `preencher_formulario(campos: dict[str, str | bool] | list[Campo], *, timeout: float | None = None) -> None`

Como `Navegador.preencher_formulario()`, mas busca os campos
*dentro* deste elemento (busca aninhada) — útil pra preencher um
formulário que está dentro de um modal/seção já encontrada.

Args:
    campos: dict (chave = seletor CSS) ou lista de `Campo` — ver
        `Navegador.preencher_formulario()`.
    timeout: segundos a esperar por cada campo; usa
        `tempo_espera_padrao` se omitido.

#### `rolar_ate() -> None`

Rola a página até este elemento ficar visível na tela (`scrollIntoView`).

#### `selecionar_por_texto(texto: str) -> None`

Se este elemento for um `<select>`, seleciona a opção pelo texto visível.

Args:
    texto: texto visível da `<option>` a selecionar.

#### `selecionar_por_valor(valor_opcao: str) -> None`

Se este elemento for um `<select>`, seleciona a opção pelo atributo `value`.

Args:
    valor_opcao: valor (`value=`) da `<option>` a selecionar.

## `Fluxo`

Uma automação nomeada, montada uma vez e reaproveitável em várias
execuções/navegadores. Cada passo adicionado (via `.adicionar()` ou pelos
atalhos `.navegar()`/`.clicar()`/`.digitar()`/`.preencher_formulario()`)
vira uma `Etapa` própria quando o fluxo roda — dá pra ver exatamente qual
passo falhou em `resultado.etapas`.

### Métodos

#### `__init__(nome: str) -> None`

Cria um fluxo vazio, sem passos ainda — use `.adicionar()` ou os
atalhos (`.navegar()`, `.clicar()`, ...) pra montá-lo.

Args:
    nome: identifica o fluxo nos logs e na mensagem de `ErroFluxo`.

#### `adicionar(passo: _Passo, *, nome: str | None = None) -> Fluxo`

Adiciona um passo customizado: uma função que recebe o `Navegador`
em execução. Use isso pra qualquer lógica que os atalhos
(`.navegar()`, `.clicar()`, ...) não cobrirem.

#### `clicar(**seletor: Any) -> Fluxo`

Adiciona um passo que chama `Navegador.clicar(**seletor)` quando o
fluxo rodar (mesmas chaves de seletor de sempre: `id=`, `css=`,
`texto=`, ...; também aceita `timeout=`).

#### `digitar(texto: str, **seletor: Any) -> Fluxo`

Adiciona um passo que chama `Navegador.digitar(texto, **seletor)`
quando o fluxo rodar.

#### `executar(bot: Navegador) -> ResultadoFluxo`

Roda todos os passos, em ordem, contra `bot`. Cada passo roda
dentro da sua própria `Etapa` (ver `Navegador.etapa`).

Raises:
    ErroFluxo: um passo falhou — a exceção original fica em `__cause__`,
        e `erro.resultado` tem as etapas concluídas até ali.

#### `navegar(url: str) -> Fluxo`

Adiciona um passo que chama `Navegador.navegar(url)` quando o fluxo rodar.

#### `preencher_formulario(campos: dict[str, str | bool] | list[Campo]) -> Fluxo`

Adiciona um passo que chama `Navegador.preencher_formulario(campos)`
quando o fluxo rodar.

## `Etapa`

Uso como `with` (roda uma vez, sem retry no nível da etapa):

    with bot.etapa("Login"):
        bot.digitar("usuario", id="usuario")
        bot.clicar(texto="Entrar")

Uso como decorator (por herdar de `ContextDecorator`) — aqui sim
`tentativas=` reexecuta a função inteira do zero se ela falhar:

    @bot.etapa("Login", tentativas=3)
    def fazer_login(bot):
        bot.digitar("usuario", id="usuario")
        bot.clicar(texto="Entrar")

    fazer_login(bot)

Em nenhum dos dois casos a exceção original é suprimida — ela sempre se
propaga (ou, na última tentativa esgotada, é relançada) depois de a
etapa registrar o que aconteceu em `.resultado` e capturar evidência.

### Métodos

#### `__init__(bot: Navegador, nome: str, *, tentativas: int = 1) -> None`

Normalmente não construído diretamente — vem de `Navegador.etapa(nome, tentativas=...)`.

Args:
    bot: o `Navegador` cujas ações serão rastreadas.
    nome: identifica a etapa nos logs/métricas/evidências.
    tentativas: só tem efeito no uso como decorator (ver docstring
        da classe) — quantas vezes reexecutar a função inteira se
        ela falhar.

## `Empacotador`

Compila um script de automação feito com webot num executável
standalone via PyInstaller — quem for rodar não precisa de Python
instalado, só o navegador (Chrome/Edge/Firefox) em si.

    Empacotador("meu_script.py", nome="MinhaAutomacao").empacotar()

### Métodos

#### `__init__(script: str | Path, *, nome: str | None = None, icone: str | Path | None = None, sem_console: bool = False, onedir: bool = False, pasta_saida: str | Path | None = None, imports_ocultos: list[str] | None = None, arquivos_adicionais: list[str] | None = None, argumentos_extras: list[str] | None = None) -> None`

Configura a compilação; nada roda até chamar `empacotar()`.

Args:
    script: caminho do script Python de automação (feito com webot).
    nome: nome do executável gerado. Padrão: nome do script (sem `.py`).
    icone: caminho de um `.ico` para o executável. Padrão: ícone
        padrão do PyInstaller.
    sem_console: `True` gera o executável sem janela de console
        (`--windowed`). Nesse modo `print()`/`input()` não
        funcionam — use logging em arquivo. Padrão: `False`.
    onedir: `True` gera uma pasta com vários arquivos (`--onedir`)
        em vez de um único `.exe` (`--onefile`, padrão). `--onedir`
        inicia mais rápido, pois `--onefile` descompacta tudo numa
        pasta temporária a cada execução. Padrão: `False`.
    pasta_saida: pasta onde o executável é gerado. Padrão: `dist/`
        na pasta do script.
    imports_ocultos: módulos que o PyInstaller não detecta sozinho
        (`--hidden-import`).
    arquivos_adicionais: arquivos/pastas extras a incluir no
        executável, no formato `'origem;destino'` do `--add-data`
        (ex.: `'modelo.xlsx;.'`).
    argumentos_extras: flags adicionais repassadas cruas ao
        PyInstaller, para casos não cobertos acima.

#### `empacotar() -> Path`

Compila o script configurado num executável standalone.

Returns:
    Caminho do executável gerado (ou da pasta, se `onedir=True`).

Raises:
    FileNotFoundError: o script configurado não existe.
    RuntimeError: PyInstaller não está instalado, ou a compilação falhou.

# Modelos de configuração e retorno

## `ConfiguracaoNavegador`

Configuração de como o navegador deve subir.

Por ser um modelo pydantic, um parâmetro com nome errado ou valor de
tipo/valor inválido já falha na criação, com uma mensagem clara indicando
qual campo está errado e quais valores são aceitos.

Selenium 4.6+ resolve o driver correto automaticamente (Selenium Manager),
então não é preciso apontar caminho de chromedriver/msedgedriver.

### Campos

- **`tipo_navegador`** — `TipoNavegador = <TipoNavegador.CHROME: 'chrome'>` — Qual navegador abrir: 'chrome', 'edge' ou 'firefox' (ou TipoNavegador.CHROME/EDGE/FIREFOX).
- **`sem_interface`** — `bool = False` — Modo headless: True roda sem abrir janela nenhuma (útil em servidor/CI).
- **`anonimo`** — `bool = True` — True abre em modo anônimo/privado (--incognito no Chrome, --inprivate no Edge, -private no Firefox).
- **`tamanho_janela`** — `tuple[int, int] | None = (1920, 1080)` — (largura, altura) em pixels da janela. None deixa o navegador decidir sozinho.
- **`maximizar_janela`** — `bool = False` — True maximiza a janela ao iniciar; tem prioridade sobre tamanho_janela.
- **`pasta_download`** — `pathlib.Path | None = None` — Pasta onde os downloads feitos pelo navegador serão salvos. None usa o padrão do sistema.
- **`espera_implicita`** — `float = 0` — Espera implícita (segundos) aplicada globalmente pelo Selenium antes de cada busca. Recomendado manter em 0 e usar os timeouts explícitos dos métodos (encontrar, clicar, etc.).
- **`tempo_espera_padrao`** — `float = 10` — Timeout padrão (segundos) das esperas explícitas quando `timeout=` não é informado na chamada.
- **`tempo_carregamento_pagina`** — `float = 30` — Tempo máximo (segundos) que navegar() espera o carregamento de uma página antes de falhar.
- **`agente_usuario`** — `str | None = None` — User-Agent customizado a enviar nas requisições. None usa o padrão do navegador.
- **`caminho_binario`** — `str | None = None` — Caminho do executável do navegador, se não estiver no local padrão do sistema.
- **`argumentos_extras`** — `list[str] = []` — Flags de linha de comando adicionais para o navegador (ex.: '--proxy-server=...').
- **`pasta_screenshot_erro`** — `pathlib.Path | None = None` — Se definida, tira um screenshot automático nessa pasta sempre que uma espera expirar (ErroElementoNaoEncontrado). None desativa (padrão).
- **`tentativas_retry_transitorio`** — `int = 2` — Quantas vezes reexecutar uma ação (clicar, digitar, ...) se ela falhar por um erro transitório do Selenium (elemento 'stale', ainda não interagível, etc.) antes de desistir.
- **`espera_entre_tentativas`** — `float = 0.3` — Segundos de espera entre uma tentativa e a próxima, ao reexecutar por erro transitório.

## `InfoElemento`

Retrato tipado de um elemento no instante da consulta (não é 'ao vivo').

Útil para logs e serialização (`.model_dump()` / `.model_dump_json()`),
já que o WebElement bruto do Selenium não é serializável.

### Campos

- **`texto`** — `str = <obrigatório>`
- **`tag`** — `str = <obrigatório>`
- **`visivel`** — `bool = <obrigatório>`
- **`habilitado`** — `bool = <obrigatório>`
- **`atributos`** — `dict[str, str] = {}`

# Resultados e estruturas de dados

## `ResultadoEtapa`

O que aconteceu durante uma etapa (`Navegador.etapa(...)`).

`acoes`/`retries` são a soma do que aconteceu com o `Navegador` (e
`Elemento`s dele) enquanto a etapa estava ativa — não são contados por
fora, são a diferença de `Navegador.metricas` entre o início e o fim.
`tentativas` só é maior que 1 quando a etapa é usada como decorator com
`tentativas=N` (ver docstring de `Etapa`); usada como `with`, uma etapa
roda no máximo uma vez.

### Propriedades

#### `sucesso` (propriedade)


### Campos

- **`nome`** — `str = <obrigatório>`
- **`status`** — `str = 'em_andamento'`
- **`duracao_segundos`** — `float = 0.0`
- **`erro`** — `str | None = None`
- **`acoes`** — `int = 0`
- **`retries`** — `int = 0`
- **`tentativas`** — `int = 1`

## `ResultadoFluxo`

O resultado de rodar um `Fluxo`: quanto tempo levou, e o `ResultadoEtapa`
de cada passo (na ordem em que rodaram).

### Propriedades

#### `sucesso` (propriedade)


#### `taxa_sucesso` (propriedade)


#### `total_acoes` (propriedade)


#### `total_falhas` (propriedade)


#### `total_retries` (propriedade)


### Campos

- **`nome`** — `str = <obrigatório>`
- **`etapas`** — `list[ResultadoEtapa] = []`
- **`duracao_segundos`** — `float = 0.0`

## `Metricas`

Contadores de uma execução: quantas ações rodaram, quantas etapas
falharam, e quantos retries de erro transitório aconteceram.

`Navegador.metricas` acumula isso pra sessão inteira. `Etapa` tira uma
"foto" no início e no fim pra saber o que aconteceu só durante ela
(ver `Etapa.resultado`).

### Campos

- **`acoes`** — `int = 0`
- **`falhas`** — `int = 0`
- **`retries`** — `int = 0`

## `Evidencia`

Um retrato do estado da automação no momento de uma falha.

`caminho_screenshot`/`caminho_html` só vêm preenchidos se
`ConfiguracaoNavegador.pasta_screenshot_erro` estiver configurada — sem
isso, a evidência ainda é registrada (em `Navegador.evidencias`), só sem
os arquivos.

### Campos

- **`timestamp`** — `datetime = <obrigatório>`
- **`erro`** — `str = <obrigatório>`
- **`etapa`** — `str | None = None`
- **`acao`** — `str | None = None`
- **`url`** — `str | None = None`
- **`caminho_screenshot`** — `Path | None = None`
- **`caminho_html`** — `Path | None = None`

## `RegistroAcao`

Um item do histórico: uma ação, quando aconteceu, com que detalhes
(seletor, URL, ...) e dentro de qual etapa nomeada (se houver).

### Campos

- **`timestamp`** — `datetime = <obrigatório>`
- **`acao`** — `str = <obrigatório>`
- **`detalhes`** — `dict[str, Any] = {}`
- **`etapa`** — `str | None = None`

## `Campo`

Um campo de formulário a preencher: o valor, mais um seletor (as
mesmas palavras-chave de sempre — exatamente uma delas).

    Campo(valor="joao", id="usuario")
    Campo(valor=True, css="#aceite-termos")        # checkbox
    Campo(valor="Brasil", css="#pais")              # <select>, por texto visível

`texto=`/`texto_link=` acham elementos pelo texto visível deles mesmos —
ótimos pra botões/links, mas a maioria dos `<input>`/`<textarea>` não tem
texto próprio (o texto fica no `<label>`, que é outro elemento). Pra
campos de formulário de verdade, prefira `id=`/`css=`/`nome=`.

### Campos

- **`valor`** — `str | bool = <obrigatório>`
- **`id`** — `str | None = None`
- **`css`** — `str | None = None`
- **`xpath`** — `str | None = None`
- **`nome`** — `str | None = None`
- **`classe`** — `str | None = None`
- **`tag`** — `str | None = None`
- **`texto`** — `str | None = None`
- **`texto_link`** — `str | None = None`
- **`texto_link_parcial`** — `str | None = None`

# Enums

## `TipoNavegador`

Navegadores suportados pelo `Navegador` (campo `tipo_navegador`).

### Valores

- **`CHROME`** = `'chrome'`
- **`EDGE`** = `'edge'`
- **`FIREFOX`** = `'firefox'`

# Exceções

## `ErroAutomacao`

Erro base para a camada de automação web.

## `ErroAoIniciarNavegador`

Falha ao iniciar o navegador.

## `ErroElementoNaoEncontrado`

Elemento ou condição não satisfeita dentro do tempo de espera configurado.

## `ErroNavegadorNaoIniciado`

O navegador foi usado antes de iniciar() ser chamado.

## `ErroSeletorInvalido`

Nenhum seletor (ou mais de um) foi informado numa chamada que exige exatamente um.

## `ErroFluxo`

Uma etapa do fluxo falhou. `.resultado` tem o que rodou até ali
(etapas concluídas, métricas parciais), pra quem quiser inspecionar o
que deu certo antes da falha.
