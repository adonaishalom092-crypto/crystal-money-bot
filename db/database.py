import aiosqlite
import logging

logger = logging.getLogger(__name__)
DB_PATH = "/app/data/database.db"

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id          INTEGER UNIQUE,
                balance          INTEGER DEFAULT 0,
                referrer_id      INTEGER,
                last_bonus_date  TEXT,
                total_referrals  INTEGER DEFAULT 0,
                total_bonus      INTEGER DEFAULT 0,
                language         TEXT,
                referral_paid    INTEGER DEFAULT 0,
                is_banned        INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS withdrawals (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id  INTEGER,
                amount   INTEGER,
                method   TEXT,
                number   TEXT,
                name     TEXT,
                status   TEXT DEFAULT 'pending'
            );
            CREATE TABLE IF NOT EXISTS channels (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE
            );
        """)
        await db.execute("INSERT OR IGNORE INTO channels (username) VALUES (?)", ("@adonaimoneychannel",))
        await db.commit()
    logger.info("Base de données initialisée.")

def _db():
    return aiosqlite.connect(DB_PATH)

async def get_user(user_id: int):
    async with _db() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id=?", (user_id,)) as cur:
            return await cur.fetchone()

async def get_or_create_user(user_id: int, referrer_id=None, language=None):
    async with _db() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id=?", (user_id,)) as cur:
            user = await cur.fetchone()
        if not user:
            await db.execute(
                "INSERT INTO users (user_id, referrer_id, language) VALUES (?, ?, ?)",
                (user_id, referrer_id, language)
            )
            await db.commit()
            async with db.execute("SELECT * FROM users WHERE user_id=?", (user_id,)) as cur:
                user = await cur.fetchone()
        return user

async def get_balance(user_id: int) -> int:
    async with _db() as db:
        async with db.execute("SELECT balance FROM users WHERE user_id=?", (user_id,)) as cur:
            row = await cur.fetchone()
            return row[0] if row else 0

async def is_banned(user_id: int) -> bool:
    async with _db() as db:
        async with db.execute("SELECT is_banned FROM users WHERE user_id=?", (user_id,)) as cur:
            row = await cur.fetchone()
            return bool(row and row[0])

async def ban_user(user_id: int):
    async with _db() as db:
        await db.execute("UPDATE users SET is_banned=1 WHERE user_id=?", (user_id,))
        await db.commit()

async def unban_user(user_id: int):
    async with _db() as db:
        await db.execute("UPDATE users SET is_banned=0 WHERE user_id=?", (user_id,))
        await db.commit()

async def claim_daily_bonus(user_id: int, today: str) -> bool:
    from config import DAILY_BONUS, REFERRAL_BONUS
    async with _db() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT last_bonus_date, referrer_id, referral_paid FROM users WHERE user_id=?", (user_id,)
        ) as cur:
            user = await cur.fetchone()
        if not user or user["last_bonus_date"] == today:
            return False
        await db.execute("BEGIN")
        try:
            await db.execute(
                "UPDATE users SET balance=balance+?, last_bonus_date=?, total_bonus=total_bonus+1 WHERE user_id=?",
                (DAILY_BONUS, today, user_id)
            )
            if user["referrer_id"] and not user["referral_paid"]:
                await db.execute(
                    "UPDATE users SET balance=balance+?, total_referrals=total_referrals+1 WHERE user_id=?",
                    (REFERRAL_BONUS, user["referrer_id"])
                )
                await db.execute("UPDATE users SET referral_paid=1 WHERE user_id=?", (user_id,))
            await db.commit()
            return True
        except Exception as e:
            await db.rollback()
            logger.error(f"Erreur claim_daily_bonus: {e}")
            raise

async def count_pending_withdrawals(user_id: int) -> int:
    async with _db() as db:
        async with db.execute(
            "SELECT COUNT(*) FROM withdrawals WHERE user_id=? AND status='pending'", (user_id,)
        ) as cur:
            row = await cur.fetchone()
            return row[0] if row else 0

async def create_withdrawal(user_id: int, amount: int, method: str, number: str, name: str) -> int:
    async with _db() as db:
        await db.execute("BEGIN")
        try:
            await db.execute("UPDATE users SET balance=balance-? WHERE user_id=?", (amount, user_id))
            await db.execute(
                "INSERT INTO withdrawals (user_id, amount, method, number, name, status) VALUES (?,?,?,?,?,'pending')",
                (user_id, amount, method, number, name)
            )
            await db.commit()
            async with db.execute("SELECT last_insert_rowid()") as cur:
                row = await cur.fetchone()
                return row[0]
        except Exception as e:
            await db.rollback()
            logger.error(f"Erreur create_withdrawal: {e}")
            raise

async def get_withdrawal(wid: int):
    async with _db() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM withdrawals WHERE id=?", (wid,)) as cur:
            return await cur.fetchone()

async def pay_withdrawal(wid: int):
    async with _db() as db:
        await db.execute("UPDATE withdrawals SET status='paid' WHERE id=?", (wid,))
        await db.commit()

async def refuse_withdrawal(wid: int) -> bool:
    async with _db() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT user_id, amount, status FROM withdrawals WHERE id=?", (wid,)) as cur:
            row = await cur.fetchone()
        if not row or row["status"] != "pending":
            return False
        await db.execute("BEGIN")
        try:
            await db.execute("UPDATE withdrawals SET status='refused' WHERE id=?", (wid,))
            await db.execute("UPDATE users SET balance=balance+? WHERE user_id=?", (row["amount"], row["user_id"]))
            await db.commit()
            return True
        except Exception as e:
            await db.rollback()
            logger.error(f"Erreur refuse_withdrawal: {e}")
            raise

async def get_user_withdrawals(user_id: int, limit: int = 20):
    async with _db() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT amount, method, status FROM withdrawals WHERE user_id=? ORDER BY id DESC LIMIT ?",
            (user_id, limit)
        ) as cur:
            return await cur.fetchall()

async def get_all_user_ids():
    async with _db() as db:
        async with db.execute("SELECT user_id FROM users WHERE is_banned=0") as cur:
            rows = await cur.fetchall()
            return [r[0] for r in rows]

async def get_stats() -> dict:
    async with _db() as db:
        async with db.execute("SELECT COUNT(*) FROM users") as cur:
            users = (await cur.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM withdrawals WHERE status='pending'") as cur:
            pending = (await cur.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM withdrawals") as cur:
            total_wd = (await cur.fetchone())[0]
        async with db.execute("SELECT COALESCE(SUM(balance),0) FROM users") as cur:
            total_balance = (await cur.fetchone())[0]
    return {"users": users, "pending": pending, "total_withdrawals": total_wd, "total_balance": total_balance}

async def get_channels():
    async with _db() as db:
        async with db.execute("SELECT username FROM channels") as cur:
            rows = await cur.fetchall()
            return [r[0] for r in rows]

async def add_channel(username: str) -> bool:
    try:
        async with _db() as db:
            await db.execute("INSERT INTO channels (username) VALUES (?)", (username,))
            await db.commit()
        return True
    except aiosqlite.IntegrityError:
        return False

async def delete_channel(username: str):
    async with _db() as db:
        await db.execute("DELETE FROM channels WHERE username=?", (username,))
        await db.commit()
