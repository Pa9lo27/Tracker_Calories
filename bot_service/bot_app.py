import os
import httpx
import re
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters, ContextTypes
)
from google import genai
from PIL import Image

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

STATE_SERVICE_URL = os.getenv("STATE_SERVICE_URL", "http://127.0.0.1:8000")
CALORIE_SERVICE_URL = os.getenv("CALORIE_SERVICE_URL", "http://127.0.0.1:8001")

ALLOWED_USERS = [992113841, 987654321, 555555555, 777777777]

ai_client = genai.Client(api_key=GEMINI_API_KEY)

GEMINI_CONFIG = {"thinking_config": {"thinking_budget": -1}}


# --- ХЕЛПЕРИ ---

def get_main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Додати їжу", callback_data="add_food")],
        [InlineKeyboardButton("Статистика", callback_data="stats_menu")]
    ])


def get_after_meal_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Кінець", callback_data="end")],
        [InlineKeyboardButton("Статистика", callback_data="stats_menu")],
        [InlineKeyboardButton("Додати їжу", callback_data="add_food")]
    ])


async def save_meal_to_db(user_id: int, calories: int, proteins: float, fats: float, carbs: float):
    try:
        async with httpx.AsyncClient() as client:
            await client.post(f"{CALORIE_SERVICE_URL}/log_meal", json={
                "user_id": user_id, "calories": calories,
                "proteins": proteins, "fats": fats, "carbs": carbs
            }, timeout=5)
    except Exception as e:
        print(f"[ERROR] Не вдалося зберегти в БД: {e}")


async def extract_data_from_text(text: str):
    try:
        calories = int(re.search(r'Всього[:\s~*]+(\d+)', text).group(1))
        proteins = float(re.search(r'Б:\s*(\d+(?:\.\d+)?)г', text).group(1))
        fats = float(re.search(r'Ж:\s*(\d+(?:\.\d+)?)г', text).group(1))
        carbs = float(re.search(r'В:\s*(\d+(?:\.\d+)?)г', text).group(1))
        return calories, proteins, fats, carbs
    except Exception as e:
        print(f"[DEBUG] Помилка парсингу: {e}")
        return 0, 0.0, 0.0, 0.0


# --- ХЕЛПЕРИ ДЛЯ СТАНІВ ---

async def get_user_state(user_id: int) -> str:
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{STATE_SERVICE_URL}/state/{user_id}", timeout=5)
            return r.json().get("state", "start")
    except:
        return "start"


async def set_user_state(user_id: int, state: str):
    try:
        async with httpx.AsyncClient() as client:
            await client.post(f"{STATE_SERVICE_URL}/state", json={"user_id": user_id, "state": state}, timeout=5)
    except Exception as e:
        print(f"[ERROR] Не вдалося оновити стан: {e}")


# --- ОБРОБНИКИ ТЕЛЕГРАМ ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ALLOWED_USERS:
        return

    await set_user_state(user_id, "start")
    await update.message.reply_text("Привіт! Обери дію:", reply_markup=get_main_keyboard())


