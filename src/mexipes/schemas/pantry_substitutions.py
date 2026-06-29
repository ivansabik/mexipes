"""Curated Mexican pantry sourcing guide for the substitution stage prompt.

Entry counts reflect frequency in the all_parsed corpus (~10,907 recipes).
"""

from dataclasses import dataclass
from typing import Literal

Availability = Literal["mainstream", "latin_market", "specialty"]


@dataclass(frozen=True)
class PantryEntry:
    names: tuple[str, ...]
    availability: Availability
    substitute: str
    notes: str
    corpus_count: int = 0


# ---------------------------------------------------------------------------
# Do-not-substitute: high-frequency Latin-market / mainstream staples
# ---------------------------------------------------------------------------

SKIP_ENTRIES: list[PantryEntry] = [
    PantryEntry(
        ("chile serrano", "serrano"),
        "latin_market",
        "",
        "Sold fresh at Latin groceries and many mainstream stores. Do not substitute.",
        875,
    ),
    PantryEntry(
        ("chile ancho", "ancho"),
        "latin_market",
        "",
        "Sold dried at Latin groceries. Do not substitute.",
        841,
    ),
    PantryEntry(
        ("manteca de cerdo", "lard"),
        "latin_market",
        "",
        "Same product as lard; widely available. Do not substitute.",
        806,
    ),
    PantryEntry(
        ("chile guajillo", "guajillo"),
        "latin_market",
        "",
        "Sold dried at Latin groceries. Do not substitute.",
        761,
    ),
    PantryEntry(
        ("nopal", "nopales"),
        "latin_market",
        "",
        "Fresh or jarred at Latin groceries. Do not substitute.",
        469,
    ),
    PantryEntry(
        ("chile poblano", "poblano"),
        "latin_market",
        "",
        "Sold fresh at Latin groceries and many mainstream stores. Do not substitute.",
        457,
    ),
    PantryEntry(
        ("chile chipotle", "chipotle"),
        "latin_market",
        "",
        "Sold dried or canned at Latin groceries. Do not substitute.",
        424,
    ),
    PantryEntry(
        ("queso fresco",),
        "latin_market",
        "",
        "Sold at Latin groceries. Do not substitute.",
        392,
    ),
    PantryEntry(
        ("chile pasilla", "pasilla"),
        "latin_market",
        "",
        "Sold dried at Latin groceries. Do not substitute.",
        352,
    ),
    PantryEntry(
        ("queso panela", "panela"),
        "latin_market",
        "",
        "Sold at Latin groceries. Do not substitute.",
        319,
    ),
    PantryEntry(
        ("tomatillo", "tomate verde"),
        "latin_market",
        "",
        "Sold fresh at mainstream and Latin groceries. Do not substitute.",
        311,
    ),
    PantryEntry(
        ("piloncillo",),
        "latin_market",
        "",
        "Sold at Latin groceries; dark brown sugar works in a pinch but prefer the original. Do not substitute.",
        295,
    ),
    PantryEntry(
        ("chile de árbol", "chile de arbol", "árbol"),
        "latin_market",
        "",
        "Sold dried at Latin groceries. Do not substitute.",
        291,
    ),
    PantryEntry(
        ("achiote", "annatto"),
        "latin_market",
        "",
        "Sold as paste or powder at Latin groceries. Do not substitute.",
        263,
    ),
    PantryEntry(
        ("orégano mexicano", "oregano mexicano", "dried oregano"),
        "latin_market",
        "",
        "Mexican oregano sold at Latin groceries; distinct from Mediterranean oregano. Do not substitute.",
        252,
    ),
    PantryEntry(
        ("chile habanero", "habanero"),
        "latin_market",
        "",
        "Sold fresh at Latin groceries and many mainstream stores. Do not substitute.",
        243,
    ),
    PantryEntry(
        ("masa harina", "Maseca", "harina de maíz"),
        "latin_market",
        "",
        "Sold at Latin groceries and many mainstream stores. Do not substitute.",
        230,
    ),
    PantryEntry(
        ("chile morita", "morita"),
        "latin_market",
        "",
        "Sold dried at Latin groceries. Do not substitute.",
        129,
    ),
    PantryEntry(
        ("chile cascabel", "cascabel"),
        "latin_market",
        "",
        "Sold dried at Latin groceries. Do not substitute.",
        116,
    ),
    PantryEntry(
        ("chile mulato", "mulato"),
        "latin_market",
        "",
        "Sold dried at Latin groceries. Do not substitute.",
        101,
    ),
    PantryEntry(
        ("crema mexicana", "Mexican crema"),
        "latin_market",
        "",
        "Sold at Latin groceries. Do not substitute.",
        62,
    ),
    PantryEntry(
        ("media crema",),
        "latin_market",
        "",
        "Nestlé product sold at Latin groceries and many mainstream stores; table cream or sour cream thinned with milk is the generic equivalent. Do not substitute.",
        62,
    ),
    # --- Not frequency-derived (corpus_count=0); added for branded-seasoning clarity ---
    PantryEntry(
        ("requesón", "requeson"),
        "latin_market",
        "",
        "Sold at Latin groceries; whole-milk ricotta is a close mainstream equivalent. Do not substitute.",
        0,
    ),
    PantryEntry(
        ("Jugo Maggi", "Salsa Maggi", "MAGGI Seasoning Sauce", "Salsa de Soya MAGGI", "MAGGI Soy Sauce"),
        "mainstream",
        "",
        "Maggi Seasoning and soy sauce are sold at mainstream supermarkets; use a splash of soy sauce if Maggi is unavailable. Do not substitute.",
        0,
    ),
    PantryEntry(
        ("CONSOMATE", "Caldo de Tomate", "Caldo de Tomate con Pollo"),
        "mainstream",
        "",
        "Tomato-chicken bouillon (e.g. Knorr) is the generic equivalent; sold at mainstream supermarkets. Do not substitute.",
        0,
    ),
    PantryEntry(
        ("Salsa Inglesa", "Crosse & Blackwell", "Worcestershire sauce"),
        "mainstream",
        "",
        "Standard Worcestershire sauce is the generic equivalent; sold at mainstream supermarkets. Do not substitute.",
        0,
    ),
    PantryEntry(
        ("galletas María", "Maria cookies", "María"),
        "latin_market",
        "",
        "Sold at Latin groceries and many mainstream stores. Do not substitute.",
        94,
    ),
    PantryEntry(
        ("rompope",),
        "latin_market",
        "",
        "Sold seasonally at Latin groceries. Do not substitute.",
        13,
    ),
    PantryEntry(
        ("mazapan", "mazapán"),
        "latin_market",
        "",
        "Sold at Latin groceries. Do not substitute.",
        2,
    ),
    PantryEntry(
        ("Nido", "powdered milk Nido"),
        "latin_market",
        "",
        "Nestlé Nido sold at Latin groceries and many mainstream stores. Do not substitute.",
        5,
    ),
    PantryEntry(
        ("cajeta",),
        "latin_market",
        "",
        "Sold at Latin groceries. Do not substitute.",
        13,
    ),
    PantryEntry(
        ("tortillas de maíz", "corn tortillas"),
        "mainstream",
        "",
        "Widely available. Do not substitute.",
        654,
    ),
    PantryEntry(
        ("tostadas",),
        "mainstream",
        "",
        "Widely available. Do not substitute.",
        366,
    ),
]

