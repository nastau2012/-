
from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from bot.database import Database
from bot.handlers.common import require_user
from bot.keyboards.menus import main_menu, stats_menu_kb
from bot.services.formatters import format_period, format_stats_day
from bot.services.recommendations import generate_recommendations

router = Router(name="stats")


@router.message(F.text == "📊 Статистика")
async def stats_home(message: Message, db: Database) -> None:
    user = await require_user(message, db)
    if not user:
        return
    totals = await db.day_totals(message.from_user.id)
    await message.answer(
        format_stats_day(user, totals),
        reply_markup=stats_menu_kb(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "stats:today")
async def stats_today(callback: CallbackQuery, db: Database) -> None:
    user = await db.get_user(callback.from_user.id)
    totals = await db.day_totals(callback.from_user.id)
    await callback.message.edit_text(
        format_stats_day(user, totals),
        reply_markup=stats_menu_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "stats:week")
async def stats_week(callback: CallbackQuery, db: Database) -> None:
    rows = await db.period_daily_calories(callback.from_user.id, days=7)
    await callback.message.edit_text(
        format_period(rows, "Неделя"),
        reply_markup=stats_menu_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "stats:month")
async def stats_month(callback: CallbackQuery, db: Database) -> None:
    rows = await db.period_daily_calories(callback.from_user.id, days=30)
    await callback.message.edit_text(
        format_period(rows, "Месяц"),
        reply_markup=stats_menu_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "stats:weight")
async def stats_weight(callback: CallbackQuery, db: Database) -> None:
    logs = await db.get_weight_history(callback.from_user.id, limit=14)
    if not logs:
        await callback.answer("Нет замеров веса", show_alert=True)
        return
    lines = ["⚖️ <b>Динамика веса</b>", ""]
    for log in reversed(list(logs)):
        lines.append(f"{log['logged_at'][:10]} — {log['weight']} кг")
    if len(logs) >= 2:
        delta = float(logs[0]["weight"]) - float(logs[-1]["weight"])
        lines.append(f"\nИзменение: <b>{delta:+.1f} кг</b>")
    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=stats_menu_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(F.text == "💡 Рекомендации")
async def recommendations_home(message: Message, db: Database) -> None:
    user = await require_user(message, db)
    if not user:
        return
    totals = await db.day_totals(message.from_user.id)
    meals = await db.get_meals_for_day(message.from_user.id)
    tips = generate_recommendations(user, totals, meals)
    for tip in tips:
        await db.save_recommendation(message.from_user.id, tip)
    text = "💡 <b>Рекомендации на сегодня</b>\n\n" + "\n\n".join(tips)
    await message.answer(text, parse_mode="HTML", reply_markup=main_menu())