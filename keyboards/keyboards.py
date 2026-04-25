from aiogram.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from config import ADMIN_ID

def main_keyboard(user_id: int) -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("🎁 Bonus", "👥 Parrainage")
    kb.row("💰 Solde", "📜 Historique")
    kb.row("💸 Retrait", "❓ Aide")
    if user_id == ADMIN_ID:
        kb.row("📊 Admin Panel", "📈 Stats")
        kb.row("📢 Broadcast", "📡 Gérer Canaux")
        kb.row("🔨 Bannir", "✅ Débannir")
    return kb

def channel_keyboard(channels: list) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup()
    for ch in channels:
        kb.add(InlineKeyboardButton(f"👉 Rejoindre {ch}", url=f"https://t.me/{ch.lstrip('@')}"))
    kb.add(InlineKeyboardButton("✅ Vérifier", callback_data="check_channel"))
    return kb

def confirm_withdraw_keyboard(amount: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup()
    kb.row(
        InlineKeyboardButton("✅ Confirmer", callback_data=f"confirm_wd:{amount}"),
        InlineKeyboardButton("❌ Annuler", callback_data="cancel_wd"),
    )
    return kb

def admin_withdraw_keyboard(wid: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup()
    kb.row(
        InlineKeyboardButton("✅ Payé", callback_data=f"wd_paid:{wid}"),
        InlineKeyboardButton("❌ Refusé", callback_data=f"wd_refused:{wid}"),
    )
    return kb

def manage_channels_keyboard(channels: list) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup()
    for ch in channels:
        kb.add(InlineKeyboardButton(f"🗑 Supprimer {ch}", callback_data=f"del_channel:{ch}"))
    kb.add(InlineKeyboardButton("➕ Ajouter un canal", callback_data="add_channel"))
    return kb
