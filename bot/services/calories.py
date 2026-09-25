
from __future__ import annotations

from bot.config import ACTIVITY_FACTORS


def calc_bmr(gender: str, weight: float, height: float, age: int) -> float:
    base = 10 * weight + 6.25 * height - 5 * age
    if gender == "male":
        return base + 5
    return base - 161


def calc_tdee(bmr: float, activity: str) -> float:
    factor = ACTIVITY_FACTORS.get(activity, 1.2)
    return bmr * factor


def adjust_for_goal(tdee: float, goal: str) -> float:
    if goal == "lose":
        return tdee * 0.85
    if goal == "gain":
        return tdee * 1.125
    return tdee


def calc_macros(calories: float, weight: float, goal: str) -> dict[str, float]:
    if goal == "lose":
        protein_g = weight * 1.8
        fat_g = (calories * 0.25) / 9
        carbs_g = (calories - protein_g * 4 - fat_g * 9) / 4
    elif goal == "gain":
        protein_g = weight * 2.0
        carbs_g = (calories * 0.55) / 4
        fat_g = (calories - protein_g * 4 - carbs_g * 4) / 9
    else:
        protein_g = weight * 1.6
        fat_g = (calories * 0.30) / 9
        carbs_g = (calories - protein_g * 4 - fat_g * 9) / 4

    return {
        "protein": max(0, round(protein_g, 1)),
        "fat": max(0, round(fat_g, 1)),
        "carbs": max(0, round(carbs_g, 1)),
    }


def calc_daily_norms(
    gender: str,
    age: int,
    height: float,
    weight: float,
    activity: str,
    goal: str,
) -> dict[str, float]:
    bmr = calc_bmr(gender, weight, height, age)
    tdee = calc_tdee(bmr, activity)
    calories = round(adjust_for_goal(tdee, goal))
    macros = calc_macros(calories, weight, goal)
    return {
        "bmr": round(bmr),
        "tdee": round(tdee),
        "calories": calories,
        **macros,
    }


def scale_nutrients(
    calories_per_100: float,
    protein_per_100: float,
    fat_per_100: float,
    carbs_per_100: float,
    weight_g: float,
) -> dict[str, float]:
    k = weight_g / 100.0
    return {
        "calories": round(calories_per_100 * k, 1),
        "protein": round(protein_per_100 * k, 1),
        "fat": round(fat_per_100 * k, 1),
        "carbs": round(carbs_per_100 * k, 1),
    }
