import os
import sqlite3
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor

from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage

# ================= CONFIG =================
API_TOKEN = os.getenv("API_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
CHANNEL_USERNAME = "@crystalmoneychannel"

# ✅ AJOUT MULTI CHANNELS
CHANNEL_USERNAMES = [
    "@crystalmoneychannel",
    # "@autre_channel"  # tu peux ajouter ici
]

bot = Bot(token=API_TOKEN, parse_mode="HTML")
dp = Dispatcher(bot, storage=MemoryStorage())

# ================= STATES =================
class WithdrawState(StatesGroup):
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

# ================= HELPERS =================
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


def get_balance(user_id):
    cursor.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
    return cursor.fetchone()[0]

# ================= WELCOME =================
WELCOME_TEXT = """
<b>Cher(e) {name},</b>

<b>Bienvenue sur l’espace de gain 🗽CRYSTAL MONEY🗽</b>

<b>Il est obligatoire de rejoindre le canal ci-dessous pour bénéficier des services du bot.</b>

<b>👉🏼 @crystalmoneychannel</b>

<b>Cliquez sur Vérifier ✅ après avoir rejoint le canal.</b>
"""

# ================= START =================
@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    user_id = message.from_user.id
    args = message.get_args()
    lang = message.from_user.language_code

    cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    user = cursor.fetchone()

    if not user:
        referrer_id = None

        if args.isdigit():
            referrer_id = int(args)

        cursor.execute(
            "INSERT INTO users (user_id, referrer_id, language) VALUES (?, ?, ?)",
            (user_id, referrer_id, lang)
        )
        conn.commit()

    name = message.from_user.first_name

    await message.answer(
        WELCOME_TEXT.format(name=name),
        reply_markup=channel_keyboard()
    )

# ================= CHECK CHANNEL =================
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

    if user[3] and user[8] == 0:
        update_balance(user[3], 150)

        cursor.execute(
            "UPDATE users SET total_referrals = total_referrals + 1 WHERE user_id=?",
            (user[3],)
        )

        cursor.execute(
            "UPDATE users SET referral_paid = 1 WHERE user_id=?",
            (user_id,)
        )

    cursor.execute("UPDATE users SET total_bonus = total_bonus + 1 WHERE user_id=?", (user_id,))
    conn.commit()

    await message.answer(
        "🎁 BONUS QUOTIDIEN\n\n"
        "Félicitations ! Tu as reçu :\n+100 FCFA 💰\n\n"
        "⏳ Reviens demain pour réclamer encore plus !"
    )

# ================= PARRAINAGE =================
@dp.message_handler(lambda m: m.text == "👥 Parrainage")
async def referral(message: types.Message):
    user = get_user(message.from_user.id)
    bot_username = (await bot.get_me()).username

    link = f"https://t.me/{bot_username}?start={message.from_user.id}"

    await message.answer(
        f"👥 TON LIEN D’AFFILIATION :\n\n"
        f"🔗 {link}\n\n"
        f"📊 Tu as déjà parrainé : {user[5]} personne(s)\n\n"
        f"💰 150 FCFA par personne"
    )

# ================= SOLDE =================
@dp.message_handler(lambda m: m.text == "💰 Solde")
async def solde(message: types.Message):
    bal = get_balance(message.from_user.id)
    await message.answer(f"💰 TON SOLDE : {bal} FCFA")

# ================= RETRAIT =================
@dp.message_handler(lambda m: m.text == "💸 Retrait")
async def retrait(message: types.Message):
    user_id = message.from_user.id
    bal = get_balance(user_id)

    if bal < 500:
        return await message.answer("❌ Minimum de retrait : 500 FCFA")

    await message.answer("💳 Quel est ton mode de paiement ?")
    await WithdrawState.method.set()

# ================= FSM =================
@dp.message_handler(state=WithdrawState.method)
async def get_method(message: types.Message, state: FSMContext):
    await state.update_data(method=message.text)
    await message.answer("📱 Envoie ton numéro avec indicatif")
    await WithdrawState.next()

@dp.message_handler(state=WithdrawState.number)
async def get_number(message: types.Message, state: FSMContext):
    await state.update_data(number=message.text)
    await message.answer("👤 Nom du bénéficiaire ?")
    await WithdrawState.next()

@dp.message_handler(state=WithdrawState.name)
async def get_name(message: types.Message, state: FSMContext):
    data = await state.get_data()

    user_id = message.from_user.id
    method = data['method']
    number = data['number']
    name = message.text

    amount = 500

    cursor.execute(
        "INSERT INTO withdrawals (user_id, amount, status) VALUES (?, ?, ?)",
        (user_id, amount, "pending")
    )
    conn.commit()

    wid = cursor.lastrowid

    await bot.send_message(
        ADMIN_ID,
        f"📥 NOUVEAU RETRAIT\n\n"
        f"👤 ID: {user_id}\n"
        f"💰 Montant: {amount} FCFA\n"
        f"💳 Méthode: {method}\n"
        f"📱 Numéro: {number}\n"
        f"👤 Nom: {name}",
        reply_markup=admin_withdraw_keyboard(wid)
    )

    await message.answer(
        "⏳ Ta demande de retrait est en attente de validation par l’admin."
    )

    await state.finish()

# ================= ADMIN ACTIONS =================
@dp.callback_query_handler(lambda c: c.data.startswith("wd_paid"))
async def wd_paid(call: types.CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        return

    wid = int(call.data.split(":")[1])

    cursor.execute("UPDATE withdrawals SET status='paid' WHERE id=?", (wid,))
    conn.commit()

    cursor.execute("SELECT user_id FROM withdrawals WHERE id=?", (wid,))
    user_id = cursor.fetchone()[0]

    await bot.send_message(user_id, "✅ Ton retrait a été validé et payé 💰")
    await call.answer("Payé confirmé")


@dp.callback_query_handler(lambda c: c.data.startswith("wd_refused"))
async def wd_refused(call: types.CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        return

    wid = int(call.data.split(":")[1])

    cursor.execute("UPDATE withdrawals SET status='refused' WHERE id=?", (wid,))

    cursor.execute("SELECT user_id, amount FROM withdrawals WHERE id=?", (wid,))
    user_id, amount = cursor.fetchone()

    cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (amount, user_id))
    conn.commit()

    await bot.send_message(user_id, "❌ Ton retrait a été refusé. Ton solde a été recrédité.")
    await call.answer("Refusé confirmé")

# ================= HISTORIQUE =================
@dp.message_handler(lambda m: m.text == "📜 Historique")
async def history(message: types.Message):
    cursor.execute("SELECT amount, status FROM withdrawals WHERE user_id=?", (message.from_user.id,))
    data = cursor.fetchall()

    if not data:
        return await message.answer("📜 Aucun historique")

    text = "📜 HISTORIQUE\n\n"
    for d in data:
        text += f"{d[0]} FCFA - {d[1]}\n"

    await message.answer(text)

# ================= ADMIN PANEL =================
@dp.message_handler(lambda m: m.text == "📊 Admin Panel")
async def admin_panel(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return

    cursor.execute("SELECT COUNT(*) FROM users")
    users = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM withdrawals WHERE status='pending'")
    pending = cursor.fetchone()[0]

    await message.answer(
        f"🛠️ ADMIN PANEL\n\n"
        f"👥 Users: {users}\n"
        f"⏳ Pending: {pending}"
    )

# ================= STATS (FIX) =================
@dp.message_handler(lambda m: m.text == "📈 Stats")
async def stats(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return

    cursor.execute("SELECT COUNT(*) FROM users")
    users = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM withdrawals")
    withdrawals = cursor.fetchone()[0]

    cursor.execute("SELECT SUM(balance) FROM users")
    total_balance = cursor.fetchone()[0] or 0

    await message.answer(
        f"📈 STATS\n\n"
        f"👥 Utilisateurs: {users}\n"
        f"💸 Retraits: {withdrawals}\n"
        f"💰 Balance totale: {total_balance} FCFA"
    )

# ================= RUN =================
if __name__ == "__main__":
    print("Bot started...")
    executor.start_polling(dp, skip_updates=True)
