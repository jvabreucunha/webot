from __future__ import annotations

import logging
import random
import time
from contextlib import suppress
from functools import wraps
from pathlib import Path
from types import TracebackType
from typing import Any, Callable, TypeVar

from selenium import webdriver
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    StaleElementReferenceException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.chrome.options import Options as OpcoesChrome
from selenium.webdriver.edge.options import Options as OpcoesEdge
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as CE
from selenium.webdriver.support.ui import Select, WebDriverWait

from .configuracao import ConfiguracaoNavegador, TipoNavegador
from .excecoes import (
    ErroAoIniciarNavegador,
    ErroElementoNaoEncontrado,
    ErroNavegadorNaoIniciado,
    ErroSeletorInvalido,
)
from .resultados import InfoElemento

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Mapa de seletores em pt-br -> estratégia de localização do Selenium.
# É o que permite o usuário chamar bot.clicar(css="...") sem nunca importar `By`.
_MAPA_SELETORES = {
    "id": "id",
    "css": "css selector",
    "xpath": "xpath",
    "nome": "name",
    "classe": "class name",
    "tag": "tag name",
    "texto_link": "link text",
    "texto_link_parcial": "partial link text",
}


def _resolver_seletor(**seletores: str | None) -> tuple[str, str]:
    invalidos = [chave for chave in seletores if chave not in _MAPA_SELETORES]
    if invalidos:
        raise ErroSeletorInvalido(
            f"Seletor(es) desconhecido(s): {invalidos}. Use um de: {list(_MAPA_SELETORES)}"
        )

    fornecidos = {chave: valor for chave, valor in seletores.items() if valor is not None}
    if len(fornecidos) != 1:
        raise ErroSeletorInvalido(
            f"Informe exatamente um seletor entre {list(_MAPA_SELETORES)}. "
            f"Recebido: {list(fornecidos) or 'nenhum'}"
        )

    chave, valor = next(iter(fornecidos.items()))
    return _MAPA_SELETORES[chave], valor


_JS_TODOS_ATRIBUTOS = """
var el = arguments[0];
var atributos = {};
for (var i = 0; i < el.attributes.length; i++) {
    atributos[el.attributes[i].name] = el.attributes[i].value;
}
return atributos;
"""


def _repetir_se_desatualizado(tentativas: int = 2, espera: float = 0.3):
    """Reexecuta a chamada se o elemento ficar 'stale' (DOM re-renderizou)."""

    def decorador(func):
        @wraps(func)
        def envoltorio(*args, **kwargs):
            ultimo_erro: StaleElementReferenceException | None = None
            for tentativa in range(tentativas + 1):
                try:
                    return func(*args, **kwargs)
                except StaleElementReferenceException as erro:
                    ultimo_erro = erro
                    logger.debug(
                        "Elemento desatualizado (stale), tentativa %s/%s", tentativa + 1, tentativas
                    )
                    time.sleep(espera)
            raise ultimo_erro  # type: ignore[misc]

        return envoltorio

    return decorador


