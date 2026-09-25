
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Mapping, Sequence

from bot.config import ACTIVITY_LABELS, GENDER_LABELS, GOAL_LABELS, MEAL_LABELS


WEEKDAYS_RU = (
    "Понедельник",
    "Вторник",
    "Среда",
    "Четверг",
    "Пятница",
    "Суббота",
    "Воскресенье",
)


def progress_bar(current: float, target: float, length: int = 10) -> str:
    if target <= 0:
        return "□" * length
    ratio = max(0.0, min(1.0, current / target))
    filled = int(round(ratio * length))
    return "■" * filled + "□" * (length - filled)


def pct(current: float, target: float) -> int:
    if target <= 0:
        return 0
    return int(round(min(999, current / target * 100)))


def circle_progress(percent: int) -> str:
    blocks = ["◔", "◑", "◕", "●"]
    if percent <= 0:
        return "○"
    if percent >= 100:
        return "●"
    idx = min(3, percent // 25)
    return blocks[idx]


def today_header() -> str:
    today = date.today()
    weekday = WEEKDAYS_RU[today.weekday()]
    return f"Сегодня, {weekday}"


def format_home(
    user: Mapping[str, Any],
    totals: Mapping[str, float],
    recent_meals: Sequence[Mapping[str, Any]],
) -> str:
    cal_norm = float(user["calories_norm"] or 0)
    p_norm = float(user["protein_norm"] or 0)
    f_norm = float(user["fat_norm"] or 0)
    c_norm = float(user["carbs_norm"] or 0)

    cal = totals["calories"]
    protein = totals["protein"]
    fat = totals["fat"]
    carbs = totals["carbs"]

    cal_pct = pct(cal, cal_norm)
    left = max(0, round(cal_norm - cal))
    mark = "✅" if cal_pct <= 100 else "⚠️"

    lines = [
        "🔥 <b>Калькулятор Калорий</b>",
        today_header(),
        "",
        f"{circle_progress(cal_pct)} <b>Калории</b>",
        f"<b>{cal_pct}%</b>",
        f"{round(cal)} / {round(cal_norm)} ккал {mark}",
        f"Осталось: <b>{left} ккал</b>",
        "",
        f"🍗 Белки: {progress_bar(protein, p_norm)} {pct(protein, p_norm)}%",
        f"    {round(protein)} / {round(p_norm)} г",
        f"🥑 Жиры: {progress_bar(fat, f_norm)} {pct(fat, f_norm)}%",
        f"    {round(fat)} / {round(f_norm)} г",
        f"🍝 Углеводы: {progress_bar(carbs, c_norm)} {pct(carbs, c_norm)}%",
        f"    {round(carbs)} / {round(c_norm)} г",
        "",
        "<b>Последние приёмы пищи</b>",
    ]

    if not recent_meals:
        lines.append("Пока пусто — добавьте приём пищи в разделе «Дневник».")
    else:
        for meal in list(recent_meals)[-5:][::-1]:
            meal_label = MEAL_LABELS.get(meal["meal_type"], meal["meal_type"])
            lines.append(
                f"• {meal_label}: {meal['product_name']} — "
                f"<b>{round(meal['calories'])} ккал</b>"
            )

    return "\n".join(lines)


def format_profile(user: Mapping[str, Any]) -> str:
    return "\n".join(
        [
            "👤 <b>Профиль</b>",
            "",
            f"Пол: {GENDER_LABELS.get(user['gender'], '—')}",
            f"Возраст: {user['age']} лет",
            f"Рост: {user['height']} см",
            f"Вес: {user['weight']} кг",
            f"Активность: {ACTIVITY_LABELS.get(user['activity'], '—')}",
            f"Цель: {GOAL_LABELS.get(user['goal'], '—')}",
            "",
            "📐 <b>Суточная норма</b>",
            f"Калории: <b>{round(user['calories_norm'])} ккал</b>",
            f"Белки: {user['protein_norm']} г",
            f"Жиры: {user['fat_norm']} г",
            f"Углеводы: {user['carbs_norm']} г",
            "",
            "<i>Формула Миффлина — Сан-Жеора</i>",
        ]
    )


def format_diary(meals: Sequence[Mapping[str, Any]], day: date | None = None) -> str:
    day = day or date.today()
    lines = [f"📖 <b>Дневник</b> — {day.strftime('%d.%m.%Y')}", ""]
    if not meals:
        lines.append("Записей за этот день нет.")
        return "\n".join(lines)

    total = 0.0
    for meal in meals:
        label = MEAL_LABELS.get(meal["meal_type"], meal["meal_type"])
        try:
            t = datetime.fromisoformat(meal["eaten_at"]).strftime("%H:%M")
        except ValueError:
            t = ""
        lines.append(
            f"#{meal['id']} {label} {t}\n"
            f"  {meal['product_name']} — {meal['weight_g']} г\n"
            f"  🔥 {round(meal['calories'])} ккал | "
            f"Б {meal['protein']} Ж {meal['fat']} У {meal['carbs']}"
        )
        total += float(meal["calories"])
    lines.append("")
    lines.append(f"<b>Итого:</b> {round(total)} ккал")
    return "\n".join(lines)


def format_stats_day(user: Mapping[str, Any], totals: Mapping[str, float]) -> str:
    cal_norm = float(user["calories_norm"] or 1)
    lines = [
        "📊 <b>Статистика за сегодня</b>",
        "",
        f"Калории: {round(totals['calories'])} / {round(cal_norm)} "
        f"({pct(totals['calories'], cal_norm)}%)",
        f"{progress_bar(totals['calories'], cal_norm)}",
        "",
        f"Белки: {round(totals['protein'])} / {user['protein_norm']} г",
        f"Жиры: {round(totals['fat'])} / {user['fat_norm']} г",
        f"Углеводы: {round(totals['carbs'])} / {user['carbs_norm']} г",
    ]
    ratio = totals["calories"] / cal_norm if cal_norm else 0
    if ratio < 0.7:
        lines.append("\n💬 Рацион ниже нормы — не забывайте про приёмы пищи.")
    elif ratio > 1.1:
        lines.append("\n⚠️ Калории выше нормы — скорректируйте ужин/перекусы.")
    else:
        lines.append("\n✅ Хороший баланс калорий на сегодня!")
    return "\n".join(lines)


def format_period(rows: Sequence[Mapping[str, Any]], title: str) -> str:
    lines = [f"📊 <b>{title}</b>", ""]
    if not rows:
        lines.append("Недостаточно данных за период.")
        return "\n".join(lines)
    for row in rows:
        day = row["day"]
        lines.append(f"{day}: {round(row['calories'])} ккал")
    avg = sum(float(r["calories"]) for r in rows) / len(rows)
    lines.append("")
    lines.append(f"Среднее: <b>{round(avg)} ккал/день</b>")
    return "\n".join(lines)


def format_product(product: Mapping[str, Any]) -> str:
    return (
        f"🍽 <b>{product['name']}</b>\n"
        f"Категория: {product['category']}\n"
        f"На 100 г: {product['calories']} ккал | "
        f"Б {product['protein']} Ж {product['fat']} У {product['carbs']}"
    )
