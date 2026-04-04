import os
import sqlite3
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor

# ========= CONFIG =========
API_TOKEN = os.getenv("API_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
CHANNEL_USERNAME = "@crystalmoneychannel"

bot = Bot(token=API_TOKEN, parse_mode="HTML")
dp = Dispatcher(bot)

# ========= DATABASE =========
conn = sqlite3.connect("database.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    balance INTEGER DEFAULT 0,
    referrer_id INTEGER,
    last_bonus_date TEXT,
    total_bonus INTEGER DEFAULT 0,
    total_referrals INTEGER DEFAULT 0,
    is_blocked INTEGER DEFAULT 0
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS withdrawals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    amount INTEGER,
    phone TEXT,
    method TEXT,
    status TEXT
)
""")

conn.commit()

# ========= MESSAGE DESIGN =========
BOT_DESCRIPTION = """
<b>💎 QUE PEUT FAIRE CE BOT ?</b>

🚀 Bienvenue sur <b>CRYSTAL MONEY BOT</b> !

💰 Gagne de l'argent facilement et légalement directement depuis ton téléphone.

━━━━━━━━━━━━━━━

<b>🔥 COMMENT ÇA MARCHE ?</b>

👥 Invite tes amis → <b>+75 FCFA</b>  
🎁 Réclame ton bonus → <b>+25 FCFA chaque jour</b>  

━━━━━━━━━━━━━━━

<b>💸 RETRAIT SIMPLE & RAPIDE</b>

💰 Minimum : <b>500 FCFA</b>  
📲 Paiements via :  
• MTN Money  
• Moov Money  
• Orange Money  
• Wave  

━━━━━━━━━━━━━━━

⚡ Plus tu es actif, plus tu gagnes !

🔥 Offre limitée : commence aujourd’hui 💸
"""

# ========= CLAVIERS =========
def main_keyboard(user_id):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("🎁 Bonus", "👥 Parrainage")
    kb.row("💰 Solde")
    kb.row("💸 Retrait", "📜 Historique")

    if user_id == ADMIN_ID:
        kb.row("📊 Admin Panel")

    return kb


def channel_keyboard():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🔘 Rejoindre le canal", url="https://t.me/crystalmoneychannel"))
    kb.add(InlineKeyboardButton("🔘 Vérifier", callback_data="check"))
    return kb

# ========= HELPERS =========
def get_user(user_id):
    cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    user = cursor.fetchone()

    if not user:
        cursor.execute("INSERT INTO users (user_id) VALUES (?)", (user_id,))
        conn.commit()
        return get_user(user_id)

    return user


def get_balance(user_id):
    cursor.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
    return cursor.fetchone()[0]

# ========= START =========
@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    user_id = message.from_user.id
    args = message.get_args()

    cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    user = cursor.fetchone()

    if not user:
        ref = None
        if args.isdigit() and int(args) != user_id:
            ref = int(args)

        cursor.execute(
            "INSERT INTO users (user_id, referrer_id) VALUES (?, ?)",
            (user_id, ref)
        )
        conn.commit()

    await message.answer(BOT_DESCRIPTION, reply_markup=channel_keyboard())

# ========= VERIFICATION CANAL =========
@dp.callback_query_handler(lambda c: c.data == "check")
async def check(call: types.CallbackQuery):
    user_id = call.from_user.id

    try:
        member = await bot.get_chat_member(CHANNEL_USERNAME, user_id)

        if member.status in ["member", "administrator", "creator"]:
            await call.message.answer("✅ Accès activé !", reply_markup=main_keyboard(user_id))
        else:
            await call.answer("🚫 Rejoins le canal", show_alert=True)

    except:
        await call.answer("Erreur", show_alert=True)

# ========= BONUS =========
@dp.message_handler(lambda m: m.text == "🎁 Bonus")
async def bonus(message: types.Message):
    user_id = message.from_user.id
    user = get_user(user_id)

    if user[6] == 1:
        return await message.answer("🚫 Compte bloqué")

    today = str(datetime.now().date())

    if user[3] == today:
        return await message.answer("⏳ Déjà réclamé aujourd'hui\nReviens demain 😉")

    cursor.execute("UPDATE users SET balance = balance + 25, last_bonus_date=? WHERE user_id=?", (today, user_id))

    # parrainage
    if user[4] == 0 and user[2]:
        cursor.execute("UPDATE users SET balance = balance + 75 WHERE user_id=?", (user[2],))
        cursor.execute("UPDATE users SET total_referrals = total_referrals + 1 WHERE user_id=?", (user[2],))

    cursor.execute("UPDATE users SET total_bonus = total_bonus + 1 WHERE user_id=?", (user_id,))
    conn.commit()

    await message.answer("🎁 BONUS REÇU\n\n+25 FCFA 💰")

# ========= PARRAINAGE =========
@dp.message_handler(lambda m: m.text == "👥 Parrainage")
async def referral(message: types.Message):
    user_id = message.from_user.id
    bot_username = (await bot.get_me()).username

    link = f"https://t.me/{bot_username}?start={user_id}"

    await message.answer(f"🔗 Ton lien :\n{link}")

# ========= SOLDE =========
@dp.message_handler(lambda m: m.text == "💰 Solde")
async def solde(message: types.Message):
    bal = get_balance(message.from_user.id)
    await message.answer(f"💰 Solde : {bal} FCFA")

# ========= RETRAIT =========
user_state = {}

@dp.message_handler(lambda m: m.text == "💸 Retrait")
async def retrait(message: types.Message):
    if get_balance(message.from_user.id) < 500:
        return await message.answer("❌ Minimum 500 FCFA")

    user_state[message.from_user.id] = "method"
    await message.answer("1️⃣ MTN\n2️⃣ Orange\n3️⃣ Wave\nChoisis méthode")

@dp.message_handler(lambda m: m.from_user.id in user_state)
async def process_retrait(message: types.Message):
    uid = message.from_user.id
    state = user_state[uid]

    if state == "method":
        methods = {"1": "MTN", "2": "Orange", "3": "Wave"}
        if message.text not in methods:
            return await message.answer("Choix invalide")

        user_state[uid] = {"method": methods[message.text]}
        await message.answer("Entre ton numéro")

    else:
        method = state["method"]
        phone = message.text

        cursor.execute(
            "INSERT INTO withdrawals (user_id, amount, phone, method, status) VALUES (?, ?, ?, ?, ?)",
            (uid, 500, phone, method, "pending")
        )

        cursor.execute("UPDATE users SET balance = balance - 500 WHERE user_id=?", (uid,))
        conn.commit()

        await bot.send_message(
            ADMIN_ID,
            f"💸 Retrait\nUser: {uid}\n500 FCFA\n{method}\n{phone}"
        )

        del user_state[uid]

        await message.answer("✅ Retrait envoyé\n⏳ 24-48h")

# ========= HISTORIQUE =========
@dp.message_handler(lambda m: m.text == "📜 Historique")
async def history(message: types.Message):
    cursor.execute("SELECT amount, status FROM withdrawals WHERE user_id=?", (message.from_user.id,))
    data = cursor.fetchall()

    if not data:
        return await message.answer("Aucun historique")

    text = "📜 Historique\n\n"
    for d in data:
        text += f"{d[0]} FCFA - {d[1]}\n"

    await message.answer(text)

# ========= ADMIN =========
@dp.message_handler(lambda m: m.text == "📊 Admin Panel")
async def admin(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return

    cursor.execute("SELECT COUNT(*) FROM users")
    users = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM withdrawals WHERE status='pending'")
    pending = cursor.fetchone()[0]

    await message.answer(f"👤 {users} utilisateurs\n💸 {pending} retraits en attente")

# ========= RUN =========
if __name__ == "__main__":
    print("Bot lancé")
    executor.start_polling(dp, skip_updates=True)