async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "add_food":
        await set_user_state(user_id, "waiting_for_food")
        await query.edit_message_text("Скинь фото тарілки або напиши текстом що ти з'їв:")

    elif query.data == "end":
        await set_user_state(user_id, "start")
        await query.edit_message_text("Дякую! Коли будеш готовий, натисни кнопку нижче.", reply_markup=get_main_keyboard())

    elif query.data == "stats_menu":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("За сьогодні", callback_data="stats_today")],
            [InlineKeyboardButton("7 днів", callback_data="stats_days_7"),
             InlineKeyboardButton("30 днів", callback_data="stats_days_30")],
            [InlineKeyboardButton("Назад", callback_data="back_to_main")]
        ])
        await query.edit_message_text("Яку статистику хочеш подивитися?", reply_markup=keyboard)

    elif query.data == "back_to_main":
        await set_user_state(user_id, "start")
        await query.edit_message_text("Обери дію:", reply_markup=get_main_keyboard())

    elif query.data in ["stats_today", "stats_days_7", "stats_days_30"]:
        try:
            async with httpx.AsyncClient() as client:
                if query.data == "stats_today":
                    r = await client.get(f"{CALORIE_SERVICE_URL}/analytics/today/{user_id}", timeout=5)
                    d = r.json()
                    text = (f"📊 Сьогодні:\n"
                            f"Калорії: {d['calories']} ккал\n"
                            f"Б: {d['proteins']}г | Ж: {d['fats']}г | В: {d['carbs']}г")
                else:
                    days = 7 if query.data == "stats_days_7" else 30
                    r = await client.get(f"{CALORIE_SERVICE_URL}/analytics/days/{user_id}/{days}", timeout=5)
                    d = r.json()
                    text = (f" За {days} днів (середнє/день):\n"
                            f"Калорії: {d['avg_calories']} ккал\n"
                            f"Б: {d['avg_proteins']}г | Ж: {d['avg_fats']}г | В: {d['avg_carbs']}г")
        except Exception as e:
            print(f"[ERROR] Статистика: {e}")
            text = "Не вдалося отримати статистику."

        await query.edit_message_text(text, reply_markup=get_main_keyboard())


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if await get_user_state(user_id) != "waiting_for_food":
        await update.message.reply_text("Спочатку натисни кнопку 'Додати їжу'")
        return

    waiting_msg = await update.message.reply_text("Рахую...")
    user_text = update.message.text
    res_text = None

    try:
        prompt = (f"Проаналізуй: '{user_text}'. "
                  "Виведи інгредієнти та КБЖВ. "
                  "Формат (строго, без зайвого тексту):\n"
                  "- Інгредієнт (вага, ккал, Б: Хг, Ж: Хг, В: Хг)\n"
                  "Всього: Х ккал (Б: Хг, Ж: Хг, В: Хг)\n"
                  "Порада: [одне речення]")

        response = ai_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=GEMINI_CONFIG
        )
        res_text = response.text
    except Exception as e:
        print(f"[ERROR] Gemini: {e}")
        await waiting_msg.edit_text("Не вдалося отримати відповідь від ШІ.")
        return

    try:
        cal, prot, fat, carb = await extract_data_from_text(res_text)
        await save_meal_to_db(user_id, cal, prot, fat, carb)
    except Exception as e:
        print(f"[DEBUG] Парсинг/збереження: {e}")

    await waiting_msg.delete()
    await update.message.reply_text(res_text, reply_markup=get_after_meal_keyboard())
    await set_user_state(user_id, "start")


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if await get_user_state(user_id) != "waiting_for_food":
        await update.message.reply_text("Спочатку натисни кнопку 'Додати їжу'")
        return

    waiting_msg = await update.message.reply_text("ШІ вивчає фото...")
    file_path = f"temp_{user_id}.png"
    res_text = None

    try:
        photo_file = await update.message.photo[-1].get_file()
        await photo_file.download_to_drive(file_path)
        image = Image.open(file_path)

        prompt = ("Проаналізуй це фото їжі. "
                  "Виведи інгредієнти та КБЖВ. "
                  "Формат (строго, без зайвого тексту):\n"
                  "- Інгредієнт (вага, ккал, Б: Хг, Ж: Хг, В: Хг)\n"
                  "Всього: Х ккал (Б: Хг, Ж: Хг, В: Хг)\n"
                  "Порада: [одне речення]")

        response = ai_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[image, prompt],
            config=GEMINI_CONFIG
        )
        res_text = response.text
    except Exception as e:
        print(f"[ERROR] Gemini фото: {e}")
        await waiting_msg.edit_text("Помилка розпізнавання.")
        if os.path.exists(file_path):
            os.remove(file_path)
        return

    try:
        cal, prot, fat, carb = await extract_data_from_text(res_text)
        await save_meal_to_db(user_id, cal, prot, fat, carb)
    except Exception as e:
        print(f"[DEBUG] Парсинг/збереження: {e}")

    if os.path.exists(file_path):
        os.remove(file_path)

    await waiting_msg.delete()
    await update.message.reply_text(res_text, reply_markup=get_after_meal_keyboard())
    await set_user_state(user_id, "start")


if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_click))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("[DEBUG] Бот успішно запущений!")
    app.run_polling()