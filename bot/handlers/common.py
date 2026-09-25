
from aiogram.types import Message

from bot.database import Database
from bot.keyboards.menus import main_menu
from bot.services.formatters import format_home


async def require_user(message: Message, db: Database):
    user = await db.get_user(message.from_user.id)
    if not user or not user["calories_norm"]:
        await message.answer(
            "Сначала пройдите регистрацию: отправьте /start"
        )
        return None
    return user


async def send_home(message: Message, db: Database) -> None:
    user = await require_user(message, db)
    if not user:
        return
    totals = await db.day_totals(message.from_user.id)
    meals = await db.get_meals_for_day(message.from_user.id)
    text = format_home(user, totals, meals)
    await message.answer(text, reply_markup=main_menu(), parse_mode="HTML")
