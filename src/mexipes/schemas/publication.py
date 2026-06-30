from pydantic import BaseModel, Field


class RegionalSection(BaseModel):
    region_name: str
    page_start: int
    page_end: int | None = None


class RecipeIndexEntry(BaseModel):
    """A recipe entry from the publication table of contents / índice."""

    title: str = Field(..., description="Canonical recipe title, e.g. 'Esquites - Granos de maíz cocidos'")
    page: int | None = Field(None, description="1-based PDF page number from the index")
    section: str | None = Field(None, description="Chapter or section heading, if visible")


class InheritedTags(BaseModel):
    """Publication-level theme tags merged into each recipe at the tag stage.

    Only book-wide themes from title/first pages — not per-recipe taxonomy.
    Values are Spanish canonical.
    """

    region: str | None = Field(
        None,
        description="Región mexicana si todo el libro es regional (p. ej. 'Yucatán', 'Oaxaca')",
    )
    dietary: list[str] = Field(
        default_factory=list,
        description="Etiquetas dietéticas globales (p. ej. ['Vegano', 'Vegetariano', 'Sin Lácteos'])",
    )
    budget: str | None = Field(
        None,
        description="Categoría de costo global (p. ej. 'Económico')",
    )


class PublicationMetadata(BaseModel):
    document_title: str | None = Field(
        None, description="The full title of the publication, if explicitly stated on the cover or first pages."
    )
    pdf_pages: str = Field(..., description="Total pages or page range of the PDF")
    recipes_count: str = Field(..., description="Estimated number of recipes in the publication")
    regional_sections: list[RegionalSection] = Field(default_factory=list)
    recipe_index: list[RecipeIndexEntry] = Field(
        default_factory=list,
        description="Recipe entries parsed from table of contents when available",
    )
    inherited_tags: InheritedTags = Field(default_factory=InheritedTags)
