"""Bilingual canonical tag vocabularies for recipe tagging.

Tagging runs on the rewritten **Spanish** text, so every controlled vocabulary is
authored Spanish-first. Each term is a ``(slug, es, en)`` tuple:

* ``slug`` — stable, language-independent identifier used for facets/similarity.
* ``es``   — canonical Spanish label emitted by the tagging stage.
* ``en``   — canonical English label produced by the localize stage via a
  deterministic lookup (no extra LLM call).
"""

from __future__ import annotations

TagTerm = tuple[str, str, str]  # (slug, es, en)


# ---------------------------------------------------------------------------
# Taxonomy fields (Spanish-first)
# ---------------------------------------------------------------------------

COURSE: list[TagTerm] = [
    ("appetizer", "Entrada", "Appetizer"),
    ("main-dish", "Plato Principal", "Main Dish"),
    ("side-dish", "Guarnición", "Side Dish"),
    ("soup", "Sopa", "Soup"),
    ("dessert", "Postre", "Dessert"),
    ("beverage", "Bebida", "Beverage"),
    ("salad", "Ensalada", "Salad"),
    ("bread", "Pan", "Bread"),
]

MEAL_TYPE: list[TagTerm] = [
    ("breakfast", "Desayuno", "Breakfast"),
    ("brunch", "Brunch", "Brunch"),
    ("lunch", "Comida", "Lunch"),
    ("dinner", "Cena", "Dinner"),
    ("snack", "Botana", "Snack"),
]

PROTEIN: list[TagTerm] = [
    ("chicken", "Pollo", "Chicken"),
    ("beef", "Res", "Beef"),
    ("pork", "Cerdo", "Pork"),
    ("shrimp", "Camarón", "Shrimp"),
    ("fish", "Pescado", "Fish"),
    ("turkey", "Pavo", "Turkey"),
    ("eggs", "Huevos", "Eggs"),
    ("beans", "Frijoles", "Beans"),
    ("cheese", "Queso", "Cheese"),
    ("none", "Ninguno", "None"),
]

# Specific finfish species the tagger sometimes emits where the taxonomy only
# carries the coarse ``Pescado`` (Fish) bucket.
PROTEIN_ALIASES: dict[str, str] = {
    "Atún": "Pescado",
    "Tuna": "Pescado",
    "Salmón": "Pescado",
    "Salmon": "Pescado",
    "Mojarra": "Pescado",
    "Tilapia": "Pescado",
    "Huachinango": "Pescado",
    "Robalo": "Pescado",
    "Róbalo": "Pescado",
    "Trucha": "Pescado",
    "Bacalao": "Pescado",
    "Sardina": "Pescado",
    "Mero": "Pescado",
    "Sierra": "Pescado",
    "Dorado": "Pescado",
    "Puerco": "Cerdo",
    "Cochino": "Cerdo",
}

OPTIONAL_CLOSED_SCALAR_FIELDS: frozenset[str] = frozenset({"spiciness", "difficulty", "budget", "meal_type"})

SPICINESS: list[TagTerm] = [
    ("mild", "Suave", "Mild"),
    ("medium", "Medio", "Medium"),
    ("hot", "Picante", "Hot"),
    ("very-hot", "Muy Picante", "Very Hot"),
]

DIETARY: list[TagTerm] = [
    ("vegetarian", "Vegetariano", "Vegetarian"),
    ("vegan", "Vegano", "Vegan"),
    ("gluten-free", "Sin Gluten", "Gluten-Free"),
    ("dairy-free", "Sin Lácteos", "Dairy-Free"),
    ("low-carb", "Bajo en Carbohidratos", "Low-Carb"),
    ("high-protein", "Alto en Proteína", "High-Protein"),
]

COOKING_METHOD: list[TagTerm] = [
    ("grilled", "Asado a la Parrilla", "Grilled"),
    ("fried", "Frito", "Fried"),
    ("roasted", "Rostizado", "Roasted"),
    ("baked", "Horneado", "Baked"),
    ("stewed", "Guisado", "Stewed"),
    ("raw", "Crudo", "Raw"),
    ("slow-cooked", "Cocción Lenta", "Slow-Cooked"),
    ("steamed", "Al Vapor", "Steamed"),
    ("boiled", "Hervido", "Boiled"),
]

