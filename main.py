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

CHANNEL_USERNAMES = [
    "@crystalmoneychannel",
]

bot = Bot(token=API_TOKEN, parse_mode="HTML")
dp = Dispatcher(bot, storage=MemoryStorage())

# ================== FSM ==================

class WithdrawState(StatesGroup):
    amount = State()
    method = State()
    number = State()
    name = State()

# ================== DATABASE ==================

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

# ================== SAFE BALANCE ==================

def get_balance(user_id):
    cursor.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
    result = cursor.fetchone()
    return result[0] if result else 0

# ================== CHANNEL CHECK ==================

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

        ok = await is_user_in_channels(user_id)

        if not ok:
            await message.answer(
                "🚫 Tu dois rejoindre tous les canaux obligatoires avant d'utiliser le bot."
            )
            raise CancelHandler()

dp.middleware.setup(ChannelCheckMiddleware())

# ================== KEYBOARDS ==================

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

# ================== USERS ==================

def get_user(user_id):
    cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    user = cursor.fetchone()

    if not user:
        cursor.execute("INSERT INTO users (user_id) VALUES (?)", (user_id,))
        conn.commit()
        return get_user(user_id)

    return user


def update_balance(user_id, amount):
    cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (amount, user_id))
    conn.commit()


def set_bonus_date(user_id, date):
    cursor.execute("UPDATE users SET last_bonus_date=? WHERE user_id=?", (date, user_id))
    conn.commit()

# ================== START ==================

WELCOME_TEXT = """
<b>Cher(e) {name},</b>

<b>Bienvenue sur l’espace de gain 🗽CRYSTAL MONEY🗽</b>

<b>Il est obligatoire de rejoindre le canal ci-dessous pour bénéficier des services du bot.</b>

<b>👉🏼 @crystalmoneychannel</b>

<b>Cliquez sur Vérifier ✅ après avoir rejoint le canal.</b>
"""

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

# ================== CHECK CHANNEL ==================

@dp.callback_query_handler(lambda c: c.data == "check_channel")
async def check_channel(call: types.CallbackQuery):
    user_id = call.from_user.id

    try:
        for channel in CHANNEL_USERNAMES:
            member = await bot.get_chat_member(channel, user_id)

            if member.status not in ["member", "administrator", "creator"]:
                return await call.answer("🚫 Rejoins tous les canaux d'abord !", show_alert=True)

        await call.message.answer("✅ Vérification réussie !", reply_markup=main_keyboard(user_id))

    except:
        await call.answer("❌ Erreur vérification", show_alert=True)

# ================== BONUS ==================

@dp.message_handler(lambda m: m.text == "🎁 Bonus")
async def bonus(message: types.Message):
    user_id = message.from_user.id
    user = get_user(user_id)

    today = str(datetime.now().date())
    last_bonus = user[4]

    if last_bonus == today:
        return await message.answer("⏳ Déjà réclamé aujourd'hui.\nReviens demain 😉")

    update_balance(user_id, 100)
    set_bonus_date(user_id, today)

    await message.answer("🎁 BONUS QUOTIDIEN\n\nFélicitations ! Tu as reçu :\n+100 FCFA 💰")

# ================== SOLDE ==================

@dp.message_handler(lambda m: m.text == "💰 Solde")
async def solde(message: types.Message):
    await message.answer(f"💰 TON SOLDE : {get_balance(message.from_user.id)} FCFA")

# ================== RETRAIT STABLE ==================

@dp.message_handler(lambda m: m.text == "💸 Retrait")
async def retrait(message: types.Message):
    bal = get_balance(message.from_user.id)

    if bal < 500:
        return await message.answer("❌ Minimum de retrait : 500 FCFA")

    await message.answer("💰 Quel montant veux-tu retirer ?")
    await WithdrawState.amount.set()


@dp.message_handler(state=WithdrawState.amount)
async def get_amount(message: types.Message, state: FSMContext):

    if not message.text.isdigit():
        return await message.answer("❌ Montant invalide")

    amount = int(message.text)
    bal = get_balance(message.from_user.id)

    if amount < 500:
        return await message.answer("❌ Minimum 500 FCFA")

    if amount > bal:
        return await message.answer("❌ Solde insuffisant")

    await state.update_data(amount=amount)
    await message.answer("💳 Mode de paiement ?")
    await WithdrawState.next()


@dp.message_handler(state=WithdrawState.method)
async def get_method(message: types.Message, state: FSMContext):
    await state.update_data(method=message.text)
    await message.answer("📱 Numéro ?")
    await WithdrawState.next()


@dp.message_handler(state=WithdrawState.number)
async def get_number(message: types.Message, state: FSMContext):
    await state.update_data(number=message.text)
    await message.answer("👤 Nom ?")
    await WithdrawState.next()


@dp.message_handler(state=WithdrawState.name)
async def get_name(message: types.Message, state: FSMContext):
    data = await state.get_data()

    user_id = message.from_user.id
    amount = data['amount']
    method = data['method']
    number = data['number']
    name = message.text

    # 🔥 Déduction immédiate
    cursor.execute(
        "UPDATE users SET balance = balance - ? WHERE user_id=?",
        (amount, user_id)
    )

    cursor.execute(
        "INSERT INTO withdrawals (user_id, amount, status) VALUES (?, ?, 'pending')",
        (user_id, amount)
    )

    conn.commit()
    wid = cursor.lastrowid

    await bot.send_message(
        ADMIN_ID,
        f"📥 NOUVEAU RETRAIT\n\n👤 ID: {user_id}\n💰 {amount} FCFA\n💳 {method}\n📱 {number}\n👤 {name}",
        reply_markup=admin_withdraw_keyboard(wid)
    )

    await message.answer("⏳ Demande envoyée")
    await state.finish()

# ================== ADMIN PAY ==================

@dp.callback_query_handler(lambda c: c.data.startswith("wd_paid"))
async def wd_paid(call: types.CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        return

    wid = int(call.data.split(":")[1])

    cursor.execute("UPDATE withdrawals SET status='paid' WHERE id=?", (wid,))
    conn.commit()

    cursor.execute("SELECT user_id FROM withdrawals WHERE id=?", (wid,))
    user_id = cursor.fetchone()[0]

    await bot.send_message(user_id, "✅ Ton retrait a été payé 💰")
    await call.answer("OK")

# ================== ADMIN REFUSE ==================

@dp.callback_query_handler(lambda c: c.data.startswith("wd_refused"))
async def wd_refused(call: types.CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        return

    wid = int(call.data.split(":")[1])

    cursor.execute("SELECT user_id, amount FROM withdrawals WHERE id=?", (wid,))
    data = cursor.fetchone()

    if not data:
        return await call.answer("Erreur")

    user_id, amount = data

    cursor.execute("UPDATE withdrawals SET status='refused' WHERE id=?", (wid,))

    cursor.execute(
        "UPDATE users SET balance = balance + ? WHERE user_id=?",
        (amount, user_id)
    )

    conn.commit()

    await bot.send_message(user_id, "❌ Retrait refusé → remboursé")
    await call.answer("Refusé")

# ================== RUN ==================

if __name__ == "__main__":
    print("Bot started...")
    executor.start_polling(dp, skip_updates=True)
