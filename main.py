import os
import psycopg2
from datetime import datetime, date
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor

# ================= CONFIG =================
API_TOKEN = os.getenv("API_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
CHANNEL = "@crystalmoneychannel"

bot = Bot(token=API_TOKEN, parse_mode="HTML")
dp = Dispatcher(bot)

# ================= DATABASE POSTGRES =================
conn = psycopg2.connect(
    dbname="botdb",
    user="postgres",
    password="password",
    host="localhost",
    port="5432"
)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY,
    balance INT DEFAULT 0,
    referrer BIGINT,
    last_bonus DATE,
    referrals INT DEFAULT 0,
    flagged INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS withdrawals (
    id SERIAL PRIMARY KEY,
    user_id BIGINT,
    amount INT,
    status TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

conn.commit()

# ================= MEMORY =================
pending = {}
admin_state = {}

# ================= HELPERS =================
def get_user(user_id):
    cursor.execute("SELECT * FROM users WHERE user_id=%s", (user_id,))
    user = cursor.fetchone()

    if not user:
        cursor.execute("INSERT INTO users (user_id) VALUES (%s)", (user_id,))
        conn.commit()
        return get_user(user_id)

    return user


def update_balance(user_id, amount):
    cursor.execute("UPDATE users SET balance = balance + %s WHERE user_id=%s", (amount, user_id))
    conn.commit()


def get_balance(user_id):
    cursor.execute("SELECT balance FROM users WHERE user_id=%s", (user_id,))
    return cursor.fetchone()[0]


def is_flagged(user_id):
    cursor.execute("SELECT flagged FROM users WHERE user_id=%s", (user_id,))
    return cursor.fetchone()[0] == 1


def flag_user(user_id):
    cursor.execute("UPDATE users SET flagged=1 WHERE user_id=%s", (user_id,))
    conn.commit()

# ================= KEYBOARDS =================
def main_kb(user_id):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("🎁 Bonus", "👥 Parrainage")
    kb.row("💰 Solde", "💸 Retrait")

    if user_id == ADMIN_ID:
        kb.row("📊 Admin Panel")

    return kb


def admin_kb():
    kb = InlineKeyboardMarkup(row_width=2)

    kb.add(
        InlineKeyboardButton("👥 Users", callback_data="ad_users"),
        InlineKeyboardButton("📊 Stats", callback_data="ad_stats")
    )
    kb.add(
        InlineKeyboardButton("💸 Retraits", callback_data="ad_withdraw"),
        InlineKeyboardButton("⚠️ Fraude", callback_data="ad_fraud")
    )
    kb.add(
        InlineKeyboardButton("📢 Broadcast", callback_data="ad_broadcast"),
        InlineKeyboardButton("➕ Solde", callback_data="ad_add_balance")
    )

    return kb

# ================= START =================
@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    user_id = message.from_user.id
    args = message.get_args()

    get_user(user_id)

    ref = int(args) if args.isdigit() and int(args) != user_id else None

    if ref:
        cursor.execute("UPDATE users SET referrals = referrals + 1 WHERE user_id=%s", (ref,))
        conn.commit()

    await message.answer("💎 Bienvenue", reply_markup=main_kb(user_id))

# ================= BONUS =================
@dp.message_handler(lambda m: m.text == "🎁 Bonus")
async def bonus(message: types.Message):
    user_id = message.from_user.id
    user = get_user(user_id)

    today = date.today()

    if user[3] == today:
        return await message.answer("⏳ Déjà pris aujourd'hui")

    update_balance(user_id, 50)

    cursor.execute("UPDATE users SET last_bonus=%s WHERE user_id=%s", (today, user_id))
    conn.commit()

    ref = user[2]
    if ref:
        update_balance(ref, 150)

    await message.answer("🎁 Bonus ajouté +50 FCFA")

# ================= RETRAIT =================
@dp.message_handler(lambda m: m.text == "💸 Retrait")
async def withdraw(message: types.Message):
    user_id = message.from_user.id
    bal = get_balance(user_id)

    if bal < 500:
        return await message.answer("❌ Minimum 500 FCFA")

    cursor.execute("SELECT COUNT(*) FROM withdrawals WHERE user_id=%s AND status='pending'", (user_id,))
    if cursor.fetchone()[0] > 0:
        return await message.answer("⏳ Retrait déjà en attente")

    cursor.execute(
        "INSERT INTO withdrawals (user_id, amount, status) VALUES (%s, %s, %s)",
        (user_id, 500, "pending")
    )
    conn.commit()

    kb = InlineKeyboardMarkup().add(
        InlineKeyboardButton("✅ Approuver", callback_data=f"approve_{user_id}"),
        InlineKeyboardButton("❌ Refuser", callback_data=f"reject_{user_id}")
    )

    await bot.send_message(
        ADMIN_ID,
        f"💸 Retrait demandé\nUser: {user_id}\nMontant: 500",
        reply_markup=kb
    )

    await message.answer("📩 Demande envoyée")

# ================= ADMIN PANEL =================
@dp.message_handler(lambda m: m.text == "📊 Admin Panel" and m.from_user.id == ADMIN_ID)
async def panel(message: types.Message):
    await message.answer("🛠 Admin Panel", reply_markup=admin_kb())

# ================= STATS =================
@dp.callback_query_handler(lambda c: c.data == "ad_stats")
async def stats(call: types.CallbackQuery):
    cursor.execute("SELECT COUNT(*) FROM users")
    users = cursor.fetchone()[0]

    cursor.execute("SELECT SUM(balance) FROM users")
    total = cursor.fetchone()[0] or 0

    await call.message.answer(
        f"📊 STATS\n👥 Users: {users}\n💰 Total: {total} FCFA"
    )

# ================= USERS =================
@dp.callback_query_handler(lambda c: c.data == "ad_users")
async def users(call: types.CallbackQuery):
    cursor.execute("SELECT user_id, balance FROM users ORDER BY balance DESC LIMIT 10")
    data = cursor.fetchall()

    text = "👥 TOP USERS\n\n"
    for u in data:
        text += f"{u[0]} - {u[1]} FCFA\n"

    await call.message.answer(text)

# ================= FRAUD =================
@dp.callback_query_handler(lambda c: c.data == "ad_fraud")
async def fraud(call: types.CallbackQuery):
    cursor.execute("SELECT user_id, referrals FROM users ORDER BY referrals DESC LIMIT 10")
    data = cursor.fetchall()

    text = "⚠️ SUSPECT USERS\n\n"
    for u in data:
        if u[1] > 10:
            text += f"🚨 {u[0]} - {u[1]} refs\n"

    await call.message.answer(text)

# ================= BROADCAST =================
@dp.callback_query_handler(lambda c: c.data == "ad_broadcast")
async def broadcast(call: types.CallbackQuery):
    admin_state["mode"] = "broadcast"
    await call.message.answer("📢 Envoyer message")

@dp.message_handler(lambda m: m.from_user.id == ADMIN_ID)
async def admin_router(message: types.Message):
    if admin_state.get("mode") == "broadcast":
        cursor.execute("SELECT user_id FROM users")
        users = cursor.fetchall()

        for u in users:
            try:
                await bot.send_message(u[0], message.text)
            except:
                pass

        admin_state["mode"] = None
        await message.answer("✅ Broadcast envoyé")

# ================= APPROVE / REJECT =================
@dp.callback_query_handler(lambda c: c.data.startswith("approve_"))
async def approve(call: types.CallbackQuery):
    uid = int(call.data.split("_")[1])

    cursor.execute("UPDATE withdrawals SET status='approved' WHERE user_id=%s AND status='pending'", (uid,))
    conn.commit()

    await bot.send_message(uid, "✅ Retrait approuvé")
    await call.message.answer("OK")

@dp.callback_query_handler(lambda c: c.data.startswith("reject_"))
async def reject(call: types.CallbackQuery):
    uid = int(call.data.split("_")[1])

    cursor.execute("UPDATE withdrawals SET status='rejected' WHERE user_id=%s AND status='pending'", (uid,))
    conn.commit()

    await bot.send_message(uid, "❌ Retrait refusé")
    await call.message.answer("OK")

# ================= RUN =================
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