CHILE_TYPE: list[TagTerm] = [
    ("guajillo", "Guajillo", "Guajillo"),
    ("ancho", "Ancho", "Ancho"),
    ("chipotle", "Chipotle", "Chipotle"),
    ("serrano", "Serrano", "Serrano"),
    ("jalapeno", "Jalapeño", "Jalapeño"),
    ("habanero", "Habanero", "Habanero"),
    ("pasilla", "Pasilla", "Pasilla"),
    ("poblano", "Poblano", "Poblano"),
    ("arbol", "Árbol", "Arbol"),
    ("morita", "Morita", "Morita"),
    ("cascabel", "Cascabel", "Cascabel"),
    ("mulato", "Mulato", "Mulato"),
    ("piquin", "Piquín", "Piquin"),
    ("chilaca", "Chilaca", "Chilaca"),
    ("manzano", "Manzano", "Manzano"),
    ("guero", "Güero", "Guero"),
]

DIFFICULTY: list[TagTerm] = [
    ("easy", "Fácil", "Easy"),
    ("intermediate", "Intermedio", "Intermediate"),
    ("advanced", "Avanzado", "Advanced"),
]

KEY_INGREDIENT: list[TagTerm] = [
    ("corn", "Maíz", "Corn"),
    ("avocado", "Aguacate", "Avocado"),
    ("chocolate", "Chocolate", "Chocolate"),
    ("mole", "Mole", "Mole"),
    ("nopales", "Nopales", "Nopales"),
    ("chayote", "Chayote", "Chayote"),
    ("masa", "Masa", "Masa"),
    ("tomatillo", "Tomatillo", "Tomatillo"),
    ("cilantro", "Cilantro", "Cilantro"),
    ("beans", "Frijol", "Beans"),
    ("squash", "Calabaza", "Squash"),
    ("plantain", "Plátano", "Plantain"),
    ("epazote", "Epazote", "Epazote"),
    ("cheese", "Queso", "Cheese"),
    ("chile", "Chile", "Chile"),
    ("tomato", "Jitomate", "Tomato"),
    ("rice", "Arroz", "Rice"),
    ("hominy", "Maíz Cacahuazintle", "Hominy"),
    ("agave", "Agave", "Agave"),
    ("vanilla", "Vainilla", "Vanilla"),
]

BUDGET: list[TagTerm] = [
    ("budget-friendly", "Económico", "Budget-Friendly"),
    ("moderate", "Moderado", "Moderate"),
    ("premium", "Premium", "Premium"),
]

DISH_FORMAT: list[TagTerm] = [
    ("tacos", "Tacos", "Tacos"),
    ("tostadas", "Tostadas", "Tostadas"),
    ("quesadillas", "Quesadillas", "Quesadillas"),
    ("enchiladas", "Enchiladas", "Enchiladas"),
    ("tamales", "Tamales", "Tamales"),
    ("empanadas", "Empanadas", "Empanadas"),
    ("tortas", "Tortas", "Tortas"),
    ("antojitos", "Antojitos", "Antojitos"),
    ("salsa", "Salsa", "Salsa"),
    ("guacamole", "Guacamole", "Guacamole"),
    ("mole", "Mole", "Mole"),
    ("pipian", "Pipián", "Pipian"),
    ("adobo", "Adobo", "Adobo"),
    ("sopa", "Sopa", "Soup"),
    ("pozole", "Pozole", "Pozole"),
    ("menudo", "Menudo", "Menudo"),
    ("caldo", "Caldo", "Broth"),
    ("birria", "Birria", "Birria"),
    ("barbacoa", "Barbacoa", "Barbacoa"),
    ("carnitas", "Carnitas", "Carnitas"),
    ("cochinita-pibil", "Cochinita Pibil", "Cochinita Pibil"),
    ("ceviche", "Ceviche", "Ceviche"),
    ("chilaquiles", "Chilaquiles", "Chilaquiles"),
    ("chiles-rellenos", "Chiles Rellenos", "Stuffed Chiles"),
    ("postre", "Postre", "Dessert"),
    ("bebida", "Bebida", "Drink"),
    ("other", "Otro", "Other"),
]

