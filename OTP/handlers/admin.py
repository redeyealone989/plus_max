from pyrogram import Client, filters
from pyrogram.errors import (
    ApiIdInvalid, PhoneNumberInvalid, PhoneCodeInvalid, 
    PhoneCodeExpired, SessionPasswordNeeded, PasswordHashInvalid
)
from pyrogram.types import Message
from config import SUDO_USERS, API_ID, API_HASH, OWNER_ID
from OTP.database.database import add_otp_data, delete_otp_data, update_user_data, fetch_user_data, get_total_stats, fetch_all_user_ids
from pyrogram.enums import ParseMode

@Client.on_message(filters.command("add_numbers") & filters.user(SUDO_USERS))
async def add_numbers(client: Client, message: Message):
    user_id = message.chat.id
    await message.reply_text("📲 **Send Phone Number to Add**\n\nFormat: `+1234567890`", parse_mode=ParseMode.MARKDOWN)
    number_msg = await client.listen(user_id)
    number = number_msg.text

    user = Client(name=f"user_{user_id}", api_id=API_ID, api_hash=API_HASH, in_memory=True)
    await user.connect()

    try:
        code = await user.send_code(number)
    except ApiIdInvalid:
        await message.reply_text("❌ **Invalid API Credentials!**\nCheck config.py settings")
        return
    except PhoneNumberInvalid:
        await message.reply_text("⚠️ **Invalid Phone Number!**\nEnsure proper country code format")
        return

    await message.reply_text("🔑 **Enter Received OTP**\n\nFormat: `1 2 3 4 5`")
    otp_msg = await client.listen(user_id)
    otp = otp_msg.text.replace(" ", "")

    try:
        await user.sign_in(number, code.phone_code_hash, otp)
    except PhoneCodeInvalid:
        await message.reply_text("❌ **Invalid OTP Code!**\nRestart process with /add_numbers")
        return
    except PhoneCodeExpired:
        await message.reply_text("⌛ **OTP Expired!**\nRequest new code and try again")
        return
    except SessionPasswordNeeded:
        await message.reply_text("🔒 **2FA Required!**\nEnter account password:")
        password_msg = await client.listen(user_id)
        password = password_msg.text
        try:
            await user.check_password(password)
        except PasswordHashInvalid:
            await message.reply_text("❌ **Wrong Password!**\nProcess cancelled")
            return

    session = await user.export_session_string()
    await message.reply_text("💵 **Set Number Price**\n\nEnter amount in USD:")
    price_msg = await client.listen(user_id)
    price = float(price_msg.text)

    await message.reply_text("🕰 **Account Age**\n\nIs this an old account? (yes/no)")
    is_old_msg = await client.listen(user_id)
    is_old = is_old_msg.text.lower() == "yes"

    year = None
    if is_old:
        await message.reply_text("📅 **Account Creation Year**\n\nEnter full year (e.g. 2018):")
        year_msg = await client.listen(user_id)
        year = int(year_msg.text)

    await add_otp_data(number, session, price, is_old, year, password)
    await message.reply_text(f"✅ **Number Added!**\n\n📱 `{number}`\n💰 ${price}\n{'📅 '+str(year) if is_old else '🌱 New Account'}", parse_mode=ParseMode.MARKDOWN)

@Client.on_message(filters.command("delete_number") & filters.user(SUDO_USERS))
async def delete_number(client: Client, message: Message):
    await message.reply_text("🗑 **Delete Number**\n\nSend full number to remove:")
    number = await client.listen(message.chat.id)
    
    result = await delete_otp_data(number.text)
    if result.deleted_count > 0:
        await message.reply_text(f"✅ Successfully deleted:\n`{number.text}`", parse_mode=ParseMode.MARKDOWN)
    else:
        await message.reply_text("⚠️ **Number Not Found!**\nCheck database and try again")

@Client.on_message(filters.command("addbalance") & filters.user(OWNER_ID))
async def add_balance(client: Client, message: Message):
    args = message.text.split()
    if len(args) == 3:
        try:
            user_id = int(args[1])
            amount = float(args[2])
            user_data = await fetch_user_data(user_id)
            if user_data:
                new_balance = user_data['balance'] + amount
                await update_user_data(user_id, {"balance": new_balance})
                await message.reply_text(f"💰 **Balance Updated**\n\nUser: `{user_id}`\nAdded: `${amount}`\nNew Balance: `${new_balance}`", parse_mode=ParseMode.MARKDOWN)
                await client.send_message(user_id, f"💸 **Wallet Credited!**\n\nAmount: `${amount}`\nNew Balance: `${new_balance}`", parse_mode=ParseMode.MARKDOWN)
            else:
                await message.reply_text("⚠️ **User Not Found!**\nCheck ID and try again")
        except ValueError:
            await message.reply_text("❌ **Invalid Input!**\nUse numbers only")
    else:
        await message.reply_text("📝 **Usage:**\n`/addbalance [user_id] [amount]`")

@Client.on_message(filters.command("removebalance") & filters.user(OWNER_ID))
async def remove_balance(client: Client, message: Message):
    try:
        _, user_id, amount = message.text.split()
        user_id = int(user_id)
        amount = float(amount)
        
        user_data = await fetch_user_data(user_id)
        if user_data:
            new_balance = max(0, user_data['balance'] - amount)
            await update_user_data(user_id, {"balance": new_balance})
            await message.reply_text(f"💰 **Balance Updated**\n\nUser: `{user_id}`\nDeducted: `${amount}`\nNew Balance: `${new_balance}`", parse_mode=ParseMode.MARKDOWN)
        else:
            await message.reply_text("⚠️ **User Not Found!**\nCheck ID and try again")
    except ValueError:
        await message.reply_text("❌ **Invalid Format!**\nUse: `/removebalance [user_id] [amount]`")

@Client.on_message(filters.command("stats") & filters.user(SUDO_USERS))
async def show_stats(client: Client, message: Message):
    total_users, total_numbers, total_balance = await get_total_stats()
    stats_text = f"📊 **System Statistics**\n\n"
    stats_text += f"👥 Users: `{total_users}`\n"
    stats_text += f"📱 Numbers: `{total_numbers}`\n"
    stats_text += f"💰 Total Balance Of All Users: `${total_balance:.2f}`"
    await message.reply_text(stats_text, parse_mode=ParseMode.MARKDOWN)

from pyrogram import Client, filters
from pyrogram.types import Message
from config import SUDO_USERS
from OTP.database.database import fetch_all_user_ids

@Client.on_message(filters.command("broadcast") & filters.user(SUDO_USERS) & filters.reply)
async def broadcast(client: Client, message: Message):
    if not message.reply_to_message:
        await message.reply_text("⚠️ **Reply to a message to broadcast it!**")
        return

    user_ids = await fetch_all_user_ids()
    broadcast_message = message.reply_to_message

    success_count = 0
    failure_count = 0

    for user_id in user_ids:
        try:
            await broadcast_message.forward(chat_id=user_id)
            success_count += 1
        except Exception as e:
            print(f"Failed to send message to {user_id}: {e}")
            failure_count += 1

    await message.reply_text(f"✅ **Broadcast completed!**\n\n**Successful:** {success_count}\n**Failed:** {failure_count}")