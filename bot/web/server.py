"""HTTP-сервер Mini App: статика + API."""

from __future__ import annotations

import logging
from pathlib import Path

from aiohttp import web

from bot.config import WEBAPP_DIR, WEB_HOST, WEB_PORT
from bot.database import Database
from bot.web.api import create_api_app

logger = logging.getLogger(__name__)


async def start_web_server(db: Database) -> web.AppRunner:
    # Один общий aiohttp-приложение с API и статикой
    app = create_api_app(db)

    static_path = Path(WEBAPP_DIR)
    if not static_path.exists():
        raise FileNotFoundError(f"webapp folder not found: {static_path}")

    async def index(_request: web.Request) -> web.FileResponse:
        return web.FileResponse(static_path / "index.html")

    app.router.add_get("/", index)
    app.router.add_static("/css/", path=static_path / "css", name="css")
    app.router.add_static("/js/", path=static_path / "js", name="js")

    assets = static_path / "assets"
    if assets.exists():
        app.router.add_static("/assets/", path=assets, name="assets")

    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(runner, WEB_HOST, WEB_PORT)
    await site.start()

    logger.info("Mini App server: http://%s:%s", WEB_HOST, WEB_PORT)

    return runner