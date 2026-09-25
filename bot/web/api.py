from __future__ import annotations

import logging
from datetime import date
from typing import Any

from aiohttp import web

from bot.config import (
    ACTIVITY_LABELS,
    BOT_TOKEN,
    DEV_TELEGRAM_ID,
    GOAL_LABELS,
    MEAL_LABELS,
)
from bot.database import Database
from bot.services.calories import calc_daily_norms, scale_nutrients
from bot.services.openfoodfacts import search_open_food_facts
from bot.services.recommendations import generate_recommendations
from bot.web.auth import validate_init_data

logger = logging.getLogger(__name__)


WEEKDAYS = (
    "Понедельник",
    "Вторник",
    "Среда",
    "Четверг",
    "Пятница",
    "Суббота",
    "Воскресенье",
)


# ============================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================

def _row_to_dict(row) -> dict[str, Any]:
    return dict(row) if row is not None else {}


def json_response(data: Any, status: int = 200) -> web.Response:
    return web.json_response(data, status=status)


async def get_telegram_id(request: web.Request) -> int:
    """
    Получает Telegram ID пользователя.

    Основной вариант:
        Telegram Mini App -> X-Telegram-Init-Data -> проверка подписи.

    Для разработки в обычном браузере:
        используется DEV_TELEGRAM_ID из .env.
    """

    init_data = request.headers.get("X-Telegram-Init-Data", "")

    logger.info(
        "Mini App auth: initData_present=%s, initData_length=%s",
        bool(init_data),
        len(init_data),
    )

    # Авторизация через Telegram Mini App
    if init_data:
        parsed = validate_init_data(init_data, BOT_TOKEN)

        logger.info(
            "Mini App auth: validation=%s, user_id=%s",
            bool(parsed),
            parsed.get("user", {}).get("id") if parsed else None,
        )

        if parsed:
            user = parsed.get("user") or {}
            telegram_id = user.get("id")

            if telegram_id:
                return int(telegram_id)

        logger.warning("Mini App auth: Invalid Telegram initData")
        raise web.HTTPUnauthorized(text="Invalid Telegram initData")

    # Режим разработки — открытие Mini App напрямую в браузере
    if DEV_TELEGRAM_ID:
        logger.info(
            "Mini App auth: используется DEV_TELEGRAM_ID=%s",
            DEV_TELEGRAM_ID,
        )
        return int(DEV_TELEGRAM_ID)

    logger.warning("Mini App auth: initData отсутствует")
    raise web.HTTPUnauthorized(text="Authorization required")


def _public_user(user) -> dict[str, Any] | None:
    if not user:
        return None

    return {
        "telegram_id": user["telegram_id"],
        "gender": user["gender"],
        "age": user["age"],
        "height": user["height"],
        "weight": user["weight"],
        "activity": user["activity"],
        "goal": user["goal"],
        "calories_norm": user["calories_norm"],
        "protein_norm": user["protein_norm"],
        "fat_norm": user["fat_norm"],
        "carbs_norm": user["carbs_norm"],
    }


def _meal_dict(meal) -> dict[str, Any]:
    return {
        "id": meal["id"],
        "product_name": meal["product_name"],
        "weight_g": meal["weight_g"],
        "meal_type": meal["meal_type"],
        "meal_label": MEAL_LABELS.get(
            meal["meal_type"],
            meal["meal_type"],
        ),
        "eaten_at": meal["eaten_at"],
        "calories": meal["calories"],
        "protein": meal["protein"],
        "fat": meal["fat"],
        "carbs": meal["carbs"],
    }


# ============================================================
# СОЗДАНИЕ API-ПРИЛОЖЕНИЯ
# ============================================================

def create_api_app(db: Database) -> web.Application:
    app = web.Application()
    app["db"] = db

    # Служебные
    app.router.add_get("/api/health", handle_health)
    app.router.add_get("/api/meta", handle_meta)

    # Профиль
    app.router.add_get("/api/me", handle_me)
    app.router.add_post("/api/register", handle_register)
    app.router.add_patch("/api/profile", handle_profile_patch)

    # Вес
    app.router.add_post("/api/weight", handle_weight)
    app.router.add_get("/api/weight", handle_weight_history)

    # Дневник
    app.router.add_get("/api/home", handle_home)
    app.router.add_get("/api/meals", handle_meals)
    app.router.add_post("/api/meals", handle_meals_add)
    app.router.add_delete("/api/meals/{meal_id}", handle_meals_delete)
    app.router.add_patch("/api/meals/{meal_id}", handle_meals_patch)

    # Продукты
    app.router.add_get("/api/products/search", handle_products_search)
    app.router.add_post("/api/products", handle_products_add)

    # Статистика и рекомендации
    app.router.add_get("/api/stats", handle_stats)
    app.router.add_get("/api/recommendations", handle_recommendations)

    return app