class Navegador:
    """Fachada em pt-br que encapsula o WebDriver do Selenium.

    Uso simples, sem precisar importar nada do Selenium:

        from automacao_web import Navegador

        with Navegador(tipo_navegador="chrome", sem_interface=False) as bot:
            bot.navegar("https://exemplo.com")
            bot.clicar(css="button.enviar")
            bot.digitar("relatorio", nome="busca")
            texto = bot.obter_texto(tag="h1")

    Localizar elementos é sempre por palavra-chave: id=, css=, xpath=, nome=,
    classe=, tag=, texto_link= ou texto_link_parcial= (exatamente um por chamada).
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
    ) -> None:
        """Cria o navegador a partir de opções soltas (uso simples) ou de um
        `ConfiguracaoNavegador` pronto (para reaproveitar a mesma config em
        vários bots). Não misture os dois.

        Args:
            config: uma `ConfiguracaoNavegador` já pronta. Use isso (em vez
                das opções soltas abaixo) quando quiser montar a config uma
                vez e reaproveitar em vários bots.
            tipo_navegador: 'chrome' ou 'edge' (ou `TipoNavegador.CHROME`/`EDGE`).
                Padrão: chrome.
            sem_interface: modo headless — True roda sem abrir janela nenhuma
                (útil em servidor/CI). Padrão: False.
            anonimo: True abre em modo anônimo/privado (--incognito no Chrome,
                --inprivate no Edge). Padrão: True.
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
        }
        fornecidas = {chave: valor for chave, valor in opcoes.items() if valor is not None}

        if config is not None and fornecidas:
            raise ValueError(
                "Passe uma ConfiguracaoNavegador pronta OU as opções soltas, não os dois."
            )
        self.config = config or ConfiguracaoNavegador(**fornecidas)
        self._driver: webdriver.Remote | None = None

    # ---------------------------------------------------------------- #
    # ciclo de vida
    # ---------------------------------------------------------------- #
    def iniciar(self) -> "Navegador":
        if self._driver is not None:
            logger.debug("Navegador já iniciado, ignorando nova chamada a iniciar()")
            return self

        opcoes = self._montar_opcoes()
        try:
            if self.config.tipo_navegador == TipoNavegador.CHROME:
                self._driver = webdriver.Chrome(options=opcoes)
            elif self.config.tipo_navegador == TipoNavegador.EDGE:
                self._driver = webdriver.Edge(options=opcoes)
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
        if self._driver is not None:
            with suppress(WebDriverException):
                self._driver.quit()
            self._driver = None
            logger.info("Navegador encerrado")

    def __enter__(self) -> "Navegador":
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
        """Acesso ao WebDriver puro do Selenium, para casos que a fachada não cobre."""
        if self._driver is None:
            raise ErroNavegadorNaoIniciado(
                "O navegador não foi iniciado. Chame iniciar() ou use como context manager (with)."
            )
        return self._driver

    def _montar_opcoes(self) -> OpcoesChrome | OpcoesEdge:
        if self.config.tipo_navegador == TipoNavegador.CHROME:
            opcoes: OpcoesChrome | OpcoesEdge = OpcoesChrome()
            if self.config.anonimo:
                opcoes.add_argument("--incognito")
        elif self.config.tipo_navegador == TipoNavegador.EDGE:
            opcoes = OpcoesEdge()
            if self.config.anonimo:
                opcoes.add_argument("--inprivate")
        else:
            raise ErroAoIniciarNavegador(f"Navegador não suportado: {self.config.tipo_navegador}")

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

        if self.config.caminho_binario:
            opcoes.binary_location = self.config.caminho_binario

        for argumento in self.config.argumentos_extras:
            opcoes.add_argument(argumento)

        return opcoes

    # ---------------------------------------------------------------- #
    # navegação
    # ---------------------------------------------------------------- #
    def navegar(self, url: str) -> None:
        logger.debug("Navegando para %s", url)
        self.driver_bruto.get(url)

    def atualizar(self) -> None:
        self.driver_bruto.refresh()

    def voltar(self) -> None:
        self.driver_bruto.back()

    def avancar(self) -> None:
        self.driver_bruto.forward()

    @property
    def url_atual(self) -> str:
        return self.driver_bruto.current_url

    @property
    def titulo(self) -> str:
        return self.driver_bruto.title

    # ---------------------------------------------------------------- #
    # esperas
    # ---------------------------------------------------------------- #
    def _wait(self, timeout: float | None = None) -> WebDriverWait:
        return WebDriverWait(self.driver_bruto, timeout or self.config.tempo_espera_padrao)

    def esperar_ate(self, condicao: Callable[[Any], T], timeout: float | None = None) -> T:
        """Escape hatch para condições customizadas (selenium.webdriver.support.expected_conditions)."""
        try:
            return self._wait(timeout).until(condicao)
        except TimeoutException as erro:
            raise ErroElementoNaoEncontrado(
                f"Condição não satisfeita dentro do tempo de espera "
                f"({timeout or self.config.tempo_espera_padrao}s)"
            ) from erro

    # ---------------------------------------------------------------- #
    # localizar elementos
    # ---------------------------------------------------------------- #
    def encontrar(self, *, timeout: float | None = None, **seletor: str | None) -> WebElement:
        by, valor = _resolver_seletor(**seletor)
        return self.esperar_ate(CE.presence_of_element_located((by, valor)), timeout)

    def encontrar_todos(self, *, timeout: float | None = None, **seletor: str | None) -> list[WebElement]:
        by, valor = _resolver_seletor(**seletor)
        return self.esperar_ate(CE.presence_of_all_elements_located((by, valor)), timeout)

    def esta_presente(self, *, timeout: float = 1, **seletor: str | None) -> bool:
        try:
            self.encontrar(timeout=timeout, **seletor)
            return True
        except ErroElementoNaoEncontrado:
            return False

    def _encontrar_visivel(self, timeout: float | None, **seletor: str | None) -> WebElement:
        by, valor = _resolver_seletor(**seletor)
        return self.esperar_ate(CE.visibility_of_element_located((by, valor)), timeout)

    def _encontrar_clicavel(self, timeout: float | None, **seletor: str | None) -> WebElement:
        by, valor = _resolver_seletor(**seletor)
        return self.esperar_ate(CE.element_to_be_clickable((by, valor)), timeout)

    # ---------------------------------------------------------------- #
    # interações
    # ---------------------------------------------------------------- #
    @_repetir_se_desatualizado()
    def clicar(self, *, timeout: float | None = None, **seletor: str | None) -> None:
        elemento = self._encontrar_clicavel(timeout, **seletor)
        try:
            elemento.click()
        except ElementClickInterceptedException:
            logger.debug("Clique interceptado, tentando via JavaScript")
            self.driver_bruto.execute_script("arguments[0].click();", elemento)

    @_repetir_se_desatualizado()
    def digitar(
        self,
        texto: str,
        *,
        limpar: bool = True,
        timeout: float | None = None,
        **seletor: str | None,
    ) -> None:
        elemento = self._encontrar_visivel(timeout, **seletor)
        if limpar:
            elemento.clear()
        elemento.send_keys(texto)

    @_repetir_se_desatualizado()
    def obter_texto(self, *, timeout: float | None = None, **seletor: str | None) -> str:
        return self._encontrar_visivel(timeout, **seletor).text

    @_repetir_se_desatualizado()
    def obter_atributo(
        self, atributo: str, *, timeout: float | None = None, **seletor: str | None
    ) -> str | None:
        return self.encontrar(timeout=timeout, **seletor).get_attribute(atributo)

    @_repetir_se_desatualizado()
    def obter_info(self, *, timeout: float | None = None, **seletor: str | None) -> InfoElemento:
        """Retorna um retrato tipado (pydantic) do elemento: texto, tag, visibilidade e atributos."""
        elemento = self.encontrar(timeout=timeout, **seletor)
        atributos = self.driver_bruto.execute_script(_JS_TODOS_ATRIBUTOS, elemento) or {}
        return InfoElemento(
            texto=elemento.text,
            tag=elemento.tag_name,
            visivel=elemento.is_displayed(),
            habilitado=elemento.is_enabled(),
            atributos=atributos,
        )

    def selecionar_por_texto(
        self, texto: str, *, timeout: float | None = None, **seletor: str | None
    ) -> None:
        Select(self._encontrar_visivel(timeout, **seletor)).select_by_visible_text(texto)

    def selecionar_por_valor(
        self, valor_opcao: str, *, timeout: float | None = None, **seletor: str | None
    ) -> None:
        Select(self._encontrar_visivel(timeout, **seletor)).select_by_value(valor_opcao)

    def enviar_arquivo(
        self, caminho_arquivo: str, *, timeout: float | None = None, **seletor: str | None
    ) -> None:
        self.encontrar(timeout=timeout, **seletor).send_keys(str(caminho_arquivo))

    # ---------------------------------------------------------------- #
    # javascript / scroll
    # ---------------------------------------------------------------- #
    def executar_script(self, script: str, *args: Any) -> Any:
        return self.driver_bruto.execute_script(script, *args)

    def rolar_para_elemento(self, elemento: WebElement) -> None:
        self.driver_bruto.execute_script("arguments[0].scrollIntoView({block: 'center'});", elemento)

    def rolar_para_baixo(self) -> None:
        self.driver_bruto.execute_script("window.scrollTo(0, document.body.scrollHeight);")

    # ---------------------------------------------------------------- #
    # janelas / abas / frames
    # ---------------------------------------------------------------- #
    def mudar_para_frame(self, referencia_frame: Any) -> None:
        self.driver_bruto.switch_to.frame(referencia_frame)

    def mudar_para_conteudo_padrao(self) -> None:
        self.driver_bruto.switch_to.default_content()

    def mudar_para_janela(self, indice: int = -1) -> None:
        janelas = self.driver_bruto.window_handles
        self.driver_bruto.switch_to.window(janelas[indice])

    def nova_aba(self, url: str | None = None) -> None:
        self.driver_bruto.switch_to.new_window("tab")
        if url:
            self.navegar(url)

    def fechar_aba_atual(self) -> None:
        self.driver_bruto.close()
        if self.driver_bruto.window_handles:
            self.mudar_para_janela(-1)

    # ---------------------------------------------------------------- #
    # alertas
    # ---------------------------------------------------------------- #
    def aceitar_alerta(self, timeout: float | None = None) -> None:
        self.esperar_ate(CE.alert_is_present(), timeout).accept()

    def recusar_alerta(self, timeout: float | None = None) -> None:
        self.esperar_ate(CE.alert_is_present(), timeout).dismiss()

    def obter_texto_alerta(self, timeout: float | None = None) -> str:
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
        self.driver_bruto.save_screenshot(caminho)
