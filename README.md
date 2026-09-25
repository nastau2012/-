# Калькулятор калорий — Telegram Mini App + бот

## Стек
- Python, aiogram 3, SQLite
- Mini App: HTML/CSS/JS (окно внутри Telegram)
- Продукты: локальная база + **Open Food Facts API**

## Запуск

### 1. Зависимости
```
pip install -r requirements.txt
```

### 2. Файл `.env`
Скопируйте `.env.example` → `.env` и укажите:
- `BOT_TOKEN` — от @BotFather
- `WEBAPP_URL` — HTTPS-адрес (см. ниже)

### 3. HTTPS для Mini App (ngrok)
Telegram открывает Mini App **только по HTTPS**.

1. Установите [ngrok](https://ngrok.com/)
2. Запустите бота (`python main.py`) — сервер на порту **8080**
3. В другом терминале:
   ```
   ngrok http 8080
   ```
4. Скопируйте URL вида `https://xxxx.ngrok-free.app` в `.env`:
   ```
   WEBAPP_URL=https://xxxx.ngrok-free.app
   ```
5. Перезапустите `main.py`
6. В Telegram: `/start` → **«Открыть калькулятор»**

### 4. Проверка в браузере
В `.env` задайте `DEV_TELEGRAM_ID=ваш_id` и откройте `http://127.0.0.1:8080`

## Возможности Mini App
- Круг прогресса калорий и полоски БЖУ
- Дневник / добавление приёма пищи
- Поиск продуктов (своя БД + Open Food Facts)
- Статистика и рекомендации
- Профиль и замеры веса

Чат-меню бота по-прежнему работает как запасной вариант.


## Важное для Mini App и телефона

Mini App открывается для авторизации через inline-кнопку сообщения бота или через кнопку меню бота. Reply Keyboard-кнопка для запуска Mini App не используется, потому что Telegram не передаёт через неё `initData`, необходимый для авторизации персонального приложения.

Для телефона: компьютер с запущенным `main.py` и `cloudflared` должен оставаться включённым. Телефон должен иметь доступ к HTTPS-адресу Cloudflare Tunnel; если сеть его блокирует, включите VPN на телефоне.
