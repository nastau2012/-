from pathlib import Path

from dotenv import load_dotenv
import os

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
DB_PATH = BASE_DIR / "data" / "calories.db"
WEBAPP_DIR = BASE_DIR / "webapp"

# Mini App
WEB_HOST = os.getenv("WEB_HOST", "0.0.0.0")
WEB_PORT = int(os.getenv("WEB_PORT", "8080"))
WEBAPP_URL = os.getenv("WEBAPP_URL", "").rstrip("/")
DEV_TELEGRAM_ID = int(os.getenv("DEV_TELEGRAM_ID", "0") or 0)

ACTIVITY_FACTORS = {
    "sedentary": 1.2,
    "light": 1.375,
    "moderate": 1.55,
    "active": 1.725,
    "very_active": 1.9,
}

ACTIVITY_LABELS = {
    "sedentary": "🪑 Малоподвижный",
    "light": "🚶 Лёгкая активность",
    "moderate": "🏃 Средняя активность",
    "active": "💪 Высокая активность",
    "very_active": "🔥 Очень высокая",
}

GOAL_LABELS = {
    "lose": "📉 Похудение",
    "maintain": "⚖️ Поддержание веса",
    "gain": "📈 Набор массы",
}

MEAL_LABELS = {
    "breakfast": "Завтрак",
    "lunch": "Обед",
    "dinner": "Ужин",
    "snack": "Перекус",
}

GENDER_LABELS = {
    "male": "Мужской",
    "female": "Женский",
}