# ============================================================
# СЛУЖЕБНЫЕ ENDPOINTS
# ============================================================

async def handle_health(_: web.Request) -> web.Response:
    return json_response({"ok": True})


async def handle_meta(_: web.Request) -> web.Response:
    return json_response(
        {
            "meals": MEAL_LABELS,
            "goals": GOAL_LABELS,
            "activities": ACTIVITY_LABELS,
        }
    )


# ============================================================
# ПРОФИЛЬ
# ============================================================

async def handle_me(request: web.Request) -> web.Response:
    db: Database = request.app["db"]
    telegram_id = await get_telegram_id(request)

    user = await db.get_user(telegram_id)

    if not user:
        await db.upsert_user(telegram_id)
        user = await db.get_user(telegram_id)

    return json_response(
        {
            "registered": bool(
                user and user["calories_norm"]
            ),
            "user": _public_user(user),
        }
    )


async def handle_register(request: web.Request) -> web.Response:
    db: Database = request.app["db"]
    telegram_id = await get_telegram_id(request)

    try:
        body = await request.json()

        gender = body["gender"]
        age = int(body["age"])
        height = float(body["height"])
        weight = float(body["weight"])
        activity = body["activity"]
        goal = body["goal"]

        if gender not in ("male", "female"):
            raise ValueError

        if activity not in ACTIVITY_LABELS:
            raise ValueError

        if goal not in GOAL_LABELS:
            raise ValueError

        if not 10 <= age <= 100:
            raise ValueError

        if not 100 <= height <= 250:
            raise ValueError

        if not 30 <= weight <= 300:
            raise ValueError

    except (KeyError, TypeError, ValueError):
        raise web.HTTPBadRequest(
            text="Invalid profile data"
        )

    norms = calc_daily_norms(
        gender,
        age,
        height,
        weight,
        activity,
        goal,
    )

    await db.upsert_user(
        telegram_id,
        gender=gender,
        age=age,
        height=height,
        weight=weight,
        activity=activity,
        goal=goal,
        calories_norm=norms["calories"],
        protein_norm=norms["protein"],
        fat_norm=norms["fat"],
        carbs_norm=norms["carbs"],
    )

    await db.add_weight_log(
        telegram_id,
        weight,
    )

    user = await db.get_user(telegram_id)

    return json_response(
        {
            "ok": True,
            "user": _public_user(user),
            "norms": norms,
        }
    )


async def handle_profile_patch(request: web.Request) -> web.Response:
    db: Database = request.app["db"]
    telegram_id = await get_telegram_id(request)

    user = await db.get_user(telegram_id)

    if not user or not user["calories_norm"]:
        raise web.HTTPBadRequest(
            text="Not registered"
        )

    try:
        body = await request.json()
    except Exception:
        raise web.HTTPBadRequest(
            text="Invalid JSON"
        )

    fields: dict[str, Any] = {}

    for key in (
        "gender",
        "age",
        "height",
        "weight",
        "activity",
        "goal",
    ):
        if key in body and body[key] is not None:
            fields[key] = body[key]

    if "gender" in fields:
        if fields["gender"] not in ("male", "female"):
            raise web.HTTPBadRequest(
                text="Invalid gender"
            )

    if "activity" in fields:
        if fields["activity"] not in ACTIVITY_LABELS:
            raise web.HTTPBadRequest(
                text="Invalid activity"
            )

    if "goal" in fields:
        if fields["goal"] not in GOAL_LABELS:
            raise web.HTTPBadRequest(
                text="Invalid goal"
            )

    if "age" in fields:
        try:
            fields["age"] = int(fields["age"])
        except (TypeError, ValueError):
            raise web.HTTPBadRequest(
                text="Invalid age"
            )

        if not 10 <= fields["age"] <= 100:
            raise web.HTTPBadRequest(
                text="Invalid age"
            )

    if "height" in fields:
        try:
            fields["height"] = float(fields["height"])
        except (TypeError, ValueError):
            raise web.HTTPBadRequest(
                text="Invalid height"
            )

        if not 100 <= fields["height"] <= 250:
            raise web.HTTPBadRequest(
                text="Invalid height"
            )

    if "weight" in fields:
        try:
            fields["weight"] = float(fields["weight"])
        except (TypeError, ValueError):
            raise web.HTTPBadRequest(
                text="Invalid weight"
            )

        if not 30 <= fields["weight"] <= 300:
            raise web.HTTPBadRequest(
                text="Invalid weight"
            )

        await db.add_weight_log(
            telegram_id,
            fields["weight"],
        )

    if fields:
        await db.upsert_user(
            telegram_id,
            **fields,
        )

    user = await db.get_user(telegram_id)

    norms = calc_daily_norms(
        user["gender"],
        user["age"],
        user["height"],
        user["weight"],
        user["activity"],
        user["goal"],
    )

    await db.upsert_user(
        telegram_id,
        calories_norm=norms["calories"],
        protein_norm=norms["protein"],
        fat_norm=norms["fat"],
        carbs_norm=norms["carbs"],
    )

    user = await db.get_user(telegram_id)

    return json_response(
        {
            "ok": True,
            "user": _public_user(user),
        }
    )


