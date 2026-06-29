"""Canonical health and nutrition tag vocabulary for recipe tagging.

Tagging runs on Spanish text, so each term is a ``(slug, es, en)`` tuple.
The tagging stage emits Spanish labels; the localize stage maps them to English
via the shared vocabulary registry in ``tag_vocabularies.py``.
"""

from __future__ import annotations

HealthNutritionTerm = tuple[str, str, str]  # (slug, es, en)

HEALTH_NUTRITION_CATEGORIES: dict[str, list[HealthNutritionTerm]] = {
    "Macronutrients": [
        ("high-protein", "Alto en Proteína", "High Protein"),
        ("extra-high-protein", "Extra Alto en Proteína (30g+ por porción)", "Extra High Protein (30g+ per serving)"),
        ("moderate-protein", "Proteína Moderada", "Moderate Protein"),
        ("low-protein", "Bajo en Proteína", "Low Protein"),
        ("high-fat", "Alto en Grasa", "High Fat"),
        ("low-fat", "Bajo en Grasa", "Low Fat"),
        ("fat-free", "Sin Grasa", "Fat-Free"),
        ("healthy-fats", "Grasas Saludables", "Healthy Fats"),
        ("high-carbohydrate", "Alto en Carbohidratos", "High Carbohydrate"),
        ("low-carb", "Bajo en Carbohidratos", "Low Carb"),
        ("very-low-carb", "Muy Bajo en Carbohidratos", "Very Low Carb"),
        ("keto-friendly", "Apto para Keto", "Keto-Friendly"),
        ("moderate-carb", "Carbohidratos Moderados", "Moderate Carb"),
        ("high-fiber", "Alto en Fibra", "High Fiber"),
        ("excellent-fiber-source", "Excelente Fuente de Fibra", "Excellent Fiber Source"),
        ("low-fiber", "Bajo en Fibra", "Low Fiber"),
        ("high-calories", "Alto en Calorías", "High Calories"),
        ("low-calorie", "Bajo en Calorías", "Low Calorie"),
        ("calorie-dense", "Denso en Calorías", "Calorie Dense"),
        ("light-meal", "Comida Ligera", "Light Meal"),
    ],
    "Sugar": [
        ("no-added-sugar", "Sin Azúcar Añadida", "No Added Sugar"),
        ("sugar-free", "Sin Azúcar", "Sugar-Free"),
        ("low-sugar", "Bajo en Azúcar", "Low Sugar"),
        ("naturally-sweetened", "Endulzado Naturalmente", "Naturally Sweetened"),
        ("low-glycemic", "Bajo Índice Glucémico", "Low Glycemic"),
        ("diabetic-friendly", "Apto para Diabéticos", "Diabetic-Friendly"),
        ("reduced-sugar", "Azúcar Reducida", "Reduced Sugar"),
    ],
    "Sodium": [
        ("low-sodium", "Bajo en Sodio", "Low Sodium"),
        ("reduced-sodium", "Sodio Reducido", "Reduced Sodium"),
        ("dash-friendly", "Apto para DASH", "DASH Friendly"),
    ],
    "Cholesterol & Fat Quality": [
        ("low-cholesterol", "Bajo en Colesterol", "Low Cholesterol"),
        ("cholesterol-free", "Sin Colesterol", "Cholesterol Free"),
        ("low-saturated-fat", "Bajo en Grasa Saturada", "Low Saturated Fat"),
        ("trans-fat-free", "Sin Grasas Trans", "Trans Fat Free"),
        ("rich-in-omega-3", "Rico en Omega-3", "Rich in Omega-3"),
        ("rich-in-monounsaturated-fats", "Rico en Grasas Monoinsaturadas", "Rich in Monounsaturated Fats"),
        ("rich-in-polyunsaturated-fats", "Rico en Grasas Poliinsaturadas", "Rich in Polyunsaturated Fats"),
    ],
    "Vitamins & Minerals": [
        ("high-iron", "Alto en Hierro", "High Iron"),
        ("high-calcium", "Alto en Calcio", "High Calcium"),
        ("high-potassium", "Alto en Potasio", "High Potassium"),
        ("high-magnesium", "Alto en Magnesio", "High Magnesium"),
        ("high-zinc", "Alto en Zinc", "High Zinc"),
        ("high-folate", "Alto en Folato", "High Folate"),
        ("high-vitamin-a", "Alto en Vitamina A", "High Vitamin A"),
        ("high-vitamin-b12", "Alto en Vitamina B12", "High Vitamin B12"),
        ("high-vitamin-c", "Alto en Vitamina C", "High Vitamin C"),
        ("high-vitamin-d", "Alto en Vitamina D", "High Vitamin D"),
        ("high-vitamin-e", "Alto en Vitamina E", "High Vitamin E"),
        ("high-vitamin-k", "Alto en Vitamina K", "High Vitamin K"),
        ("selenium-rich", "Rico en Selenio", "Selenium Rich"),
        ("antioxidant-rich", "Rico en Antioxidantes", "Antioxidant Rich"),
    ],
    "Functional Nutrition": [
        ("anti-inflammatory", "Antiinflamatorio", "Anti-Inflammatory"),
        ("gut-healthy", "Saludable para el Intestino", "Gut Healthy"),
        ("high-probiotics", "Alto en Probióticos", "High Probiotics"),
        ("high-prebiotics", "Alto en Prebióticos", "High Prebiotics"),
        ("immune-supporting", "Apoyo Inmunológico", "Immune Supporting"),
        ("brain-healthy", "Saludable para el Cerebro", "Brain Healthy"),
        ("bone-healthy", "Saludable para los Huesos", "Bone Healthy"),
        ("eye-healthy", "Saludable para los Ojos", "Eye Healthy"),
        ("heart-healthy", "Saludable para el Corazón", "Heart Healthy"),
        ("liver-friendly", "Amigable con el Hígado", "Liver Friendly"),
        ("kidney-friendly", "Amigable con los Riñones", "Kidney Friendly"),
        ("energy-boosting", "Energizante", "Energy Boosting"),
        ("recovery-meal", "Comida de Recuperación", "Recovery Meal"),
        ("hydrating", "Hidratante", "Hydrating"),
    ],
    "Weight Goals": [
        ("weight-loss", "Pérdida de Peso", "Weight Loss"),
        ("weight-maintenance", "Mantenimiento de Peso", "Weight Maintenance"),
        ("weight-gain", "Aumento de Peso", "Weight Gain"),
        ("lean-muscle", "Músculo Magro", "Lean Muscle"),
        ("bulking", "Volumen Muscular", "Bulking"),
        ("cutting", "Definición Muscular", "Cutting"),
        ("high-satiety", "Alta Saciedad", "High Satiety"),
        ("filling-meal", "Comida Saciante", "Filling Meal"),
    ],
    "Sports Nutrition": [
        ("post-workout", "Post-Entrenamiento", "Post Workout"),
        ("pre-workout", "Pre-Entrenamiento", "Pre Workout"),
        ("endurance-fuel", "Combustible de Resistencia", "Endurance Fuel"),
        ("high-electrolytes", "Alto en Electrolitos", "High Electrolytes"),
        ("high-protein-snack", "Botana Alta en Proteína", "High Protein Snack"),
        ("recovery-food", "Alimento de Recuperación", "Recovery Food"),
    ],
    "Special Medical Diets": [
        ("prediabetes-friendly", "Apto para Prediabetes", "Prediabetes Friendly"),
        ("gerd-friendly", "Apto para GERD", "GERD Friendly"),
        ("ibs-friendly", "Apto para SII", "IBS Friendly"),
        ("fodmap-friendly", "Apto para FODMAP", "FODMAP Friendly"),
        ("low-fodmap", "Bajo en FODMAP", "Low FODMAP"),
        ("renal-diet", "Dieta Renal", "Renal Diet"),
        ("bariatric-friendly", "Apto para Bariátrica", "Bariatric Friendly"),
        ("pcos-friendly", "Apto para SOP", "PCOS Friendly"),
        ("pregnancy-friendly", "Apto para Embarazo", "Pregnancy Friendly"),
        ("breastfeeding-friendly", "Apto para Lactancia", "Breastfeeding Friendly"),
    ],
    "Ingredient Quality": [
        ("whole-foods", "Alimentos Integrales", "Whole Foods"),
        ("minimally-processed", "Mínimamente Procesado", "Minimally Processed"),
        ("ultra-processed-free", "Sin Ultraprocesados", "Ultra-Processed Free"),
        ("clean-eating", "Alimentación Limpia", "Clean Eating"),
        ("organic-ingredients", "Ingredientes Orgánicos", "Organic Ingredients"),
        ("seasonal-ingredients", "Ingredientes de Temporada", "Seasonal Ingredients"),
        ("fresh-ingredients", "Ingredientes Frescos", "Fresh Ingredients"),
    ],
    "Plant-Based Quality": [
        ("plant-protein", "Proteína Vegetal", "Plant Protein"),
        ("animal-protein", "Proteína Animal", "Animal Protein"),
        ("legume-based", "A Base de Legumbres", "Legume Based"),
        ("whole-grain", "Grano Integral", "Whole Grain"),
        ("ancient-grains", "Granos Antiguos", "Ancient Grains"),
        ("healthy-oils", "Aceites Saludables", "Healthy Oils"),
        ("olive-oil-based", "A Base de Aceite de Oliva", "Olive Oil Based"),
    ],
    "Nutrient Density": [
        ("nutrient-dense", "Denso en Nutrientes", "Nutrient Dense"),
        ("superfood", "Superalimento", "Superfood"),
        ("high-antioxidants", "Alto en Antioxidantes", "High Antioxidants"),
        ("high-polyphenols", "Alto en Polifenoles", "High Polyphenols"),
    ],
    "Meal Function": [
        ("breakfast-fuel", "Combustible para Desayuno", "Breakfast Fuel"),
        ("high-energy-breakfast", "Desayuno de Alta Energía", "High Energy Breakfast"),
        ("light-lunch", "Comida del Mediodía Ligera", "Light Lunch"),
        ("filling-dinner", "Cena Saciante", "Filling Dinner"),
        ("healthy-snack", "Botana Saludable", "Healthy Snack"),
        ("healthy-dessert", "Postre Saludable", "Healthy Dessert"),
    ],
}

