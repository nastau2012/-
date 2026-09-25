from __future__ import annotations

import aiosqlite
from datetime import date, datetime
from pathlib import Path
from typing import Any, Optional


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._conn: Optional[aiosqlite.Connection] = None

    async def connect(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = await aiosqlite.connect(self.path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.execute("PRAGMA foreign_keys = ON")
        await self._create_tables()

    async def close(self) -> None:
        if self._conn:
            await self._conn.close()
            self._conn = None

    @property
    def conn(self) -> aiosqlite.Connection:
        if self._conn is None:
            raise RuntimeError("База данных не подключена")
        return self._conn

    async def _create_tables(self) -> None:
        await self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                telegram_id INTEGER PRIMARY KEY,
                gender TEXT,
                age INTEGER,
                height REAL,
                weight REAL,
                activity TEXT,
                goal TEXT,
                calories_norm REAL,
                protein_norm REAL,
                fat_norm REAL,
                carbs_norm REAL,
                registered_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS weight_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                weight REAL NOT NULL,
                logged_at TEXT NOT NULL,
                FOREIGN KEY (telegram_id) REFERENCES users(telegram_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                calories REAL NOT NULL,
                protein REAL NOT NULL,
                fat REAL NOT NULL,
                carbs REAL NOT NULL,
                owner_id INTEGER,
                synonym TEXT DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS meal_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                product_name TEXT NOT NULL,
                weight_g REAL NOT NULL,
                meal_type TEXT NOT NULL,
                eaten_at TEXT NOT NULL,
                calories REAL NOT NULL,
                protein REAL NOT NULL,
                fat REAL NOT NULL,
                carbs REAL NOT NULL,
                FOREIGN KEY (telegram_id) REFERENCES users(telegram_id) ON DELETE CASCADE,
                FOREIGN KEY (product_id) REFERENCES products(id)
            );

            CREATE TABLE IF NOT EXISTS templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (telegram_id) REFERENCES users(telegram_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS template_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                template_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                weight_g REAL NOT NULL,
                FOREIGN KEY (template_id) REFERENCES templates(id) ON DELETE CASCADE,
                FOREIGN KEY (product_id) REFERENCES products(id)
            );

            CREATE TABLE IF NOT EXISTS recommendations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                text TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                is_read INTEGER DEFAULT 0,
                FOREIGN KEY (telegram_id) REFERENCES users(telegram_id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_products_name ON products(name);
            CREATE INDEX IF NOT EXISTS idx_meals_user_date ON meal_entries(telegram_id, eaten_at);
            """
        )
        await self.conn.commit()


    async def get_user(self, telegram_id: int) -> Optional[aiosqlite.Row]:
        cur = await self.conn.execute(
            "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
        )
        return await cur.fetchone()

    async def upsert_user(self, telegram_id: int, **fields: Any) -> None:
        existing = await self.get_user(telegram_id)
        if existing is None:
            cols = ["telegram_id"] + list(fields.keys())
            placeholders = ", ".join("?" * len(cols))
            await self.conn.execute(
                f"INSERT INTO users ({', '.join(cols)}) VALUES ({placeholders})",
                [telegram_id, *fields.values()],
            )
        else:
            if fields:
                sets = ", ".join(f"{k} = ?" for k in fields)
                await self.conn.execute(
                    f"UPDATE users SET {sets} WHERE telegram_id = ?",
                    [*fields.values(), telegram_id],
                )
        await self.conn.commit()

    async def is_registered(self, telegram_id: int) -> bool:
        user = await self.get_user(telegram_id)
        return bool(user and user["gender"] and user["calories_norm"])


    async def add_weight_log(self, telegram_id: int, weight: float) -> None:
        await self.conn.execute(
            "INSERT INTO weight_logs (telegram_id, weight, logged_at) VALUES (?, ?, ?)",
            (telegram_id, weight, datetime.now().isoformat(timespec="seconds")),
        )
        await self.upsert_user(telegram_id, weight=weight)
        await self.conn.commit()

    async def get_weight_history(self, telegram_id: int, limit: int = 10) -> list[aiosqlite.Row]:
        cur = await self.conn.execute(
            """
            SELECT * FROM weight_logs
            WHERE telegram_id = ?
            ORDER BY logged_at DESC
            LIMIT ?
            """,
            (telegram_id, limit),
        )
        return await cur.fetchall()

    async def count_products(self) -> int:
        cur = await self.conn.execute("SELECT COUNT(*) AS c FROM products")
        row = await cur.fetchone()
        return int(row["c"]) if row else 0

    async def seed_products(self, products: list[tuple]) -> None:
        """Добавляет отсутствующие системные продукты, не трогая пользовательские записи."""
        for product in products:
            name, category, calories, protein, fat, carbs, synonym = product
            cur = await self.conn.execute(
                "SELECT id FROM products WHERE lower(name) = lower(?) AND owner_id IS NULL LIMIT 1",
                (name,),
            )
            if await cur.fetchone() is None:
                await self.conn.execute(
                    """
                    INSERT INTO products (name, category, calories, protein, fat, carbs, owner_id, synonym)
                    VALUES (?, ?, ?, ?, ?, ?, NULL, ?)
                    """,
                    product,
                )
        await self.conn.commit()

    async def search_products(
        self, query: str, limit: int = 10, owner_id: Optional[int] = None
    ) -> list[aiosqlite.Row]:
        q = f"%{query.strip().lower()}%"
        if owner_id is None:
            cur = await self.conn.execute(
                """
                SELECT * FROM products
                WHERE owner_id IS NULL
                  AND (lower(name) LIKE ? OR lower(IFNULL(synonym, '')) LIKE ?)
                ORDER BY name
                LIMIT ?
                """,
                (q, q, limit),
            )
        else:
            cur = await self.conn.execute(
                """
                SELECT * FROM products
                WHERE (owner_id IS NULL OR owner_id = ?)
                  AND (lower(name) LIKE ? OR lower(IFNULL(synonym, '')) LIKE ?)
                ORDER BY CASE WHEN owner_id = ? THEN 0 ELSE 1 END, name
                LIMIT ?
                """,
                (owner_id, q, q, owner_id, limit),
            )
        return await cur.fetchall()

    async def get_product(self, product_id: int) -> Optional[aiosqlite.Row]:
        cur = await self.conn.execute("SELECT * FROM products WHERE id = ?", (product_id,))
        return await cur.fetchone()

    async def add_product(
        self,
        name: str,
        category: str,
        calories: float,
        protein: float,
        fat: float,
        carbs: float,
        owner_id: Optional[int] = None,
        synonym: str = "",
    ) -> int:
        cur = await self.conn.execute(
            """
            INSERT INTO products (name, category, calories, protein, fat, carbs, owner_id, synonym)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (name, category, calories, protein, fat, carbs, owner_id, synonym),
        )
        await self.conn.commit()
        return cur.lastrowid

    async def find_by_synonym(self, synonym: str) -> Optional[aiosqlite.Row]:
        cur = await self.conn.execute(
            "SELECT * FROM products WHERE synonym = ? LIMIT 1", (synonym,)
        )
        return await cur.fetchone()

    async def ensure_product(
        self,
        name: str,
        category: str,
        calories: float,
        protein: float,
        fat: float,
        carbs: float,
        owner_id: Optional[int] = None,
        synonym: str = "",
    ) -> int:
        if synonym:
            existing = await self.find_by_synonym(synonym)
            if existing:
                return int(existing["id"])
        return await self.add_product(
            name, category, calories, protein, fat, carbs, owner_id, synonym
        )

    async def list_products(
        self, owner_id: Optional[int] = None, limit: int = 20, offset: int = 0
    ) -> list[aiosqlite.Row]:
        if owner_id is None:
            cur = await self.conn.execute(
                "SELECT * FROM products ORDER BY name LIMIT ? OFFSET ?",
                (limit, offset),
            )
        else:
            cur = await self.conn.execute(
                """
                SELECT * FROM products
                WHERE owner_id IS NULL OR owner_id = ?
                ORDER BY name LIMIT ? OFFSET ?
                """,
                (owner_id, limit, offset),
            )
        return await cur.fetchall()

    async def delete_product(self, product_id: int, owner_id: int) -> bool:
        cur = await self.conn.execute(
            "DELETE FROM products WHERE id = ? AND owner_id = ?",
            (product_id, owner_id),
        )
        await self.conn.commit()
        return cur.rowcount > 0

    async def get_categories(self) -> list[str]:
        cur = await self.conn.execute(
            "SELECT DISTINCT category FROM products ORDER BY category"
        )
        rows = await cur.fetchall()
        return [r["category"] for r in rows]

    # --- Meals ---

    async def add_meal(
        self,
        telegram_id: int,
        product_id: int,
        product_name: str,
        weight_g: float,
        meal_type: str,
        calories: float,
        protein: float,
        fat: float,
        carbs: float,
        eaten_at: Optional[str] = None,
    ) -> int:
        when = eaten_at or datetime.now().isoformat(timespec="seconds")
        cur = await self.conn.execute(
            """
            INSERT INTO meal_entries (
                telegram_id, product_id, product_name, weight_g, meal_type,
                eaten_at, calories, protein, fat, carbs
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                telegram_id,
                product_id,
                product_name,
                weight_g,
                meal_type,
                when,
                calories,
                protein,
                fat,
                carbs,
            ),
        )
        await self.conn.commit()
        return cur.lastrowid

    async def get_meals_for_day(
        self, telegram_id: int, day: Optional[date] = None
    ) -> list[aiosqlite.Row]:
        day = day or date.today()
        day_str = day.isoformat()
        cur = await self.conn.execute(
            """
            SELECT * FROM meal_entries
            WHERE telegram_id = ? AND date(eaten_at) = date(?)
            ORDER BY eaten_at
            """,
            (telegram_id, day_str),
        )
        return await cur.fetchall()

    async def get_meal(self, meal_id: int) -> Optional[aiosqlite.Row]:
        cur = await self.conn.execute(
            "SELECT * FROM meal_entries WHERE id = ?", (meal_id,)
        )
        return await cur.fetchone()

    async def update_meal(self, meal_id: int, **fields: Any) -> None:
        if not fields:
            return
        sets = ", ".join(f"{k} = ?" for k in fields)
        await self.conn.execute(
            f"UPDATE meal_entries SET {sets} WHERE id = ?",
            [*fields.values(), meal_id],
        )
        await self.conn.commit()

    async def delete_meal(self, meal_id: int, telegram_id: int) -> bool:
        cur = await self.conn.execute(
            "DELETE FROM meal_entries WHERE id = ? AND telegram_id = ?",
            (meal_id, telegram_id),
        )
        await self.conn.commit()
        return cur.rowcount > 0

    async def day_totals(
        self, telegram_id: int, day: Optional[date] = None
    ) -> dict[str, float]:
        day = day or date.today()
        cur = await self.conn.execute(
            """
            SELECT
                COALESCE(SUM(calories), 0) AS calories,
                COALESCE(SUM(protein), 0) AS protein,
                COALESCE(SUM(fat), 0) AS fat,
                COALESCE(SUM(carbs), 0) AS carbs
            FROM meal_entries
            WHERE telegram_id = ? AND date(eaten_at) = date(?)
            """,
            (telegram_id, day.isoformat()),
        )
        row = await cur.fetchone()
        return {
            "calories": float(row["calories"]),
            "protein": float(row["protein"]),
            "fat": float(row["fat"]),
            "carbs": float(row["carbs"]),
        }

    async def period_daily_calories(
        self, telegram_id: int, days: int = 7
    ) -> list[aiosqlite.Row]:
        cur = await self.conn.execute(
            """
            SELECT date(eaten_at) AS day, SUM(calories) AS calories,
                   SUM(protein) AS protein, SUM(fat) AS fat, SUM(carbs) AS carbs
            FROM meal_entries
            WHERE telegram_id = ?
              AND date(eaten_at) >= date('now', ?)
            GROUP BY date(eaten_at)
            ORDER BY day
            """,
            (telegram_id, f"-{days - 1} days"),
        )
        return await cur.fetchall()

    # --- Templates ---

    async def create_template(self, telegram_id: int, name: str) -> int:
        cur = await self.conn.execute(
            "INSERT INTO templates (telegram_id, name) VALUES (?, ?)",
            (telegram_id, name),
        )
        await self.conn.commit()
        return cur.lastrowid

    async def add_template_item(
        self, template_id: int, product_id: int, weight_g: float
    ) -> None:
        await self.conn.execute(
            """
            INSERT INTO template_items (template_id, product_id, weight_g)
            VALUES (?, ?, ?)
            """,
            (template_id, product_id, weight_g),
        )
        await self.conn.commit()

    async def list_templates(self, telegram_id: int) -> list[aiosqlite.Row]:
        cur = await self.conn.execute(
            "SELECT * FROM templates WHERE telegram_id = ? ORDER BY name",
            (telegram_id,),
        )
        return await cur.fetchall()

    async def get_template_items(self, template_id: int) -> list[aiosqlite.Row]:
        cur = await self.conn.execute(
            """
            SELECT ti.*, p.name, p.calories, p.protein, p.fat, p.carbs
            FROM template_items ti
            JOIN products p ON p.id = ti.product_id
            WHERE ti.template_id = ?
            """,
            (template_id,),
        )
        return await cur.fetchall()

    async def delete_template(self, template_id: int, telegram_id: int) -> bool:
        cur = await self.conn.execute(
            "DELETE FROM templates WHERE id = ? AND telegram_id = ?",
            (template_id, telegram_id),
        )
        await self.conn.commit()
        return cur.rowcount > 0


    async def save_recommendation(self, telegram_id: int, text: str) -> None:
        await self.conn.execute(
            "INSERT INTO recommendations (telegram_id, text) VALUES (?, ?)",
            (telegram_id, text),
        )
        await self.conn.commit()

    async def get_recent_recommendations(
        self, telegram_id: int, limit: int = 5
    ) -> list[aiosqlite.Row]:
        cur = await self.conn.execute(
            """
            SELECT * FROM recommendations
            WHERE telegram_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (telegram_id, limit),
        )
        return await cur.fetchall()

    async def mark_recommendations_read(self, telegram_id: int) -> None:
        await self.conn.execute(
            "UPDATE recommendations SET is_read = 1 WHERE telegram_id = ?",
            (telegram_id,),
        )
        await self.conn.commit()
