
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.database import Database
from bot.handlers.common import require_user
from bot.keyboards.menus import (
    activity_kb,
    edit_profile_fields_kb,
    goal_kb,
    profile_menu_kb,
)
from bot.services.calories import calc_daily_norms
from bot.services.formatters import format_profile
from bot.states import EditProfile, WeightLog

router = Router(name="profile")


async def _recalc_and_save(db: Database, telegram_id: int, user) -> dict:
    norms = calc_daily_norms(
        gender=user["gender"],
        age=user["age"],
        height=user["height"],
        weight=user["weight"],
        activity=user["activity"],
        goal=user["goal"],
    )
    await db.upsert_user(
        telegram_id,
        calories_norm=norms["calories"],
        protein_norm=norms["protein"],
        fat_norm=norms["fat"],
        carbs_norm=norms["carbs"],
    )
    return norms


@router.message(F.text == "👤 Профиль")
async def profile_home(message: Message, db: Database) -> None:
    user = await require_user(message, db)
    if not user:
        return
    await message.answer(
        format_profile(user),
        reply_markup=profile_menu_kb(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "profile:back")
async def profile_back(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    await state.clear()
    user = await db.get_user(callback.from_user.id)
    await callback.message.edit_text(
        format_profile(user),
        reply_markup=profile_menu_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "profile:recalc")
async def profile_recalc(callback: CallbackQuery, db: Database) -> None:
    user = await db.get_user(callback.from_user.id)
    norms = await _recalc_and_save(db, callback.from_user.id, user)
    user = await db.get_user(callback.from_user.id)
    await callback.message.edit_text(
        f"🔄 Норма пересчитана: <b>{norms['calories']} ккал</b>\n\n"
        f"{format_profile(user)}",
        reply_markup=profile_menu_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "profile:weight")
async def profile_weight_start(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.edit_text("Введите текущий вес (кг):")
    await state.set_state(WeightLog.weight)
    await callback.answer()


@router.message(WeightLog.weight)
async def profile_weight_save(message: Message, state: FSMContext, db: Database) -> None:
    try:
        weight = float(message.text.strip().replace(",", "."))
        if not 30 <= weight <= 300:
            raise ValueError
    except (TypeError, ValueError):
        await message.answer("Введите вес от 30 до 300 кг.")
        return
    await db.add_weight_log(message.from_user.id, weight)
    user = await db.get_user(message.from_user.id)
    norms = await _recalc_and_save(db, message.from_user.id, user)
    await state.clear()
    await message.answer(
        f"✅ Вес {weight} кг сохранён.\n"
        f"Новая норма: <b>{norms['calories']} ккал</b>",
        parse_mode="HTML",
        reply_markup=profile_menu_kb(),
    )


@router.callback_query(F.data == "profile:history")
async def profile_history(callback: CallbackQuery, db: Database) -> None:
    logs = await db.get_weight_history(callback.from_user.id, limit=10)
    if not logs:
        await callback.answer("История пуста", show_alert=True)
        return
    lines = ["📈 <b>История веса</b>", ""]
    for log in logs:
        lines.append(f"• {log['logged_at'][:10]} — <b>{log['weight']} кг</b>")
    if len(logs) >= 2:
        delta = float(logs[0]["weight"]) - float(logs[-1]["weight"])
        trend = "📉" if delta < 0 else "📈" if delta > 0 else "➡️"
        lines.append(f"\n{trend} Изменение за период: {delta:+.1f} кг")
    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=profile_menu_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "profile:edit")
async def profile_edit(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(EditProfile.field)
    await callback.message.edit_text(
        "Что изменить?",
        reply_markup=edit_profile_fields_kb(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("profile:set:"))
async def profile_set_field(callback: CallbackQuery, state: FSMContext) -> None:
    field = callback.data.split(":")[-1]
    await state.update_data(field=field)
    if field == "activity":
        await callback.message.edit_text(
            "Выберите активность:", reply_markup=activity_kb()
        )
        await state.set_state(EditProfile.value)
    elif field == "goal":
        await callback.message.edit_text("Выберите цель:", reply_markup=goal_kb())
        await state.set_state(EditProfile.value)
    else:
        labels = {"age": "возраст (лет)", "height": "рост (см)", "weight": "вес (кг)"}
        await callback.message.edit_text(f"Введите новый {labels[field]}:")
        await state.set_state(EditProfile.value)
    await callback.answer()


@router.callback_query(EditProfile.value, F.data.startswith("reg:activity:"))
async def profile_set_activity(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    activity = callback.data.split(":")[-1]
    await db.upsert_user(callback.from_user.id, activity=activity)
    user = await db.get_user(callback.from_user.id)
    await _recalc_and_save(db, callback.from_user.id, user)
    await state.clear()
    user = await db.get_user(callback.from_user.id)
    await callback.message.edit_text(
        f"✅ Активность обновлена.\n\n{format_profile(user)}",
        reply_markup=profile_menu_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(EditProfile.value, F.data.startswith("reg:goal:"))
async def profile_set_goal(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    goal = callback.data.split(":")[-1]
    await db.upsert_user(callback.from_user.id, goal=goal)
    user = await db.get_user(callback.from_user.id)
    await _recalc_and_save(db, callback.from_user.id, user)
    await state.clear()
    user = await db.get_user(callback.from_user.id)
    await callback.message.edit_text(
        f"✅ Цель обновлена.\n\n{format_profile(user)}",
        reply_markup=profile_menu_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(EditProfile.value)
async def profile_set_value(message: Message, state: FSMContext, db: Database) -> None:
    data = await state.get_data()
    field = data.get("field")
    try:
        if field == "age":
            value = int(message.text.strip())
            if not 10 <= value <= 100:
                raise ValueError
        elif field == "height":
            value = float(message.text.strip().replace(",", "."))
            if not 100 <= value <= 250:
                raise ValueError
        elif field == "weight":
            value = float(message.text.strip().replace(",", "."))
            if not 30 <= value <= 300:
                raise ValueError
            await db.add_weight_log(message.from_user.id, value)
        else:
            await message.answer("Выберите поле кнопкой.")
            return
    except (TypeError, ValueError):
        await message.answer("Некорректное значение, попробуйте ещё раз.")
        return

    await db.upsert_user(message.from_user.id, **{field: value})
    user = await db.get_user(message.from_user.id)
    await _recalc_and_save(db, message.from_user.id, user)
    await state.clear()
    user = await db.get_user(message.from_user.id)
    await message.answer(
        f"✅ Данные обновлены.\n\n{format_profile(user)}",
        reply_markup=profile_menu_kb(),
        parse_mode="HTML",
    )
