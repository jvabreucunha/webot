# webot

[![CI](https://github.com/jvabreucunha/webot/actions/workflows/ci.yml/badge.svg)](https://github.com/jvabreucunha/webot/actions/workflows/ci.yml)

Abstração em pt-br sobre o Selenium para automação/RPA web. Um objeto (`Navegador`)
com métodos em português para ciclo de vida do navegador, esperas explícitas,
localizar elementos e interagir com eles — sem precisar importar nada do
Selenium (`By`, `expected_conditions`, etc.) no seu código de automação.

- Configuração validada com **Pydantic** (parâmetro errado ou valor inválido
  falha na hora, com mensagem clara).
- Suporta **Chrome**, **Edge** e **Firefox**, resolvendo o driver sozinho
  (Selenium Manager, sem precisar baixar/apontar chromedriver/msedgedriver/geckodriver).
- Pensado para ser instalado como **lib** e reaproveitado em vários projetos.
- Além da API simples (`bot.clicar(...)`, `bot.digitar(...)`), tem um sistema
  de observabilidade para automações maiores: **etapas nomeadas** (com
  status/duração/retries), **fluxos** reutilizáveis (`Fluxo`), **métricas**
  e **evidências** (screenshot + HTML) automáticas em caso de erro — ver
  [Etapas, fluxos, métricas e evidências](#etapas-fluxos-métricas-e-evidências).

## Sumário

- [Guia rápido](#guia-rápido) — instale e rode seu primeiro script
- [Seletores: sempre por palavra-chave](#seletores-sempre-por-palavra-chave)
  - [Achar agora, agir depois](#achar-agora-agir-depois)
- [Configuração](#configuração) — como configurar o bot (`ConfiguracaoNavegador`)
- [Funcionalidades](#funcionalidades)
  - [Ciclo de vida](#ciclo-de-vida) — inicialização/encerramento do navegador
  - [Navegação](#navegação)
  - [Localizar elementos](#localizar-elementos)
  - [Interações](#interações)
  - [Preenchimento de formulário](#preenchimento-de-formulário)
  - [Esperas em pt-br](#esperas-em-pt-br-sem-tocar-em-expected_conditions)
  - [Download de arquivo](#download-de-arquivo)
  - [JavaScript e scroll](#javascript-e-scroll)
  - [Abas, janelas e frames](#abas-janelas-e-frames)
  - [Alertas](#alertas)
  - [Tempo](#tempo)
  - [Utilidades](#utilidades)
- [Elemento](#elemento)
- [Etapas, fluxos, métricas e evidências](#etapas-fluxos-métricas-e-evidências)
  - [Etapas nomeadas](#etapas-nomeadas)
  - [Fluxo](#fluxo)
  - [Métricas](#métricas)
  - [Evidências](#evidências)
  - [Modo debug](#modo-debug)
- [Erros](#erros)
- [Empacotar num executável](#empacotar-num-executável)
- [Estrutura do projeto](#estrutura-do-projeto)
- [Referência para IA](#referência-para-ia)
- [Desenvolvimento](#desenvolvimento) — só se for mexer no código do webot
- [Versionamento](#versionamento)

## Guia rápido

### Instalação

Dentro deste repositório (modo desenvolvimento, com auto-reload das edições):

```bash
pip install -e .
```

Em outro projeto, depois que este repositório estiver num remoto (GitHub/GitLab):

```bash
pip install git+https://github.com/<usuario>/<repo>.git@v0.1.0
```

Sempre trave numa tag (`@v0.1.0`) para não puxar mudanças futuras sem querer.
Requer Python 3.10+.

### Uso rápido

```python
from webot import Navegador

with Navegador(tipo_navegador="chrome", sem_interface=False) as bot:
    bot.navegar("https://exemplo.com")
    bot.clicar(css="button.enviar")
    bot.digitar("relatorio", nome="busca")
    texto = bot.obter_texto(tag="h1")
```

`Navegador` é um context manager: `iniciar()` roda no `with ... as bot:` e
`encerrar()` roda automaticamente ao sair do bloco, mesmo se der exceção.

## Seletores: sempre por palavra-chave

Nenhum método pede um objeto `By`. Em vez disso, toda busca de elemento aceita
exatamente **uma** destas palavras-chave:

| chave                 | equivalente Selenium      |
| --------------------- | -------------------------- |
| `id`                  | `By.ID`                     |
| `css`                 | `By.CSS_SELECTOR`           |
| `xpath`               | `By.XPATH`                  |
| `nome`                | `By.NAME`                   |
| `classe`              | `By.CLASS_NAME`             |
| `tag`                 | `By.TAG_NAME`                |
| `texto`               | (traduzido pra um XPath por baixo — ver abaixo) |
| `texto_link`          | `By.LINK_TEXT`              |
| `texto_link_parcial`  | `By.PARTIAL_LINK_TEXT`      |

```python
bot.clicar(css="button.enviar")
bot.obter_texto(xpath="//h1")
bot.clicar(texto="Entrar")  # acha pelo texto visível do próprio elemento
```

`texto=` acha qualquer elemento (não só `<a>`, ao contrário de `texto_link=`)
cujo texto direto seja exatamente aquele — ótimo para botões/spans/divs com
rótulo visível. Só não acha o texto de um elemento cujo conteúdo está todo
dentro de um filho (ex.: `<button><span>Entrar</span></button>` — aí quem
casa é o `<span>`, não o `<button>`; funciona igual, já que clicar no filho
já aciona o botão).

Passar zero, duas ou mais chaves, ou uma chave desconhecida, levanta
`ErroSeletorInvalido` com uma mensagem explicando o que era esperado.

### Achar agora, agir depois

`encontrar()`/`encontrar_todos()` não devolvem o `WebElement` puro do
Selenium — devolvem um `Elemento` (ver [Elemento](#elemento) abaixo), que já
tem `.clicar()`, `.digitar()`, `.obter_texto()`, etc. Isso resolve o caso de
filtrar uma lista e agir num item específico:

```python
itens = bot.encontrar_todos(css=".item")
itens[2].clicar()
```

Se preferir, os métodos do `Navegador` também aceitam esse `Elemento` via
`elemento=`, em vez do seletor — equivalente ao `.clicar()` acima:

```python
bot.clicar(elemento=itens[2])
```

Não misture os dois: passar `elemento=` e um seletor na mesma chamada levanta
`ErroSeletorInvalido`.

## Configuração

Duas formas de configurar, não misture as duas:

**1. Opções soltas** (uso simples, um bot avulso):

```python
from webot import Navegador

bot = Navegador(tipo_navegador="edge", sem_interface=True, tamanho_janela=(1366, 768))
```

**2. `ConfiguracaoNavegador` pronta** (para reaproveitar a mesma config em
vários bots, ou quando quiser passar tudo explícito):

```python
from webot import ConfiguracaoNavegador, Navegador, TipoNavegador

config = ConfiguracaoNavegador(
    tipo_navegador=TipoNavegador.CHROME,
    sem_interface=True,
    tempo_espera_padrao=15,
)
bot = Navegador(config)
```

Todo campo tem descrição (aparece no hover do editor) e validação — por
exemplo, `tempo_espera_padrao` precisa ser `> 0`, e `tipo_navegador` só aceita
`"chrome"`/`"edge"`/`"firefox"`. Campos disponíveis:

| campo                          | tipo                    | padrão      | o que faz                                                                 |
| ------------------------------ | ------------------------ | ----------- | -------------------------------------------------------------------------- |
| `tipo_navegador`                | `TipoNavegador \| str`   | `chrome`    | qual navegador abrir                                                        |
| `sem_interface`                 | `bool`                   | `False`     | modo headless                                                              |
| `anonimo`                       | `bool`                   | `True`      | modo anônimo/privado                                                       |
| `tamanho_janela`                | `tuple[int, int] \| None`| `(1920,1080)`| tamanho da janela em pixels                                                |
| `maximizar_janela`              | `bool`                   | `False`     | maximiza a janela (tem prioridade sobre `tamanho_janela`)                  |
| `pasta_download`                | `Path \| None`           | `None`      | pasta de destino dos downloads (necessária para `baixar_arquivo()`)        |
| `espera_implicita`              | `float`                  | `0`         | espera implícita global do Selenium (recomendado manter em 0)              |
| `tempo_espera_padrao`           | `float`                  | `10`        | timeout padrão das esperas explícitas                                      |
| `tempo_carregamento_pagina`     | `float`                  | `30`        | timeout de carregamento de página                                          |
| `agente_usuario`                | `str \| None`            | `None`      | User-Agent customizado                                                     |
| `caminho_binario`               | `str \| None`            | `None`      | caminho do executável do navegador                                         |
| `argumentos_extras`             | `list[str]`              | `[]`        | flags extras de linha de comando (ex.: `--proxy-server=...`)               |
| `pasta_screenshot_erro`         | `Path \| None`           | `None`      | tira screenshot automático nessa pasta quando uma espera expira            |
| `tentativas_retry_transitorio`  | `int`                    | `2`         | quantas vezes reexecutar uma ação após erro transitório (stale, etc.)      |
| `espera_entre_tentativas`       | `float`                  | `0.3`       | segundos entre uma tentativa e a próxima nesse retry                       |

## Funcionalidades

### Ciclo de vida
- `iniciar()` / `encerrar()` — abre e fecha o navegador. Também funciona como
  context manager (`with Navegador(...) as bot:`).
- `driver_bruto` — acesso ao `WebDriver` puro do Selenium, para os casos raros
  que a abstração não cobre.

### Navegação
- `navegar(url)`, `atualizar()`, `voltar()`, `avancar()`
- `url_atual`, `titulo` (properties)

### Localizar elementos
- `encontrar(**seletor, timeout=None)` — espera o elemento existir no DOM.
  Retorna um [`Elemento`](#elemento).
- `encontrar_todos(**seletor, timeout=None)` — mesma coisa, mas retorna uma
  `list[Elemento]` com todos os elementos que casam com o seletor.
- `esta_presente(**seletor, timeout=1)` — `True`/`False`, sem lançar exceção.
- `obter_info(**seletor, timeout=None)` — retorna um `InfoElemento` (modelo
  Pydantic tipado, serializável) com `texto`, `tag`, `visivel`, `habilitado` e
  `atributos` (dict com todos os atributos HTML do elemento). Útil para logs
  de auditoria de um fluxo de RPA.

### Interações
Todas aceitam `**seletor` (o padrão de sempre) ou `elemento=` (um `Elemento`
já obtido antes — ver [Achar agora, agir depois](#achar-agora-agir-depois)):
- `clicar(elemento=None, *, timeout=None, **seletor)` — espera o elemento
  ficar clicável; se o clique for interceptado por outro elemento, tenta de
  novo via JavaScript.
- `digitar(texto, *, elemento=None, limpar=True, timeout=None, **seletor)`
- `obter_texto(*, elemento=None, timeout=None, **seletor)`
- `obter_atributo(atributo, *, elemento=None, timeout=None, **seletor)`
- `selecionar_por_texto(texto, ...)` / `selecionar_por_valor(valor_opcao, ...)` — `<select>` HTML.
- `enviar_arquivo(caminho_arquivo, ...)` — upload de arquivo.

Essas chamadas usam um retry automático quando a ação falha por um erro
**transitório** do Selenium — elemento "stale" (DOM re-renderizou entre a
busca e a ação) ou ainda não interagível — sem precisar tratar isso na mão.
Quantas vezes tentar de novo e o intervalo entre tentativas são configuráveis
(`tentativas_retry_transitorio`/`espera_entre_tentativas`, ver a seção
Configuração acima).

### Preenchimento de formulário
- `preencher_formulario(campos, *, timeout=None)` — preenche vários campos de
  uma vez, escolhendo como interagir com cada um pela tag/tipo dele:
  `<select>` seleciona por texto visível, checkbox/radio marca conforme um
  booleano (só clica se o estado atual for diferente do desejado — idempotente),
  o resto (`input`, `textarea`, ...) digita como texto.

  No formato simples, as chaves são seletores CSS:

  ```python
  bot.preencher_formulario({
      "#nome": "Maria",
      "#comentario": "Cadastro via webot",
      "#pais": "Brasil",       # <select>
      "#aceite-termos": True,  # checkbox
  })
  ```

  Para seletor flexível por campo (`id=`, `xpath=`, `nome=`, `texto=`, ...),
  use uma lista de `Campo` no lugar do dict:

  ```python
  from webot import Campo

  bot.preencher_formulario([
      Campo(valor="Maria", id="nome"),
      Campo(valor="Brasil", xpath="//select[@name='pais']"),
  ])
  ```

  `Elemento` também tem `.preencher_formulario(...)` — igual, mas busca os
  campos *dentro* dele (útil pra um formulário dentro de um modal já achado).

### Esperas em pt-br (sem tocar em `expected_conditions`)
- `esperar_url_conter(trecho, timeout=None)`
- `esperar_titulo_conter(trecho, timeout=None)`
- `esperar_texto_conter(texto, *, timeout=None, **seletor)` — espera o texto
  de um elemento existente mudar (útil depois de uma ação que atualiza a
  página via JS/AJAX, sem trocar de URL).
- `esperar_rede_ociosa(*, tempo_estavel=0.5, timeout=None)` — heurística para
  "a página parou de carregar coisa nova" em SPAs: observa o DOM via
  `MutationObserver` e considera estável quando nada muda por `tempo_estavel`
  segundos seguidos. **Não é** uma detecção real de requisições de rede (isso
  exigiria CDP, específico do Chromium) — é uma aproximação que funciona nos
  três navegadores suportados.

### Download de arquivo
- `baixar_arquivo(disparar, *, timeout=30.0)` — dispara um download e aguarda
  o arquivo terminar de baixar em `pasta_download` (precisa estar configurada),
  devolvendo o `Path` completo. `disparar` é uma função sem argumentos que
  inicia o download — chamada só depois de "fotografar" a pasta, pra saber
  identificar qual arquivo é novo:

  ```python
  caminho = bot.baixar_arquivo(lambda: bot.clicar(css="a.download"))
  ```

  Ignora arquivos temporários do navegador (`.crdownload`/`.part`/`.tmp`) até
  o download terminar de verdade. Em Chrome/Edge headless, a liberação do
  download via CDP é feita automaticamente por `iniciar()` — não precisa
  configurar nada além de `pasta_download`.

### JavaScript e scroll
- `executar_script(script, *args)`
- `rolar_para_elemento(elemento)`, `rolar_para_baixo()`

### Abas, janelas e frames
- `nova_aba(url=None)`, `fechar_aba_atual()`, `mudar_para_janela(indice=-1)`
- `mudar_para_frame(referencia_frame)`, `mudar_para_conteudo_padrao()`
- `aba(url=None)` — context manager que abre uma aba nova, roda o bloco e
  fecha sozinha ao sair (mesmo se der exceção), voltando pra aba original:

  ```python
  with bot.aba("https://outro-site.com") as nova:
      nova.clicar(css=".algo")
  # de volta na aba original aqui
  ```

### Alertas
- `aceitar_alerta(timeout=None)`, `recusar_alerta(timeout=None)`, `obter_texto_alerta(timeout=None)`

### Tempo
- `aguardar(segundos)` — pausa fixa (`bot.aguardar(1.5)`) ou aleatória dentro
  de um intervalo (`bot.aguardar((0.5, 1.5))`), para dar um ritmo mais humano
  entre ações num fluxo de RPA.

### Utilidades
- `capturar_tela(caminho)` — screenshot da página atual.
- Screenshot **automático** em erro: se `pasta_screenshot_erro` estiver
  configurada, toda vez que uma espera expirar (`ErroElementoNaoEncontrado`)
  um screenshot é salvo lá sozinho — útil pra RPA rodando sem supervisão.
  Desligado por padrão (`None`).
- `esperar_ate(condicao, timeout=None, *, descricao=None)` — escape hatch para
  condições customizadas do Selenium (`selenium.webdriver.support.expected_conditions`),
  para os casos avançados que os métodos prontos não cobrem.

## Elemento

O que `encontrar()`/`encontrar_todos()` devolvem. Um envelope em pt-br sobre
o `WebElement` do Selenium, com os mesmos métodos de interação do `Navegador`
já mirados naquele elemento (sem precisar de seletor de novo):

- **Estado**: `.texto`, `.tag`, `.visivel`, `.habilitado`, `.selecionado`
  (checkbox/radio/`<option>` marcado — properties), `.obter_atributo(nome)`,
  `.obter_info()` (mesmo `InfoElemento` de cima). `.config`/`.metricas` dão a
  mesma `ConfiguracaoNavegador`/`Metricas` do `Navegador` que encontrou o elemento.
- **Interação**: `.clicar(timeout=None)`, `.digitar(texto, limpar=True, timeout=None)`,
  `.obter_texto(timeout=None)`, `.selecionar_por_texto(texto)`,
  `.selecionar_por_valor(valor_opcao)`, `.enviar_arquivo(caminho_arquivo)`,
  `.preencher_formulario(campos)` (busca os campos dentro deste elemento),
  `.rolar_ate()`.
- **Busca aninhada** — procurar um elemento *dentro* deste, sem re-selecionar
  a partir da página inteira. Ótimo para tabelas/listas, onde senão você
  precisaria de um seletor único complicado misturando linha e coluna:

  ```python
  linhas = bot.encontrar_todos(css="table tr")
  preco = linhas[2].encontrar(css=".preco")       # Elemento, busca só dentro da linha
  print(preco.obter_texto())

  itens_da_linha = linhas[2].encontrar_todos(css="td")
  linhas[2].esta_presente(css=".desconto")         # True/False, sem lançar exceção
  ```

- **Escape hatch**: `.bruto` é o `WebElement` puro do Selenium, para os casos
  raros que a abstração não cobre.

## Etapas, fluxos, métricas e evidências

Pra automações pequenas, os métodos do `Navegador` já bastam. Pra automações
maiores — várias telas, vários formulários — tem um sistema de observabilidade
por cima: agrupe ações em **etapas** nomeadas, monte a sequência inteira como
um **fluxo** reutilizável, e acompanhe **métricas** e **evidências** de erro
automaticamente.

A diferença entre os dois: **`Fluxo` é o roteiro** — os passos que você monta
uma vez, sem navegador nenhum, e guarda pra rodar quantas vezes quiser contra
bots diferentes (é a parte de reaproveitamento). **`Etapa` é o rastreamento**
de um pedaço de código que já está rodando — status, duração, ações, e qual
etapa especificamente falhou. Você pode usar `Etapa` sozinha, sem `Fluxo`
nenhum, num script que já existe; e quando você roda um `Fluxo`, ele usa uma
`Etapa` por baixo dos panos pra cada passo — é assim que `resultado.etapas`
sabe apontar exatamente onde parou.

### Etapas nomeadas

`bot.etapa(nome, *, tentativas=1)` agrupa um bloco de ações sob um nome, pra
rastrear status/duração/erro/ações/retries — e saber exatamente qual etapa
falhou. Funciona como `with`:

```python
with bot.etapa("Login") as etapa:
    bot.digitar("usuario", id="usuario")
    bot.clicar(texto="Entrar")

print(etapa.resultado.status, etapa.resultado.duracao_segundos)
```

... e também como decorator (por isso o `bot.etapa(...)` do título — é
literalmente o objeto que decora):

```python
@bot.etapa("Login", tentativas=3)
def fazer_login(bot):
    bot.digitar("usuario", id="usuario")
    bot.clicar(texto="Entrar")

fazer_login(bot)
```

`tentativas=` só tem efeito no uso como decorator — aí ele reexecuta a
**função inteira** do zero se ela falhar (até `tentativas` vezes). Usada como
`with`, uma etapa roda no máximo uma vez (não tem como reexecutar um bloco
`with` de fora). Em nenhum dos dois casos a exceção original é suprimida —
ela sempre se propaga (ou, na última tentativa esgotada, é relançada) depois
de a etapa registrar o que aconteceu.

`ResultadoEtapa` (em `etapa.resultado`) tem: `nome`, `status`
(`"sucesso"`/`"falha"`/`"em_andamento"`), `duracao_segundos`, `erro`, `acoes`,
`retries` e `tentativas`.

### Fluxo

`Fluxo` é uma automação nomeada, **montada independente de qualquer
`Navegador`** e executada contra um depois — o navegador só entra na hora de
rodar:

```python
from webot import Fluxo, Navegador

fluxo = Fluxo("Cadastro de cliente")
fluxo.navegar("https://exemplo.com/cadastro")
fluxo.preencher_formulario({"#nome": "Maria", "#pais": "Brasil"})
fluxo.clicar(texto="Salvar")

with Navegador() as bot:
    resultado = fluxo.executar(bot)
```

Cada passo adicionado (pelos atalhos `.navegar()`/`.clicar()`/`.digitar()`/
`.preencher_formulario()`, ou por `.adicionar(funcao, nome=...)` pra qualquer
lógica customizada) vira uma `Etapa` própria quando o fluxo roda — por isso
`resultado.etapas` mostra exatamente a sequência, com o status de cada uma.

Se uma etapa falhar, `.executar()` levanta `ErroFluxo` (em vez de devolver um
resultado com status de falha) — consistente com o resto do webot, que sempre
sinaliza problema por exceção. `erro.resultado` tem as etapas concluídas até
ali, pra quem quiser inspecionar o que rodou antes da falha:

```python
from webot import ErroFluxo

try:
    fluxo.executar(bot)
except ErroFluxo as erro:
    print(f"{erro.resultado.nome} parou na etapa: {erro.resultado.etapas[-1].nome}")
```

O mesmo `Fluxo`, montado uma vez, pode rodar contra navegadores diferentes
(útil pra rodar a mesma automação em Chrome e Firefox, por exemplo).

### Métricas

`bot.metricas` (um `Metricas`) acumula `acoes`, `falhas` e `retries` pra
sessão inteira do navegador — incrementado automaticamente pelas ações
principais (`navegar`, `encontrar`, `clicar`, `digitar`, `preencher_formulario`)
e pelo retry em erro transitório. `falhas` conta etapas que terminaram em
erro especificamente (não qualquer exceção solta fora de uma etapa).
`ResultadoFluxo`/`ResultadoEtapa` têm suas próprias `total_acoes`/`acoes`,
`total_retries`/`retries`, `total_falhas` e `taxa_sucesso` — o recorte de
cada fluxo/etapa, não a sessão inteira.

### Histórico de ações

`bot.historico` (uma lista de `RegistroAcao`) acumula, em ordem, cada ação
bem-sucedida do `Navegador` (e dos `Elemento`s dele) — `navegar`, `encontrar`,
`encontrar_todos`, `clicar` e `digitar` — com timestamp, os detalhes do alvo
(seletor ou tag do elemento) e a etapa nomeada ativa no momento, se houver:

```python
with bot.etapa("Login"):
    bot.clicar(id="botao-entrar")

for registro in bot.historico:
    print(registro.timestamp, registro.etapa, registro.acao, registro.detalhes)
# 2026-... None  navegar {"url": "..."}
# 2026-... Login clicar  {"seletor": {"id": "botao-entrar"}}
```

Por segurança, `digitar()` **nunca** grava o texto digitado em `detalhes` —
só o seletor/elemento alvo — pra não acabar salvando senha/dado sensível em
memória ou num relatório exportado. Não é um substituto de `Evidencia`
(que também registra falhas) nem das `metricas` (contadores agregados); os
três juntos saem num só arquivo com `salvar_relatorio_json()`, abaixo.

### Evidências

Toda vez que uma espera expira, o webot registra uma `Evidencia` (timestamp,
URL, etapa, ação e o erro) em `bot.evidencias` — mesmo sem nenhuma
configuração. Se `pasta_screenshot_erro` estiver definida (ver
[Configuração](#configuração)), a mesma evidência também ganha um screenshot
PNG **e o HTML da página no momento do erro**, salvos nessa pasta:

```python
try:
    bot.encontrar(id="algo-que-sumiu", timeout=5)
except ErroElementoNaoEncontrado:
    evidencia = bot.evidencias[-1]
    print(evidencia.etapa, evidencia.url, evidencia.caminho_screenshot, evidencia.caminho_html)
```

Se a falha acontece dentro de uma `with bot.etapa(...):` e se propaga pra
fora dela, a evidência já vem com `etapa` preenchido (a etapa não duplica a
captura — só anota o próprio nome na evidência que a ação já tinha registrado).

`bot.salvar_relatorio_json(caminho)` exporta `metricas` + `historico` +
todas as `evidencias` acumuladas num arquivo `.json` de uma vez — útil pra
auditoria/dashboard de um robô rodando desacompanhado:

```python
bot.salvar_relatorio_json("relatorio.json")
```

```json
{
  "metricas": {"acoes": 12, "falhas": 1, "retries": 0},
  "historico": [
    {"timestamp": "2026-09-14T10:03:12.100000", "acao": "navegar", "detalhes": {"url": "https://exemplo.com"}, "etapa": null},
    {"timestamp": "2026-09-14T10:03:12.300000", "acao": "clicar", "detalhes": {"seletor": {"id": "botao-entrar"}}, "etapa": "Login"}
  ],
  "evidencias": [
    {
      "timestamp": "2026-09-14T10:03:12.481903",
      "erro": "...",
      "etapa": "Login",
      "acao": "encontrar",
      "url": "https://exemplo.com",
      "caminho_screenshot": null,
      "caminho_html": null
    }
  ]
}
```

### Modo debug

`bot.debug()` liga, no console, um log estruturado de cada ação do webot a
partir daquele momento — sem precisar configurar o `logging` do Python na
mão. `bot.debug(False)` desliga de novo:

```python
bot.navegar("https://exemplo.com")  # nada é logado (modo debug desligado)

bot.debug()
bot.clicar(texto="Entrar")  # essa ação aparece no console

bot.debug(False)
```

Por baixo, isso só liga um handler de console no logger `"webot"` (pai de
todos os loggers do pacote) e sobe o nível pra `DEBUG` — os `logger.info`
que cada método já chama internamente (navegar, clicar, etapas, retries...)
passam a aparecer. Como `logging` é global no processo, ligar afeta os logs
de **qualquer** `Navegador` ativo, não só o que chamou `.debug()`.

## Erros

Toda exceção lançada pela abstração herda de `ErroAutomacao`, então dá pra
capturar tudo de uma vez ou ser específico:

- `ErroAoIniciarNavegador` — falha ao subir o navegador (driver ausente,
  binário não encontrado, etc.).
- `ErroNavegadorNaoIniciado` — algum método foi chamado antes de `iniciar()`.
- `ErroElementoNaoEncontrado` — a condição esperada (elemento, alerta, etc.)
  não aconteceu dentro do timeout. A mensagem inclui o seletor/elemento que
  estava sendo esperado, para facilitar achar qual `encontrar()`/`clicar()`
  falhou num fluxo com vários seguidos.
- `ErroSeletorInvalido` — zero, duas ou mais chaves de seletor foram passadas
  numa mesma chamada, ou uma chave desconhecida.
- `ErroFluxo` — uma etapa de um `Fluxo.executar()` falhou. `erro.resultado`
  (um `ResultadoFluxo`) tem as etapas concluídas até a falha.

## Empacotar num executável

`Empacotador` compila um script de automação feito com webot num `.exe`
standalone (via [PyInstaller](https://pyinstaller.org/)) — quem for rodar não
precisa ter Python instalado, só o **navegador** em si (Chrome/Edge/Firefox),
do mesmo jeito que qualquer robô de RPA corporativo.

```bash
pip install webot[empacotar]     # instala o PyInstaller
```

```python
from webot import Empacotador

Empacotador("meu_script.py", nome="MinhaAutomacao").empacotar()
# gerado em: dist/MinhaAutomacao.exe
```

Por ser uma classe (em vez de só um comando de terminal), a configuração de
build fica em código — dá pra versionar no repositório do robô ao lado do
próprio script, em vez de depender de lembrar flags de cor. O mesmo também
está disponível direto no terminal, útil pra um empacotamento pontual:

```bash
python -m webot empacotar meu_script.py --nome MinhaAutomacao
```

### Opções

- **`nome`** — nome do executável gerado. Padrão: nome do script (sem `.py`).
- **`icone`** — caminho de um `.ico` para o executável.
- **`sem_console`** (`--sem-console` na CLI) — gera sem janela de console
  (`--windowed` do PyInstaller). Nesse modo `print()`/`input()` não
  funcionam — troque por logging em arquivo antes de empacotar assim.
- **`onedir`** (`--onedir` na CLI) — gera uma pasta com vários arquivos em
  vez de um único `.exe`. Inicia mais rápido, já que o `--onefile` (padrão)
  descompacta tudo numa pasta temporária a cada execução.
- **`pasta_saida`** (`--pasta-saida`) — onde o executável é gerado. Padrão:
  `dist/` na pasta do script.
- **`imports_ocultos`** (`--hidden-import`, repetível) — módulos que o
  PyInstaller não detecta sozinho.
- **`arquivos_adicionais`** (`--add-data`, repetível) — arquivos/pastas
  extras a incluir, no formato `'origem;destino'`.
- **`argumentos_extras`** — flags cruas repassadas direto ao PyInstaller,
  para casos não cobertos acima (só via classe, não tem flag na CLI).

```python
config_producao = Empacotador(
    "meu_script.py",
    nome="MinhaAutomacao",
    icone="logo.ico",
    sem_console=True,
    onedir=True,
)
executavel = config_producao.empacotar()
```

Não é compilação nativa de verdade (o Python continua interpretado por
dentro) — é o interpretador + o script + as dependências, tudo dentro de um
único arquivo (ou pasta, com `onedir=True`). Isso também significa que o
`.exe` **não** leva o navegador junto: a máquina que for rodar precisa ter
Chrome/Edge/Firefox já instalado.

## Estrutura do projeto

```
webot/
├── pyproject.toml          # metadados do pacote e dependências (fonte única)
├── webot/
│   ├── __init__.py         # API pública (o que é exportado) + __version__
│   ├── configuracao.py     # ConfiguracaoNavegador (pydantic) e TipoNavegador
│   ├── navegador.py        # a classe Navegador (a abstração em si)
│   ├── elemento.py         # a classe Elemento (envelope de um WebElement já achado)
│   ├── formulario.py       # Campo e a lógica de preencher_formulario()
│   ├── etapa.py            # Etapa (with/decorator) e ResultadoEtapa
│   ├── fluxo.py            # Fluxo, ResultadoFluxo e ErroFluxo
│   ├── metricas.py         # Metricas (contadores de ações/falhas/retries)
│   ├── evidencias.py       # Evidencia (o formato do registro de uma falha)
│   ├── historico.py        # RegistroAcao (o passo a passo de ações bem-sucedidas)
│   ├── resultados.py       # modelos de retorno tipados (InfoElemento)
│   ├── excecoes.py         # hierarquia de exceções do pacote
│   ├── _utilitarios.py     # seletor/retry/scripts JS compartilhados (uso interno)
│   ├── empacotar.py        # Empacotador (PyInstaller) + CLI de `python -m webot empacotar`
│   ├── __main__.py         # CLI: `python -m webot <comando>`
│   └── py.typed            # marcador de suporte a tipagem (PEP 561)
├── scripts/
│   ├── introspeccao.py         # lê a API pública do webot via inspect
│   └── gerar_referencia_ia.py  # gera REFERENCIA_IA.md a partir da introspecção
├── REFERENCIA_IA.md        # gerado — API completa num arquivo só, para dar a uma IA
├── exemplos/
│   ├── basico.py                     # primeiro contato: navegar/clicar/ler, trocar de navegador
│   ├── seletores_e_busca.py          # id/css/xpath/nome/classe/tag/texto/texto_link, busca aninhada
│   ├── interacao_e_formularios.py    # clicar/digitar/selects/upload, preencher_formulario
│   ├── esperas.py                    # esperar_url/titulo/texto_conter, esperar_rede_ociosa, esperar_ate
│   ├── abas_frames_alertas.py        # aba(), nova_aba/mudar_para_janela, mudar_para_frame, alertas JS
│   ├── downloads_e_evidencias.py     # baixar_arquivo, screenshot automático, evidências, retry
│   ├── etapas_e_fluxo.py             # etapa(), Fluxo, métricas
│   ├── configuracao_avancada.py      # iniciar/encerrar manual, driver_bruto, demais campos de config
│   ├── modo_debug.py                 # debug(): log estruturado no console, sem configurar logging
│   └── empacotamento.py              # Empacotador: gerar um .exe standalone (PyInstaller)
└── tests/
    ├── conftest.py                  # fixtures: browser de teste + página local
    ├── fixtures/pagina_teste.html
    ├── test_navegador.py
    ├── test_seletor_texto.py
    ├── test_formulario.py
    ├── test_etapa.py
    ├── test_fluxo.py
    ├── test_metricas.py
    ├── test_evidencias.py
    ├── test_historico.py
    ├── test_debug.py
    ├── test_empacotar.py            # Empacotador: comando montado (mock) + integração real com o PyInstaller
    ├── test_downloads_e_erros.py    # baixar_arquivo() e screenshot automático
    ├── test_utilitarios.py          # retry configurável (sem browser)
    ├── test_introspeccao.py         # introspecção usada por gerar_referencia_ia.py
    ├── test_gerar_referencia_ia.py
    ├── test_cobertura_exemplos.py   # todo método/campo público tem exemplo em exemplos/
    └── test_contrato_configuracao.py
```

Todo método/propriedade público de `Navegador`/`Elemento`/`Fluxo`/`Etapa` e
todo campo de `ConfiguracaoNavegador` aparece em pelo menos um exemplo —
garantido por `tests/test_cobertura_exemplos.py`, que cruza
`scripts/introspeccao.py` com o texto dos arquivos em `exemplos/` (falha se
algo novo na API ficar sem exemplo). Todos os exemplos foram rodados de
verdade contra Chrome. `basico.py` também foi testado com `tipo_navegador="edge"`;
com `"firefox"` não pôde ser testado na máquina onde foi escrito por falta do
Firefox instalado — vale rodar uma vez antes de confiar nele.

`exemplos/` não vai para o pacote instalado via `pip install` (só `webot/`
vai — ver `[tool.hatch.build.targets.wheel]` em `pyproject.toml`); ele existe
para quem clona o repositório, não para quem instala a lib.

Cada módulo tem uma responsabilidade: `configuracao.py` só valida entrada,
`resultados.py` só define o formato de saída, `excecoes.py` só nomeia erros,
`navegador.py` fala com o Selenium no nível da página, e `elemento.py` faz a
mesma coisa no nível de um elemento já encontrado (inclusive busca aninhada
dentro dele). `formulario.py`, `etapa.py`, `fluxo.py`, `metricas.py` e
`evidencias.py` são a camada de observabilidade — cada um cuidando de uma
coisa só, pra não inchar `navegador.py`/`elemento.py`. `_utilitarios.py` é o
que `navegador.py`/`elemento.py` compartilham por baixo (mapa de seletores,
retry em elemento "stale", os scripts JS).

## Referência para IA

`REFERENCIA_IA.md`, na raiz do projeto, é a API inteira do webot num único
arquivo Markdown — todas as classes, métodos, propriedades e campos, cada um
com assinatura e docstring reais. É pra isso mesmo: copie o arquivo pra dentro
de outro projeto, ou cole o conteúdo numa conversa com uma IA, e ela entende
como usar a biblioteca sem precisar ler o código-fonte.

Ele é **gerado**, não escrito à mão — `scripts/gerar_referencia_ia.py` lê a
API via `inspect` (mesma técnica de `scripts/introspeccao.py`) e escreve o
Markdown. Rode de novo depois de qualquer mudança na API pública (precisa do
projeto instalado em modo editável — `pip install -e .`, ver
[Instalação](#instalação)):

```bash
python scripts/gerar_referencia_ia.py
```

Não precisa de nenhuma dependência além do que o projeto já tem (`selenium`,
`pydantic`) — é só um script Python, sem servidor, sem processo rodando, sem
protocolo pra configurar em cliente nenhum.

## Desenvolvimento

> Esta seção é só para quem vai mexer no código do webot em si — pra só usar
> a lib num projeto de automação, o [Guia rápido](#guia-rápido) já basta.

```bash
pip install -e ".[dev]"   # instala selenium/pydantic + pytest/ruff/mypy
pytest                    # roda a suite contra uma página HTML local (sem internet)
ruff check .              # lint
mypy webot scripts        # checagem de tipos
```

`tests/test_contrato_configuracao.py` existe especificamente para pegar o
caso de alguém adicionar um campo em `ConfiguracaoNavegador` e esquecer de
replicá-lo em `Navegador.__init__` (ou vice-versa) — falha alto e claro em
vez de deixar os dois saírem de sincronia silenciosamente.

### CI

Todo push/PR em `main` roda [`.github/workflows/ci.yml`](.github/workflows/ci.yml)
em 4 jobs paralelos: `ruff check .`, `mypy webot scripts`, a suíte completa
(`pytest`, incluindo os testes de integração reais do `Empacotador`), e uma
checagem de que `REFERENCIA_IA.md` está sincronizado com o código (roda
`scripts/gerar_referencia_ia.py` de novo e falha se o resultado for
diferente do commitado). Nada disso substitui rodar localmente antes de
commitar — só pega o que passou batido.

## Versionamento

O projeto segue [SemVer](https://semver.org/lang/pt-BR/). Cada versão publicada
vira uma tag Git (`v0.1.0`, `v0.2.0`, ...) e projetos consumidores travam numa
tag específica no `pip install git+URL@tag`. Atualizar a lib em um projeto é
só trocar a tag depois de conferir o changelog da nova versão.
