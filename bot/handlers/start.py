
from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.config import WEBAPP_URL
from bot.database import Database
from bot.handlers.common import send_home
from bot.keyboards.menus import (
    activity_kb,
    gender_kb,
    goal_kb,
    main_menu,
    webapp_keyboard,
)
from bot.services.calories import calc_daily_norms
from bot.states import Registration

router = Router(name="start")


def _start_text(name: str) -> str:
    base = (
        f"🔥 <b>Калькулятор Калорий</b>\n\n"
        f"Привет, {name}!\n"
        f"Ведите дневник питания в удобном окне приложения."
    )
    if WEBAPP_URL:
        return base + "\n\nНажмите кнопку ниже, чтобы открыть Mini App 👇"
    return (
        base
        + "\n\n⚠️ Mini App пока не настроен: укажите <code>WEBAPP_URL</code> в .env "
        "(HTTPS через ngrok). Пока доступно текстовое меню."
    )


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, db: Database) -> None:
    await state.clear()
    await db.upsert_user(message.from_user.id)
    kb = webapp_keyboard()
    await message.answer(
        _start_text(message.from_user.first_name or "друг"),
        reply_markup=kb or main_menu(),
        parse_mode="HTML",
    )
    await message.answer("Меню:", reply_markup=main_menu())

    # Если профиль не заполнен — предложить регистрацию в чате (или в Mini App)
    if not await db.is_registered(message.from_user.id):
        if not WEBAPP_URL:
            await message.answer(
                "Давайте настроим профиль в чате. Укажите пол:",
                reply_markup=gender_kb(),
            )
            await state.set_state(Registration.gender)
        else:
            await message.answer(
                "Профиль можно заполнить прямо в приложении "
                "(откроется форма при первом входе)."
            )


@router.callback_query(Registration.gender, F.data.startswith("reg:gender:"))
async def reg_gender(callback: CallbackQuery, state: FSMContext) -> None:
    gender = callback.data.split(":")[-1]
    await state.update_data(gender=gender)
    await callback.message.edit_text("Введите возраст (полных лет):")
    await state.set_state(Registration.age)
    await callback.answer()


@router.message(Registration.age)
async def reg_age(message: Message, state: FSMContext) -> None:
    try:
        age = int(message.text.strip())
        if not 10 <= age <= 100:
            raise ValueError
    except (TypeError, ValueError):
        await message.answer("Введите возраст числом от 10 до 100.")
        return
    await state.update_data(age=age)
    await message.answer("Введите рост в сантиметрах (например, 175):")
    await state.set_state(Registration.height)


@router.message(Registration.height)
async def reg_height(message: Message, state: FSMContext) -> None:
    try:
        height = float(message.text.strip().replace(",", "."))
        if not 100 <= height <= 250:
            raise ValueError
    except (TypeError, ValueError):
        await message.answer("Введите рост числом от 100 до 250 см.")
        return
    await state.update_data(height=height)
    await message.answer("Введите вес в килограммах (например, 70.5):")
    await state.set_state(Registration.weight)


@router.message(Registration.weight)
async def reg_weight(message: Message, state: FSMContext, db: Database) -> None:
    try:
        weight = float(message.text.strip().replace(",", "."))
        if not 30 <= weight <= 300:
            raise ValueError
    except (TypeError, ValueError):
        await message.answer("Введите вес числом от 30 до 300 кг.")
        return
    await state.update_data(weight=weight)
    await db.add_weight_log(message.from_user.id, weight)
    await message.answer("Выберите уровень активности:", reply_markup=activity_kb())
    await state.set_state(Registration.activity)


@router.callback_query(Registration.activity, F.data.startswith("reg:activity:"))
async def reg_activity(callback: CallbackQuery, state: FSMContext) -> None:
    activity = callback.data.split(":")[-1]
    await state.update_data(activity=activity)
    await callback.message.edit_text("Выберите цель:", reply_markup=goal_kb())
    await state.set_state(Registration.goal)
    await callback.answer()


@router.callback_query(Registration.goal, F.data.startswith("reg:goal:"))
async def reg_goal(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    goal = callback.data.split(":")[-1]
    data = await state.get_data()
    norms = calc_daily_norms(
        gender=data["gender"],
        age=data["age"],
        height=data["height"],
        weight=data["weight"],
        activity=data["activity"],
        goal=goal,
    )
    await db.upsert_user(
        callback.from_user.id,
        gender=data["gender"],
        age=data["age"],
        height=data["height"],
        weight=data["weight"],
        activity=data["activity"],
        goal=goal,
        calories_norm=norms["calories"],
        protein_norm=norms["protein"],
        fat_norm=norms["fat"],
        carbs_norm=norms["carbs"],
    )
    await state.clear()
    await callback.message.edit_text(
        f"✅ Профиль сохранён!\n\n"
        f"Суточная норма: <b>{norms['calories']} ккал</b>\n"
        f"Белки: {norms['protein']} г | Жиры: {norms['fat']} г | "
        f"Углеводы: {norms['carbs']} г\n\n"
        f"(BMR {norms['bmr']} → TDEE {norms['tdee']} с учётом цели)",
        parse_mode="HTML",
    )
    await callback.message.answer("Главное меню:", reply_markup=main_menu())
    await callback.message.answer(
        "Откройте «🏠 Главная» или разделы меню ниже.",
        reply_markup=main_menu(),
    )
    await callback.answer()


@router.message(F.text == "🏠 Главная")
@router.message(Command("home"))
async def cmd_home(message: Message, db: Database) -> None:
    await send_home(message, db)


@router.message(F.text == "❓ Помощь")
@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(
        "❓ <b>Справка</b>\n\n"
        "<b>Mini App</b>\n"
        "Нажмите «📱 Открыть приложение» — полноценное окно "
        "с кругом калорий, БЖУ и поиском продуктов.\n\n"
        "<b>Продукты</b>\n"
        "Локальная база + Open Food Facts API.\n\n"
        "<b>Формула</b>\n"
        "Миффлин — Сан-Жеор (активность + цель).\n\n"
        "/start — открыть бота\n"
        "/help — справка",
        parse_mode="HTML",
        reply_markup=main_menu(),
    )


@router.callback_query(F.data == "cancel")
async def cancel_any(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text("Отменено.")
    await callback.answer()