# ---------------------------------------------------------------------------
# Specialty-tier: substitution candidates (ordered by corpus frequency)
# ---------------------------------------------------------------------------

SPECIALTY_ENTRIES: list[PantryEntry] = [
    PantryEntry(
        ("epazote",),
        "specialty",
        "Cilantro plus a pinch of Mexican oregano",
        "Add at the end of cooking; use equal volume. Epazote has a sharper, almost petroleum-like note that no sub fully replicates.",
        830,
    ),
    PantryEntry(
        ("hojas de maíz", "corn husks", "hoja de maíz"),
        "specialty",
        "Parchment paper wrapped in foil, or frozen banana leaves",
        "Soak dried husks if using; banana leaves impart a different aroma but work for wrapping tamales.",
        228,
    ),
    PantryEntry(
        ("masa para tortillas", "masa para tamales", "masa de nixtamal", "fresh masa", "masa fresca"),
        "specialty",
        "Masa harina mixed with warm water (plus lard if the recipe calls for manteca)",
        "About 2 cups masa harina + 1.5 cups warm water per kg of fresh masa. Rest 15 minutes before using. Only substitute when the recipe needs nixtamal dough for tamales, tortillas, or gorditas — not for atole or pozole bolitas.",
        169,
    ),
    PantryEntry(
        ("chaya",),
        "specialty",
        "Spinach or Swiss chard",
        "Blanch briefly; chaya must be cooked. Use equal weight.",
        114,
    ),
    PantryEntry(
        ("queso menonita", "queso Chihuahua", "Chihuahua cheese"),
        "specialty",
        "Monterey Jack or mild cheddar",
        "Prefer the original from a Latin grocery for melting. Use equal weight; Jack melts similarly.",
        108,
    ),
    PantryEntry(
        ("queso Oaxaca", "Oaxaca cheese", "quesillo"),
        "specialty",
        "Low-moisture mozzarella or string cheese",
        "Prefer the original from a Latin grocery. Pull into strings for melting; use equal weight.",
        108,
    ),
    PantryEntry(
        ("hoja santa", "acuyo", "hierba santa"),
        "specialty",
        "Omit, or a tiny pinch of anise seed plus chopped spinach (imperfect)",
        "No true substitute. Hoja santa has a root-beer/anise flavor. Use sparingly if substituting.",
        98,
    ),
    PantryEntry(
        ("pulque", "aguamiel", "semilla de pulque"),
        "specialty",
        "Light lager beer with a pinch of piloncillo, or omit",
        "Adds subtle sweetness and fermentation; beer approximates the liquid volume only.",
        82,
    ),
    PantryEntry(
        ("queso cotija", "cotija"),
        "specialty",
        "Feta or ricotta salata (mainstream fallback only)",
        "Prefer cotija from a Latin grocery. Crumble; cotija is saltier — reduce added salt slightly.",
        79,
    ),
    # --- Not frequency-derived (corpus_count=0); regional fresh cheeses ---
    PantryEntry(
        ("queso añejo", "queso anejo", "queso añejo enchilado", "queso anejo enchilado"),
        "specialty",
        "Cotija, or Pecorino/Romano (mainstream fallback)",
        "Aged and salty; crumble over finished dishes. Reduce added salt slightly. Prefer from a Latin grocery.",
        0,
    ),
    PantryEntry(
        ("queso asadero",),
        "specialty",
        "Monterey Jack or low-moisture mozzarella",
        "Melting cheese for quesadillas and gratins. Prefer from a Latin grocery. Use equal weight.",
        0,
    ),
    PantryEntry(
        ("queso de bola", "Edam", "queso Edam"),
        "specialty",
        "Edam or Gouda",
        "Ball cheese used in Yucatecan and holiday dishes. Prefer from a Latin grocery. Use equal weight.",
        0,
    ),
    PantryEntry(
        ("queso doble crema",),
        "specialty",
        "Cream cheese loosened with a little crema or sour cream",
        "Soft, spreadable melting cheese. Prefer from a Latin grocery. Use equal weight.",
        0,
    ),
    PantryEntry(
        ("queso adobera",),
        "specialty",
        "Monterey Jack (melting) or queso fresco (fresh)",
        "Use Jack for melting applications; queso fresco when the cheese stays intact. Prefer from a Latin grocery.",
        0,
    ),
    # --- Not frequency-derived (corpus_count=0); Mexico-only prepared seasoning kits ---
    PantryEntry(
        (
            "MAGGI Jugoso al Sartén",
            "JUGOSO AL SARTÉN",
            "JUICY PAN",
            "Pastor seasoning sheets",
            "Hoja con Sazonador MAGGI",
            "Sazonador para Pollo Asado",
        ),
        "specialty",
        "Make the matching adobo from scratch and cook the seasoned protein in a lightly oiled pan or foil packet",
        "Mexico-only pre-seasoned cooking sheets with no US/Canada equivalent. For al pastor: achiote paste + guajillo + pineapple juice + vinegar marinade; season protein, then pan-cook as directed.",
        0,
    ),
    PantryEntry(
        ("xoconostle",),
        "specialty",
        "Green tomatillo plus extra lime juice",
        "Xoconostle is tart and firm; tomatillo plus lime approximates the sourness. Use equal weight.",
        50,
    ),
    PantryEntry(
        ("huitlacoche", "corn smut"),
        "specialty",
        "Sautéed cremini or button mushrooms with fresh corn kernels and a pinch of epazote",
        "Frozen huitlacoche is sometimes available at Latin groceries — prefer that over this sub. Use equal volume.",
        47,
    ),
    PantryEntry(
        ("tequesquite",),
        "specialty",
        "A tiny pinch of baking soda",
        "Tequesquite is a natural leavening/alkali for nixtamal. Use no more than 1/4 tsp per kg of masa.",
        39,
    ),
    PantryEntry(
        ("chilhuacle", "chile costeño", "chile de agua", "chile manzano", "chile güero"),
        "specialty",
        "Closest match by heat and color from the guide notes below",
        "Chilhuacle negro → mulato; chilhuacle rojo → ancho; costeño → cascabel; de agua → jalapeño; manzano → habanero (much hotter).",
        36,
    ),
    PantryEntry(
        ("maíz cacahuazintle", "cacahuazintle", "hominy"),
        "specialty",
        "Canned hominy, rinsed",
        "Use equal weight; canned hominy is softer — add later in cooking if the recipe requires long simmer.",
        31,
    ),
    PantryEntry(
        ("hoja de aguacate", "avocado leaf"),
        "specialty",
        "Bay leaf (flavor differs — note limitation)",
        "Avocado leaves have an anise note; bay leaf is a rough stand-in. One leaf per leaf.",
        25,
    ),
    PantryEntry(
        ("jocoque",),
        "specialty",
        "Greek yogurt thinned with a little heavy cream",
        "Tangy cultured dairy; use equal volume.",
        18,
    ),
    PantryEntry(
        ("huauzontle", "huazontle"),
        "specialty",
        "Broccoli rabe or spinach stems, blanched",
        "Mildly bitter green; use equal weight and cook until tender.",
        16,
    ),
    PantryEntry(
        ("queso ranchero",),
        "specialty",
        "Queso fresco or farmer's cheese",
        "Prefer from a Latin grocery. Crumble; use equal weight.",
        17,
    ),
    PantryEntry(
        ("flor de calabaza", "squash blossom"),
        "specialty",
        "Zucchini slices or spinach (when blossoms unavailable)",
        "Fresh blossoms appear at Latin groceries in season. Use equal volume of zucchini.",
        68,
    ),
    PantryEntry(
        ("verdolagas", "purslane"),
        "specialty",
        "Spinach or watercress",
        "Verdolagas are slightly sour; add a squeeze of lime. Use equal weight.",
        35,
    ),
]


