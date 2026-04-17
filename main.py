        
        import os
import sqlite3
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor

# ================= CONFIG =================
API_TOKEN = os.getenv("API_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

CHANNELS = ["@crystalmoneychannel"]

bot = Bot(token=API_TOKEN, parse_mode="HTML")
dp = Dispatcher(bot)

# ================= DATABASE =================
conn = sqlite3.connect("database.db")
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
    for ch in CHANNELS:
        kb.add(InlineKeyboardButton(f"🔘 {ch}", url=f"https://t.me/{ch.replace('@','')}"))
    kb.add(InlineKeyboardButton("✅ Vérifier", callback_data="check_channel"))
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


def add_referral(referrer_id):
    cursor.execute(
        "UPDATE users SET total_referrals = total_referrals + 1 WHERE user_id=?",
        (referrer_id,)
    )
    conn.commit()

# ================= CHECK SUB =================
async def check_subscription(user_id):
    for ch in CHANNELS:
        try:
            member = await bot.get_chat_member(ch, user_id)
            if member.status not in ["member", "creator", "administrator"]:
                return False
        except:
            return False
    return True

# ================= START =================
@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    user_id = message.from_user.id
    args = message.get_args()

    cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    if not cursor.fetchone():
        ref = int(args) if args.isdigit() and int(args) != user_id else None

        if ref:
            add_referral(ref)

        cursor.execute(
            "INSERT INTO users (user_id, referrer_id, language) VALUES (?, ?, ?)",
            (user_id, ref, message.from_user.language_code)
        )
        conn.commit()

    name = message.from_user.first_name

    # ✅ MESSAGE DE BIENVENUE EN GRAS
    await message.answer(
        f"<b>👤 Cher(e) {name},</b>\n\n"
        f"<b>🗽 Bienvenue sur l’espace de gain CRYSTAL MONEY 🗽</b>\n\n"
        f"<b>Il est obligatoire de rejoindre le canal ci-dessous pour bénéficier des services du bot.</b>\n\n"
        f"<b>🏅 Rejoins 👉 @crystalmoneychannel</b>\n\n"
        f"<b>Clique sur Vérifier ✅ après avoir rejoint la chaîne.</b>",
        reply_markup=channel_keyboard()
    )

# ================= CHECK CHANNEL =================
@dp.callback_query_handler(lambda c: c.data == "check_channel")
async def check_channel(call: types.CallbackQuery):
    if await check_subscription(call.from_user.id):
        await call.message.answer("✅ Accès autorisé", reply_markup=main_keyboard(call.from_user.id))
    else:
        await call.answer("🚫 Rejoins le canal", show_alert=True)

# ================= BONUS =================
@dp.message_handler(lambda m: m.text == "🎁 Bonus")
async def bonus(message: types.Message):
    user = get_user(message.from_user.id)

    if not await check_subscription(message.from_user.id):
        return await message.answer("🚫 Tu dois rejoindre le canal")

    today = str(datetime.now().date())

    if user[4] == today:
        return await message.answer("⏳ Bonus déjà récupéré aujourd’hui")

    update_balance(message.from_user.id, 100)
    set_bonus_date(message.from_user.id, today)

    if user[3] and user[6] == 0:
        update_balance(user[3], 150)
        add_referral(user[3])

    cursor.execute("UPDATE users SET total_bonus = total_bonus + 1 WHERE user_id=?", (message.from_user.id,))
    conn.commit()

    await message.answer(
        "🎁 BONUS QUOTIDIEN ACTIVÉ\n\n"
        "💰 +100 FCFA crédité\n"
        "🔥 Reviens chaque jour pour gagner plus"
    )

# ================= PARRAINAGE =================
@dp.message_handler(lambda m: m.text == "👥 Parrainage")
async def referral(message: types.Message):
    user = get_user(message.from_user.id)

    bot_username = (await bot.get_me()).username
    link = f"https://t.me/{bot_username}?start={message.from_user.id}"

    await message.answer(
        f"👥 TON LIEN : {link}\n\n"
        f"📊 Parrainés : {user[5]}"
    )

# ================= SOLDE =================
@dp.message_handler(lambda m: m.text == "💰 Solde")
async def balance(message: types.Message):
    bal = get_balance(message.from_user.id)
    await message.answer(f"💰 Solde : {bal} FCFA")

# ================= RETRAIT =================
@dp.message_handler(lambda m: m.text == "💸 Retrait")
async def withdraw(message: types.Message):
    user_id = message.from_user.id
    bal = get_balance(user_id)

    if bal < 500:
        return await message.answer("❌ Minimum 500 FCFA")

    cursor.execute(
        "INSERT INTO withdrawals (user_id, amount, status) VALUES (?, ?, ?)",
        (user_id, 500, "pending")
    )

    cursor.execute("UPDATE users SET balance = balance - 500 WHERE user_id=?", (user_id,))
    conn.commit()

    await message.answer("✅ Demande envoyée")

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

# ================= RUN =================
if __name__ == "__main__":
    print("Bot started...")
    executor.start_polling(dp, skip_updates=True)
