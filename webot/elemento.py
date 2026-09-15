from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as CE
from selenium.webdriver.support.ui import Select

from ._utilitarios import (
    JS_TODOS_ATRIBUTOS,
    clicar_com_fallback,
    presente_dentro,
    repetir_se_transitorio,
    resolver_seletor,
    todos_presentes_dentro,
)
from .excecoes import ErroElementoNaoEncontrado
from .formulario import Campo, normalizar_campos, preencher_campo
from .resultados import InfoElemento

if TYPE_CHECKING:
    from .configuracao import ConfiguracaoNavegador
    from .metricas import Metricas
    from .navegador import Navegador

logger = logging.getLogger(__name__)


class Elemento:
    """Envelope em pt-br sobre um elemento já encontrado na página.

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
    """

    def __init__(self, bruto: WebElement, bot: Navegador):
        """Não construído diretamente pelo código do usuário — vem de
        `Navegador.encontrar()`/`encontrar_todos()` ou de `Elemento.encontrar()`/
        `encontrar_todos()` (busca aninhada).

        Args:
            bruto: o `WebElement` do Selenium já localizado.
            bot: o `Navegador` que localizou este elemento (usado internamente
                para esperas/config compartilhadas).
        """
        self.bruto = bruto
        self._bot = bot

    def __repr__(self) -> str:
        return f"Elemento(tag={self.tag!r})"

    @property
    def config(self) -> ConfiguracaoNavegador:
        """A mesma `ConfiguracaoNavegador` do `Navegador` que encontrou este elemento."""
        return self._bot.config

    @property
    def metricas(self) -> Metricas:
        """As mesmas `Metricas` do `Navegador` que encontrou este elemento
        (usado internamente pelo retry — ver `_utilitarios.repetir_se_transitorio`)."""
        return self._bot.metricas

    # ---------------------------------------------------------------- #
    # estado
    # ---------------------------------------------------------------- #
    @property
    def texto(self) -> str:
        """Texto visível do elemento (equivalente ao `.text` do Selenium).
        Leitura direta, sem esperar visibilidade — use `obter_texto()` se
        precisar esperar."""
        return self.bruto.text

    @property
    def tag(self) -> str:
        """Nome da tag HTML do elemento (ex.: `"a"`, `"button"`, `"input"`), em minúsculas."""
        return self.bruto.tag_name

    @property
    def visivel(self) -> bool:
        """`True` se o elemento está visível na página neste instante
        (presente no DOM e com largura/altura maiores que zero)."""
        return self.bruto.is_displayed()

    @property
    def habilitado(self) -> bool:
        """`True` se o elemento está habilitado (não tem o atributo `disabled`)."""
        return self.bruto.is_enabled()

    @property
    def selecionado(self) -> bool:
        """`True` se um checkbox/radio (ou `<option>` dentro de um `<select>`) está selecionado."""
        return self.bruto.is_selected()

    @repetir_se_transitorio
    def obter_atributo(self, atributo: str) -> str | None:
        """Devolve o valor de um atributo HTML do elemento (ex.: `"href"`,
        `"value"`, `"class"`).

        Args:
            atributo: nome do atributo HTML.

        Returns:
            O valor do atributo, ou `None` se o elemento não tiver esse atributo.
        """
        return self.bruto.get_attribute(atributo)

    @repetir_se_transitorio
    def obter_info(self) -> InfoElemento:
        """Retorna um retrato tipado (pydantic) deste elemento: `texto`,
        `tag`, `visivel`, `habilitado` e `atributos` (dict com todos os
        atributos HTML). Diferente do `Elemento` em si, é serializável
        (`.model_dump()`/`.model_dump_json()`) — útil para logs de auditoria.

        Returns:
            Um `InfoElemento`.
        """
        atributos = self._bot.driver_bruto.execute_script(JS_TODOS_ATRIBUTOS, self.bruto) or {}
        return InfoElemento(
            texto=self.bruto.text,
            tag=self.bruto.tag_name,
            visivel=self.bruto.is_displayed(),
            habilitado=self.bruto.is_enabled(),
            atributos=atributos,
        )

    # ---------------------------------------------------------------- #
    # interação
    # ---------------------------------------------------------------- #
    @repetir_se_transitorio
    def clicar(self, *, timeout: float | None = None) -> None:
        """Espera este elemento ficar clicável (visível e habilitado) e
        clica nele; se o clique for interceptado por outro elemento (overlay,
        header fixo, etc.), tenta de novo via JavaScript.

        Args:
            timeout: segundos a esperar; usa `tempo_espera_padrao` (config
                do `Navegador` original) se omitido.

        Raises:
            ErroElementoNaoEncontrado: o elemento não ficou clicável a tempo.
        """
        alvo = self._bot.esperar_ate(
            CE.element_to_be_clickable(self.bruto), timeout, descricao=f"elemento <{self.tag}> clicável"
        )
        clicar_com_fallback(self._bot.driver_bruto, alvo)
        self.metricas.acoes += 1
        logger.info("Clique realizado (elemento <%s>)", self.tag)

    @repetir_se_transitorio
    def digitar(self, texto: str, *, limpar: bool = True, timeout: float | None = None) -> None:
        """Espera este elemento ficar visível e digita `texto` nele.

        Args:
            texto: o que digitar.
            limpar: se `True` (padrão), limpa o campo antes de digitar.
            timeout: segundos a esperar; usa `tempo_espera_padrao` se omitido.

        Raises:
            ErroElementoNaoEncontrado: o elemento não ficou visível a tempo.
        """
        alvo = self._bot.esperar_ate(
            CE.visibility_of(self.bruto), timeout, descricao=f"elemento <{self.tag}> visível"
        )
        if limpar:
            alvo.clear()
        alvo.send_keys(texto)
        self.metricas.acoes += 1
        logger.info("Texto digitado (elemento <%s>)", self.tag)

    @repetir_se_transitorio
    def obter_texto(self, *, timeout: float | None = None) -> str:
        """Espera este elemento ficar visível e devolve seu texto.

        Args:
            timeout: segundos a esperar; usa `tempo_espera_padrao` se omitido.

        Returns:
            O texto visível do elemento.
        """
        return self._bot.esperar_ate(
            CE.visibility_of(self.bruto), timeout, descricao=f"elemento <{self.tag}> visível"
        ).text

    @repetir_se_transitorio
    def selecionar_por_texto(self, texto: str) -> None:
        """Se este elemento for um `<select>`, seleciona a opção pelo texto visível.

        Args:
            texto: texto visível da `<option>` a selecionar.
        """
        Select(self.bruto).select_by_visible_text(texto)

    @repetir_se_transitorio
    def selecionar_por_valor(self, valor_opcao: str) -> None:
        """Se este elemento for um `<select>`, seleciona a opção pelo atributo `value`.

        Args:
            valor_opcao: valor (`value=`) da `<option>` a selecionar.
        """
        Select(self.bruto).select_by_value(valor_opcao)

    @repetir_se_transitorio
    def enviar_arquivo(self, caminho_arquivo: str) -> None:
        """Se este elemento for um `<input type="file">`, envia um arquivo
        escrevendo o caminho absoluto nele (não abre seletor de arquivo do SO).

        Args:
            caminho_arquivo: caminho absoluto do arquivo no disco local.
        """
        self.bruto.send_keys(str(caminho_arquivo))

    def preencher_formulario(
        self, campos: dict[str, str | bool] | list[Campo], *, timeout: float | None = None
    ) -> None:
        """Como `Navegador.preencher_formulario()`, mas busca os campos
        *dentro* deste elemento (busca aninhada) — útil pra preencher um
        formulário que está dentro de um modal/seção já encontrada.

        Args:
            campos: dict (chave = seletor CSS) ou lista de `Campo` — ver
                `Navegador.preencher_formulario()`.
            timeout: segundos a esperar por cada campo; usa
                `tempo_espera_padrao` se omitido.
        """
        for campo in normalizar_campos(campos):
            elemento = self.encontrar(timeout=timeout, **campo.seletor())
            preencher_campo(elemento, campo.valor)
            logger.debug("Campo %s preenchido (dentro de <%s>)", campo.seletor(), self.tag)
        logger.info("Formulário preenchido (%d campo(s), dentro de <%s>)", len(campos), self.tag)

    def rolar_ate(self) -> None:
        """Rola a página até este elemento ficar visível na tela (`scrollIntoView`)."""
        self._bot.driver_bruto.execute_script(
            "arguments[0].scrollIntoView({block: 'center'});", self.bruto
        )

    # ---------------------------------------------------------------- #
    # busca aninhada (dentro deste elemento)
    # ---------------------------------------------------------------- #
    def encontrar(self, *, timeout: float | None = None, **seletor: str | None) -> Elemento:
        """Espera um elemento existir *dentro* deste (busca aninhada) e o
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
        """
        by, valor = resolver_seletor(**seletor)
        bruto = self._bot.esperar_ate(presente_dentro(self.bruto, by, valor), timeout)
        self.metricas.acoes += 1
        logger.info("Elemento encontrado (%s=%r, dentro de <%s>)", by, valor, self.tag)
        return Elemento(bruto, self._bot)

    def encontrar_todos(self, *, timeout: float | None = None, **seletor: str | None) -> list[Elemento]:
        """Como `encontrar()`, mas espera existir pelo menos um elemento
        dentro deste e devolve todos os que casarem com o seletor.

        Args:
            timeout: segundos a esperar; usa `tempo_espera_padrao` se omitido.
            **seletor: mesmas chaves de `encontrar()`.

        Returns:
            Lista de `Elemento` filhos (nunca vazia — se nada casar, levanta
            `ErroElementoNaoEncontrado` em vez de `[]`).
        """
        by, valor = resolver_seletor(**seletor)
        brutos = self._bot.esperar_ate(todos_presentes_dentro(self.bruto, by, valor), timeout)
        self.metricas.acoes += 1
        logger.info("%d elemento(s) encontrado(s) (%s=%r, dentro de <%s>)", len(brutos), by, valor, self.tag)
        return [Elemento(bruto, self._bot) for bruto in brutos]

    def esta_presente(self, *, timeout: float = 1, **seletor: str | None) -> bool:
        """Verifica se um elemento existe dentro deste, sem lançar exceção.

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