def _render_entry(entry: PantryEntry) -> str:
    names = ", ".join(f"`{n}`" for n in entry.names)
    sub = entry.substitute or "*(do not substitute)*"
    return f"- **{names}** ({entry.availability}): {sub}. {entry.notes}"


def format_pantry_substitutions_prompt_section() -> str:
    """Render the pantry sourcing guide for the substitution LLM prompt."""
    lines = [
        "### Do not substitute (Latin-market / mainstream staples)",
        "",
        "These appear frequently in the corpus and are sold at Latin/Hispanic groceries",
        "nationwide. **Return no entry for these.** Also skip generic Western staples",
        "(cream cheese, vanilla, Oreos, etc.) and brand-name products (La Costeña, Herdez, Tajín).",
        "",
    ]
    for entry in SKIP_ENTRIES:
        lines.append(_render_entry(entry))

    lines.extend(
        [
            "",
            "### Specialty items — substitute only when unavailable at Latin groceries",
            "",
            "Ordered by frequency in the recipe corpus. Emit **one entry per specialty ingredient**",
            "found in the recipe; do not collapse multiple items into one entry.",
            "",
        ]
    )
    for entry in SPECIALTY_ENTRIES:
        lines.append(_render_entry(entry))

    lines.extend(
        [
            "",
            "### Masa disambiguation",
            "",
            "- `masa harina` / `Maseca` → Latin-market item; **do not substitute**.",
            "- `masa para tortillas`, `masa para tamales`, `masa de nixtamal`, `masa fresca` →",
            "  specialty; substitute with masa harina + water (+ lard if recipe uses manteca).",
            "- Generic `masa de maíz` in atole, pozole bolitas, or beverage contexts → **do not substitute**",
            "  unless the recipe clearly requires fresh nixtamal dough.",
        ]
    )

    return "\n".join(lines)
