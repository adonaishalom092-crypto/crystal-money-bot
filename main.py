    import os
import sqlite3
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor

# ================= CONFIG =================
API_TOKEN = os.getenv("API_TOKEN", "")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

CHANNELS = ["@crystalmoneychannel"]

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
    last_bonus_date TEXT DEFAULT '',
    total_referrals INTEGER DEFAULT 0
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
        cursor.execute(
            "INSERT INTO users (user_id) VALUES (?)",
            (user_id,)
        )
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
    row = cursor.fetchone()
    return row[0] if row else 0


def set_bonus_date(user_id, date):
    cursor.execute(
        "UPDATE users SET last_bonus_date=? WHERE user_id=?",
        (date, user_id)
    )
    conn.commit()


def add_referral(ref_id):
    cursor.execute(
        "UPDATE users SET total_referrals = total_referrals + 1 WHERE user_id=?",
        (ref_id,)
    )
    conn.commit()


async def check_subscription(user_id):
    for ch in CHANNELS:
        try:
            m = await bot.get_chat_member(ch, user_id)
            if m.status not in ["member", "creator", "administrator"]:
                return False
        except:
            return False
    return True


# ================= KEYBOARD =================
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
        kb.add(InlineKeyboardButton("🔘 Rejoindre le canal", url=f"https://t.me/{ch.replace('@','')}"))
    kb.add(InlineKeyboardButton("✅ Vérifier", callback_data="check_channel"))
    return kb


# ================= START =================
@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    user_id = message.from_user.id
    args = message.get_args()

    if not get_user(user_id):
        ref = int(args) if args.isdigit() and int(args) != user_id else None

        if ref:
            add_referral(ref)

        cursor.execute(
            "INSERT INTO users (user_id, referrer_id) VALUES (?, ?)",
            (user_id, ref)
        )
        conn.commit()

    name = message.from_user.first_name

    await message.answer(
        f"👤 Cher(e) {name},\n\n"
        "🗽 Bienvenue sur l’espace de gain CRYSTAL MONEY 🗽\n\n"
        "Il est obligatoire de rejoindre le canal ci-dessous pour bénéficier des services du bot.\n\n"
        "🏅 Rejoins 👉 @crystalmoneychannel\n\n"
        "Clique sur Vérifier ✅ après avoir rejoint la chaîne.",
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

    last_bonus = user[4]

    if last_bonus == today:
        return await message.answer("⏳ Déjà récupéré aujourd’hui")

    update_balance(message.from_user.id, 100)
    set_bonus_date(message.from_user.id, today)

    ref = user[3]

    if ref:
        update_balance(ref, 150)

    await message.answer(
        "🎁 BONUS QUOTIDIEN\n\n"
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
        f"📊 ADMIN PANEL\n\n"
        f"👥 Users : {users}\n"
        f"💸 Withdrawals : {pending}"
    )


# ================= STATS =================
@dp.message_handler(lambda m: m.text == "📈 Stats")
async def stats(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return

    cursor.execute("SELECT COUNT(*) FROM users")
    total = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM users WHERE total_referrals > 0")
    active = cursor.fetchone()[0]

    await message.answer(
        f"📈 STATS\n\n"
        f"👥 Total : {total}\n"
        f"🔥 Actifs : {active}"
    )


# ================= RUN =================
if __name__ == "__main__":
    print("Bot started...")
    executor.start_polling(dp, skip_updates=True)
