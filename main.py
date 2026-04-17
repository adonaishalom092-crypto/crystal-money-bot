import os
import sqlite3
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor

# ================= CONFIG =================
API_TOKEN = os.getenv("API_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
CHANNEL_USERNAME = "@crystalmoneychannel"

bot = Bot(token=API_TOKEN, parse_mode="HTML")
dp = Dispatcher(bot)

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
    language TEXT
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


def get_balance(user_id):
    cursor.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
    return cursor.fetchone()[0]


def set_bonus_date(user_id, date):
    cursor.execute("UPDATE users SET last_bonus_date=? WHERE user_id=?", (date, user_id))
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
    kb.add(InlineKeyboardButton("🔘 Rejoindre le canal", url=f"https://t.me/{CHANNEL_USERNAME.replace('@','')}"))
    kb.add(InlineKeyboardButton("🔘 Vérifier", callback_data="check_channel"))
    return kb


# ================= START =================
@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    user_id = message.from_user.id
    args = message.get_args()
    lang = message.from_user.language_code

    user = get_user(user_id)

    if not user:
        referrer_id = None
        if args and args.isdigit():
            referrer_id = int(args)

        cursor.execute(
            "INSERT INTO users (user_id, referrer_id, language) VALUES (?, ?, ?)",
            (user_id, referrer_id, lang)
        )
        conn.commit()

    await message.answer(
        "💎 <b>Bienvenue sur Crystal Money Bot</b>\n\n"
        "Rejoins le canal pour continuer 👇",
        reply_markup=channel_keyboard()
    )


# ================= CHECK CHANNEL =================
@dp.callback_query_handler(lambda c: c.data == "check_channel")
async def check_channel(call: types.CallbackQuery):
    user_id = call.from_user.id

    try:
        member = await bot.get_chat_member(CHANNEL_USERNAME, user_id)

        if member.status in ["member", "administrator", "creator"]:
            await call.message.answer("✅ Vérification réussie !", reply_markup=main_keyboard(user_id))
        else:
            await call.answer("🚫 Rejoins le canal d'abord !", show_alert=True)

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
        member = await bot.get_chat_member(CHANNEL_USERNAME, user_id)
        if member.status not in ["member", "administrator", "creator"]:
            return await message.answer("🚫 Rejoins le canal")
    except:
        return await message.answer("❌ Erreur canal")

    if last_bonus == today:
        return await message.answer("⏳ Déjà pris aujourd’hui")

    update_balance(user_id, 100)
    set_bonus_date(user_id, today)

    referrer_id = user[3]
    if referrer_id:
        update_balance(referrer_id, 150)

    cursor.execute("UPDATE users SET total_bonus = total_bonus + 1 WHERE user_id=?", (user_id,))
    conn.commit()

    await message.answer("🎁 +100 FCFA reçu !")


# ================= PARRAINAGE =================
@dp.message_handler(lambda m: m.text == "👥 Parrainage")
async def referral(message: types.Message):
    bot_username = (await bot.get_me()).username
    link = f"https://t.me/{bot_username}?start={message.from_user.id}"

    cursor.execute("SELECT COUNT(*) FROM users WHERE referrer_id=?", (message.from_user.id,))
    count = cursor.fetchone()[0]

    await message.answer(
        f"👥 Ton lien :\n{link}\n\n"
        f"📊 Tu as {count} filleuls"
    )


# ================= SOLDE =================
@dp.message_handler(lambda m: m.text == "💰 Solde")
async def balance(message: types.Message):
    bal = get_balance(message.from_user.id)
    await message.answer(f"💰 Solde: {bal} FCFA")


# ================= RETRAIT =================
@dp.message_handler(lambda m: m.text == "💸 Retrait")
async def withdraw(message: types.Message):
    user_id = message.from_user.id
    bal = get_balance(user_id)

    if bal < 500:
        return await message.answer("❌ Min 500 FCFA")

    cursor.execute(
        "INSERT INTO withdrawals (user_id, amount, status) VALUES (?, ?, ?)",
        (user_id, 500, "pending")
    )

    cursor.execute("UPDATE users SET balance = balance - 500 WHERE user_id=?", (user_id,))
    conn.commit()

    await message.answer("✅ Demande envoyée")

    await bot.send_message(
        ADMIN_ID,
        f"🚨 RETRAIT\nUser: {user_id}\nMontant: 500 FCFA\n\n/send {user_id} message"
    )


# ================= HISTORIQUE =================
@dp.message_handler(lambda m: m.text == "📜 Historique")
async def history(message: types.Message):
    cursor.execute("SELECT amount, status FROM withdrawals WHERE user_id=?", (message.from_user.id,))
    data = cursor.fetchall()

    if not data:
        return await message.answer("Aucun historique")

    text = "📜 Historique\n\n"
    for d in data:
        text += f"{d[0]} - {d[1]}\n"

    await message.answer(text)


# ================= ADMIN SEND =================
@dp.message_handler(commands=["send"])
async def send(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return

    try:
        _, user_id, text = message.text.split(" ", 2)
        await bot.send_message(user_id, f"📩 Admin:\n{text}")
        await message.reply("Envoyé")
    except:
        await message.reply("/send id message")


# ================= ADMIN STATS =================
@dp.message_handler(commands=["stats"])
async def stats(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return

    cursor.execute("SELECT COUNT(*) FROM users")
    users = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM withdrawals WHERE status='pending'")
    pending = cursor.fetchone()[0]

    await message.answer(f"👥 Users: {users}\n💸 Retraits: {pending}")


# ================= RUN =================
if __name__ == "__main__":
    print("Bot started...")
    executor.start_polling(dp, skip_updates=True)
