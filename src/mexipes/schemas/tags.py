from pydantic import BaseModel, Field

# Current tag taxonomy schema version. Bump when the controlled vocabulary or
# field set changes so previously tagged recipes can be re-tagged.
TAG_SCHEMA_VERSION = 2


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

    # -- Existing taxonomy ---------------------------------------------------
    course: list[str] = Field(
        default_factory=list,
        description="Tipo de plato: Entrada, Plato Principal, Guarnición, Sopa, Postre, Bebida, Ensalada, Pan",
    )
    meal_type: list[str] = Field(
        default_factory=list,
        description="Momento de la comida: Desayuno, Brunch, Comida, Cena, Botana, Trasnoche",
    )
    region: str | None = Field(
        None,
        description="Región mexicana de origen (p. ej. Oaxaca, Puebla, Yucatán, Jalisco, Sonora, Veracruz)",
    )
    protein: list[str] = Field(
        default_factory=list,
        description="Fuentes de proteína (Pollo, Res, Cerdo, Camarón, Pescado, Pavo, Huevos, Frijoles, Queso, Ninguno)",
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
        description="Métodos de cocción (Asado a la Parrilla, Frito, Rostizado, Horneado, Guisado, Crudo, Cocción Lenta, Al Vapor, Hervido)",
    )
    chile_type: list[str] = Field(
        default_factory=list,
        description="Chiles utilizados (Guajillo, Ancho, Chipotle, Serrano, Jalapeño, Habanero, Pasilla, Poblano, Árbol)",
    )
    cuisine_style: list[str] = Field(
        default_factory=list,
        description="Estilo de cocina: Comida Callejera, Casera, Tradicional Regional, Festivo, Fusión Moderna",
    )
    difficulty: str = Field(
        ...,
        description="Dificultad (uno de: Fácil, Intermedio, Avanzado)",
    )
    season: list[str] = Field(
        default_factory=list,
        description="Temporada o evento (Todo el Año, Verano, Invierno, Primavera, Otoño, Festividad, Cuaresma)",
    )
    key_ingredient: list[str] = Field(
        default_factory=list,
        description="Ingredientes clave definitorios (Maíz, Aguacate, Chocolate, Mole, Nopales, Chayote, Masa, Tomatillo, Cilantro)",
    )
    budget: str = Field(
        ...,
        description="Categoría de costo (uno de: Económico, Moderado, Premium)",
    )
    cooking_equipment: list[str] = Field(
        default_factory=list,
        description="Equipo esencial (Molcajete, Comal, Licuadora, Olla de Hierro, Cazuela, Prensa para Tortillas)",
    )
    health_nutrition: list[str] = Field(
        default_factory=list,
        description=(
            "Atributos de salud y nutrición (vocabulario canónico en español de 13 categorías): "
            "Macronutrientes, Azúcar, Sodio, Colesterol y Calidad de Grasa, Vitaminas y Minerales, "
            "Nutrición Funcional, Objetivos de Peso, Nutrición Deportiva, Dietas Médicas Especiales, "
            "Calidad de Ingredientes, Calidad Vegetal, Densidad Nutricional, Función de la Comida"
        ),
    )

    # -- New recommendation fields ------------------------------------------
    dish_format: list[str] = Field(
        default_factory=list,
        description="Formato del platillo (Tacos, Mole, Pozole, Sopa, Caldo, etc.); máximo 2",
    )
    preparation_style: list[str] = Field(
        default_factory=list,
        description="Estilo de preparación para el caso largo (En Salsa, Relleno, En Mole, A la Mexicana); máximo 2",
    )
    flavor_profile: list[str] = Field(
        default_factory=list,
        description="Perfil de sabor (Ahumado, Terroso, Rico, Brillante, Ácido, Picante, Dulce); 2-5",
    )
    texture: list[str] = Field(
        default_factory=list,
        description="Textura (Crujiente, Cremoso, Caldoso, Masticable, Tierno); 1-3",
    )
    occasion: list[str] = Field(
        default_factory=list,
        description="Ocasión (Entre Semana, Proyecto de Fin de Semana, Festividad, Fiesta); 0-3",
    )
    pairs_well_with: list[str] = Field(
        default_factory=list,
        description="Acompañamientos sugeridos (Guarnición, Sopa, Arroz, Frijoles, Tortillas, Salsa); 0-4",
    )

    # -- New filter fields ---------------------------------------------------
    serving_size: str | None = Field(
        None,
        description="Tamaño de porción (1-2, 3-4, 5-8, 9+)",
    )
    allergens: list[str] = Field(
        default_factory=list,
        description="Alérgenos presentes (Frutos Secos, Cacahuates, Mariscos, Pescado, Huevo, Lácteos, Trigo/Gluten, Soya, Ajonjolí, Ninguno)",
    )
    contains_alcohol: bool = Field(
        default=False,
        description="True si la receta contiene alcohol",
    )
    make_ahead: list[str] = Field(
        default_factory=list,
        description="Preparación anticipada (Mismo Día, Un Día Antes, Apto para Congelar, Bueno como Sobras)",
    )
    kid_friendly: str | None = Field(
        None,
        description="Apto para niños (Suave, Moderado, No apto para niños)",
    )