# ============================================================
# ВЕС
# ============================================================

async def handle_weight(request: web.Request) -> web.Response:
    db: Database = request.app["db"]
    telegram_id = await get_telegram_id(request)

    try:
        body = await request.json()
        weight = float(body["weight"])
    except (KeyError, TypeError, ValueError):
        raise web.HTTPBadRequest(
            text="Invalid weight"
        )

    if not 30 <= weight <= 300:
        raise web.HTTPBadRequest(
            text="Invalid weight"
        )

    await db.add_weight_log(
        telegram_id,
        weight,
    )

    user = await db.get_user(telegram_id)

    if user and user["gender"]:
        norms = calc_daily_norms(
            user["gender"],
            user["age"],
            user["height"],
            weight,
            user["activity"],
            user["goal"],
        )

        await db.upsert_user(
            telegram_id,
            weight=weight,
            calories_norm=norms["calories"],
            protein_norm=norms["protein"],
            fat_norm=norms["fat"],
            carbs_norm=norms["carbs"],
        )

    return json_response({"ok": True})


async def handle_weight_history(
    request: web.Request,
) -> web.Response:
    db: Database = request.app["db"]
    telegram_id = await get_telegram_id(request)

    logs = await db.get_weight_history(
        telegram_id,
        limit=20,
    )

    return json_response(
        {
            "items": [
                {
                    "weight": row["weight"],
                    "logged_at": row["logged_at"],
                }
                for row in logs
            ]
        }
    )


# ============================================================
# ГЛАВНАЯ
# ============================================================

async def handle_home(request: web.Request) -> web.Response:
    db: Database = request.app["db"]
    telegram_id = await get_telegram_id(request)

    user = await db.get_user(telegram_id)

    if not user or not user["calories_norm"]:
        return json_response(
            {"registered": False}
        )

    totals = await db.day_totals(telegram_id)
    meals = await db.get_meals_for_day(telegram_id)

    today = date.today()

    calories_norm = float(
        user["calories_norm"]
    )

    calories = float(
        totals["calories"]
    )

    percent = int(
        round(
            min(
                999,
                (
                    calories / calories_norm * 100
                    if calories_norm
                    else 0
                ),
            )
        )
    )

    return json_response(
        {
            "registered": True,
            "date_label": (
                f"Сегодня, "
                f"{WEEKDAYS[today.weekday()]}"
            ),
            "user": _public_user(user),
            "totals": totals,
            "percent": percent,
            "remaining": max(
                0,
                round(calories_norm - calories),
            ),
            "meals": [
                _meal_dict(meal)
                for meal in meals
            ],
            "recent": [
                _meal_dict(meal)
                for meal in list(meals)[-5:][::-1]
            ],
        }
    )


# ============================================================
# ДНЕВНИК
# ============================================================

async def handle_meals(request: web.Request) -> web.Response:
    db: Database = request.app["db"]
    telegram_id = await get_telegram_id(request)

    day_str = request.query.get("date")

    try:
        day = (
            date.fromisoformat(day_str)
            if day_str
            else date.today()
        )
    except ValueError:
        raise web.HTTPBadRequest(
            text="Invalid date"
        )

    meals = await db.get_meals_for_day(
        telegram_id,
        day,
    )

    totals = await db.day_totals(
        telegram_id,
        day,
    )

    return json_response(
        {
            "date": day.isoformat(),
            "meals": [
                _meal_dict(meal)
                for meal in meals
            ],
            "totals": totals,
        }
    )


