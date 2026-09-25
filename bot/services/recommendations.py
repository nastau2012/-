from __future__ import annotations

from collections import Counter
from typing import Any, Mapping, Sequence


def generate_recommendations(
    user: Mapping[str, Any],
    totals: Mapping[str, float],
    meals: Sequence[Mapping[str, Any]],
) -> list[str]:
    tips: list[str] = []
    cal_norm = float(user["calories_norm"] or 1)
    p_norm = float(user["protein_norm"] or 1)
    f_norm = float(user["fat_norm"] or 1)
    c_norm = float(user["carbs_norm"] or 1)

    cal = totals["calories"]
    protein = totals["protein"]
    fat = totals["fat"]
    carbs = totals["carbs"]

    if cal < cal_norm * 0.7 and meals:
        tips.append(
            "📉 Калорий заметно меньше нормы. Добавьте полноценный приём пищи, "
            "чтобы не срываться вечером."
        )
    elif cal > cal_norm * 1.15:
        tips.append(
            "⚠️ Сегодня превышение калорий. Уменьшите порции перекусов "
            "или выберите более лёгкий ужин."
        )

    if protein < p_norm * 0.7:
        tips.append(
            "🍗 Недостаток белка. Добавьте курицу, творог, яйца или рыбу."
        )
    if fat > f_norm * 1.2:
        tips.append(
            "🥑 Жиров больше нормы. Сократите масла, орехи и жареные блюда."
        )
    if carbs > c_norm * 1.2:
        tips.append(
            "🍝 Углеводов больше цели. Сместите акцент на овощи и белковые продукты."
        )

    meal_types = Counter(m["meal_type"] for m in meals)
    if meal_types and "breakfast" not in meal_types:
        tips.append("🌅 Вы пропустили завтрак. Регулярные приёмы пищи стабилизируют аппетит.")

    categories_hint = " ".join(m["product_name"].lower() for m in meals)
    veg_keywords = ("огурец", "помидор", "капуст", "брокколи", "морков", "салат", "овощ")
    if meals and not any(k in categories_hint for k in veg_keywords):
        tips.append(
            "🥦 В рационе мало овощей. Добавьте салат или гарнир из овощей."
        )

    if not tips and meals:
        tips.append(
            "🌟 Отличная работа! Вы держите рацион под контролем. Так держать!"
        )
    elif not meals:
        tips.append(
            "✍️ Начните день с записи завтрака — так проще уложиться в норму."
        )

    goal = user["goal"]
    if goal == "lose" and cal > cal_norm:
        tips.append("🎯 Для похудения важен устойчивый дефицит — постарайтесь уложиться в норму.")
    elif goal == "gain" and protein < p_norm:
        tips.append("💪 Для набора массы увеличьте белок до целевого уровня.")

    return tips[:5]
