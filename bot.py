import asyncio
import logging
import json
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.client.default import DefaultBotProperties
import sqlite3

BOT_TOKEN = "8702014027:AAEN5quGp1uSH45Xaa3W-HOmSTEPYjn4d8o"
CHANNEL_USERNAME = "ilyshatgk" 
GAME_URL = "https://confity127-tech.github.io/flappy-ton/"

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()

# Инициализация Базы Данных
def init_db():
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            high_score INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

# Функция проверки подписки
async def check_subscription(user_id: int) -> bool:
    try:
        # Пытаемся получить статус пользователя в канале
        member = await bot.get_chat_member(chat_id=f"@{CHANNEL_USERNAME}", user_id=user_id)
        if member.status in ["member", "administrator", "creator"]:
            return True
        return False
    except Exception as e:
        logging.error(f"Ошибка проверки подписки: {e}")
        # Если канал еще не создан или бота там нет в админах, временно пропускаем
        return True 

@dp.message(Command("start"))
async def start_cmd(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username or "Anonymous"
    
    # Сохраняем пользователя в БД
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)", (user_id, username))
    conn.commit()
    conn.close()

    is_subscribed = await check_subscription(user_id)
    
    if not is_subscribed:
        # Если не подписан — требуем подписку
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="1. Подписаться на Навигатор", url=f"https://t.me/{CHANNEL_USERNAME}")],
            [InlineKeyboardButton(text="2. Я подписался! 🚀", callback_data="check_sub")]
        ])
        await message.answer(
            f"Привет, {message.from_user.first_name}!\n\n"
            f"Чтобы открыть игру и принять участие в розыгрыше, подпишись на наш второй проект — Навигатор Скидок!",
            reply_markup=keyboard
        )
    else:
        # Если подписан — даем кнопку игры
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎮 Играть в Flappy Jet", web_app=WebAppInfo(url=GAME_URL))]
        ])
        await message.answer(
            f"Добро пожаловать обратно, {message.from_user.first_name}!\n"
            f"Твой рекорд готов к новым высотам. Жми кнопку ниже 👇",
            reply_markup=keyboard
        )

# Обработка данных из игры (когда игрок проиграл)
@dp.message(F.web_app_data)
async def handle_game_data(message: Message):
    try:
        data = json.loads(message.web_app_data.data)
        score = int(data.get("score", 0))
        user_id = message.from_user.id
        
        conn = sqlite3.connect("users.db")
        cursor = conn.cursor()
        
        # Получаем текущий рекорд
        cursor.execute("SELECT high_score FROM users WHERE user_id = ?", (user_id,))
        res = cursor.fetchone()
        current_high = res[0] if res else 0
        
        if score > current_high:
            cursor.execute("UPDATE users SET high_score = ? WHERE user_id = ?", (score, user_id))
            conn.commit()
            await message.answer(f"🔥 НОВЫЙ РЕКОРД! Ты набрал {score} очков! Результат сохранен в таблицу лидеров.")
        else:
            await message.answer(f"Игра окончена! Твой результат: {score} очков. Твой лучший рекорд: {current_high}.")
            
        conn.close()
    except Exception as e:
        logging.error(f"Ошибка обработки данных игры: {e}")

@dp.callback_query(F.data == "check_sub")
async def check_callback(callback: F.CallbackQuery):
    is_subscribed = await check_subscription(callback.from_user.id)
    if is_subscribed:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎮 Играть в Flappy Jet", web_app=WebAppInfo(url=GAME_URL))]
        ])
        await callback.message.edit_text("Успешно! Подписка подтверждена. Погнали играть! 🔥", reply_markup=keyboard)
    else:
        await callback.answer("Ты еще не подписался! Пожалуйста, подпишись на канал, чтобы продолжить.", show_alert=True)

async def main():
    init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())