ALLERGENS: list[TagTerm] = [
    ("tree-nuts", "Frutos Secos", "Tree Nuts"),
    ("peanuts", "Cacahuates", "Peanuts"),
    ("shellfish", "Mariscos", "Shellfish"),
    ("fish", "Pescado", "Fish"),
    ("eggs", "Huevo", "Eggs"),
    ("dairy", "Lácteos", "Dairy"),
    ("wheat-gluten", "Trigo/Gluten", "Wheat/Gluten"),
    ("soy", "Soya", "Soy"),
    ("sesame", "Ajonjolí", "Sesame"),
    ("none", "Ninguno", "None"),
]

REGION: list[TagTerm] = [
    (slug, name, name)
    for slug, name in [
        ("aguascalientes", "Aguascalientes"),
        ("baja-california", "Baja California"),
        ("baja-california-sur", "Baja California Sur"),
        ("campeche", "Campeche"),
        ("chiapas", "Chiapas"),
        ("chihuahua", "Chihuahua"),
        ("ciudad-de-mexico", "Ciudad de México"),
        ("coahuila", "Coahuila"),
        ("colima", "Colima"),
        ("durango", "Durango"),
        ("estado-de-mexico", "Estado de México"),
        ("guanajuato", "Guanajuato"),
        ("guerrero", "Guerrero"),
        ("hidalgo", "Hidalgo"),
        ("jalisco", "Jalisco"),
        ("michoacan", "Michoacán"),
        ("morelos", "Morelos"),
        ("nayarit", "Nayarit"),
        ("nuevo-leon", "Nuevo León"),
        ("oaxaca", "Oaxaca"),
        ("puebla", "Puebla"),
        ("queretaro", "Querétaro"),
        ("quintana-roo", "Quintana Roo"),
        ("san-luis-potosi", "San Luis Potosí"),
        ("sinaloa", "Sinaloa"),
        ("sonora", "Sonora"),
        ("tabasco", "Tabasco"),
        ("tamaulipas", "Tamaulipas"),
        ("tlaxcala", "Tlaxcala"),
        ("veracruz", "Veracruz"),
        ("yucatan", "Yucatán"),
        ("zacatecas", "Zacatecas"),
    ]
]

# Legacy v2 dish_format slugs mapped to v3 canonical labels for sanitization.
DISH_FORMAT_LEGACY_MAP: dict[str, str] = {
    "Huaraches": "Antojitos",
    "Burritos": "Antojitos",
    "Nachos": "Antojitos",
    "Crema": "Sopa",
    "Mixiote": "Otro",
    "Chilorio": "Otro",
    "Tinga": "Otro",
    "Picadillo": "Otro",
    "Albóndigas": "Otro",
    "Cabrito": "Otro",
    "Machaca": "Otro",
    "Discada": "Otro",
    "Aguachile": "Ceviche",
    "Huevos": "Otro",
    "Arroz": "Otro",
    "Frijoles": "Otro",
    "Ensalada": "Otro",
    "Tortillas": "Otro",
    "Pan Dulce": "Postre",
    "Papadzul": "Otro",
    "Chirmol": "Salsa",
    "Plátano": "Otro",
    "Volteado": "Postre",
}

# When legacy meal_type lists contain multiple values, prefer the most specific.
MEAL_TYPE_LEGACY_PRIORITY: tuple[str, ...] = (
    "Botana",
    "Desayuno",
    "Brunch",
    "Comida",
    "Cena",
)

# Maximum list lengths enforced during sanitization (matches RecipeTagSet).
LIST_FIELD_MAX_LENGTHS: dict[str, int] = {
    "key_ingredient": 3,
    "chile_type": 3,
    "cooking_method": 2,
    "dish_format": 2,
}


# ---------------------------------------------------------------------------
# Registry + derived lookups
# ---------------------------------------------------------------------------

