from pydantic import BaseModel, Field


class InfoElemento(BaseModel):
    """Retrato tipado de um elemento no instante da consulta (não é 'ao vivo').

    Útil para logs e serialização (`.model_dump()` / `.model_dump_json()`),
    já que o WebElement bruto do Selenium não é serializável.
    """

    texto: str
    tag: str
    visivel: bool
    habilitado: bool
    atributos: dict[str, str] = Field(default_factory=dict)
