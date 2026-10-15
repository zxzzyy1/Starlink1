import os
import json
import asyncio
import logging

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
DATA_FILE = "vouchers.json"

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def load_vouchers():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_vouchers(vouchers):
    with open(DATA_FILE, "w", encoding="utf-8") as file:
        json.dump(vouchers, file, ensure_ascii=False, indent=2)


def is_admin(update: Update) -> bool:
    user = update.effective_user
    return bool(user and ADMIN_ID and user.id == ADMIN_ID)


def main_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "➕ Voucher ထည့်ရန်",
                callback_data="add",
            ),
        ],
        [
            InlineKeyboardButton(
                "📋 Voucher စာရင်း",
                callback_data="list",
            ),
            InlineKeyboardButton(
                "📊 အခြေအနေ",
                callback_data="status",
            ),
        ],
    ])


async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not is_admin(update):
        await update.effective_message.reply_text(
            "❌ Admin သာ အသုံးပြုနိုင်ပါသည်။"
        )
        return

    context.user_data.pop("waiting_for_voucher", None)

    await update.effective_message.reply_text(
        "🤖 Voucher Manager Bot\n\n"
        "အောက်ပါ Menu မှ လုပ်ဆောင်ချက်ကို ရွေးပါ။",
        reply_markup=main_keyboard(),
    )


async def button_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query
    await query.answer()

    if not is_admin(update):
        await query.edit_message_text("❌ ခွင့်ပြုချက်မရှိပါ။")
        return

    if query.data == "add":
        context.user_data["waiting_for_voucher"] = True
        await query.edit_message_text(
            "➕ Voucher Code ကို ပို့ပေးပါ။\n\n"
            "Code တစ်ခုကို တစ်ကြောင်းစီ ထည့်နိုင်ပါတယ်။\n"
            "/cancel ဖြင့် ပြန်ထွက်နိုင်ပါတယ်။"
        )

    elif query.data == "list":
        vouchers = load_vouchers()

        if not vouchers:
            message = "📋 Voucher စာရင်း မရှိသေးပါ။"
        else:
            lines = [
                f"{i}. {item}"
                for i, item in enumerate(vouchers[:50], 1)
            ]
            message = "📋 Voucher စာရင်း\n\n" + "\n".join(lines)

            if len(vouchers) > 50:
                message += (
                    f"\n\nနောက်ထပ် {len(vouchers) - 50} ခု ရှိပါသေးတယ်။"
                )

        await query.edit_message_text(
            message,
            reply_markup=main_keyboard(),
        )

    elif query.data == "status":
        count = len(load_vouchers())
        await query.edit_message_text(
            f"📊 Bot အခြေအနေ\n\n"
            f"✅ Bot အလုပ်လုပ်နေသည်\n"
            f"📦 သိမ်းထားသော Voucher: {count}",
            reply_markup=main_keyboard(),
        )


async def handle_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not is_admin(update):
        return

    if not context.user_data.get("waiting_for_voucher"):
        await update.effective_message.reply_text(
            "Menu အသုံးပြုရန် /start ကို နှိပ်ပါ။"
        )
        return

    text = update.effective_message.text or ""
    codes = [line.strip() for line in text.splitlines() if line.strip()]

    if not codes:
        await update.effective_message.reply_text(
            "❌ Code မတွေ့ပါ။ ပြန်ပို့ပေးပါ။"
        )
        return

    vouchers = load_vouchers()
    existing = set(vouchers)
    added = 0

    for code in codes:
        if code not in existing:
            vouchers.append(code)
            existing.add(code)
            added += 1

    save_vouchers(vouchers)
    context.user_data["waiting_for_voucher"] = False

    await update.effective_message.reply_text(
        f"✅ သိမ်းဆည်းပြီးပါပြီ။\n"
        f"➕ အသစ်ထည့်ထားသော Code: {added}\n"
        f"📦 စုစုပေါင်း Code: {len(vouchers)}",
        reply_markup=main_keyboard(),
    )


async def cancel(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not is_admin(update):
        return

    context.user_data.pop("waiting_for_voucher", None)
    await update.effective_message.reply_text(
        "လုပ်ဆောင်ချက်ကို ပယ်ဖျက်ပြီးပါပြီ။",
        reply_markup=main_keyboard(),
    )


def main():
    if not BOT_TOKEN or not ADMIN_ID:
        raise RuntimeError(
            "BOT_TOKEN နဲ့ ADMIN_ID ကို Environment Variables "
            "မှာ မှန်ကန်စွာ ထည့်ပါ။"
        )

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    logger.info("Voucher Manager Bot started")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