VOCABULARIES: dict[str, list[TagTerm]] = {
    "course": COURSE,
    "meal_type": MEAL_TYPE,
    "region": REGION,
    "primary_protein": PROTEIN,
    "spiciness": SPICINESS,
    "dietary": DIETARY,
    "cooking_method": COOKING_METHOD,
    "chile_type": CHILE_TYPE,
    "difficulty": DIFFICULTY,
    "key_ingredient": KEY_INGREDIENT,
    "budget": BUDGET,
    "dish_format": DISH_FORMAT,
    "allergens": ALLERGENS,
}

SCALAR_FIELDS: frozenset[str] = frozenset(
    {
        "region",
        "primary_protein",
        "spiciness",
        "difficulty",
        "budget",
        "meal_type",
    }
)

OPEN_FIELDS: frozenset[str] = frozenset({"region", "chile_type"})


def es_values(field: str) -> set[str]:
    """Set of canonical Spanish values for a field."""
    return {es for _, es, _ in VOCABULARIES.get(field, [])}


def en_values(field: str) -> set[str]:
    """Set of canonical English values for a field."""
    return {en for _, _, en in VOCABULARIES.get(field, [])}


def es_to_en(field: str) -> dict[str, str]:
    """Spanish -> English label map for a field."""
    return {es: en for _, es, en in VOCABULARIES.get(field, [])}


def en_to_es(field: str) -> dict[str, str]:
    """English -> Spanish label map for a field."""
    return {en: es for _, es, en in VOCABULARIES.get(field, [])}


def es_to_slug(field: str) -> dict[str, str]:
    """Spanish label -> slug map for a field."""
    return {es: slug for slug, es, _ in VOCABULARIES.get(field, [])}


def en_to_slug(field: str) -> dict[str, str]:
    """English label -> slug map for a field."""
    return {en: slug for slug, _, en in VOCABULARIES.get(field, [])}


def localize_value(field: str, value_es: str | None) -> str | None:
    """Translate a single Spanish value to English (passthrough if unknown)."""
    if value_es is None:
        return None
    return es_to_en(field).get(value_es, value_es)


def localize_list(field: str, values_es: list[str]) -> list[str]:
    """Translate a list of Spanish values to English (passthrough if unknown)."""
    mapping = es_to_en(field)
    return [mapping.get(v, v) for v in values_es]


def normalize_value_to_es(field: str, value: str | None) -> str | None:
    """Coerce a value that may be English into the canonical Spanish label."""
    if value is None:
        return None
    if value in es_values(field):
        return value
    return en_to_es(field).get(value, value)


def normalize_list_to_es(field: str, values: list[str]) -> list[str]:
    """Coerce a list of possibly-English values into canonical Spanish labels."""
    es_known = es_values(field)
    reverse = en_to_es(field)
    out: list[str] = []
    for v in values:
        out.append(v if v in es_known else reverse.get(v, v))
    return out


def _coerce_meal_type_scalar(value: object) -> str | None:
    """Normalize meal_type to a single canonical Spanish label (v3 scalar)."""
    if value is None:
        return None
    if isinstance(value, str):
        candidates = [value]
    elif isinstance(value, list):
        candidates = [v for v in value if isinstance(v, str)]
    else:
        return None

    es_known = es_values("meal_type")
    reverse = en_to_es("meal_type")
    canonicals: list[str] = []
    for raw in candidates:
        canonical = raw if raw in es_known else reverse.get(raw, raw)
        if canonical in es_known and canonical not in canonicals:
            canonicals.append(canonical)
    if not canonicals:
        return None
    if len(canonicals) == 1:
        return canonicals[0]
    for preferred in MEAL_TYPE_LEGACY_PRIORITY:
        if preferred in canonicals:
            return preferred
    return canonicals[0]


def _cap_list(field: str, values: list[str]) -> list[str]:
    max_len = LIST_FIELD_MAX_LENGTHS.get(field)
    if max_len is None:
        return values
    return values[:max_len]


