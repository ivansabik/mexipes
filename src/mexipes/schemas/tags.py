from pydantic import BaseModel, Field

# Current tag taxonomy schema version. Bump when the controlled vocabulary or
# field set changes so previously tagged recipes can be re-tagged.
TAG_SCHEMA_VERSION = 3


class TagTranslation(BaseModel):
    """Single Spanish -> English tag term mapping."""

    es: str = Field(..., description="Original Spanish tag value")
    en: str = Field(..., description="English translation")


class TagTranslations(BaseModel):
    """LLM response for localizing free-form tag values not in the controlled vocabulary."""

    translations: list[TagTranslation] = Field(
        default_factory=list,
        description="One entry per Spanish term to translate",
    )


class RecipeTagSet(BaseModel):
    """Output of the tagging stage.

    Values are authored in **Spanish canonical** form (tagging runs on the
    rewritten Spanish text). The localize stage produces an English copy of this
    same shape via a deterministic lookup; see ``tag_vocabularies.py``.
    """

    tag_schema_version: int = Field(
        default=TAG_SCHEMA_VERSION,
        description="Version of the tag taxonomy used to produce this tag set",
    )

    course: list[str] = Field(
        default_factory=list,
        description="Tipo de plato: Entrada, Plato Principal, Guarnición, Sopa, Postre, Bebida, Ensalada, Pan",
    )
    meal_type: str | None = Field(
        None,
        description="Momento de la comida (exactamente uno): Desayuno, Brunch, Comida, Cena, Botana",
    )
    region: str | None = Field(
        None,
        description="Región mexicana de origen (p. ej. Oaxaca, Puebla, Yucatán, Jalisco, Sonora, Veracruz)",
    )
    primary_protein: str = Field(
        ...,
        description="Proteína principal (exactamente una). Usa 'Ninguno' para platos sin proteína animal.",
    )
    spiciness: str = Field(
        ...,
        description="Nivel de picor (uno de: Suave, Medio, Picante, Muy Picante)",
    )
    dietary: list[str] = Field(
        default_factory=list,
        description="Propiedades dietéticas (Vegetariano, Vegano, Sin Gluten, Sin Lácteos, Bajo en Carbohidratos, Alto en Proteína)",
    )
    cooking_method: list[str] = Field(
        default_factory=list,
        max_length=2,
        description="Métodos de cocción (máximo 2)",
    )
    chile_type: list[str] = Field(
        default_factory=list,
        max_length=3,
        description="Chiles utilizados (máximo 3; vocabulario canónico o variantes regionales)",
    )
    difficulty: str = Field(
        ...,
        description="Dificultad (uno de: Fácil, Intermedio, Avanzado)",
    )
    key_ingredient: list[str] = Field(
        default_factory=list,
        max_length=3,
        description="Ingredientes clave definitorios del vocabulario controlado (máximo 3)",
    )
    budget: str = Field(
        ...,
        description="Categoría de costo (uno de: Económico, Moderado, Premium)",
    )
    dish_format: list[str] = Field(
        default_factory=list,
        max_length=2,
        description="Formato del platillo (Tacos, Mole, Pozole, Sopa, etc.); máximo 2",
    )
    allergens: list[str] = Field(
        default_factory=list,
        description="Alérgenos presentes (Frutos Secos, Cacahuates, Mariscos, Pescado, Huevo, Lácteos, Trigo/Gluten, Soya, Ajonjolí, Ninguno)",
    )
