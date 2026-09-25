from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.config import MEAL_LABELS
from bot.database import Database
from bot.handlers.common import require_user
from bot.keyboards.menus import (
    confirm_meal_kb,
    diary_actions_kb,
    edit_meal_fields_kb,
    meal_type_kb,
    meals_list_kb,
    products_result_kb,
    templates_kb,
)
from bot.services.calories import scale_nutrients
from bot.services.formatters import format_diary
from bot.states import AddMeal, EditMeal, TemplateCreate

router = Router(name="diary")


@router.message(F.text == "📖 Дневник")
async def diary_home(message: Message, db: Database) -> None:
    user = await require_user(message, db)
    if not user:
        return

    meals = await db.get_meals_for_day(message.from_user.id)

    await message.answer(
        format_diary(meals),
        reply_markup=diary_actions_kb(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "diary:back")
async def diary_back(
    callback: CallbackQuery,
    state: FSMContext,
    db: Database,
) -> None:
    await state.clear()

    meals = await db.get_meals_for_day(callback.from_user.id)

    await callback.message.edit_text(
        format_diary(meals),
        reply_markup=diary_actions_kb(),
        parse_mode="HTML",
    )

    await callback.answer()


@router.callback_query(F.data == "diary:add")
async def diary_add(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await state.clear()

    await callback.message.edit_text(
        "<b>Добавление приёма пищи</b>\n\n"
        "Выберите категорию:",
        reply_markup=meal_type_kb(),
        parse_mode="HTML",
    )

    await state.set_state(AddMeal.meal_type)
    await callback.answer()


@router.callback_query(
    AddMeal.meal_type,
    F.data.startswith("meal:type:"),
)
async def meal_type_chosen(
    callback: CallbackQuery,
    state: FSMContext,
    db: Database,
) -> None:
    meal_type = callback.data.split(":")[-1]
    data = await state.get_data()

    # Быстрое добавление из шаблона
    if data.get("from_template"):
        for item in data.get("tpl_items", []):
            nutrients = scale_nutrients(
                item["calories"],
                item["protein"],
                item["fat"],
                item["carbs"],
                item["weight_g"],
            )

            await db.add_meal(
                telegram_id=callback.from_user.id,
                product_id=item["product_id"],
                product_name=item["name"],
                weight_g=item["weight_g"],
                meal_type=meal_type,
                **nutrients,
            )

        await state.clear()

        meals = await db.get_meals_for_day(callback.from_user.id)

        await callback.message.edit_text(
            f"✅ Шаблон добавлен в {MEAL_LABELS.get(meal_type)}.\n\n"
            f"{format_diary(meals)}",
            reply_markup=diary_actions_kb(),
            parse_mode="HTML",
        )

        await callback.answer()
        return

    await state.update_data(meal_type=meal_type)

    label = MEAL_LABELS.get(meal_type, meal_type)

    await callback.message.edit_text(
        f"{label}\n\n"
        "🔍 Введите название продукта для поиска\n"
        "(например: овсянка, яблоко, курица):",
    )

    await state.set_state(AddMeal.search)
    await callback.answer()


@router.callback_query(F.data == "meal:cancel")
async def meal_cancel(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await state.clear()

    await callback.message.edit_text(
        "Добавление отменено."
    )

    await callback.answer()


@router.message(AddMeal.search)
async def meal_search(
    message: Message,
    state: FSMContext,
    db: Database,
) -> None:
    query = (message.text or "").strip()

    if len(query) < 2:
        await message.answer("Введите минимум 2 символа.")
        return

    products = await db.search_products(
        query,
        limit=8,
        owner_id=message.from_user.id,
    )

    if not products:
        await state.update_data(custom_name=query)

        await message.answer(
            f"Продукт «{query}» не найден.\n"
            "Можно добавить свой: введите калории на 100 г "
            "(или уточните запрос)."
        )

        await message.answer(
            "Либо нажмите кнопку ниже, если хотите создать продукт позже "
            "в разделе «Продукты».\n"
            "Попробуйте другой запрос или добавьте продукт через меню "
            "«🍽 Продукты»."
        )

        return

    await message.answer(
        "Выберите продукт:",
        reply_markup=products_result_kb(products),
    )

    await state.set_state(AddMeal.choose_product)


@router.callback_query(
    AddMeal.choose_product,
    F.data.startswith("meal:product:"),
)
async def meal_product_chosen(
    callback: CallbackQuery,
    state: FSMContext,
    db: Database,
) -> None:
    product_id = int(callback.data.split(":")[-1])
    product = await db.get_product(product_id)

    if not product:
        await callback.answer(
            "Продукт не найден",
            show_alert=True,
        )
        return

    await state.update_data(
        product_id=product["id"],
        product_name=product["name"],
        p_cal=product["calories"],
        p_prot=product["protein"],
        p_fat=product["fat"],
        p_carb=product["carbs"],
    )

    await callback.message.edit_text(
        f"🍽 <b>{product['name']}</b>\n"
        f"На 100 г: {product['calories']} ккал\n\n"
        "Введите вес в граммах:",
        parse_mode="HTML",
    )

    await state.set_state(AddMeal.weight)
    await callback.answer()


@router.message(AddMeal.weight)
async def meal_weight(
    message: Message,
    state: FSMContext,
) -> None:
    try:
        weight = float(
            message.text.strip().replace(",", ".")
        )

        if not 1 <= weight <= 5000:
            raise ValueError

    except (TypeError, ValueError):
        await message.answer(
            "Введите вес числом от 1 до 5000 г."
        )
        return

    data = await state.get_data()

    nutrients = scale_nutrients(
        data["p_cal"],
        data["p_prot"],
        data["p_fat"],
        data["p_carb"],
        weight,
    )

    await state.update_data(
        weight_g=weight,
        **nutrients,
    )

    label = MEAL_LABELS.get(
        data["meal_type"],
        data["meal_type"],
    )

    await message.answer(
        f"<b>{label}</b>\n"
        f"Продукт: {data['product_name']}\n"
        f"Вес: {weight} г\n"
        f"🔥 Всего: <b>{nutrients['calories']} ккал</b>\n"
        f"Б {nutrients['protein']} | "
        f"Ж {nutrients['fat']} | "
        f"У {nutrients['carbs']}",
        reply_markup=confirm_meal_kb(),
        parse_mode="HTML",
    )

    await state.set_state(AddMeal.confirm)


@router.callback_query(
    AddMeal.confirm,
    F.data == "meal:confirm",
)
async def meal_confirm(
    callback: CallbackQuery,
    state: FSMContext,
    db: Database,
) -> None:
    data = await state.get_data()

    await db.add_meal(
        telegram_id=callback.from_user.id,
        product_id=data["product_id"],
        product_name=data["product_name"],
        weight_g=data["weight_g"],
        meal_type=data["meal_type"],
        calories=data["calories"],
        protein=data["protein"],
        fat=data["fat"],
        carbs=data["carbs"],
    )

    await state.clear()

    await callback.message.edit_text(
        f"✅ Добавлено: "
        f"{data['product_name']} — "
        f"{data['calories']} ккал"
    )

    meals = await db.get_meals_for_day(
        callback.from_user.id
    )

    await callback.message.answer(
        format_diary(meals),
        reply_markup=diary_actions_kb(),
        parse_mode="HTML",
    )

    await callback.answer()


@router.callback_query(F.data == "diary:delete")
async def diary_delete_start(
    callback: CallbackQuery,
    db: Database,
) -> None:
    meals = await db.get_meals_for_day(
        callback.from_user.id
    )

    if not meals:
        await callback.answer(
            "Нечего удалять",
            show_alert=True,
        )
        return

    await callback.message.edit_text(
        "Выберите запись для удаления:",
        reply_markup=meals_list_kb(
            meals,
            "delmeal",
        ),
    )

    await callback.answer()


@router.callback_query(F.data.startswith("delmeal:"))
async def diary_delete_confirm(
    callback: CallbackQuery,
    db: Database,
) -> None:
    meal_id = int(
        callback.data.split(":")[-1]
    )

    ok = await db.delete_meal(
        meal_id,
        callback.from_user.id,
    )

    text = (
        "✅ Запись удалена."
        if ok
        else "Не удалось удалить."
    )

    meals = await db.get_meals_for_day(
        callback.from_user.id
    )

    await callback.message.edit_text(
        f"{text}\n\n{format_diary(meals)}",
        reply_markup=diary_actions_kb(),
        parse_mode="HTML",
    )

    await callback.answer()


@router.callback_query(F.data == "diary:edit")
async def diary_edit_start(
    callback: CallbackQuery,
    state: FSMContext,
    db: Database,
) -> None:
    meals = await db.get_meals_for_day(
        callback.from_user.id
    )

    if not meals:
        await callback.answer(
            "Нечего редактировать",
            show_alert=True,
        )
        return

    await state.set_state(EditMeal.choose)

    await callback.message.edit_text(
        "Выберите запись:",
        reply_markup=meals_list_kb(
            meals,
            "pickmeal",
        ),
    )

    await callback.answer()


@router.callback_query(
    EditMeal.choose,
    F.data.startswith("pickmeal:"),
)
async def diary_edit_pick(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    meal_id = int(
        callback.data.split(":")[-1]
    )

    await state.update_data(
        meal_id=meal_id
    )

    await callback.message.edit_text(
        "Что изменить?",
        reply_markup=edit_meal_fields_kb(
            meal_id
        ),
    )

    await state.set_state(
        EditMeal.field
    )

    await callback.answer()


@router.callback_query(
    EditMeal.field,
    F.data.startswith("editmeal:weight:"),
)
async def edit_weight_ask(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await callback.message.edit_text(
        "Введите новый вес в граммах:"
    )

    await state.update_data(
        edit_field="weight"
    )

    await state.set_state(
        EditMeal.value
    )

    await callback.answer()


@router.callback_query(
    EditMeal.field,
    F.data.startswith("editmeal:type:"),
)
async def edit_type_ask(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await callback.message.edit_text(
        "Выберите новую категорию:",
        reply_markup=meal_type_kb(),
    )

    await state.update_data(
        edit_field="type"
    )

    await callback.answer()


@router.callback_query(
    EditMeal.field,
    F.data.startswith("meal:type:"),
)
async def edit_type_save(
    callback: CallbackQuery,
    state: FSMContext,
    db: Database,
) -> None:
    data = await state.get_data()

    meal_type = callback.data.split(":")[-1]

    meal = await db.get_meal(
        data["meal_id"]
    )

    if (
        not meal
        or meal["telegram_id"] != callback.from_user.id
    ):
        await callback.answer(
            "Запись не найдена",
            show_alert=True,
        )
        return

    await db.update_meal(
        data["meal_id"],
        meal_type=meal_type,
    )

    await state.clear()

    meals = await db.get_meals_for_day(
        callback.from_user.id
    )

    await callback.message.edit_text(
        f"✅ Категория изменена.\n\n"
        f"{format_diary(meals)}",
        reply_markup=diary_actions_kb(),
        parse_mode="HTML",
    )

    await callback.answer()


@router.message(EditMeal.value)
async def edit_weight_save(
    message: Message,
    state: FSMContext,
    db: Database,
) -> None:
    data = await state.get_data()

    try:
        weight = float(
            message.text.strip().replace(",", ".")
        )

        if not 1 <= weight <= 5000:
            raise ValueError

    except (TypeError, ValueError):
        await message.answer(
            "Введите корректный вес."
        )
        return

    meal = await db.get_meal(
        data["meal_id"]
    )

    if (
        not meal
        or meal["telegram_id"] != message.from_user.id
    ):
        await message.answer(
            "Запись не найдена."
        )
        await state.clear()
        return

    product = await db.get_product(
        meal["product_id"]
    )

    if not product:
        await message.answer(
            "Продукт удалён из базы."
        )
        await state.clear()
        return

    nutrients = scale_nutrients(
        product["calories"],
        product["protein"],
        product["fat"],
        product["carbs"],
        weight,
    )

    await db.update_meal(
        data["meal_id"],
        weight_g=weight,
        calories=nutrients["calories"],
        protein=nutrients["protein"],
        fat=nutrients["fat"],
        carbs=nutrients["carbs"],
    )

    await state.clear()

    meals = await db.get_meals_for_day(
        message.from_user.id
    )

    await message.answer(
        f"✅ Вес обновлён.\n\n"
        f"{format_diary(meals)}",
        reply_markup=diary_actions_kb(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "diary:templates")
async def templates_menu(
    callback: CallbackQuery,
    db: Database,
) -> None:
    templates = await db.list_templates(
        callback.from_user.id
    )

    await callback.message.edit_text(
        "📋 <b>Шаблоны блюд</b>\n"
        "Выберите шаблон или создайте новый:",
        reply_markup=templates_kb(
            templates
        ),
        parse_mode="HTML",
    )

    await callback.answer()


@router.callback_query(F.data == "tpl:create")
async def tpl_create(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await callback.message.edit_text(
        "Введите название шаблона:"
    )

    await state.set_state(
        TemplateCreate.name
    )

    await callback.answer()


@router.message(TemplateCreate.name)
async def tpl_name(
    message: Message,
    state: FSMContext,
) -> None:
    name = (message.text or "").strip()

    if len(name) < 2:
        await message.answer(
            "Слишком короткое название."
        )
        return

    await state.update_data(
        tpl_name=name
    )

    await message.answer(
        "Введите продукт для шаблона (поиск):"
    )

    await state.set_state(
        TemplateCreate.product_search
    )


@router.message(TemplateCreate.product_search)
async def tpl_product_search(
    message: Message,
    state: FSMContext,
    db: Database,
) -> None:
    products = await db.search_products(
        message.text.strip(),
        limit=5,
        owner_id=message.from_user.id,
    )

    if not products:
        await message.answer(
            "Ничего не найдено, попробуйте ещё раз."
        )
        return

    await message.answer(
        "Выберите продукт:",
        reply_markup=products_result_kb(
            products
        ),
    )

    await state.update_data(
        tpl_mode=True
    )

    await state.set_state(
        TemplateCreate.product_weight
    )


@router.callback_query(
    TemplateCreate.product_weight,
    F.data.startswith("meal:product:"),
)
async def tpl_product_chosen(
    callback: CallbackQuery,
    state: FSMContext,
    db: Database,
) -> None:
    product_id = int(
        callback.data.split(":")[-1]
    )

    product = await db.get_product(
        product_id
    )

    await state.update_data(
        tpl_product_id=product_id,
        tpl_product_name=product["name"],
    )

    await callback.message.edit_text(
        f"{product['name']}\n"
        "Введите вес в граммах для шаблона:"
    )

    await callback.answer()


@router.message(TemplateCreate.product_weight)
async def tpl_save(
    message: Message,
    state: FSMContext,
    db: Database,
) -> None:
    data = await state.get_data()

    if "tpl_product_id" not in data:
        await message.answer(
            "Сначала выберите продукт кнопкой из списка."
        )
        return

    try:
        weight = float(
            message.text.strip().replace(",", ".")
        )

        if not 1 <= weight <= 5000:
            raise ValueError

    except (TypeError, ValueError):
        await message.answer(
            "Введите вес числом."
        )
        return

    tpl_id = await db.create_template(
        message.from_user.id,
        data["tpl_name"],
    )

    await db.add_template_item(
        tpl_id,
        data["tpl_product_id"],
        weight,
    )

    await state.clear()

    templates = await db.list_templates(
        message.from_user.id
    )

    await message.answer(
        f"✅ Шаблон «{data['tpl_name']}» создан.",
        reply_markup=templates_kb(
            templates
        ),
    )


@router.callback_query(
    F.data.startswith("tpl:use:")
)
async def tpl_use(
    callback: CallbackQuery,
    state: FSMContext,
    db: Database,
) -> None:
    tpl_id = int(
        callback.data.split(":")[-1]
    )

    items = await db.get_template_items(
        tpl_id
    )

    if not items:
        await callback.answer(
            "Шаблон пуст",
            show_alert=True,
        )
        return

    await state.set_state(
        AddMeal.meal_type
    )

    await state.update_data(
        from_template=True,
        tpl_items=[dict(i) for i in items],
    )

    await callback.message.edit_text(
        "В какую категорию добавить шаблон?",
        reply_markup=meal_type_kb(),
    )

    await callback.answer()


@router.callback_query(
    F.data == "tpl:delete"
)
async def tpl_delete_start(
    callback: CallbackQuery,
    db: Database,
) -> None:
    templates = await db.list_templates(
        callback.from_user.id
    )

    if not templates:
        await callback.answer(
            "Нет шаблонов",
            show_alert=True,
        )
        return

    from aiogram.types import (
        InlineKeyboardButton,
        InlineKeyboardMarkup,
    )

    rows = [
        [
            InlineKeyboardButton(
                text=f"🗑 {t['name']}",
                callback_data=f"tpl:rm:{t['id']}",
            )
        ]
        for t in templates
    ]

    rows.append(
        [
            InlineKeyboardButton(
                text="◀️ Назад",
                callback_data="diary:templates",
            )
        ]
    )

    await callback.message.edit_text(
        "Выберите шаблон для удаления:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=rows
        ),
    )

    await callback.answer()


@router.callback_query(
    F.data.startswith("tpl:rm:")
)
async def tpl_delete_do(
    callback: CallbackQuery,
    db: Database,
) -> None:
    tpl_id = int(
        callback.data.split(":")[-1]
    )

    await db.delete_template(
        tpl_id,
        callback.from_user.id,
    )

    templates = await db.list_templates(
        callback.from_user.id
    )

    await callback.message.edit_text(
        "✅ Шаблон удалён.",
        reply_markup=templates_kb(
            templates
        ),
    )

    await callback.answer()