def sanitize_recipe_tags_data(data: dict) -> dict:
    """Drop out-of-vocabulary values and enforce v3 field constraints."""
    out = dict(data)
    for field in VOCABULARIES:
        if field in SCALAR_FIELDS or field in OPEN_FIELDS:
            continue
        values = data.get(field)
        if not values:
            continue
        es_known = es_values(field)
        reverse = en_to_es(field)
        cleaned: list[str] = []
        for value in values:
            canonical = value if value in es_known else reverse.get(value, value)
            if field == "dish_format":
                canonical = DISH_FORMAT_LEGACY_MAP.get(canonical, canonical)
            if canonical in es_known and canonical not in cleaned:
                cleaned.append(canonical)
        out[field] = _cap_list(field, cleaned)

    primary = data.get("primary_protein")
    if isinstance(primary, str):
        canonical = normalize_value_to_es("primary_protein", primary)
        canonical = PROTEIN_ALIASES.get(canonical or primary, canonical or primary)
        out["primary_protein"] = canonical

    for field in OPTIONAL_CLOSED_SCALAR_FIELDS:
        value = data.get(field)
        if not isinstance(value, str):
            continue
        canonical = normalize_value_to_es(field, value)
        out[field] = canonical if canonical in es_values(field) else None

    out["meal_type"] = _coerce_meal_type_scalar(data.get("meal_type"))

    # Open chile_type: keep unknowns but cap length.
    chiles = data.get("chile_type")
    if isinstance(chiles, list):
        out["chile_type"] = _cap_list("chile_type", [v for v in chiles if isinstance(v, str)])

    return out


def slug_for(field: str, value_es: str | None) -> str | None:
    """Resolve the stable slug for a Spanish value (None if unknown/empty)."""
    if not value_es:
        return None
    return es_to_slug(field).get(value_es)


def bilingual_entry(field: str, value_es: str | None, value_en: str | None = None) -> dict[str, str] | None:
    """Build a ``{slug, es, en}`` dict for a Spanish value (None if empty)."""
    if not value_es:
        return None

    dict_en = es_to_en(field).get(value_es, value_es)
    final_en = value_en if (dict_en == value_es and value_en is not None) else dict_en

    return {
        "slug": es_to_slug(field).get(value_es, _fallback_slug(value_es)),
        "es": value_es,
        "en": final_en,
    }


def _fallback_slug(value: str) -> str:
    """Best-effort slug for values outside the controlled vocabulary."""
    out = []
    for ch in value.lower().strip():
        if ch.isalnum():
            out.append(ch)
        elif ch in " /_":
            out.append("-")
    slug = "".join(out)
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-")


FACET_FIELDS: tuple[str, ...] = (
    "course",
    "meal_type",
    "region",
    "primary_protein",
    "dietary",
    "cooking_method",
    "chile_type",
    "spiciness",
    "difficulty",
    "key_ingredient",
    "budget",
    "dish_format",
    "allergens",
)


def to_bilingual(tag_data: dict, tag_data_en: dict | None = None) -> dict:
    """Build a ``{slug, es, en}`` export view from a Spanish tag-set ``model_dump``."""
    out: dict = {}
    tag_data_en = tag_data_en or {}
    for field, value in tag_data.items():
        if field not in VOCABULARIES:
            out[field] = value
            continue
        en_value = tag_data_en.get(field)
        if field in SCALAR_FIELDS:
            out[field] = bilingual_entry(field, value, en_value)
        else:
            out[field] = []
            for i, v in enumerate(value or []):
                if not v:
                    continue
                v_en = en_value[i] if (isinstance(en_value, list) and i < len(en_value)) else None
                out[field].append(bilingual_entry(field, v, v_en))
    return out


def slug_map_for(tag_data: dict) -> dict[str, list[str]]:
    """Map each facet field to its list of slugs (scalars yield a 1-element list)."""
    result: dict[str, list[str]] = {}
    for field in FACET_FIELDS:
        value = tag_data.get(field)
        slugs: list[str] = []
        if field in SCALAR_FIELDS:
            slug = slug_for(field, value) or (_fallback_slug(value) if value else None)
            if slug:
                slugs.append(slug)
        else:
            for v in value or []:
                slug = slug_for(field, v) or _fallback_slug(v)
                if slug:
                    slugs.append(slug)
        if slugs:
            result[field] = slugs
    return result


