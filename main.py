import os
import sqlite3
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor

from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage

from aiogram.dispatcher.middlewares import BaseMiddleware
from aiogram.dispatcher.handler import CancelHandler

API_TOKEN = os.getenv("API_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
CHANNEL_USERNAME = "@crystalmoneychannel"

CHANNEL_USERNAMES = ["@crystalmoneychannel"]

bot = Bot(token=API_TOKEN, parse_mode="HTML")
dp = Dispatcher(bot, storage=MemoryStorage())

# ================= FSM =================

class WithdrawState(StatesGroup):
    amount = State()
    method = State()
    number = State()
    name = State()

# ================= DATABASE =================

conn = sqlite3.connect("database.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE,
    balance INTEGER DEFAULT 0,
    referrer_id INTEGER,
    last_bonus_date TEXT,
    total_referrals INTEGER DEFAULT 0,
    total_bonus INTEGER DEFAULT 0,
    language TEXT,
    referral_paid INTEGER DEFAULT 0
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS withdrawals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    amount INTEGER,
    status TEXT
)
""")

conn.commit()

# ================= SAFE BALANCE =================

def get_balance(user_id):
    cursor.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
    r = cursor.fetchone()
    return r[0] if r else 0

# ================= RESET FSM (IMPORTANT FIX) =================

@dp.message_handler(state="*")
async def cancel_fsm(message: types.Message, state: FSMContext):
    # permet de sortir du FSM automatiquement
    if message.text in [
        "💰 Solde",
        "👥 Parrainage",
        "📜 Historique",
        "📊 Admin Panel",
        "📈 Stats",
        "🎁 Bonus"
    ]:
        await state.finish()

# ================= CHANNEL CHECK =================

async def is_user_in_channels(user_id: int):
    try:
        for channel in CHANNEL_USERNAMES:
            member = await bot.get_chat_member(channel, user_id)
            if member.status not in ["member", "administrator", "creator"]:
                return False
        return True
    except:
        return False


class ChannelCheckMiddleware(BaseMiddleware):
    async def on_pre_process_message(self, message: types.Message, data: dict):
        user_id = message.from_user.id

        if message.get_command() == "/start":
            return

        if not await is_user_in_channels(user_id):
            await message.answer("🚫 Tu dois rejoindre tous les canaux obligatoires avant d'utiliser le bot.")
            raise CancelHandler()

dp.middleware.setup(ChannelCheckMiddleware())

# ================= KEYBOARDS =================

def main_keyboard(user_id):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("🎁 Bonus", "👥 Parrainage")
    kb.row("💰 Solde")
    kb.row("💸 Retrait", "📜 Historique")

    if user_id == ADMIN_ID:
        kb.row("📊 Admin Panel", "📈 Stats")

    return kb


def channel_keyboard():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("✅ Vérifier", callback_data="check_channel"))
    return kb


def admin_withdraw_keyboard(wid):
    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("✅ Payé", callback_data=f"wd_paid:{wid}"),
        InlineKeyboardButton("❌ Refusé", callback_data=f"wd_refused:{wid}")
    )
    return kb

# ================= USERS =================

def get_user(user_id):
    cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    u = cursor.fetchone()

    if not u:
        cursor.execute("INSERT INTO users (user_id) VALUES (?)", (user_id,))
        conn.commit()
        return get_user(user_id)

    return u


def update_balance(user_id, amount):
    cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (amount, user_id))
    conn.commit()


def set_bonus_date(user_id, date):
    cursor.execute("UPDATE users SET last_bonus_date=? WHERE user_id=?", (date, user_id))
    conn.commit()

# ================= START =================

WELCOME_TEXT = """
<b>Cher(e) {name},</b>

<b>Bienvenue sur l’espace de gain 🗽CRYSTAL MONEY🗽</b>

<b>Il est obligatoire de rejoindre le canal ci-dessous pour bénéficier des services du bot.</b>

<b>👉🏼 @crystalmoneychannel</b>

<b>Cliquez sur Vérifier ✅ après avoir rejoint le canal.</b>
"""

@dp.message_handler(commands=["start"], state="*")
async def start(message: types.Message, state: FSMContext):
    await state.finish()

    user_id = message.from_user.id
    args = message.get_args()
    lang = message.from_user.language_code

    cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    user = cursor.fetchone()

    if not user:
        ref = int(args) if args.isdigit() else None
        cursor.execute(
            "INSERT INTO users (user_id, referrer_id, language) VALUES (?, ?, ?)",
            (user_id, ref, lang)
        )
        conn.commit()

    await message.answer(
        WELCOME_TEXT.format(name=message.from_user.first_name),
        reply_markup=channel_keyboard()
    )

# ================= CHECK CHANNEL =================

@dp.callback_query_handler(lambda c: c.data == "check_channel")
async def check_channel(call: types.CallbackQuery):
    user_id = call.from_user.id

    try:
        for c in CHANNEL_USERNAMES:
            m = await bot.get_chat_member(c, user_id)
            if m.status not in ["member", "administrator", "creator"]:
                return await call.answer("🚫 Rejoins tous les canaux", show_alert=True)

        await call.message.answer("✅ Vérification réussie !", reply_markup=main_keyboard(user_id))

    except:
        await call.answer("❌ Erreur")

# ================= BONUS =================

@dp.message_handler(lambda m: m.text == "🎁 Bonus", state="*")
async def bonus(message: types.Message, state: FSMContext):
    await state.finish()

    user_id = message.from_user.id
    u = get_user(user_id)

    today = str(datetime.now().date())
    if u[4] == today:
        return await message.answer("⏳ Déjà pris aujourd’hui")

    update_balance(user_id, 100)
    set_bonus_date(user_id, today)

    await message.answer("🎁 +100 FCFA reçu")

# ================= SOLDE =================

@dp.message_handler(lambda m: m.text == "💰 Solde", state="*")
async def solde(message: types.Message, state: FSM
