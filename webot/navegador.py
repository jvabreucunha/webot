from __future__ import annotations

import logging
import random
import time
from collections.abc import Callable, Generator
from contextlib import contextmanager, suppress
from datetime import datetime
from pathlib import Path
from types import TracebackType
from typing import Any, Literal, TypeVar

from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.chrome.options import Options as OpcoesChrome
from selenium.webdriver.edge.options import Options as OpcoesEdge
from selenium.webdriver.firefox.options import Options as OpcoesFirefox
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as CE
from selenium.webdriver.support.ui import Select, WebDriverWait

from ._utilitarios import (
    JS_INJETAR_OBSERVADOR_MUTACOES,
    arquivos_prontos,
    clicar_com_fallback,
    repetir_se_transitorio,
    resolver_seletor,
)
from .configuracao import ConfiguracaoNavegador, TipoNavegador
from .elemento import Elemento
from .etapa import Etapa
from .evidencias import Evidencia
from .excecoes import (
    ErroAoIniciarNavegador,
    ErroElementoNaoEncontrado,
    ErroNavegadorNaoIniciado,
    ErroSeletorInvalido,
)
from .formulario import Campo, normalizar_campos, preencher_campo
from .metricas import Metricas
from .resultados import InfoElemento

logger = logging.getLogger(__name__)

# Logger raiz de todo o pacote (ex.: "webot.navegador" é filho de "webot") —
# é nele que Navegador.debug() liga/desliga o handler de console.
_LOGGER_PACOTE = logging.getLogger("webot")
_handler_debug: logging.Handler | None = None

T = TypeVar("T")


