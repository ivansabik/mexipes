from pydantic import BaseModel, Field


class RegionalSection(BaseModel):
    region_name: str
    page_start: int
    page_end: int | None = None


class InheritedTags(BaseModel):
    """Publication-level tag defaults merged into each recipe at the tag stage.

    Values are Spanish canonical.
    """

    course: list[str] = Field(
        default_factory=list,
        description="Tipos de plato globales (p. ej. ['Postre'])",
    )
    meal_type: list[str] = Field(
        default_factory=list,
        description="Momentos de comida globales (p. ej. ['Desayuno'])",
    )
    region: str | None = Field(
        None,
        description="Región mexicana si todo el libro es regional (p. ej. 'Yucatán', 'Oaxaca')",
    )
    protein: list[str] = Field(
        default_factory=list,
        description="Proteínas globales (p. ej. ['Pollo'], ['Ninguno'] para vegano)",
    )
    spiciness: str | None = Field(
        None,
        description="Nivel de picor global (p. ej. 'Suave')",
    )
    dietary: list[str] = Field(
        default_factory=list,
        description="Etiquetas dietéticas globales (p. ej. ['Vegano', 'Vegetariano', 'Sin Lácteos'])",
    )
    cooking_method: list[str] = Field(
        default_factory=list,
        description="Métodos de cocción globales (p. ej. ['Asado a la Parrilla'])",
    )
    chile_type: list[str] = Field(
        default_factory=list,
        description="Chiles usados globalmente en el libro",
    )
    cuisine_style: list[str] = Field(
        default_factory=list,
        description="Estilo de cocina global (p. ej. ['Comida Callejera', 'Tradicional Regional'])",
    )
    difficulty: str | None = Field(
        None,
        description="Dificultad global (p. ej. 'Fácil')",
    )
    total_time: str | None = Field(
        None,
        description="Tiempo total global (p. ej. 'Menos de 30 min')",
    )
    season: list[str] = Field(
        default_factory=list,
        description="Temporadas o eventos globales (p. ej. ['Festividad'])",
    )
    key_ingredient: list[str] = Field(
        default_factory=list,
        description="Ingredientes clave definitorios compartidos globalmente",
    )
    budget: str | None = Field(
        None,
        description="Categoría de costo global (p. ej. 'Económico')",
    )
    cooking_equipment: list[str] = Field(
        default_factory=list,
        description="Equipo esencial global (p. ej. ['Comal', 'Licuadora'])",
    )
    health_nutrition: list[str] = Field(
        default_factory=list,
        description=(
            "Atributos de salud/nutrición globales (vocabulario canónico en español): "
            "p. ej. Bajo en Sodio, Alto en Proteína, Alimentos Integrales"
        ),
    )


class PublicationMetadata(BaseModel):
    document_title: str | None = Field(
        None, description="The full title of the publication, if explicitly stated on the cover or first pages."
    )
    pdf_pages: str = Field(..., description="Total pages or page range of the PDF")
    recipes_count: str = Field(..., description="Estimated number of recipes in the publication")
    regional_sections: list[RegionalSection] = Field(default_factory=list)
    inherited_tags: InheritedTags = Field(default_factory=InheritedTags)
