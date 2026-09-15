"""Utilidades internas compartilhadas entre `Navegador` e `Elemento`.

Não faz parte da API pública do pacote (nada daqui é exportado em `__init__.py`).
"""

from __future__ import annotations

import logging
import time
from functools import wraps
from pathlib import Path

from selenium.common.exceptions import (
    ElementClickInterceptedException,
    ElementNotInteractableException,
    NoSuchElementException,
    StaleElementReferenceException,
)
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement

from .excecoes import ErroSeletorInvalido

# Erros do Selenium considerados transitórios: reexecutar a ação de novo
# costuma resolver sozinho (o elemento "assentou" após um re-render, ficou
# interagível, etc.). Ver `repetir_se_transitorio`.
EXCECOES_TRANSITORIAS: tuple[type[Exception], ...] = (
    StaleElementReferenceException,
    ElementNotInteractableException,
)

logger = logging.getLogger(__name__)

# Mapa de seletores em pt-br -> estratégia de localização do Selenium.
# É o que permite o usuário chamar bot.clicar(css="...") sem nunca importar `By`.
# "texto" é especial: não é uma estratégia direta do Selenium, e sim traduzido
# pra um XPath (ver `_xpath_localizar_por_texto`).
MAPA_SELETORES = {
    "id": "id",
    "css": "css selector",
    "xpath": "xpath",
    "nome": "name",
    "classe": "class name",
    "tag": "tag name",
    "texto": "xpath",
    "texto_link": "link text",
    "texto_link_parcial": "partial link text",
}


def _xpath_literal(texto: str) -> str:
    """Um literal XPath 1.0 seguro mesmo se `texto` tiver aspas simples e/ou duplas."""
    if '"' not in texto:
        return f'"{texto}"'
    if "'" not in texto:
        return f"'{texto}'"
    partes = texto.split('"')
    return "concat(" + ', \'"\', '.join(f'"{parte}"' for parte in partes) + ")"


def _xpath_localizar_por_texto(texto: str) -> str:
    """XPath que casa com qualquer elemento cujo texto direto (sem contar
    filhos) seja exatamente `texto`, ignorando espaços nas pontas. Não
    encontra elementos que só têm texto via um filho (ex.: `<button><span>
    Entrar</span></button>` — nesse caso o `<span>` casa, o `<button>` não)."""
    return f"//*[normalize-space(text())={_xpath_literal(texto)}]"


def resolver_seletor(**seletores: str | None) -> tuple[str, str]:
    invalidos = [chave for chave in seletores if chave not in MAPA_SELETORES]
    if invalidos:
        raise ErroSeletorInvalido(
            f"Seletor(es) desconhecido(s): {invalidos}. Use um de: {list(MAPA_SELETORES)}"
        )

    fornecidos = {chave: valor for chave, valor in seletores.items() if valor is not None}
    if len(fornecidos) != 1:
        raise ErroSeletorInvalido(
            f"Informe exatamente um seletor entre {list(MAPA_SELETORES)}. "
            f"Recebido: {list(fornecidos) or 'nenhum'}"
        )

    chave, valor = next(iter(fornecidos.items()))
    if chave == "texto":
        return MAPA_SELETORES[chave], _xpath_localizar_por_texto(valor)
    return MAPA_SELETORES[chave], valor


def repetir_se_transitorio(func):
    """Reexecuta o método decorado se ele falhar com um erro transitório do
    Selenium (`EXCECOES_TRANSITORIAS`): elemento 'stale' (DOM re-renderizou),
    ainda não interagível, etc.

    Número de tentativas e intervalo entre elas vêm de `ConfiguracaoNavegador`
    (`tentativas_retry_transitorio`/`espera_entre_tentativas`) — por isso só
    decora métodos de instância de `Navegador`/`Elemento`, que expõem `.config`.
    """

    @wraps(func)
    def envoltorio(self, *args, **kwargs):
        config = self.config
        tentativas = config.tentativas_retry_transitorio
        ultimo_erro: Exception | None = None
        for tentativa in range(tentativas + 1):
            try:
                return func(self, *args, **kwargs)
            except EXCECOES_TRANSITORIAS as erro:
                ultimo_erro = erro
                if tentativa == tentativas:
                    # última tentativa permitida esgotada: desiste sem contar
                    # como retry (não haverá uma próxima) nem esperar à toa.
                    break
                self.metricas.retries += 1
                logger.warning(
                    "Retry da operação %s (%s), tentativa %s/%s",
                    func.__name__,
                    type(erro).__name__,
                    tentativa + 1,
                    tentativas,
                )
                time.sleep(config.espera_entre_tentativas)
        assert ultimo_erro is not None
        raise ultimo_erro

    return envoltorio


def clicar_com_fallback(driver_bruto: WebDriver, alvo: WebElement) -> None:
    """Clica no elemento; se o clique for interceptado por outro elemento
    (overlay, sticky header, etc.), tenta de novo via JavaScript."""
    try:
        alvo.click()
    except ElementClickInterceptedException:
        logger.debug("Clique interceptado, tentando via JavaScript")
        driver_bruto.execute_script("arguments[0].click();", alvo)


def presente_dentro(pai: WebElement, by: str, valor: str):
    """Condição (para WebDriverWait) de um elemento existir dentro de `pai`."""

    def _condicao(_driver):
        try:
            return pai.find_element(by, valor)
        except NoSuchElementException:
            return False

    return _condicao


def todos_presentes_dentro(pai: WebElement, by: str, valor: str):
    """Condição (para WebDriverWait) de ao menos um elemento existir dentro de `pai`."""

    def _condicao(_driver):
        return pai.find_elements(by, valor) or False

    return _condicao


SUFIXOS_DOWNLOAD_EM_ANDAMENTO = (".crdownload", ".part", ".tmp")


def arquivos_prontos(pasta: Path, ignorar_nomes: set[str]) -> list[Path]:
    """Arquivos em `pasta` que não estavam em `ignorar_nomes` e não parecem
    downloads ainda em andamento (extensões temporárias do navegador),
    do mais recente para o mais antigo."""
    candidatos = [
        item
        for item in pasta.iterdir()
        if item.is_file()
        and item.name not in ignorar_nomes
        and not item.name.endswith(SUFIXOS_DOWNLOAD_EM_ANDAMENTO)
    ]
    return sorted(candidatos, key=lambda item: item.stat().st_mtime, reverse=True)


JS_TODOS_ATRIBUTOS = """
var el = arguments[0];
var atributos = {};
for (var i = 0; i < el.attributes.length; i++) {
    atributos[el.attributes[i].name] = el.attributes[i].value;
}
return atributos;
"""

# Observa mutações no DOM inteiro; usado como heurística de "rede ociosa"
# (esperar_rede_ociosa): não é uma detecção real de requisições de rede (isso
# exigiria CDP, específico do Chromium) — em vez disso, considera a página
# estável quando o DOM para de mudar por um tempo seguido.
JS_INJETAR_OBSERVADOR_MUTACOES = """
if (!window.__webot_observador__) {
    window.__webot_mutacoes__ = 0;
    window.__webot_observador__ = new MutationObserver(function () {
        window.__webot_mutacoes__++;
    });
    window.__webot_observador__.observe(document, {
        childList: true, subtree: true, attributes: true, characterData: true
    });
}
"""
