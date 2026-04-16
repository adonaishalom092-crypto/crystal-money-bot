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

admin_state = {}
pending_channel = False

# ================= DATABASE =================
conn = sqlite3.connect("database.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    balance INTEGER DEFAULT 0,
    referrer_id INTEGER,
    last_bonus TEXT,
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
        cursor.execute("INSERT INTO users (user_id) VALUES (?)", (user_id,))
        conn.commit()
        return get_user(user_id)

    return user


def update_balance(user_id, amount):
    cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (amount, user_id))
    conn.commit()


def get_balance(user_id):
    cursor.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
    res = cursor.fetchone()
    return res[0] if res else 0


def set_bonus_date(user_id, date):
    cursor.execute("UPDATE users SET last_bonus=? WHERE user_id=?", (date, user_id))
    conn.commit()


# ================= KEYBOARDS =================
def main_keyboard(user_id):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("🎁 Bonus", "👥 Parrainage")
    kb.row("💰 Solde", "💸 Retrait")

    if user_id == ADMIN_ID:
        kb.row("📊 Admin Panel")

    return kb


def channel_keyboard():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton(
        "🔘 Rejoindre le canal",
        url=f"https://t.me/{CHANNEL_USERNAME.replace('@','')}"
    ))
    kb.add(InlineKeyboardButton("🔘 Vérifier", callback_data="check_channel"))
    return kb


def admin_keyboard():
    kb = InlineKeyboardMarkup(row_width=2)

    kb.add(
        InlineKeyboardButton("👥 Users", callback_data="admin_users"),
        InlineKeyboardButton("📊 Stats", callback_data="admin_stats")
    )
    kb.add(
        InlineKeyboardButton("💸 Retraits", callback_data="admin_withdrawals"),
        InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast")
    )
    kb.add(
        InlineKeyboardButton("🔗 Canal", callback_data="change_channel")
    )

    return kb

# ================= START =================
@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    user_id = message.from_user.id
    args = message.get_args()

    get_user(user_id)

    if args.isdigit():
        ref = int(args)
        if ref != user_id:
            cursor.execute("UPDATE users SET total_referrals = total_referrals + 1 WHERE user_id=?", (ref,))
            conn.commit()

    await message.answer("💎 Bienvenue", reply_markup=channel_keyboard())


# ================= CHECK CHANNEL =================
@dp.callback_query_handler(lambda c: c.data == "check_channel")
async def check_channel(call: types.CallbackQuery):
    user_id = call.from_user.id

    try:
        member = await bot.get_chat_member(CHANNEL_USERNAME, user_id)

        if member.status in ["member", "administrator", "creator"]:
            await call.message.answer("✅ Vérifié", reply_markup=main_keyboard(user_id))
        else:
            await call.answer("🚫 Rejoins le canal", show_alert=True)

    except:
        await call.answer("❌ Erreur", show_alert=True)


# ================= BONUS =================
@dp.message_handler(lambda m: m.text == "🎁 Bonus")
async def bonus(message: types.Message):
    user_id = message.from_user.id
    user = get_user(user_id)

    today = str(datetime.now().date())

    if user[3] == today:
        return await message.answer("⏳ Déjà pris aujourd'hui")

    update_balance(user_id, 50)
    set_bonus_date(user_id, today)

    ref = user[2]
    if ref:
        update_balance(ref, 150)

    await message.answer("🎁 +50 FCFA ajouté")


# ================= SOLDE =================
@dp.message_handler(lambda m: m.text == "💰 Solde")
async def solde(message: types.Message):
    bal = get_balance(message.from_user.id)
    await message.answer(f"💰 Solde: {bal} FCFA")


# ================= RETRAIT =================
@dp.message_handler(lambda m: m.text == "💸 Retrait")
async def withdraw(message: types.Message):
    user_id = message.from_user.id
    bal = get_balance(user_id)

    cursor.execute("""
        SELECT COUNT(*) FROM withdrawals 
        WHERE user_id=? AND status='pending'
    """, (user_id,))
    pending = cursor.fetchone()[0]

    if pending > 0:
        return await message.answer("⏳ Déjà une demande en cours")

    if bal < 500:
        return await message.answer("❌ Minimum 500 FCFA")

    cursor.execute("""
        INSERT INTO withdrawals (user_id, amount, status)
        VALUES (?, ?, 'pending')
    """, (user_id, 500))
    conn.commit()

    kb = InlineKeyboardMarkup().add(
        InlineKeyboardButton("📩 Contacter", callback_data=f"msg_{user_id}")
    )

    await bot.send_message(
        ADMIN_ID,
        f"💸 Retrait\nUser: {user_id}\nMontant: 500 FCFA",
        reply_markup=kb
    )

    await message.answer("📩 Demande envoyée")


# ================= ADMIN PANEL =================
@dp.message_handler(lambda m: m.text == "📊 Admin Panel" and m.from_user.id == ADMIN_ID)
async def admin_panel(message: types.Message):
    await message.answer("🛠 Admin Panel", reply_markup=admin_keyboard())


# ================= ADMIN STATS =================
@dp.callback_query_handler(lambda c: c.data == "admin_stats")
async def admin_stats(call: types.CallbackQuery):
    cursor.execute("SELECT COUNT(*) FROM users")
    users = cursor.fetchone()[0]

    cursor.execute("SELECT SUM(balance) FROM users")
    total = cursor.fetchone()[0] or 0

    await call.message.answer(f"📊 Users: {users}\n💰 Total: {total} FCFA")


# ================= USERS =================
@dp.callback_query_handler(lambda c: c.data == "admin_users")
async def admin_users(call: types.CallbackQuery):
    cursor.execute("SELECT user_id, balance FROM users ORDER BY balance DESC LIMIT 10")
    data = cursor.fetchall()

    text = "👥 TOP USERS\n\n"
    for u in data:
        text += f"{u[0]} - {u[1]} FCFA\n"

    await call.message.answer(text)


# ================= RETRAITS =================
@dp.callback_query_handler(lambda c: c.data == "admin_withdrawals")
async def admin_withdrawals(call: types.CallbackQuery):
    cursor.execute("SELECT user_id, amount FROM withdrawals WHERE status='pending'")
    rows = cursor.fetchall()

    text = "💸 RETRAITS:\n\n"
    for r in rows:
        text += f"{r[0]} - {r[1]} FCFA\n"

    await call.message.answer(text or "Aucun retrait")


# ================= BROADCAST (FIX UNIQUE HANDLER) =================
@dp.callback_query_handler(lambda c: c.data == "admin_broadcast")
async def broadcast(call: types.CallbackQuery):
    admin_state["mode"] = "broadcast"
    await call.message.answer("📢 Envoie le message à diffuser")


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


# ================= CHANGE CHANNEL =================
@dp.callback_query_handler(lambda c: c.data == "change_channel")
async def change_channel(call: types.CallbackQuery):
    global pending_channel
    pending_channel = True
    await call.message.answer("Envoie le nouveau canal")


@dp.message_handler(lambda m: m.from_user.id == ADMIN_ID)
async def set_channel(message: types.Message):
    global CHANNEL_USERNAME, pending_channel

    if pending_channel:
        CHANNEL_USERNAME = message.text
        pending_channel = False
        await message.answer("✅ Canal mis à jour")


# ================= RUN =================
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
