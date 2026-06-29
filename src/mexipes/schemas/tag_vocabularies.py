"""Bilingual canonical tag vocabularies for recipe tagging.

Tagging runs on the rewritten **Spanish** text, so every controlled vocabulary is
authored Spanish-first. Each term is a ``(slug, es, en)`` tuple:

* ``slug`` — stable, language-independent identifier used for facets/similarity.
* ``es``   — canonical Spanish label emitted by the tagging stage.
* ``en``   — canonical English label produced by the localize stage via a
  deterministic lookup (no extra LLM call).

The ``health_nutrition`` field uses the bilingual vocabulary in
``health_nutrition_tags.py`` (registered in ``VOCABULARIES`` like other fields).
"""

from __future__ import annotations

from mexipes.schemas.health_nutrition_tags import HEALTH_NUTRITION

TagTerm = tuple[str, str, str]  # (slug, es, en)


# ---------------------------------------------------------------------------
# Existing taxonomy fields (now Spanish-first)
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
    ("late-night", "Trasnoche", "Late Night"),
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
# carries the coarse ``Pescado`` (Fish) bucket. Mapped deterministically so a
# required scalar like ``primary_protein`` never lands on an off-vocabulary value
# (which would be a hard DQ error). Shellfish/molluscs are intentionally omitted
# since they have no clean canonical bucket here.
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
}

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

CUISINE_STYLE: list[TagTerm] = [
    ("street-food", "Comida Callejera", "Street Food"),
    ("home-style", "Casera", "Home-Style"),
    ("regional-traditional", "Tradicional Regional", "Regional Traditional"),
    ("holiday-festive", "Festivo", "Holiday/Festive"),
    ("modern-fusion", "Fusión Moderna", "Modern Fusion"),
]

DIFFICULTY: list[TagTerm] = [
    ("easy", "Fácil", "Easy"),
    ("intermediate", "Intermedio", "Intermediate"),
    ("advanced", "Avanzado", "Advanced"),
]

TOTAL_TIME: list[TagTerm] = [
    ("under-30-min", "Menos de 30 min", "Under 30 min"),
    ("30-60-min", "30-60 min", "30-60 min"),
    ("1-2-hours", "1-2 horas", "1-2 hours"),
    ("2-plus-hours", "2+ horas", "2+ hours"),
]

ACTIVE_TIME: list[TagTerm] = [
    ("active-under-15-min", "Menos de 15 min", "Under 15 min"),
    ("active-15-30-min", "15-30 min", "15-30 min"),
    ("active-30-60-min", "30-60 min", "30-60 min"),
    ("active-1-plus-hours", "1+ horas", "1+ hours"),
]

