from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import MenuButtonWebApp, WebAppInfo

from bot.config import BOT_TOKEN, DB_PATH, WEBAPP_URL, WEB_PORT
from bot.data.seed_products import ALL_SEED_PRODUCTS
from bot.database import Database
from bot.handlers import setup_routers
from bot.web.server import start_web_server


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    db = Database(DB_PATH)
    await db.connect()
    await db.seed_products(ALL_SEED_PRODUCTS)

    runner = await start_web_server(db)

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    if WEBAPP_URL:
        try:
            await bot.set_chat_menu_button(
                menu_button=MenuButtonWebApp(
                    text="📱 CalFlow",
                    web_app=WebAppInfo(url=WEBAPP_URL),
                )
            )
            logging.info("Кнопка меню Mini App настроена")
        except Exception:
            logging.exception("Не удалось настроить кнопку меню Mini App")

    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(setup_routers())

    @dp.update.middleware()
    async def db_middleware(handler, event, data):
        data["db"] = db
        return await handler(event, data)

    if WEBAPP_URL:
        logging.info("Mini App URL: %s", WEBAPP_URL)
    else:
        logging.warning(
            "WEBAPP_URL не задан в .env — кнопка Mini App не откроется в Telegram. "
            "Поднимите HTTPS-туннель (ngrok http %s) и пропишите URL в .env",
            WEB_PORT,
        )

    logging.info("Бот запущен")
    try:
        await dp.start_polling(bot)
    finally:
        await runner.cleanup()
        await db.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
