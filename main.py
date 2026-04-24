import asyncio
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


# ================= CONFIG =================
API_TOKEN = os.getenv("API_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

CHANNEL_USERNAMES = ["@crystalmoneychannel"]

bot = Bot(token=API_TOKEN, parse_mode="HTML")
dp = Dispatcher(bot, storage=MemoryStorage())


# ================= STATES =================
class WithdrawState(StatesGroup):
    method = State()
    number = State()
    name = State()


# ================= DB =================
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
        if message.get_command() == "/start":
            return

        ok = await is_user_in_channels(message.from_user.id)

        if not ok:
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


# ================= USER =================
def get_user(user_id):
    cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    user = cursor.fetchone()

    if not user:
        cursor.execute("INSERT INTO users (user_id) VALUES (?)", (user_id,))
        conn.commit()
        return get_user(user_id)

    return user


def update_balance(user_id, amount):
    cursor.execute(
        "UPDATE users SET balance = balance + ? WHERE user_id=?",
        (amount, user_id)
    )
    conn.commit()


def get_balance(user_id):
    cursor.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
    return cursor.fetchone()[0]


def set_bonus_date(user_id, date):
    cursor.execute("UPDATE users SET last_bonus_date=? WHERE user_id=?", (date, user_id))
    conn.commit()


# ================= START =================
@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    user_id = message.from_user.id
    args = message.get_args()
    lang = message.from_user.language_code

    cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    user = cursor.fetchone()

    if not user:
        referrer_id = int(args) if args.isdigit() else None

        cursor.execute(
            "INSERT INTO users (user_id, referrer_id, language) VALUES (?, ?, ?)",
            (user_id, referrer_id, lang)
        )
        conn.commit()

    await message.answer(
        WELCOME_TEXT.format(name=message.from_user.first_name),
        reply_markup=channel_keyboard()
    )


# ================= CHANNEL CHECK =================
@dp.callback_query_handler(lambda c: c.data == "check_channel")
async def check_channel(call: types.CallbackQuery):
    ok = await is_user_in_channels(call.from_user.id)

    if not ok:
        return await call.answer("🚫 Rejoins tous les canaux d'abord !", show_alert=True)

    await call.message.answer("✅ Vérification réussie !", reply_markup=main_keyboard(call.from_user.id))


# ================= BONUS =================
@dp.message_handler(lambda m: m.text == "🎁 Bonus")
async def bonus(message: types.Message):
    user_id = message.from_user.id
    user = get_user(user_id)

    today = str(datetime.now().date())
    last_bonus = user[4]

    try:
        for channel in CHANNEL_USERNAMES:
            member = await bot.get_chat_member(channel, user_id)
            if member.status not in ["member", "administrator", "creator"]:
                return await message.answer("🚫 Tu dois rejoindre tous les canaux pour réclamer ton bonus")
    except:
        return await message.answer("❌ Erreur vérification canal")

    if last_bonus == today:
        return await message.answer("⏳ Déjà réclamé aujourd'hui.\nReviens demain 😉")

    update_balance(user_id, 100)
    set_bonus_date(user_id, today)

    await message.answer(
        "🎁 BONUS QUOTIDIEN\n\n"
        "Félicitations ! Tu as reçu :\n+100 FCFA 💰\n\n"
        "⏳ Reviens demain pour réclamer encore plus !"
    )


# ================= SOLDE =================
@dp.message_handler(lambda m: m.text == "💰 Solde")
async def solde(message: types.Message):
    await message.answer(f"💰 TON SOLDE : {get_balance(message.from_user.id)} FCFA")


# ================= RETRAIT =================
@dp.message_handler(lambda m: m.text == "💸 Retrait")
async def retrait(message: types.Message):
    await message.answer("💳 Quel est ton mode de paiement ?")
    await WithdrawState.method.set()


@dp.message_handler(state=WithdrawState.method)
async def method(message: types.Message, state: FSMContext):
    await state.update_data(method=message.text)
    await message.answer("📱 Envoie ton numéro avec indicatif")
    await WithdrawState.next()


@dp.message_handler(state=WithdrawState.number)
async def number(message: types.Message, state: FSMContext):
    await state.update_data(number=message.text)
    await message.answer("👤 Nom du bénéficiaire ?")
    await WithdrawState.next()


@dp.message_handler(state=WithdrawState.name)
async def name(message: types.Message, state: FSMContext):
    data = await state.get_data()

    user_id = message.from_user.id
    amount = 500

    update_balance(user_id, -amount)

    cursor.execute(
        "INSERT INTO withdrawals (user_id, amount, status) VALUES (?, ?, ?)",
        (user_id, amount, "pending")
    )
    conn.commit()

    wid = cursor.lastrowid

    await bot.send_message(
        ADMIN_ID,
        f"📥 NOUVEAU RETRAIT\n\n👤 ID: {user_id}\n💰 Montant: {amount} FCFA",
        reply_markup=admin_withdraw_keyboard(wid)
    )

    await message.answer("⏳ Ta demande de retrait est en attente.")
    await state.finish()


# ================= MAIN =================
if __name__ == "__main__":
    print("Bot started...")
    executor.start_polling(dp, skip_updates=True)