async def handle_meals_add(
    request: web.Request,
) -> web.Response:
    db: Database = request.app["db"]
    telegram_id = await get_telegram_id(request)

    try:
        body = await request.json()

        meal_type = body.get(
            "meal_type",
            "snack",
        )

        weight_g = float(
            body["weight_g"]
        )

    except (KeyError, TypeError, ValueError):
        raise web.HTTPBadRequest(
            text="Invalid meal data"
        )

    if meal_type not in MEAL_LABELS:
        raise web.HTTPBadRequest(
            text="Invalid meal type"
        )

    if not 1 <= weight_g <= 5000:
        raise web.HTTPBadRequest(
            text="Invalid weight"
        )

    product_id = body.get("product_id")

    if product_id:
        try:
            product_id = int(product_id)
        except (TypeError, ValueError):
            raise web.HTTPBadRequest(
                text="Invalid product id"
            )

        product = await db.get_product(
            product_id
        )

        if not product:
            raise web.HTTPNotFound(
                text="Product not found"
            )

        name = product["name"]

        nutrients = scale_nutrients(
            product["calories"],
            product["protein"],
            product["fat"],
            product["carbs"],
            weight_g,
        )

        database_product_id = int(
            product["id"]
        )

    else:
        name = (
            body.get("name") or ""
        ).strip()

        if not name:
            raise web.HTTPBadRequest(
                text="Product name required"
            )

        try:
            calories_100 = float(
                body["calories"]
            )
            protein_100 = float(
                body.get("protein", 0)
            )
            fat_100 = float(
                body.get("fat", 0)
            )
            carbs_100 = float(
                body.get("carbs", 0)
            )
        except (TypeError, ValueError, KeyError):
            raise web.HTTPBadRequest(
                text="Invalid nutrient data"
            )

        category = (
            body.get("category")
            or "Пользовательский"
        )

        off_id = body.get("off_id")

        synonym = (
            f"off:{off_id}"
            if off_id
            else ""
        )

        database_product_id = (
            await db.ensure_product(
                name=name,
                category=category,
                calories=calories_100,
                protein=protein_100,
                fat=fat_100,
                carbs=carbs_100,
                owner_id=telegram_id,
                synonym=synonym,
            )
        )

        nutrients = scale_nutrients(
            calories_100,
            protein_100,
            fat_100,
            carbs_100,
            weight_g,
        )

    meal_id = await db.add_meal(
        telegram_id=telegram_id,
        product_id=database_product_id,
        product_name=name,
        weight_g=weight_g,
        meal_type=meal_type,
        **nutrients,
    )

    return json_response(
        {
            "ok": True,
            "id": meal_id,
            **nutrients,
        }
    )


async def handle_meals_delete(
    request: web.Request,
) -> web.Response:
    db: Database = request.app["db"]
    telegram_id = await get_telegram_id(request)

    try:
        meal_id = int(
            request.match_info["meal_id"]
        )
    except ValueError:
        raise web.HTTPBadRequest(
            text="Invalid meal id"
        )

    ok = await db.delete_meal(
        meal_id,
        telegram_id,
    )

    return json_response(
        {"ok": ok}
    )


async def handle_meals_patch(
    request: web.Request,
) -> web.Response:
    db: Database = request.app["db"]
    telegram_id = await get_telegram_id(request)

    try:
        meal_id = int(
            request.match_info["meal_id"]
        )
    except ValueError:
        raise web.HTTPBadRequest(
            text="Invalid meal id"
        )

    meal = await db.get_meal(
        meal_id
    )

    if (
        not meal
        or meal["telegram_id"] != telegram_id
    ):
        raise web.HTTPNotFound()

    try:
        body = await request.json()
    except Exception:
        raise web.HTTPBadRequest(
            text="Invalid JSON"
        )

    fields: dict[str, Any] = {}

    if "meal_type" in body:
        meal_type = body["meal_type"]

        if meal_type not in MEAL_LABELS:
            raise web.HTTPBadRequest(
                text="Invalid meal type"
            )

        fields["meal_type"] = meal_type

    if "weight_g" in body:
        try:
            weight_g = float(
                body["weight_g"]
            )
        except (TypeError, ValueError):
            raise web.HTTPBadRequest(
                text="Invalid weight"
            )

        if not 1 <= weight_g <= 5000:
            raise web.HTTPBadRequest(
                text="Invalid weight"
            )

        product = await db.get_product(
            meal["product_id"]
        )

        if product:
            nutrients = scale_nutrients(
                product["calories"],
                product["protein"],
                product["fat"],
                product["carbs"],
                weight_g,
            )

            fields.update(
                weight_g=weight_g,
                **nutrients,
            )

    if fields:
        await db.update_meal(
            meal_id,
            **fields,
        )

    return json_response(
        {"ok": True}
    )


