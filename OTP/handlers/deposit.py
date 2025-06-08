from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery
from config import UPI_ID, OWNER_ID, USDT
from OTP.utils.helpers import generate_qr_code
from OTP.utils.keyboards import deposit_amount_keyboard
from OTP.database.database import fetch_user_data, update_user_data
from constants import DEPOSIT_TEXT
from pyrogram.enums import ParseMode

deposit_messages = {}

@Client.on_message(filters.command("deposit") & filters.private)
async def deposit(client: Client, message: Message):
    await message.reply_text(DEPOSIT_TEXT, reply_markup=deposit_amount_keyboard(), parse_mode=ParseMode.MARKDOWN)

@Client.on_callback_query(filters.regex(r'^deposit_(\d+)$'))
async def process_deposit(client: Client, callback_query: CallbackQuery):
    amount = int(callback_query.matches[0].group(1))
    user_id = callback_query.from_user.id
    
    qr_code = generate_qr_code(UPI_ID, amount)
    deposit_message = await callback_query.message.reply_photo(
        qr_code,
        caption=f"**🔍 Payment Instructions**\n\n💳 Amount: `${amount}`\n\n📲 Scan QR or send to:\n`{UPI_ID}`\n\n🌐 USDT TRC20:\n`{USDT}`\n\n📸 Reply with payment screenshot after sending",
        parse_mode=ParseMode.MARKDOWN
    )
    deposit_messages[user_id] = {"message_id": deposit_message.id, "amount": amount}


@Client.on_callback_query(filters.regex(r'^custom_deposit$'))
async def custom_deposit(client: Client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    await callback_query.message.reply_text("💵 **Enter the deposit amount:**", parse_mode=ParseMode.MARKDOWN)
    
    
    amount_message = await client.listen(user_id)
    amount = int(amount_message.text)
    
    qr_code = generate_qr_code(UPI_ID, amount)
    deposit_message = await callback_query.message.reply_photo(
        qr_code,
        caption=f"**🔍 Payment Instructions**\n\n💳 Amount: `${amount}`\n\n📲 Scan QR or send to:\n`{UPI_ID}`\n\n🌐 USDT TRC20:\n`{USDT}`\n\n📸 Reply with payment screenshot after sending",
        parse_mode=ParseMode.MARKDOWN
    )
    deposit_messages[user_id] = {"message_id": deposit_message.id, "amount": amount}


@Client.on_message(filters.photo & filters.private)
async def handle_payment_screenshot(client: Client, message: Message):
    user_id = message.from_user.id
    if user_id in deposit_messages and message.reply_to_message and message.reply_to_message.id == deposit_messages[user_id]["message_id"]:
        amount = deposit_messages[user_id]["amount"]
        forwarded_msg = await message.forward(OWNER_ID)
        await forwarded_msg.reply_text(
            f"**📤 New Deposit Request**\n\n👤 User: `{user_id}`\n💵 Amount: `${amount}`\n\n⚡ Approve with:\n`/addbalance {user_id} {amount}`",
            parse_mode=ParseMode.MARKDOWN
        )
        await message.reply_text("**📨 Payment Received!**\nAdmin notified! Balance will update within 24 hours.", parse_mode=ParseMode.MARKDOWN)
        del deposit_messages[user_id]
    else:
        await message.reply_text("⚠️ **Invalid Submission!**\nReply to the deposit message with your screenshot.", parse_mode=ParseMode.MARKDOWN)
