from aiogram import Router

from bot.handlers import diary, products, profile, start, stats


def setup_routers() -> Router:
    root = Router()
    root.include_router(start.router)
    root.include_router(diary.router)
    root.include_router(products.router)
    root.include_router(profile.router)
    root.include_router(stats.router)
    return root