SEASON: list[TagTerm] = [
    ("year-round", "Todo el Año", "Year-Round"),
    ("summer", "Verano", "Summer"),
    ("winter", "Invierno", "Winter"),
    ("spring", "Primavera", "Spring"),
    ("autumn", "Otoño", "Autumn"),
    ("holiday", "Festividad", "Holiday"),
    ("lent", "Cuaresma", "Lent/Cuaresma"),
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

COOKING_EQUIPMENT: list[TagTerm] = [
    ("molcajete", "Molcajete", "Molcajete"),
    ("comal", "Comal", "Comal"),
    ("blender", "Licuadora", "Blender"),
    ("dutch-oven", "Olla de Hierro", "Dutch Oven"),
    ("cazuela", "Cazuela", "Cazuela"),
    ("tortilla-press", "Prensa para Tortillas", "Tortilla Press"),
    ("slow-cooker", "Olla de Cocción Lenta", "Slow Cooker"),
    ("steamer", "Vaporera", "Steamer"),
    ("pressure-cooker", "Olla Exprés", "Pressure Cooker"),
    ("griddle", "Plancha", "Griddle"),
    ("oven", "Horno", "Oven"),
    ("metate", "Metate", "Metate"),
]


# ---------------------------------------------------------------------------
# New recommendation-focused fields
# ---------------------------------------------------------------------------

DISH_FORMAT: list[TagTerm] = [
    # Core antojitos & handhelds
    ("tacos", "Tacos", "Tacos"),
    ("tostadas", "Tostadas", "Tostadas"),
    ("huaraches", "Huaraches", "Huaraches"),
    ("quesadillas", "Quesadillas", "Quesadillas"),
    ("enchiladas", "Enchiladas", "Enchiladas"),
    ("tamales", "Tamales", "Tamales"),
    ("antojitos", "Antojitos", "Antojitos"),
    ("empanadas", "Empanadas", "Empanadas"),
    ("tortas", "Tortas", "Tortas"),
    ("burritos", "Burritos", "Burritos"),
    ("nachos", "Nachos", "Nachos"),
    # Sauces & condiments (standalone)
    ("salsa", "Salsa", "Salsa"),
    ("guacamole", "Guacamole", "Guacamole"),
    ("mole", "Mole", "Mole"),
    ("pipian", "Pipián", "Pipian"),
    ("adobo", "Adobo", "Adobo"),
    # Soups & broths
    ("sopa", "Sopa", "Soup"),
    ("pozole", "Pozole", "Pozole"),
    ("menudo", "Menudo", "Menudo"),
    ("caldo", "Caldo", "Broth"),
    ("crema", "Crema", "Cream Soup"),
    # Proteins & braises
    ("birria", "Birria", "Birria"),
    ("barbacoa", "Barbacoa", "Barbacoa"),
    ("carnitas", "Carnitas", "Carnitas"),
    ("cochinita-pibil", "Cochinita Pibil", "Cochinita Pibil"),
    ("mixiote", "Mixiote", "Mixiote"),
    ("chilorio", "Chilorio", "Chilorio"),
    ("tinga", "Tinga", "Tinga"),
    ("picadillo", "Picadillo", "Picadillo"),
    ("albondigas", "Albóndigas", "Meatballs"),
    ("cabrito", "Cabrito", "Roast Goat"),
    ("machaca", "Machaca", "Machaca"),
    ("discada", "Discada", "Discada"),
    # Seafood
    ("ceviche", "Ceviche", "Ceviche"),
    ("aguachile", "Aguachile", "Aguachile"),
    # Stuffed & egg
    ("chiles-rellenos", "Chiles Rellenos", "Stuffed Chiles"),
    ("chilaquiles", "Chilaquiles", "Chilaquiles"),
    ("huevos", "Huevos", "Eggs"),
    # Sides & staples
    ("arroz", "Arroz", "Rice"),
    ("frijoles", "Frijoles", "Beans"),
    ("ensalada", "Ensalada", "Salad"),
    ("tortillas", "Tortillas", "Tortillas"),
    # Sweet & baked
    ("postre", "Postre", "Dessert"),
    ("pan-dulce", "Pan Dulce", "Sweet Bread"),
    # Drinks
    ("bebida", "Bebida", "Drink"),
    # Regional specialties
    ("papadzul", "Papadzul", "Papadzul"),
    ("chirmol", "Chirmol", "Chirmol"),
    ("platano", "Plátano", "Plantain Dish"),
    ("volteado", "Volteado", "Upside-Down Cake"),
    ("other", "Otro", "Other"),
]

PREPARATION_STYLE: list[TagTerm] = [
    ("en-salsa", "En Salsa", "In Sauce"),
    ("relleno", "Relleno", "Stuffed"),
    ("en-mole", "En Mole", "In Mole"),
    ("en-pipian", "En Pipián", "In Pipian"),
    ("en-adobo", "En Adobo", "In Adobo"),
    ("a-la-mexicana", "A la Mexicana", "Mexican-Style"),
    ("empanizado", "Empanizado", "Breaded"),
    ("capeado", "Capeado", "Battered"),
    ("en-escabeche", "En Escabeche", "Pickled"),
    ("other", "Otro", "Other"),
]

FLAVOR_PROFILE: list[TagTerm] = [
    ("smoky", "Ahumado", "Smoky"),
    ("earthy", "Terroso", "Earthy"),
    ("rich", "Rico", "Rich"),
    ("bright", "Brillante", "Bright"),
    ("tangy", "Ácido", "Tangy"),
    ("spicy", "Picante", "Spicy"),
    ("sweet", "Dulce", "Sweet"),
    ("savory", "Salado", "Savory"),
    ("fresh", "Fresco", "Fresh"),
    ("herbal", "Herbal", "Herbal"),
    ("nutty", "A Nuez", "Nutty"),
    ("smoky-chile", "Ahumado-Chile", "Smoky-Chile"),
    ("citrus", "Cítrico", "Citrus"),
    ("umami", "Umami", "Umami"),
]

TEXTURE: list[TagTerm] = [
    ("crispy", "Crujiente", "Crispy"),
    ("creamy", "Cremoso", "Creamy"),
    ("brothy", "Caldoso", "Brothy"),
    ("chewy", "Masticable", "Chewy"),
    ("tender", "Tierno", "Tender"),
    ("crunchy", "Crocante", "Crunchy"),
    ("silky", "Sedoso", "Silky"),
    ("chunky", "En Trozos", "Chunky"),
    ("flaky", "Hojaldrado", "Flaky"),
]

OCCASION: list[TagTerm] = [
    ("weeknight", "Entre Semana", "Weeknight"),
    ("weekend-project", "Proyecto de Fin de Semana", "Weekend Project"),
    ("holiday", "Festividad", "Holiday"),
    ("lent", "Cuaresma", "Lent"),
    ("party", "Fiesta", "Party"),
    ("meal-prep", "Preparación de Comidas", "Meal Prep"),
    ("date-night", "Cita Romántica", "Date Night"),
    ("comfort-food", "Comida Reconfortante", "Comfort Food"),
    ("street-food", "Comida Callejera", "Street Food"),
    ("brunch", "Brunch", "Brunch"),
    ("game-day", "Día de Partido", "Game Day"),
]

PAIRS_WELL_WITH: list[TagTerm] = [
    ("side-dish", "Guarnición", "Side Dish"),
    ("soup", "Sopa", "Soup"),
    ("salad", "Ensalada", "Salad"),
    ("rice", "Arroz", "Rice"),
    ("beans", "Frijoles", "Beans"),
    ("tortillas", "Tortillas", "Tortillas"),
    ("salsa", "Salsa", "Salsa"),
    ("beverage", "Bebida", "Beverage"),
    ("dessert", "Postre", "Dessert"),
    ("appetizer", "Entrada", "Appetizer"),
]

SERVING_SIZE: list[TagTerm] = [
    ("1-2", "1-2", "1-2"),
    ("3-4", "3-4", "3-4"),
    ("5-8", "5-8", "5-8"),
    ("9-plus", "9+", "9+"),
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

MAKE_AHEAD: list[TagTerm] = [
    ("same-day", "Mismo Día", "Same Day"),
    ("1-day-ahead", "Un Día Antes", "1 Day Ahead"),
    ("freezer-friendly", "Apto para Congelar", "Freezer Friendly"),
    ("leftover-friendly", "Bueno como Sobras", "Leftover Friendly"),
]

KID_FRIENDLY: list[TagTerm] = [
    ("kid-mild", "Suave", "Mild"),
    ("kid-moderate", "Moderado", "Moderate"),
    ("kid-not", "No apto para niños", "Not Kid-Friendly"),
]

# Mexican regions of origin (es == en for proper nouns).
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


# ---------------------------------------------------------------------------
# Registry + derived lookups
# ---------------------------------------------------------------------------

# Maps each tag field name to its vocabulary. Order is used for prompt rendering.
VOCABULARIES: dict[str, list[TagTerm]] = {
    "course": COURSE,
    "meal_type": MEAL_TYPE,
    "region": REGION,
    "protein": PROTEIN,
    "primary_protein": PROTEIN,
    "spiciness": SPICINESS,
    "dietary": DIETARY,
    "cooking_method": COOKING_METHOD,
    "chile_type": CHILE_TYPE,
    "cuisine_style": CUISINE_STYLE,
    "difficulty": DIFFICULTY,
    "total_time": TOTAL_TIME,
    "active_time": ACTIVE_TIME,
    "season": SEASON,
    "key_ingredient": KEY_INGREDIENT,
    "budget": BUDGET,
    "cooking_equipment": COOKING_EQUIPMENT,
    "dish_format": DISH_FORMAT,
    "preparation_style": PREPARATION_STYLE,
    "flavor_profile": FLAVOR_PROFILE,
    "texture": TEXTURE,
    "occasion": OCCASION,
    "pairs_well_with": PAIRS_WELL_WITH,
    "serving_size": SERVING_SIZE,
    "allergens": ALLERGENS,
    "make_ahead": MAKE_AHEAD,
    "kid_friendly": KID_FRIENDLY,
    "health_nutrition": HEALTH_NUTRITION,
}

# Fields that hold a single scalar value (not a list).
SCALAR_FIELDS: frozenset[str] = frozenset(
    {
        "region",
        "primary_protein",
        "spiciness",
        "difficulty",
        "total_time",
        "active_time",
        "budget",
        "serving_size",
        "kid_friendly",
    }
)

# Fields that are open-ended: validate as warnings, allow unknown values.
OPEN_FIELDS: frozenset[str] = frozenset({"region", "chile_type", "key_ingredient", "cooking_equipment"})


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
    """Coerce a value that may be English into the canonical Spanish label.

    Used when merging publication-level inherited tags (which may have been
    produced in English) into a Spanish recipe tag set.
    """
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


def sanitize_recipe_tags_data(data: dict) -> dict:
    """Drop out-of-vocabulary values from closed-vocabulary list fields.

    Safety net applied after LLM tagging. The model occasionally places a value
    that is valid for a *different* field (e.g. ``Botana`` is a ``meal_type``, not
    a ``course`` or ``occasion``) or otherwise off-vocabulary. Such values would
    survive into localization and leak **untranslated** into the English tag set,
    so each value is first coerced to its canonical Spanish label and then dropped
    if it is still not in the field's vocabulary (order-preserving, de-duplicated).

    Scalar fields, open fields (``region``, ``chile_type``, ``key_ingredient``,
    ``cooking_equipment``), and any non-vocabulary field are left untouched.
    """
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
            if field == "protein":
                canonical = PROTEIN_ALIASES.get(canonical, canonical)
            if canonical in es_known and canonical not in cleaned:
                cleaned.append(canonical)
        out[field] = cleaned
    # Coerce the required scalar `primary_protein` onto its canonical bucket so a
    # specific species (e.g. 'Atún') never produces an invalid-enum DQ error.
    primary = data.get("primary_protein")
    if isinstance(primary, str):
        out["primary_protein"] = PROTEIN_ALIASES.get(primary, primary)
    return out


def slug_for(field: str, value_es: str | None) -> str | None:
    """Resolve the stable slug for a Spanish value (None if unknown/empty)."""
    if not value_es:
        return None
    return es_to_slug(field).get(value_es)


def bilingual_entry(field: str, value_es: str | None) -> dict[str, str] | None:
    """Build a ``{slug, es, en}`` dict for a Spanish value (None if empty)."""
    if not value_es:
        return None
    return {
        "slug": es_to_slug(field).get(value_es, _fallback_slug(value_es)),
        "es": value_es,
        "en": es_to_en(field).get(value_es, value_es),
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


# Fields surfaced as facets and used for tag-overlap similarity (slug-based).
FACET_FIELDS: tuple[str, ...] = (
    "course",
    "meal_type",
    "region",
    "protein",
    "primary_protein",
    "dietary",
    "cooking_method",
    "chile_type",
    "cuisine_style",
    "difficulty",
    "total_time",
    "season",
    "key_ingredient",
    "budget",
    "dish_format",
    "preparation_style",
    "flavor_profile",
    "texture",
    "occasion",
    "pairs_well_with",
    "serving_size",
    "allergens",
    "make_ahead",
    "kid_friendly",
)


def to_bilingual(tag_data: dict) -> dict:
    """Build a ``{slug, es, en}`` export view from a Spanish tag-set ``model_dump``.

    List fields become lists of entries; scalar fields become a single entry (or
    ``None``). Non-vocabulary fields pass through.
    """
    out: dict = {}
    for field, value in tag_data.items():
        if field not in VOCABULARIES:
            out[field] = value
            continue
        if field in SCALAR_FIELDS:
            out[field] = bilingual_entry(field, value)
        else:
            out[field] = [bilingual_entry(field, v) for v in (value or []) if v]
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


# Fields on ``InheritedTags`` (publication-level defaults merged into each recipe).
INHERITED_TAG_FIELDS: tuple[str, ...] = (
    "course",
    "meal_type",
    "region",
    "protein",
    "spiciness",
    "dietary",
    "cooking_method",
    "chile_type",
    "cuisine_style",
    "difficulty",
    "total_time",
    "season",
    "key_ingredient",
    "budget",
    "cooking_equipment",
    "health_nutrition",
)


def normalize_inherited_tags_data(data: dict) -> dict:
    """Coerce publication-level inherited tag values to Spanish canonical labels.

    Unknown values pass through.
    """
    out = dict(data)
    for field, value in data.items():
        if field not in VOCABULARIES:
            continue
        if field in SCALAR_FIELDS:
            if isinstance(value, str):
                normalized_scalar = normalize_value_to_es(field, value)
                if field == "primary_protein":
                    normalized_scalar = PROTEIN_ALIASES.get(normalized_scalar, normalized_scalar)
                out[field] = normalized_scalar
        elif isinstance(value, list):
            normalized = normalize_list_to_es(field, value)
            if field == "protein":
                normalized = [PROTEIN_ALIASES.get(v, v) for v in normalized]
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
        "`health_nutrition` también usa valores canónicos en **español** (ver vocabulario abajo).",
        "",
    ]

    def render(field: str, label_es: str, note: str = "") -> None:
        values = ", ".join(f"`{es}`" for _, es, _ in VOCABULARIES[field])
        suffix = f" {note}" if note else ""
        lines.append(f"- **{field}** ({label_es}): {values}.{suffix}")

    render("course", "tipo de plato")
    render("meal_type", "momento de la comida")
    render(
        "region",
        "región mexicana",
        "Solo si TODAS las recetas son de esa región y el título/subtítulo lo afirma. NO uses autor, editor ni institución publicadora.",
    )
    render(
        "protein",
        "proteínas",
        "p. ej. `Pollo`, `Ninguno` para vegano/vegetariano. Cualquier pez de aleta (atún, salmón, etc.) es `Pescado`.",
    )
    render("spiciness", "picor", "Elige EXACTAMENTE una si aplica a todo el libro.")
    render("dietary", "dietético", "Si es vegano: `Vegano`, `Vegetariano`, `Sin Lácteos`.")
    render("cooking_method", "método de cocción")
    render("chile_type", "chiles")
    render(
        "cuisine_style",
        "estilo de cocina",
        "`Tradicional Regional` solo si el libro afirma explícitamente cocina regional/tradicional; no por nombre de estado en la editorial.",
    )
    render("difficulty", "dificultad", "Elige EXACTAMENTE una si aplica globalmente.")
    render("total_time", "tiempo total", "Elige EXACTAMENTE una si aplica globalmente.")
    render("season", "temporada o evento", "p. ej. bolis/paletas/nieves → `Verano`; no uses `Todo el Año` por defecto.")
    render("key_ingredient", "ingredientes clave")
    render("budget", "presupuesto", "Elige EXACTAMENTE una si aplica globalmente.")
    render("cooking_equipment", "equipo", "p. ej. `Comal`, `Licuadora`.")

    return "\n".join(lines)


def format_tag_taxonomy_prompt_section() -> str:
    """Render the Spanish controlled vocabularies for the tagging prompt."""
    lines: list[str] = []

    def render(num: int, field: str, label_es: str, note: str = "") -> None:
        values = ", ".join(f"`{es}`" for _, es, _ in VOCABULARIES[field])
        suffix = f" {note}" if note else ""
        lines.append(f"{num}. **{field}** ({label_es}): {values}.{suffix}")

    render(1, "course", "tipo de plato")
    render(2, "meal_type", "momento de la comida")
    render(3, "region", "región mexicana de origen", "Usa el estado si se menciona o se infiere; si no, omite.")
    render(
        4,
        "protein",
        "fuentes de proteína",
        "Usa `Pescado` para CUALQUIER pez de aleta (atún, salmón, mojarra, tilapia, huachinango, bacalao, etc.); `Camarón` para camarón.",
    )
    render(
        5,
        "primary_protein",
        "proteína principal",
        "Elige EXACTAMENTE una de la lista (la más prominente). Cualquier pez de aleta es `Pescado`. Usa `Ninguno` para platos sin proteína animal.",
    )
    render(6, "spiciness", "nivel de picor", "Elige EXACTAMENTE una.")
    render(7, "dietary", "propiedades dietéticas")
    render(8, "cooking_method", "métodos de cocción")
    render(9, "chile_type", "chiles utilizados")
    render(10, "cuisine_style", "estilo de cocina")
    render(11, "difficulty", "dificultad", "Elige EXACTAMENTE una.")
    render(12, "total_time", "tiempo total", "Elige EXACTAMENTE una.")
    render(13, "active_time", "tiempo activo (manos a la obra)", "Elige EXACTAMENTE una si es posible.")
    render(14, "season", "temporada o evento")
    render(15, "key_ingredient", "ingredientes clave definitorios")
    render(16, "budget", "categoría de costo", "Elige EXACTAMENTE una.")
    render(17, "cooking_equipment", "equipo esencial")
    render(
        18,
        "dish_format",
        "formato del platillo",
        "Máximo 2. Úsalo SOLO cuando aplica un formato reconocible. No uses `Salsa` cuando la salsa es un componente (p. ej. 'Pollo en salsa de...').",
    )
    render(
        19,
        "preparation_style",
        "estilo de preparación",
        "Máximo 2. Úsalo para platos sin formato claro (p. ej. 'Pescado en salsa' -> `En Salsa`). No dupliques `cooking_method`.",
    )
    render(20, "flavor_profile", "perfil de sabor", "Elige 2-5.")
    render(21, "texture", "textura", "Elige 1-3.")
    render(
        22,
        "occasion",
        "ocasión",
        "0-3. Infiere de la dificultad, el tiempo y el estilo (rara vez aparece en el texto).",
    )
    render(
        23,
        "pairs_well_with",
        "acompañamientos",
        "0-4. Extrae de frases como 'se sirve con...' en las instrucciones.",
    )
    render(24, "serving_size", "tamaño de porción", "Deriva del rendimiento si es numérico.")
    render(25, "allergens", "alérgenos", "Incluye solo alérgenos claramente presentes; usa `Ninguno` si no hay.")
    render(26, "make_ahead", "preparación anticipada")
    render(27, "kid_friendly", "apto para niños", "Elige EXACTAMENTE una si aplica.")

    lines.append("")
    lines.append("Además: **contains_alcohol** (booleano) — `true` si la receta contiene alcohol.")

    return "\n".join(lines)
