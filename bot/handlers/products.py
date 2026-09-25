
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.database import Database
from bot.handlers.common import require_user
from bot.keyboards.menus import products_menu_kb
from bot.services.formatters import format_product
from bot.states import AddProduct, SearchProduct

router = Router(name="products")

DEFAULT_CATEGORIES = [
    "Мясо и птица",
    "Рыба и морепродукты",
    "Молочные",
    "Крупы",
    "Овощи",
    "Фрукты",
    "Хлеб и выпечка",
    "Жиры и масла",
    "Орехи",
    "Сладости",
    "Напитки",
    "Готовые блюда",
    "Другое",
]


@router.message(F.text == "🍽 Продукты")
async def products_home(message: Message, db: Database) -> None:
    if not await require_user(message, db):
        return
    count = await db.count_products()
    await message.answer(
        f"🍽 <b>Продукты</b>\n\nВ базе: <b>{count}</b> позиций.\n"
        "Поиск, список или добавление своего продукта:",
        reply_markup=products_menu_kb(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "products:cancel")
async def products_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text("Отменено.")
    await callback.answer()


@router.callback_query(F.data == "products:search")
async def products_search_start(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.edit_text("🔍 Введите название продукта:")
    await state.set_state(SearchProduct.query)
    await callback.answer()


@router.message(SearchProduct.query)
async def products_search(message: Message, state: FSMContext, db: Database) -> None:
    products = await db.search_products(message.text.strip(), limit=10, owner_id=message.from_user.id)
    await state.clear()
    if not products:
        await message.answer("Ничего не найдено. Попробуйте другое название.")
        return
    lines = ["🔍 <b>Результаты поиска</b>", ""]
    for p in products:
        lines.append(
            f"• <b>{p['name']}</b> ({p['category']})\n"
            f"  {p['calories']} ккал | Б {p['protein']} Ж {p['fat']} У {p['carbs']} /100г"
        )
    await message.answer("\n".join(lines), parse_mode="HTML", reply_markup=products_menu_kb())


@router.callback_query(F.data == "products:list")
async def products_list(callback: CallbackQuery, db: Database) -> None:
    products = await db.list_products(owner_id=callback.from_user.id, limit=15)
    lines = ["📋 <b>Продукты</b> (первые 15)", ""]
    for p in products:
        mark = " 👤" if p["owner_id"] else ""
        lines.append(f"• {p['name']}{mark} — {p['calories']} ккал/100г")
    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=products_menu_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "products:cats")
async def products_cats(callback: CallbackQuery, db: Database) -> None:
    cats = await db.get_categories()
    text = "🗂 <b>Категории</b>\n\n" + "\n".join(f"• {c}" for c in cats)
    await callback.message.edit_text(
        text, reply_markup=products_menu_kb(), parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "products:add")
async def products_add_start(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.edit_text("Введите название нового продукта:")
    await state.set_state(AddProduct.name)
    await callback.answer()


@router.message(AddProduct.name)
async def products_add_name(message: Message, state: FSMContext) -> None:
    name = (message.text or "").strip()
    if len(name) < 2:
        await message.answer("Слишком короткое название.")
        return
    await state.update_data(name=name)
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    rows = [
        [InlineKeyboardButton(text=c, callback_data=f"newprod:cat:{c}")]
        for c in DEFAULT_CATEGORIES
    ]
    await message.answer(
        "Выберите категорию:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
    )
    await state.set_state(AddProduct.category)


@router.callback_query(AddProduct.category, F.data.startswith("newprod:cat:"))
async def products_add_cat(callback: CallbackQuery, state: FSMContext) -> None:
    category = callback.data.split(":", 2)[-1]
    await state.update_data(category=category)
    await callback.message.edit_text("Калории на 100 г:")
    await state.set_state(AddProduct.calories)
    await callback.answer()


def _parse_float(text: str) -> float:
    return float(text.strip().replace(",", "."))


@router.message(AddProduct.calories)
async def products_add_cal(message: Message, state: FSMContext) -> None:
    try:
        val = _parse_float(message.text)
        if val < 0 or val > 1000:
            raise ValueError
    except (TypeError, ValueError):
        await message.answer("Введите число калорий (0–1000).")
        return
    await state.update_data(calories=val)
    await message.answer("Белки на 100 г (г):")
    await state.set_state(AddProduct.protein)


@router.message(AddProduct.protein)
async def products_add_prot(message: Message, state: FSMContext) -> None:
    try:
        val = _parse_float(message.text)
        if val < 0 or val > 100:
            raise ValueError
    except (TypeError, ValueError):
        await message.answer("Введите число белков (0–100).")
        return
    await state.update_data(protein=val)
    await message.answer("Жиры на 100 г (г):")
    await state.set_state(AddProduct.fat)


@router.message(AddProduct.fat)
async def products_add_fat(message: Message, state: FSMContext) -> None:
    try:
        val = _parse_float(message.text)
        if val < 0 or val > 100:
            raise ValueError
    except (TypeError, ValueError):
        await message.answer("Введите число жиров (0–100).")
        return
    await state.update_data(fat=val)
    await message.answer("Углеводы на 100 г (г):")
    await state.set_state(AddProduct.carbs)


@router.message(AddProduct.carbs)
async def products_add_carbs(message: Message, state: FSMContext, db: Database) -> None:
    try:
        val = _parse_float(message.text)
        if val < 0 or val > 100:
            raise ValueError
    except (TypeError, ValueError):
        await message.answer("Введите число углеводов (0–100).")
        return
    data = await state.get_data()
    pid = await db.add_product(
        name=data["name"],
        category=data["category"],
        calories=data["calories"],
        protein=data["protein"],
        fat=data["fat"],
        carbs=val,
        owner_id=message.from_user.id,
    )
    await state.clear()
    product = await db.get_product(pid)
    await message.answer(
        f"✅ Продукт добавлен!\n\n{format_product(product)}",
        parse_mode="HTML",
        reply_markup=products_menu_kb(),
    )