# Flat list for vocabulary registry and lookups.
HEALTH_NUTRITION: list[HealthNutritionTerm] = [term for terms in HEALTH_NUTRITION_CATEGORIES.values() for term in terms]

VALID_HEALTH_NUTRITION_ES: set[str] = {es for _, es, _ in HEALTH_NUTRITION}
VALID_HEALTH_NUTRITION_EN: set[str] = {en for _, _, en in HEALTH_NUTRITION}

# Backward-compatible alias (English labels).
VALID_HEALTH_NUTRITION: set[str] = VALID_HEALTH_NUTRITION_EN


def format_health_nutrition_prompt_section() -> str:
    """Render the health_nutrition taxonomy and selection rules for the LLM prompt."""
    lines = [
        "16. **health_nutrition**: Atributos de salud, fitness y nutrición.",
        "",
        "    Usa **exactamente** las cadenas canónicas en **español** del vocabulario abajo (sin etiquetas libres).",
        "    Aplica todas las etiquetas claramente respaldadas por ingredientes, método de cocción y contexto —",
        "    típicamente **3–10 etiquetas**; evita sobre-etiquetar.",
        "    Infiere solo de ingredientes y contexto (sin calcular macros).",
        "    Prefiere el nivel más fuerte aplicable dentro de una escala (p. ej. `Extra Alto en Proteína` sobre",
        "    `Alto en Proteína`, `Muy Bajo en Carbohidratos` sobre `Bajo en Carbohidratos`) — no apliques niveles conflictivos.",
        "    **Límite con `dietary`**: `dietary` cubre etiquetas de estilo de vida/alérgenos (`Vegetariano`,",
        "    `Sin Gluten`, etc.); `health_nutrition` cubre perfil nutricional y atributos de salud.",
        "    No dupliques etiquetas dietéticas con guión (`Bajo en Carbohidratos`, `Alto en Proteína`) aquí —",
        "    usa las etiquetas de perfil nutricional del vocabulario abajo cuando aplique.",
        "",
        "    **Vocabulario por categoría:**",
    ]

    for category, terms in HEALTH_NUTRITION_CATEGORIES.items():
        tag_list = ", ".join(f"`{es}`" for _, es, _ in terms)
        lines.append(f"    - **{category}**: {tag_list}")

    return "\n".join(lines)