# ============================================================
# ПРОДУКТЫ
# ============================================================

async def handle_products_search(
    request: web.Request,
) -> web.Response:
    db: Database = request.app["db"]

    # Авторизация вызывается один раз
    telegram_id = await get_telegram_id(
        request
    )

    query = (
        request.query.get("q") or ""
    ).strip()

    if len(query) < 2:
        return json_response(
            {
                "local": [],
                "off": [],
            }
        )

    local_rows = await db.search_products(
        query,
        limit=8,
        owner_id=telegram_id,
    )

    local = [
        {
            "source": "local",
            "id": row["id"],
            "name": row["name"],
            "category": row["category"],
            "calories": row["calories"],
            "protein": row["protein"],
            "fat": row["fat"],
            "carbs": row["carbs"],
            "owner_id": row["owner_id"],
        }
        for row in local_rows
    ]

    off = await search_open_food_facts(
        query,
        limit=10,
    )

    return json_response(
        {
            "local": local,
            "off": off,
        }
    )


async def handle_products_add(
    request: web.Request,
) -> web.Response:
    db: Database = request.app["db"]
    telegram_id = await get_telegram_id(
        request
    )

    try:
        body = await request.json()

        name = str(
            body.get("name", "")
        ).strip()

        category = str(
            body.get("category")
            or "Другое"
        ).strip()

        calories = float(
            body.get("calories", 0)
        )

        protein = float(
            body.get("protein", 0)
        )

        fat = float(
            body.get("fat", 0)
        )

        carbs = float(
            body.get("carbs", 0)
        )

    except (TypeError, ValueError, KeyError):
        return json_response(
            {
                "error":
                    "Проверьте данные продукта"
            },
            status=400,
        )

    if len(name) < 2:
        return json_response(
            {
                "error":
                    "Укажите название продукта"
            },
            status=400,
        )

    if not (
        0 <= calories <= 5000
        and 0 <= protein <= 100
        and 0 <= fat <= 100
        and 0 <= carbs <= 100
    ):
        return json_response(
            {
                "error":
                    "Проверьте значения КБЖУ на 100 г"
            },
            status=400,
        )

    product_id = await db.add_product(
        name=name,
        category=category,
        calories=calories,
        protein=protein,
        fat=fat,
        carbs=carbs,
        owner_id=telegram_id,
        synonym=name.lower(),
    )

    return json_response(
        {
            "ok": True,
            "id": product_id,
        }
    )


# ============================================================
# СТАТИСТИКА
# ============================================================

async def handle_stats(
    request: web.Request,
) -> web.Response:
    db: Database = request.app["db"]
    telegram_id = await get_telegram_id(
        request
    )

    user = await db.get_user(
        telegram_id
    )

    if not user:
        raise web.HTTPBadRequest(
            text="User not registered"
        )

    period = request.query.get(
        "period",
        "today",
    )

    if period == "today":
        totals = await db.day_totals(
            telegram_id
        )

        return json_response(
            {
                "period": "today",
                "totals": totals,
                "norms": {
                    "calories": user["calories_norm"],
                    "protein": user["protein_norm"],
                    "fat": user["fat_norm"],
                    "carbs": user["carbs_norm"],
                },
            }
        )

    if period == "week":
        days = 7
    elif period == "month":
        days = 30
    else:
        raise web.HTTPBadRequest(
            text="Invalid period"
        )

    rows = await db.period_daily_calories(
        telegram_id,
        days=days,
    )

    return json_response(
        {
            "period": period,
            "days": [
                {
                    "day": row["day"],
                    "calories": row["calories"],
                    "protein": row["protein"],
                    "fat": row["fat"],
                    "carbs": row["carbs"],
                }
                for row in rows
            ],
        }
    )


# ============================================================
# РЕКОМЕНДАЦИИ
# ============================================================

async def handle_recommendations(
    request: web.Request,
) -> web.Response:
    db: Database = request.app["db"]
    telegram_id = await get_telegram_id(
        request
    )

    user = await db.get_user(
        telegram_id
    )

    if not user:
        raise web.HTTPBadRequest(
            text="User not registered"
        )

    totals = await db.day_totals(
        telegram_id
    )

    meals = await db.get_meals_for_day(
        telegram_id
    )

    tips = generate_recommendations(
        user,
        totals,
        meals,
    )

    for tip in tips:
        await db.save_recommendation(
            telegram_id,
            tip,
        )

    return json_response(
        {
            "tips": tips
        }
    )