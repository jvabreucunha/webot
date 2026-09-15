"""Testa que `ConfiguracaoNavegador` e `Navegador.__init__` não saem de sincronia.

`Navegador.__init__` replica manualmente cada campo de `ConfiguracaoNavegador`
como parâmetro nomeado (para dar autocomplete/tipagem real em vez de
`**kwargs: Any`). Nada impede alguém de adicionar um campo num lado só — este
teste existe para pegar esse esquecimento.
"""

import inspect

from webot import ConfiguracaoNavegador, Navegador


def test_campos_da_configuracao_tem_parametro_correspondente_no_init() -> None:
    campos = set(ConfiguracaoNavegador.model_fields)
    parametros = set(inspect.signature(Navegador.__init__).parameters) - {"self", "config"}

    faltando_no_init = campos - parametros
    sobrando_no_init = parametros - campos

    assert not faltando_no_init, (
        "Campo(s) de ConfiguracaoNavegador sem parâmetro correspondente em "
        f"Navegador.__init__: {sorted(faltando_no_init)}"
    )
    assert not sobrando_no_init, (
        "Parâmetro(s) solto(s) em Navegador.__init__ sem campo correspondente em "
        f"ConfiguracaoNavegador: {sorted(sobrando_no_init)}"
    )