class Navegador:
    """Abstração em pt-br que encapsula o WebDriver do Selenium.

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
    """

    def __init__(
        self,
        config: ConfiguracaoNavegador | None = None,
        *,
        tipo_navegador: TipoNavegador | None = None,
        sem_interface: bool | None = None,
        anonimo: bool | None = None,
        tamanho_janela: tuple[int, int] | None = None,
        maximizar_janela: bool | None = None,
        pasta_download: str | Path | None = None,
        espera_implicita: float | None = None,
        tempo_espera_padrao: float | None = None,
        tempo_carregamento_pagina: float | None = None,
        agente_usuario: str | None = None,
        caminho_binario: str | None = None,
        argumentos_extras: list[str] | None = None,
        pasta_screenshot_erro: str | Path | None = None,
        tentativas_retry_transitorio: int | None = None,
        espera_entre_tentativas: float | None = None,
    ) -> None:
        """Cria o navegador a partir de opções soltas (uso simples) ou de um
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
        """
        opcoes = {
            "tipo_navegador": tipo_navegador,
            "sem_interface": sem_interface,
            "anonimo": anonimo,
            "tamanho_janela": tamanho_janela,
            "maximizar_janela": maximizar_janela,
            "pasta_download": pasta_download,
            "espera_implicita": espera_implicita,
            "tempo_espera_padrao": tempo_espera_padrao,
            "tempo_carregamento_pagina": tempo_carregamento_pagina,
            "agente_usuario": agente_usuario,
            "caminho_binario": caminho_binario,
            "argumentos_extras": argumentos_extras,
            "pasta_screenshot_erro": pasta_screenshot_erro,
            "tentativas_retry_transitorio": tentativas_retry_transitorio,
            "espera_entre_tentativas": espera_entre_tentativas,
        }
        fornecidas = {chave: valor for chave, valor in opcoes.items() if valor is not None}

        if config is not None and fornecidas:
            raise ValueError(
                "Passe uma ConfiguracaoNavegador pronta OU as opções soltas, não os dois."
            )
        # mypy não consegue verificar um dict heterogêneo contra os campos nomeados
        # do pydantic; a correspondência de nome/tipo é garantida em runtime pelo
        # próprio pydantic e coberta por tests/test_contrato_configuracao.py.
        self.config = config or ConfiguracaoNavegador(**fornecidas)  # type: ignore[arg-type]
        self._driver: webdriver.Remote | None = None
        self.metricas = Metricas()
        self.evidencias: list[Evidencia] = []
        self._etapa_atual: Etapa | None = None

    # ---------------------------------------------------------------- #
    # ciclo de vida
    # ---------------------------------------------------------------- #
    def iniciar(self) -> Navegador:
        """Abre o navegador de acordo com a config. Idempotente — chamar de
        novo com o navegador já aberto não faz nada. Normalmente não precisa
        ser chamado direto: use `with Navegador(...) as bot:`.

        Returns:
            O próprio `Navegador` (para permitir `bot = Navegador(...).iniciar()`).

        Raises:
            ErroAoIniciarNavegador: driver/binário do navegador não encontrado
                ou falha ao subir o processo.
        """
        if self._driver is not None:
            logger.debug("Navegador já iniciado, ignorando nova chamada a iniciar()")
            return self

        opcoes = self._montar_opcoes()
        try:
            if isinstance(opcoes, OpcoesChrome):
                self._driver = webdriver.Chrome(options=opcoes)
            elif isinstance(opcoes, OpcoesEdge):
                self._driver = webdriver.Edge(options=opcoes)
            elif isinstance(opcoes, OpcoesFirefox):
                self._driver = webdriver.Firefox(options=opcoes)
            else:
                raise ErroAoIniciarNavegador(
                    f"Navegador não suportado: {self.config.tipo_navegador}"
                )
        except WebDriverException as erro:
            raise ErroAoIniciarNavegador(
                f"Falha ao iniciar o navegador {self.config.tipo_navegador}: {erro}"
            ) from erro

        self._driver.set_page_load_timeout(self.config.tempo_carregamento_pagina)
        self._driver.implicitly_wait(self.config.espera_implicita)

        if isinstance(opcoes, OpcoesChrome | OpcoesEdge) and self.config.sem_interface and self.config.pasta_download:
            # Chrome/Edge headless bloqueiam download disparado por JS/clique a
            # menos que isso seja liberado explicitamente via CDP.
            with suppress(WebDriverException):
                self._driver.execute_cdp_cmd(
                    "Page.setDownloadBehavior",
                    {"behavior": "allow", "downloadPath": str(self.config.pasta_download)},
                )

        if self.config.maximizar_janela:
            self._driver.maximize_window()
        elif self.config.tamanho_janela:
            largura, altura = self.config.tamanho_janela
            self._driver.set_window_size(largura, altura)

        logger.info(
            "Navegador %s iniciado (sem_interface=%s, anonimo=%s)",
            self.config.tipo_navegador,
            self.config.sem_interface,
            self.config.anonimo,
        )
        return self

    def encerrar(self) -> None:
        """Fecha o navegador. Idempotente e seguro de chamar mesmo se o
        navegador ainda não tiver sido iniciado ou já estiver fechado."""
        if self._driver is not None:
            with suppress(WebDriverException):
                self._driver.quit()
            self._driver = None
            logger.info("Navegador encerrado")

    def __enter__(self) -> Navegador:
        return self.iniciar()

    def __exit__(
        self,
        _tipo_exc: type[BaseException] | None,
        _valor_exc: BaseException | None,
        _traceback_exc: TracebackType | None,
    ) -> None:
        self.encerrar()

    @property
    def driver_bruto(self) -> webdriver.Remote:
        """Acesso ao WebDriver puro do Selenium, para casos que a abstração não cobre."""
        if self._driver is None:
            raise ErroNavegadorNaoIniciado(
                "O navegador não foi iniciado. Chame iniciar() ou use como context manager (with)."
            )
        return self._driver

    def _montar_opcoes(self) -> OpcoesChrome | OpcoesEdge | OpcoesFirefox:
        opcoes: OpcoesChrome | OpcoesEdge | OpcoesFirefox
        if self.config.tipo_navegador == TipoNavegador.CHROME:
            opcoes = OpcoesChrome()
        elif self.config.tipo_navegador == TipoNavegador.EDGE:
            opcoes = OpcoesEdge()
        elif self.config.tipo_navegador == TipoNavegador.FIREFOX:
            opcoes = OpcoesFirefox()
        else:
            raise ErroAoIniciarNavegador(f"Navegador não suportado: {self.config.tipo_navegador}")

        if isinstance(opcoes, OpcoesFirefox):
            self._aplicar_opcoes_firefox(opcoes)
        else:
            self._aplicar_opcoes_chromium(opcoes)

        if self.config.caminho_binario:
            opcoes.binary_location = self.config.caminho_binario

        for argumento in self.config.argumentos_extras:
            opcoes.add_argument(argumento)

        return opcoes

    def _aplicar_opcoes_chromium(self, opcoes: OpcoesChrome | OpcoesEdge) -> None:
        """Chrome e Edge são ambos Chromium: mesma sintaxe de flags/prefs."""
        if self.config.anonimo:
            opcoes.add_argument("--incognito" if isinstance(opcoes, OpcoesChrome) else "--inprivate")

        if self.config.sem_interface:
            opcoes.add_argument("--headless=new")

        if self.config.tamanho_janela and not self.config.maximizar_janela:
            largura, altura = self.config.tamanho_janela
            opcoes.add_argument(f"--window-size={largura},{altura}")

        if self.config.pasta_download:
            opcoes.add_experimental_option(
                "prefs", {"download.default_directory": str(self.config.pasta_download)}
            )

        if self.config.agente_usuario:
            opcoes.add_argument(f"--user-agent={self.config.agente_usuario}")

    def _aplicar_opcoes_firefox(self, opcoes: OpcoesFirefox) -> None:
        if self.config.anonimo:
            opcoes.set_preference("browser.privatebrowsing.autostart", True)

        if self.config.sem_interface:
            opcoes.add_argument("-headless")

        if self.config.pasta_download:
            opcoes.set_preference("browser.download.folderList", 2)
            opcoes.set_preference("browser.download.dir", str(self.config.pasta_download))

        if self.config.agente_usuario:
            opcoes.set_preference("general.useragent.override", self.config.agente_usuario)

    # ---------------------------------------------------------------- #
    # navegação
    # ---------------------------------------------------------------- #
    def navegar(self, url: str) -> None:
        """Abre `url` na aba atual e espera o carregamento terminar.

        Args:
            url: endereço com esquema (ex.: `"https://exemplo.com"`).

        Raises:
            selenium.common.exceptions.TimeoutException: a página não carregou
                dentro de `tempo_carregamento_pagina` (config). Essa é uma
                exceção do próprio Selenium, não uma `Erro*` do webot — é o
                único ponto onde isso ainda acontece, porque `navegar()` não
                passa por `esperar_ate()`.
        """
        logger.info("Navegando para %s", url)
        self.driver_bruto.get(url)
        self.metricas.acoes += 1

    def atualizar(self) -> None:
        """Recarrega a página atual (equivalente a F5)."""
        self.driver_bruto.refresh()

    def voltar(self) -> None:
        """Volta uma página no histórico de navegação."""
        self.driver_bruto.back()

    def avancar(self) -> None:
        """Avança uma página no histórico de navegação."""
        self.driver_bruto.forward()

    @property
    def url_atual(self) -> str:
        """URL da aba atual."""
        return self.driver_bruto.current_url

    @property
    def titulo(self) -> str:
        """Título (`<title>`) da página atual."""
        return self.driver_bruto.title

    # ---------------------------------------------------------------- #
    # esperas
    # ---------------------------------------------------------------- #
    def _wait(self, timeout: float | None = None) -> WebDriverWait:
        return WebDriverWait(self.driver_bruto, timeout or self.config.tempo_espera_padrao)

    def esperar_ate(
        self,
        condicao: Callable[[Any], Literal[False] | T],
        timeout: float | None = None,
        *,
        descricao: str | Callable[[], str] | None = None,
    ) -> T:
        """Escape hatch para condições customizadas (selenium.webdriver.support.expected_conditions).

        `descricao` (texto fixo ou função sem argumentos) só é avaliada se o
        timeout realmente estourar, e aparece na mensagem de erro — útil para
        dizer qual seletor/elemento estava sendo esperado.
        """
        try:
            return self._wait(timeout).until(condicao)
        except TimeoutException as erro:
            texto_descricao = descricao() if callable(descricao) else descricao
            sufixo = f" — {texto_descricao}" if texto_descricao else ""
            self._registrar_evidencia(acao=texto_descricao, erro=erro)
            raise ErroElementoNaoEncontrado(
                f"Condição não satisfeita dentro do tempo de espera "
                f"({timeout or self.config.tempo_espera_padrao}s){sufixo}"
            ) from erro

    def _registrar_evidencia(
        self, *, etapa: str | None = None, acao: str | None = None, erro: BaseException | str | None = None
    ) -> Evidencia:
        """Registra uma `Evidencia` do estado atual (sempre, em `self.evidencias`)
        e, se `pasta_screenshot_erro` estiver configurada, também salva
        screenshot + HTML da página nela. Nunca deixa uma falha ao capturar
        mascarar o erro original — no máximo registra um aviso no log."""
        url_atual: str | None = None
        with suppress(WebDriverException):
            url_atual = self.driver_bruto.current_url
        evidencia = Evidencia(
            timestamp=datetime.now(),
            erro=str(erro) if erro is not None else "",
            etapa=etapa,
            acao=acao,
            url=url_atual,
        )
        self.evidencias.append(evidencia)

        if self.config.pasta_screenshot_erro:
            pasta = Path(self.config.pasta_screenshot_erro)
            carimbo = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            try:
                pasta.mkdir(parents=True, exist_ok=True)
                caminho_screenshot = pasta / f"erro_{carimbo}.png"
                self.driver_bruto.save_screenshot(str(caminho_screenshot))
                evidencia.caminho_screenshot = caminho_screenshot
                logger.warning("Screenshot do erro salvo em %s", caminho_screenshot)

                caminho_html = pasta / f"erro_{carimbo}.html"
                caminho_html.write_text(self.driver_bruto.page_source, encoding="utf-8")
                evidencia.caminho_html = caminho_html
                logger.warning("HTML da página no erro salvo em %s", caminho_html)
            except (OSError, WebDriverException) as erro_captura:
                logger.warning("Falha ao capturar evidência do erro: %s", erro_captura)

        return evidencia

    def esperar_url_conter(self, trecho: str, *, timeout: float | None = None) -> None:
        """Espera a URL atual conter `trecho` (útil depois de um clique que navega)."""
        self.esperar_ate(CE.url_contains(trecho), timeout, descricao=f"url conter {trecho!r}")

    def esperar_titulo_conter(self, trecho: str, *, timeout: float | None = None) -> None:
        """Espera o título da página conter `trecho`."""
        self.esperar_ate(CE.title_contains(trecho), timeout, descricao=f"título conter {trecho!r}")

    def esperar_texto_conter(
        self, texto: str, *, timeout: float | None = None, **seletor: str | None
    ) -> None:
        """Espera o texto de um elemento (por seletor) conter `texto` — útil
        depois de uma ação que atualiza um elemento já existente via JS/AJAX."""
        by, valor = resolver_seletor(**seletor)
        self.esperar_ate(
            CE.text_to_be_present_in_element((by, valor), texto),
            timeout,
            descricao=f"{by}={valor!r} conter texto {texto!r}",
        )

    def esperar_rede_ociosa(self, *, tempo_estavel: float = 0.5, timeout: float | None = None) -> None:
        """Espera o DOM parar de mudar — uma heurística para "rede ociosa" em
        SPAs que carregam dados via AJAX depois do carregamento inicial.

        Não é uma detecção real de requisições de rede (isso exigiria CDP,
        específico do Chromium); em vez disso, observa mutações no DOM via
        `MutationObserver` e considera a página estável quando nenhuma
        mutação acontece por `tempo_estavel` segundos seguidos.
        """
        limite = timeout or self.config.tempo_espera_padrao
        fim = time.monotonic() + limite
        self.executar_script(JS_INJETAR_OBSERVADOR_MUTACOES)
        ultima_contagem = -1
        while time.monotonic() < fim:
            contagem_atual = self.executar_script("return window.__webot_mutacoes__;")
            if contagem_atual == ultima_contagem:
                return
            ultima_contagem = contagem_atual
            time.sleep(tempo_estavel)
        erro = ErroElementoNaoEncontrado(f"A página não ficou estável (rede ociosa) dentro de {limite}s")
        self._registrar_evidencia(acao="esperar_rede_ociosa", erro=erro)
        raise erro

    # ---------------------------------------------------------------- #
    # localizar elementos
    # ---------------------------------------------------------------- #
    def encontrar(self, *, timeout: float | None = None, **seletor: str | None) -> Elemento:
        """Espera um elemento existir no DOM e o devolve.

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
        """
        by, valor = resolver_seletor(**seletor)
        bruto = self.esperar_ate(
            CE.presence_of_element_located((by, valor)), timeout, descricao=f"{by}={valor!r}"
        )
        self.metricas.acoes += 1
        logger.info("Elemento encontrado (%s=%r)", by, valor)
        return Elemento(bruto, self)

    def encontrar_todos(self, *, timeout: float | None = None, **seletor: str | None) -> list[Elemento]:
        """Como `encontrar()`, mas espera existir pelo menos um elemento e
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
        """
        by, valor = resolver_seletor(**seletor)
        brutos = self.esperar_ate(
            CE.presence_of_all_elements_located((by, valor)), timeout, descricao=f"{by}={valor!r}"
        )
        self.metricas.acoes += 1
        logger.info("%d elemento(s) encontrado(s) (%s=%r)", len(brutos), by, valor)
        return [Elemento(bruto, self) for bruto in brutos]

    def esta_presente(self, *, timeout: float = 1, **seletor: str | None) -> bool:
        """Verifica se um elemento existe, sem lançar exceção.

        Como o timeout padrão é curto (1s, diferente dos outros métodos que
        usam `tempo_espera_padrao`), não é ideal pra confirmar ausência
        definitiva de algo que ainda pode demorar a aparecer — nesse caso
        aumente `timeout`.

        Args:
            timeout: segundos a esperar. Padrão: 1.
            **seletor: mesmas chaves de `encontrar()`.

        Returns:
            `True` se achou dentro do timeout, `False` caso contrário.
        """
        try:
            self.encontrar(timeout=timeout, **seletor)
            return True
        except ErroElementoNaoEncontrado:
            return False

    def _encontrar_visivel(self, timeout: float | None, **seletor: str | None) -> WebElement:
        by, valor = resolver_seletor(**seletor)
        return self.esperar_ate(
            CE.visibility_of_element_located((by, valor)), timeout, descricao=f"{by}={valor!r} visível"
        )

    def _encontrar_clicavel(self, timeout: float | None, **seletor: str | None) -> WebElement:
        by, valor = resolver_seletor(**seletor)
        return self.esperar_ate(
            CE.element_to_be_clickable((by, valor)), timeout, descricao=f"{by}={valor!r} clicável"
        )

    @staticmethod
    def _validar_elemento_ou_seletor(elemento: Elemento | None, seletor: dict[str, str | None]) -> None:
        if elemento is not None and any(valor is not None for valor in seletor.values()):
            raise ErroSeletorInvalido(
                "Passe um elemento já encontrado (elemento=...) OU um seletor, não os dois."
            )

    def _resolver_elemento(
        self, elemento: Elemento | None, timeout: float | None, **seletor: str | None
    ) -> Elemento:
        """Resolve para um `Elemento` já pronto para uso: o que foi passado em
        `elemento=`, ou o resultado de `encontrar(**seletor)`."""
        self._validar_elemento_ou_seletor(elemento, seletor)
        if elemento is not None:
            return elemento
        return self.encontrar(timeout=timeout, **seletor)

    def _resolver_visivel(
        self, elemento: Elemento | None, timeout: float | None, **seletor: str | None
    ) -> WebElement:
        self._validar_elemento_ou_seletor(elemento, seletor)
        if elemento is not None:
            return self.esperar_ate(
                CE.visibility_of(elemento.bruto), timeout, descricao=lambda: f"elemento <{elemento.tag}> visível"
            )
        return self._encontrar_visivel(timeout, **seletor)

    def _resolver_clicavel(
        self, elemento: Elemento | None, timeout: float | None, **seletor: str | None
    ) -> WebElement:
        self._validar_elemento_ou_seletor(elemento, seletor)
        if elemento is not None:
            return self.esperar_ate(
                CE.element_to_be_clickable(elemento.bruto),
                timeout,
                descricao=lambda: f"elemento <{elemento.tag}> clicável",
            )
        return self._encontrar_clicavel(timeout, **seletor)

    # ---------------------------------------------------------------- #
    # interações
    # ---------------------------------------------------------------- #
    @repetir_se_transitorio
    def clicar(
        self,
        *,
        elemento: Elemento | None = None,
        timeout: float | None = None,
        **seletor: str | None,
    ) -> None:
        """Clica no elemento. Passe um seletor (`css=`, `id=`, ...) para achar e
        clicar em um só passo, ou um `elemento` já obtido antes via `encontrar`/
        `encontrar_todos` (por exemplo, para clicar no 3º item de uma lista —
        equivalente a chamar `.clicar()` direto no `Elemento`)."""
        alvo = self._resolver_clicavel(elemento, timeout, **seletor)
        clicar_com_fallback(self.driver_bruto, alvo)
        self.metricas.acoes += 1
        logger.info("Clique realizado (%s)", seletor or "elemento")

    @repetir_se_transitorio
    def digitar(
        self,
        texto: str,
        *,
        elemento: Elemento | None = None,
        limpar: bool = True,
        timeout: float | None = None,
        **seletor: str | None,
    ) -> None:
        """Espera o elemento ficar visível e digita `texto` nele.

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
        """
        alvo = self._resolver_visivel(elemento, timeout, **seletor)
        if limpar:
            alvo.clear()
        alvo.send_keys(texto)
        self.metricas.acoes += 1
        logger.info("Texto digitado (%s)", seletor or "elemento")

    @repetir_se_transitorio
    def obter_texto(
        self, *, elemento: Elemento | None = None, timeout: float | None = None, **seletor: str | None
    ) -> str:
        """Espera o elemento ficar visível e devolve seu texto visível
        (equivalente ao `.text` do Selenium).

        Args:
            elemento: um `Elemento` já encontrado, como alternativa ao seletor.
            timeout: segundos a esperar; usa `tempo_espera_padrao` se omitido.
            **seletor: exatamente uma chave — não use junto com `elemento=`.

        Returns:
            O texto visível do elemento.
        """
        return self._resolver_visivel(elemento, timeout, **seletor).text

    @repetir_se_transitorio
    def obter_atributo(
        self,
        atributo: str,
        *,
        elemento: Elemento | None = None,
        timeout: float | None = None,
        **seletor: str | None,
    ) -> str | None:
        """Devolve o valor de um atributo HTML do elemento (ex.: `"href"`,
        `"value"`, `"class"`).

        Args:
            atributo: nome do atributo HTML.
            elemento: um `Elemento` já encontrado, como alternativa ao seletor.
            timeout: segundos a esperar; usa `tempo_espera_padrao` se omitido.
            **seletor: exatamente uma chave — não use junto com `elemento=`.

        Returns:
            O valor do atributo, ou `None` se o elemento não tiver esse atributo.
        """
        return self._resolver_elemento(elemento, timeout, **seletor).obter_atributo(atributo)

    @repetir_se_transitorio
    def obter_info(
        self, *, elemento: Elemento | None = None, timeout: float | None = None, **seletor: str | None
    ) -> InfoElemento:
        """Retorna um retrato tipado (pydantic) do elemento: `texto`, `tag`,
        `visivel`, `habilitado` e `atributos` (dict com todos os atributos
        HTML). Útil para logs de auditoria de um fluxo de RPA, já que
        (diferente de um `WebElement`/`Elemento`) é serializável.

        Args:
            elemento: um `Elemento` já encontrado, como alternativa ao seletor.
            timeout: segundos a esperar; usa `tempo_espera_padrao` se omitido.
            **seletor: exatamente uma chave — não use junto com `elemento=`.

        Returns:
            Um `InfoElemento` (`.model_dump()`/`.model_dump_json()` para serializar).
        """
        return self._resolver_elemento(elemento, timeout, **seletor).obter_info()

    @repetir_se_transitorio
    def selecionar_por_texto(
        self,
        texto: str,
        *,
        elemento: Elemento | None = None,
        timeout: float | None = None,
        **seletor: str | None,
    ) -> None:
        """Num `<select>` HTML, seleciona a opção pelo texto visível.

        Args:
            texto: texto visível da `<option>` a selecionar.
            elemento: um `Elemento` já encontrado (o próprio `<select>`), como
                alternativa ao seletor.
            timeout: segundos a esperar; usa `tempo_espera_padrao` se omitido.
            **seletor: exatamente uma chave — não use junto com `elemento=`.
        """
        Select(self._resolver_visivel(elemento, timeout, **seletor)).select_by_visible_text(texto)

    @repetir_se_transitorio
    def selecionar_por_valor(
        self,
        valor_opcao: str,
        *,
        elemento: Elemento | None = None,
        timeout: float | None = None,
        **seletor: str | None,
    ) -> None:
        """Num `<select>` HTML, seleciona a opção pelo atributo `value`.

        Args:
            valor_opcao: valor (`value=`) da `<option>` a selecionar.
            elemento: um `Elemento` já encontrado (o próprio `<select>`), como
                alternativa ao seletor.
            timeout: segundos a esperar; usa `tempo_espera_padrao` se omitido.
            **seletor: exatamente uma chave — não use junto com `elemento=`.
        """
        Select(self._resolver_visivel(elemento, timeout, **seletor)).select_by_value(valor_opcao)

    @repetir_se_transitorio
    def enviar_arquivo(
        self,
        caminho_arquivo: str,
        *,
        elemento: Elemento | None = None,
        timeout: float | None = None,
        **seletor: str | None,
    ) -> None:
        """Envia um arquivo para um `<input type="file">`, escrevendo o
        caminho absoluto nele (não abre nenhum seletor de arquivo do SO).

        Args:
            caminho_arquivo: caminho absoluto do arquivo no disco local.
            elemento: um `Elemento` já encontrado (o próprio `<input>`), como
                alternativa ao seletor.
            timeout: segundos a esperar; usa `tempo_espera_padrao` se omitido.
            **seletor: exatamente uma chave — não use junto com `elemento=`.
        """
        self._resolver_elemento(elemento, timeout, **seletor).enviar_arquivo(caminho_arquivo)

    def preencher_formulario(
        self, campos: dict[str, str | bool] | list[Campo], *, timeout: float | None = None
    ) -> None:
        """Preenche vários campos de um formulário de uma vez, escolhendo
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
        """
        for campo in normalizar_campos(campos):
            elemento = self.encontrar(timeout=timeout, **campo.seletor())
            preencher_campo(elemento, campo.valor)
            logger.debug("Campo %s preenchido", campo.seletor())
        logger.info("Formulário preenchido (%d campo(s))", len(campos))

    # ---------------------------------------------------------------- #
    # javascript / scroll
    # ---------------------------------------------------------------- #
    def executar_script(self, script: str, *args: Any) -> Any:
        """Executa `script` (JavaScript) na página atual e devolve o
        resultado (equivalente a `driver.execute_script`).

        Args:
            script: código JavaScript. Use `return` nele para obter um valor
                de volta; `arguments[0]`, `arguments[1]`, ... referenciam `*args`.
            *args: valores passados ao script (strings, números, `Elemento.bruto`, ...).

        Returns:
            O que o script retornar (convertido pro Selenium/Python correspondente).
        """
        return self.driver_bruto.execute_script(script, *args)

    def rolar_para_elemento(self, elemento: Elemento) -> None:
        """Rola a página até `elemento` ficar visível na tela (`scrollIntoView`).

        Args:
            elemento: um `Elemento` já encontrado.
        """
        elemento.rolar_ate()

    def rolar_para_baixo(self) -> None:
        """Rola a página até o fim (equivalente a End/Ctrl+End)."""
        self.driver_bruto.execute_script("window.scrollTo(0, document.body.scrollHeight);")

    # ---------------------------------------------------------------- #
    # janelas / abas / frames
    # ---------------------------------------------------------------- #
    def mudar_para_frame(self, referencia_frame: Elemento | int | str) -> None:
        """Muda o foco do navegador para dentro de um `<iframe>`/`<frame>` —
        necessário antes de `encontrar`/`clicar`/etc. em elementos que estão
        dentro dele.

        Args:
            referencia_frame: um `Elemento` já encontrado (tipicamente via
                `bot.encontrar(tag="iframe")`), ou o índice/nome/id do frame.
        """
        alvo = referencia_frame.bruto if isinstance(referencia_frame, Elemento) else referencia_frame
        self.driver_bruto.switch_to.frame(alvo)

    def mudar_para_conteudo_padrao(self) -> None:
        """Sai de qualquer frame e volta o foco para o documento principal."""
        self.driver_bruto.switch_to.default_content()

    def mudar_para_janela(self, indice: int = -1) -> None:
        """Muda o foco para outra janela/aba, pelo índice em que foi aberta.

        Args:
            indice: índice na lista de janelas abertas. Padrão `-1` (a mais
                recente).
        """
        janelas = self.driver_bruto.window_handles
        self.driver_bruto.switch_to.window(janelas[indice])

    def nova_aba(self, url: str | None = None) -> None:
        """Abre uma aba nova e já muda o foco para ela.

        Args:
            url: se dada, navega direto para ela na aba nova.
        """
        self.driver_bruto.switch_to.new_window("tab")
        if url:
            self.navegar(url)

    def fechar_aba_atual(self) -> None:
        """Fecha a aba atual e muda o foco para a última aba ainda aberta
        (se houver alguma). Para fechar uma aba temporária e voltar
        especificamente para a aba original, prefira `aba()`."""
        self.driver_bruto.close()
        if self.driver_bruto.window_handles:
            self.mudar_para_janela(-1)

    @contextmanager
    def aba(self, url: str | None = None) -> Generator[Navegador, None, None]:
        """Abre uma aba nova, roda o bloco `with` nela, e fecha a aba sozinha
        ao sair — voltando pra aba original, mesmo se o bloco levantar exceção.

            with bot.aba("https://outro-site.com") as nova:
                nova.clicar(css=".algo")
            # de volta na aba original aqui
        """
        janela_original = self.driver_bruto.current_window_handle
        self.nova_aba(url)
        try:
            yield self
        finally:
            with suppress(WebDriverException):
                self.driver_bruto.close()
            if janela_original in self.driver_bruto.window_handles:
                self.driver_bruto.switch_to.window(janela_original)

    # ---------------------------------------------------------------- #
    # alertas
    # ---------------------------------------------------------------- #
    def aceitar_alerta(self, timeout: float | None = None) -> None:
        """Espera um alerta JS (`alert`/`confirm`/`prompt`) aparecer e clica em OK/aceitar.

        Args:
            timeout: segundos a esperar; usa `tempo_espera_padrao` se omitido.
        """
        self.esperar_ate(CE.alert_is_present(), timeout).accept()

    def recusar_alerta(self, timeout: float | None = None) -> None:
        """Espera um alerta JS aparecer e clica em cancelar/dispensar.

        Args:
            timeout: segundos a esperar; usa `tempo_espera_padrao` se omitido.
        """
        self.esperar_ate(CE.alert_is_present(), timeout).dismiss()

    def obter_texto_alerta(self, timeout: float | None = None) -> str:
        """Espera um alerta JS aparecer e devolve o texto dele, sem fechá-lo.

        Args:
            timeout: segundos a esperar; usa `tempo_espera_padrao` se omitido.

        Returns:
            O texto exibido no alerta.
        """
        return self.esperar_ate(CE.alert_is_present(), timeout).text

    # ---------------------------------------------------------------- #
    # utilidades
    # ---------------------------------------------------------------- #
    def aguardar(self, segundos: float | tuple[float, float]) -> None:
        """Pausa a execução.

        Aceita um tempo fixo (`bot.aguardar(1.5)`) ou um intervalo para uma
        pausa aleatória (`bot.aguardar((0.5, 1.5))`), útil para simular um
        ritmo mais humano entre ações num fluxo de RPA.
        """
        tempo = random.uniform(*segundos) if isinstance(segundos, tuple) else segundos
        logger.debug("Aguardando %.2fs", tempo)
        time.sleep(tempo)

    def capturar_tela(self, caminho: str) -> None:
        """Salva um screenshot (PNG) da página atual.

        Args:
            caminho: caminho do arquivo a salvar (ex.: `"tela.png"`).
        """
        self.driver_bruto.save_screenshot(caminho)

    def baixar_arquivo(self, disparar: Callable[[], None], *, timeout: float = 30.0) -> Path:
        """Dispara um download e aguarda o arquivo terminar de baixar em
        `pasta_download` (precisa estar configurado), devolvendo o caminho.

        `disparar` é uma função sem argumentos que inicia o download
        (tipicamente um `lambda: bot.clicar(css="a.download")`) — chamada só
        depois de tirar uma "foto" da pasta, para conseguir identificar qual
        arquivo é novo. Ignora arquivos temporários do navegador
        (`.crdownload`/`.part`/`.tmp`) até o download terminar de verdade.
        """
        if not self.config.pasta_download:
            raise ValueError(
                "baixar_arquivo() precisa de ConfiguracaoNavegador.pasta_download definido."
            )
        pasta = Path(self.config.pasta_download)
        pasta.mkdir(parents=True, exist_ok=True)
        existentes = {item.name for item in pasta.iterdir() if item.is_file()}

        disparar()

        fim = time.monotonic() + timeout
        while time.monotonic() < fim:
            prontos = arquivos_prontos(pasta, existentes)
            if prontos:
                return prontos[0]
            time.sleep(0.2)

        erro = ErroElementoNaoEncontrado(
            f"Nenhum arquivo novo terminou de baixar em {pasta} dentro de {timeout}s"
        )
        self._registrar_evidencia(acao="baixar_arquivo", erro=erro)
        raise erro

    # ---------------------------------------------------------------- #
    # observabilidade: etapas, métricas e evidências
    # ---------------------------------------------------------------- #
    def etapa(self, nome: str, *, tentativas: int = 1) -> Etapa:
        """Agrupa um bloco de ações sob um nome, pra rastrear
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
        """
        return Etapa(self, nome, tentativas=tentativas)

    def debug(self, ativar: bool = True) -> None:
        """Liga (ou desliga) log estruturado no console de cada ação
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
        """
        global _handler_debug
        if ativar:
            if _handler_debug is None:
                _handler_debug = logging.StreamHandler()
                _handler_debug.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
                _LOGGER_PACOTE.addHandler(_handler_debug)
            _LOGGER_PACOTE.setLevel(logging.DEBUG)
        elif _handler_debug is not None:
            _LOGGER_PACOTE.removeHandler(_handler_debug)
            _handler_debug = None
            _LOGGER_PACOTE.setLevel(logging.NOTSET)
