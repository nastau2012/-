
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    WebAppInfo,
)

from bot.config import ACTIVITY_LABELS, GOAL_LABELS, MEAL_LABELS, WEBAPP_URL


def webapp_keyboard() -> InlineKeyboardMarkup | None:
    if not WEBAPP_URL:
        return None
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📱 Открыть калькулятор",
                    web_app=WebAppInfo(url=WEBAPP_URL),
                )
            ]
        ]
    )


def main_menu() -> ReplyKeyboardMarkup:
    rows = []
    rows.extend(
        [
            [KeyboardButton(text="📖 Дневник"), KeyboardButton(text="📊 Статистика")],
            [KeyboardButton(text="🍽 Продукты"), KeyboardButton(text="👤 Профиль")],
            [KeyboardButton(text="🏠 Главная"), KeyboardButton(text="💡 Рекомендации")],
            [KeyboardButton(text="❓ Помощь")],
        ]
    )
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def remove_kb() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()


def gender_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Мужской", callback_data="reg:gender:male"),
                InlineKeyboardButton(text="Женский", callback_data="reg:gender:female"),
            ]
        ]
    )


def activity_kb() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=label, callback_data=f"reg:activity:{key}")]
        for key, label in ACTIVITY_LABELS.items()
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def goal_kb() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=label, callback_data=f"reg:goal:{key}")]
        for key, label in GOAL_LABELS.items()
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def meal_type_kb() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=label, callback_data=f"meal:type:{key}")]
        for key, label in MEAL_LABELS.items()
    ]
    rows.append([InlineKeyboardButton(text="❌ Отмена", callback_data="meal:cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def products_result_kb(products: list) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=f"{p['name']} ({round(p['calories'])} ккал)",
                callback_data=f"meal:product:{p['id']}",
            )
        ]
        for p in products
    ]
    rows.append(
        [InlineKeyboardButton(text="➕ Свой продукт", callback_data="meal:custom")]
    )
    rows.append([InlineKeyboardButton(text="❌ Отмена", callback_data="meal:cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def confirm_meal_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="➕ Добавить в дневник", callback_data="meal:confirm"
                )
            ],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="meal:cancel")],
        ]
    )


def diary_actions_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить приём пищи", callback_data="diary:add")],
            [
                InlineKeyboardButton(text="✏️ Изменить", callback_data="diary:edit"),
                InlineKeyboardButton(text="🗑 Удалить", callback_data="diary:delete"),
            ],
            [InlineKeyboardButton(text="📋 Шаблоны", callback_data="diary:templates")],
        ]
    )


def meals_list_kb(meals: list, prefix: str) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=f"#{m['id']} {m['product_name']} ({round(m['calories'])} ккал)",
                callback_data=f"{prefix}:{m['id']}",
            )
        ]
        for m in meals
    ]
    rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data="diary:back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def edit_meal_fields_kb(meal_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Вес", callback_data=f"editmeal:weight:{meal_id}")],
            [
                InlineKeyboardButton(
                    text="Категория", callback_data=f"editmeal:type:{meal_id}"
                )
            ],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="diary:back")],
        ]
    )


def products_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔍 Поиск", callback_data="products:search")],
            [InlineKeyboardButton(text="📋 Список", callback_data="products:list")],
            [InlineKeyboardButton(text="➕ Добавить продукт", callback_data="products:add")],
            [InlineKeyboardButton(text="🗂 Категории", callback_data="products:cats")],
        ]
    )


def profile_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Изменить данные", callback_data="profile:edit")],
            [InlineKeyboardButton(text="⚖️ Замер веса", callback_data="profile:weight")],
            [InlineKeyboardButton(text="📈 История веса", callback_data="profile:history")],
            [InlineKeyboardButton(text="🔄 Пересчитать норму", callback_data="profile:recalc")],
        ]
    )


def stats_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📅 Сегодня", callback_data="stats:today")],
            [InlineKeyboardButton(text="📆 Неделя", callback_data="stats:week")],
            [InlineKeyboardButton(text="🗓 Месяц", callback_data="stats:month")],
            [InlineKeyboardButton(text="⚖️ Динамика веса", callback_data="stats:weight")],
        ]
    )


def categories_kb(categories: list[str], prefix: str = "prodcat") -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=cat, callback_data=f"{prefix}:{cat}")]
        for cat in categories
    ]
    rows.append([InlineKeyboardButton(text="❌ Отмена", callback_data="products:cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def cancel_inline() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")]
        ]
    )


def templates_kb(templates: list) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=t["name"], callback_data=f"tpl:use:{t['id']}"
            )
        ]
        for t in templates
    ]
    rows.append(
        [InlineKeyboardButton(text="➕ Создать шаблон", callback_data="tpl:create")]
    )
    if templates:
        rows.append(
            [InlineKeyboardButton(text="🗑 Удалить шаблон", callback_data="tpl:delete")]
        )
    rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data="diary:back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def edit_profile_fields_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Возраст", callback_data="profile:set:age")],
            [InlineKeyboardButton(text="Рост", callback_data="profile:set:height")],
            [InlineKeyboardButton(text="Вес", callback_data="profile:set:weight")],
            [InlineKeyboardButton(text="Активность", callback_data="profile:set:activity")],
            [InlineKeyboardButton(text="Цель", callback_data="profile:set:goal")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="profile:back")],
        ]
    )
