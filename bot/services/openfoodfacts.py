from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)

# Русскоязычный зеркальный поиск OFF
SEARCH_URL = "https://world.openfoodfacts.org/cgi/search.pl"


def _nutrient(n: dict, *keys: str) -> float:
    for key in keys:
        val = n.get(key)
        if val is None:
            continue
        try:
            return round(float(val), 1)
        except (TypeError, ValueError):
            continue
    return 0.0


def _parse_product(p: dict[str, Any]) -> dict[str, Any] | None:
    name = (
        p.get("product_name_ru")
        or p.get("product_name")
        or p.get("generic_name_ru")
        or p.get("generic_name")
        or ""
    ).strip()
    if not name:
        return None

    nutriments = p.get("nutriments") or {}
    calories = _nutrient(
        nutriments,
        "energy-kcal_100g",
        "energy-kcal",
        "energy_100g",
    )
    if calories <= 0:
        kj = _nutrient(nutriments, "energy-kj_100g", "energy_100g")
        if kj > 200:  # скорее кДж
            calories = round(kj / 4.184, 1)

    protein = _nutrient(nutriments, "proteins_100g", "proteins")
    fat = _nutrient(nutriments, "fat_100g", "fat")
    carbs = _nutrient(nutriments, "carbohydrates_100g", "carbohydrates")

    if calories <= 0 and protein <= 0 and fat <= 0 and carbs <= 0:
        return None

    cats = p.get("categories_tags") or []
    category = "Open Food Facts"
    if cats:
        raw = str(cats[0]).replace("en:", "").replace("ru:", "").replace("-", " ")
        category = raw[:40].title() if raw else category

    brand = (p.get("brands") or "").split(",")[0].strip()
    display = f"{name}" + (f" ({brand})" if brand else "")

    return {
        "source": "off",
        "off_id": p.get("code") or p.get("_id") or "",
        "name": display[:120],
        "category": category,
        "calories": calories,
        "protein": protein,
        "fat": fat,
        "carbs": carbs,
        "image": (p.get("image_front_small_url") or p.get("image_thumb_url") or ""),
    }


async def search_open_food_facts(query: str, limit: int = 12) -> list[dict[str, Any]]:
    query = (query or "").strip()
    if len(query) < 2:
        return []

    params = {
        "search_terms": query,
        "search_simple": 1,
        "action": "process",
        "json": 1,
        "page_size": limit,
        "fields": (
            "code,product_name,product_name_ru,generic_name,generic_name_ru,"
            "brands,categories_tags,nutriments,image_front_small_url,image_thumb_url"
        ),
    }
    timeout = aiohttp.ClientTimeout(total=12)
    headers = {"User-Agent": "CalorieCalculatorBot/1.0 (student project)"}
    data = None
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            for attempt in range(3):
                async with session.get(SEARCH_URL, params=params, headers=headers) as resp:
                    if resp.status == 200:
                        data = await resp.json(content_type=None)
                        break
                    logger.warning("OFF status %s (attempt %s)", resp.status, attempt + 1)
                await asyncio.sleep(0.6 * (attempt + 1))
    except Exception as exc:
        logger.warning("OFF request failed: %s", exc)
        return []

    if not data:
        return []

    results: list[dict[str, Any]] = []
    for product in data.get("products") or []:
        parsed = _parse_product(product)
        if parsed:
            results.append(parsed)
        if len(results) >= limit:
            break
    return results