INHERITED_TAG_FIELDS: tuple[str, ...] = (
    "region",
    "dietary",
    "budget",
)

INHERITABLE_MERGE_FIELDS: tuple[str, ...] = (
    "dietary",
    "budget",
)


def normalize_inherited_tags_data(data: dict) -> dict:
    """Coerce publication-level inherited tag values to Spanish canonical labels."""
    out = dict(data)
    for field, value in data.items():
        if field not in VOCABULARIES:
            continue
        if field in SCALAR_FIELDS:
            if isinstance(value, str):
                out[field] = normalize_value_to_es(field, value)
        elif isinstance(value, list):
            normalized = normalize_list_to_es(field, value)
            deduped: list[str] = []
            for item in normalized:
                if item not in deduped:
                    deduped.append(item)
            out[field] = deduped
    return out


def format_inherited_tags_prompt_section() -> str:
    """Render controlled vocab for publication-level ``inherited_tags`` (Spanish)."""
    lines = [
        "Usa **exactamente** estos valores canónicos en **español** para `inherited_tags`.",
        "Deja los campos vacíos o null si no hay un tema global claro para toda la publicación.",
        "",
    ]

    def render(field: str, label_es: str, note: str = "") -> None:
        values = ", ".join(f"`{es}`" for _, es, _ in VOCABULARIES[field])
        suffix = f" {note}" if note else ""
        lines.append(f"- **{field}** ({label_es}): {values}.{suffix}")

    render(
        "region",
        "región mexicana",
        "Solo si TODAS las recetas son de esa región y el título/subtítulo lo afirma. NO uses autor, editor ni institución publicadora.",
    )
    render("dietary", "dietético", "Si es vegano: `Vegano`, `Vegetariano`, `Sin Lácteos`.")
    render("budget", "presupuesto", "Elige EXACTAMENTE una si aplica globalmente.")

    return "\n".join(lines)


def format_tag_taxonomy_prompt_section() -> str:
    """Render the Spanish controlled vocabularies for the tagging prompt."""
    lines: list[str] = []

    def render(num: int, field: str, label_es: str, note: str = "") -> None:
        values = ", ".join(f"`{es}`" for _, es, _ in VOCABULARIES[field])
        suffix = f" {note}" if note else ""
        lines.append(f"{num}. **{field}** ({label_es}): {values}.{suffix}")

    render(1, "course", "tipo de plato")
    render(2, "meal_type", "momento de la comida", "Elige EXACTAMENTE uno, o omite para platos principales genéricos.")
    render(3, "region", "región mexicana de origen", "Usa el estado si se menciona o se infiere; si no, omite.")
    render(
        4,
        "primary_protein",
        "proteína principal",
        "Elige EXACTAMENTE una de la lista (la más prominente). Cualquier pez de aleta es `Pescado`. "
        "NO uses `Ninguno` si hay proteína animal o mariscos en la receta.",
    )
    render(5, "spiciness", "nivel de picor", "Elige EXACTAMENTE una.")
    render(6, "dietary", "propiedades dietéticas")
    render(7, "cooking_method", "métodos de cocción", "Máximo 2.")
    render(8, "chile_type", "chiles utilizados", "Máximo 3.")
    render(9, "difficulty", "dificultad", "Elige EXACTAMENTE una.")
    render(10, "key_ingredient", "ingredientes clave definitorios", "Máximo 3; solo del vocabulario.")
    render(11, "budget", "categoría de costo", "Elige EXACTAMENTE una.")
    render(
        12,
        "dish_format",
        "formato del platillo",
        "Máximo 2. Úsalo SOLO cuando aplica un formato reconocible. No uses `Salsa` cuando la salsa es un componente.",
    )
    render(13, "allergens", "alérgenos", "Incluye solo alérgenos claramente presentes; usa `Ninguno` si no hay.")

    return "\n".join(lines)
