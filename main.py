import sqlite3
import os
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
import datetime

API_TOKEN = os.getenv("API_TOKEN")

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

conn = sqlite3.connect("bot.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    balance INTEGER DEFAULT 0,
    referrer INTEGER,
    last_claim TEXT
)
""")
conn.commit()

CHANNEL = "@crystalmoneychannel"

async def check_sub(user_id):
    try:
        member = await bot.get_chat_member(CHANNEL, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await message.answer("✅ Bot fonctionne !")

    if not await check_sub(user_id):
        await message.answer("🚫 Rejoins le canal pour continuer:\nhttps://t.me/+RBJns9gbyWdiYWYy")
        return

    cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    user = cursor.fetchone()

    if not user:
        ref = int(args) if args.isdigit() else None
        cursor.execute("INSERT INTO users (user_id, referrer) VALUES (?, ?)", (user_id, ref))
        
        if ref:
            cursor.execute("UPDATE users SET balance = balance + 75 WHERE user_id=?", (ref,))
        
        conn.commit()

    await message.answer("💎 Bienvenue sur Crystal Money Bot\n\nTape /bonus pour commencer")

@dp.message_handler(commands=['bonus'])
async def bonus(message: types.Message):
    user_id = message.from_user.id
    today = str(datetime.date.today())

    cursor.execute("SELECT last_claim FROM users WHERE user_id=?", (user_id,))
    result = cursor.fetchone()

    if result and result[0] == today:
        await message.answer("❌ Déjà réclamé aujourd'hui")
        return

    cursor.execute("UPDATE users SET balance = balance + 25, last_claim=? WHERE user_id=?", (today, user_id))
    conn.commit()

    await message.answer("🎉 +25 FCFA ajouté")

@dp.message_handler(commands=['solde'])
async def solde(message: types.Message):
    cursor.execute("SELECT balance FROM users WHERE user_id=?", (message.from_user.id,))
    result = cursor.fetchone()
    balance = result[0] if result else 0
    await message.answer(f"💰 Solde: {balance} FCFA")

@dp.message_handler(commands=['refer'])
async def refer(message: types.Message):
    link = f"https://t.me/wellcashgain_bot?start={message.from_user.id}"
    await message.answer(f"🔗 Ton lien:\n{link}")

if __name__ == "__main__":
    print("Bot started...")
    executor.start_polling(dp, skip_updates=True)
