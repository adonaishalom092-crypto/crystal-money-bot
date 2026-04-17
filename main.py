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
    kb.add(InlineKeyboardButton("🔘 Rejoindre le canal", url=f"https://t.me/{CHANNEL_USERNAME.replace('@','')}"))
    kb.add(InlineKeyboardButton("🔘 Vérifier", callback_data="check_channel"))
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
💎 Bienvenue sur <b>Crystal Money Bot</b>

🔥 Gagne facilement et légalement du FCFA chaque jour !

💰 Ce que tu gagnes :
🎁 Bonus quotidien : 100 FCFA
👥 Parrainage : 150 FCFA par personne

🚀 Retrait à partir de 500 FCFA

📲 Paiement rapide via :

MTN Money
Orange Money
Wave
Moov Money

🚨 <b>IMPORTANT :</b>
Rejoins le canal pour continuer 👇

👉 <b>@crystalmoneychannel</b>

Puis clique sur Vérifier
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
            if referrer_id != user_id:
                referrer_id = referrer_id

        cursor.execute(
            "INSERT INTO users (user_id, referrer_id, language) VALUES (?, ?, ?)",
            (user_id, referrer_id, lang)
        )
        conn.commit()

    await message.answer(WELCOME_TEXT, reply_markup=channel_keyboard())

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
            return await message.answer("🚫 Tu dois rejoindre le canal pour réclamer ton bonus")
    except:
        return await message.answer("❌ Erreur vérification canal")

    if last_bonus == today:
        return await message.answer("⏳ Déjà réclamé aujourd'hui.\nReviens demain 😉")

    update_balance(user_id, 100)
    set_bonus_date(user_id, today)

    # ✅ BONUS PARRAIN (UNE SEULE FOIS)
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

    cursor.execute(
        "INSERT INTO withdrawals (user_id, amount, status) VALUES (?, ?, ?)",
        (user_id, 500, "pending")
    )
    cursor.execute("UPDATE users SET balance = balance - 500 WHERE user_id=?", (user_id,))
    conn.commit()

    # 🔔 USER NOTIFIED
    await message.answer(
        "⏳ Ta demande de retrait est en attente.\n"
        "Tu seras notifié après validation par l’admin."
    )

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

    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("📥 Voir retraits", callback_data="admin_withdrawals"))

    await message.answer("🛠️ PANEL ADMIN", reply_markup=kb)

# ================= ADMIN WITHDRAW =================
@dp.callback_query_handler(lambda c: c.data == "admin_withdrawals")
async def admin_withdrawals(call: types.CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        return

    cursor.execute("SELECT id, user_id, amount FROM withdrawals WHERE status='pending'")
    data = cursor.fetchall()

    if not data:
        return await call.message.answer("📭 Aucun retrait en attente")

    for w in data:
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("✅ Approuver", callback_data=f"approve_{w[0]}"))

        await call.message.answer(
            f"💸 Retrait ID: {w[0]}\n👤 User: {w[1]}\n💰 {w[2]} FCFA",
            reply_markup=kb
        )

# ================= APPROVE =================
@dp.callback_query_handler(lambda c: c.data.startswith("approve_"))
async def approve_withdraw(call: types.CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        return

    withdrawal_id = int(call.data.split("_")[1])

    cursor.execute("SELECT user_id, amount FROM withdrawals WHERE id=?", (withdrawal_id,))
    data = cursor.fetchone()

    if not data:
        return

    user_id, amount = data

    cursor.execute("UPDATE withdrawals SET status='approved' WHERE id=?", (withdrawal_id,))
    conn.commit()

    try:
        await bot.send_message(
            user_id,
            f"✅ Ton retrait de {amount} FCFA a été approuvé et payé 💰"
        )
    except:
        pass

    await call.message.answer("✅ Retrait approuvé")

# ================= STATS =================
@dp.message_handler(lambda m: m.text == "📈 Stats")
async def stats(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return

    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM withdrawals WHERE status='pending'")
    pending = cursor.fetchone()[0]

    await message.answer(
        f"📊 STATISTIQUES\n\n"
        f"👥 Utilisateurs : {total_users}\n"
        f"💸 Retraits en attente : {pending}"
    )

# ================= RUN =================
if __name__ == "__main__":
    print("Bot started...")
    executor.start_polling(dp, skip_updates=True)
