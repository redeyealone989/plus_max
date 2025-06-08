from pyrogram import Client, filters
from pyrogram.types import CallbackQuery
from pyrogram.errors import (
    PhoneNumberInvalid, PhoneCodeInvalid,
    PhoneCodeExpired, SessionPasswordNeeded
)
from OTP.utils.keyboards import buy_otp_keyboard, account_navigation_keyboard, confirmation_keyboard, otp_received_keyboard, years_keyboard, deposit_amount_keyboard
from OTP.database.database import fetch_otp_data, fetch_user_data, update_user_data, delete_otp_data, count_otp_data, get_unique_years, lock_number, unlock_number, is_number_locked, fetch_otp_number
from config import API_ID, API_HASH
import asyncio
import re
from pyrogram.enums import ParseMode

@Client.on_callback_query(filters.regex(r'^buy_otp$'))
async def buy_otp(client: Client, callback_query: CallbackQuery):
    fresh_count = await count_otp_data(is_old=False)
    old_count = await count_otp_data(is_old=True)
    
    await callback_query.edit_message_text(
        "**🔎 Select Account Type:**",
        reply_markup=buy_otp_keyboard(fresh_count, old_count),
        parse_mode=ParseMode.MARKDOWN
    )

@Client.on_callback_query(filters.regex(r'^back_to_main$'))
async def back_to_main(client: Client, callback_query: CallbackQuery):
    fresh_count = await count_otp_data(is_old=False)
    old_count = await count_otp_data(is_old=True)
    
    await callback_query.edit_message_text(
        "**🔎 Select Account Type:**",
        reply_markup=buy_otp_keyboard(fresh_count, old_count),
        parse_mode=ParseMode.MARKDOWN
    )

@Client.on_callback_query(filters.regex(r'^old_accounts$'))
async def show_old_accounts(client: Client, callback_query: CallbackQuery):
    years = await get_unique_years()
    year_counts = {}
    for year in years:
        year_counts[year] = await count_otp_data(is_old=True, year=year)
    
    await callback_query.edit_message_text(
        "**📅 Select Account Year:**",
        reply_markup=years_keyboard(year_counts),
        parse_mode=ParseMode.MARKDOWN
    )


    
@Client.on_callback_query(filters.regex(r'^fresh_accounts$'))
async def show_fresh_accounts(client: Client, callback_query: CallbackQuery):
    accounts = await fetch_otp_data(is_old=False)
    if not accounts:
        await callback_query.answer("⚠️ No fresh accounts available!", show_alert=True)
        return
    
    account = accounts[0]
    text = f"**📱 Number:** `{account['number']}`\n**💵 Price:** `${account['price']}`"
    
    await callback_query.edit_message_text(
        text,
        reply_markup=account_navigation_keyboard(False, 0, len(accounts)),
        parse_mode=ParseMode.MARKDOWN
    )

@Client.on_callback_query(filters.regex(r'^year_(\d{4})$'))
async def show_old_accounts_by_year(client: Client, callback_query: CallbackQuery):
    year = int(callback_query.matches[0].group(1))
    accounts = await fetch_otp_data(is_old=True, year=year)
    if not accounts:
        await callback_query.answer(f"⚠️ No {year} accounts available!", show_alert=True)
        return
    
    account = accounts[0]
    text = f"**📱 Number:** `{account['number']}`\n**💵 Price:** `${account['price']}`\n**📅 Year:** {year}"
    
    await callback_query.edit_message_text(
        text,
        reply_markup=account_navigation_keyboard(True, 0, len(accounts)),
        parse_mode=ParseMode.MARKDOWN
    )


@Client.on_callback_query(filters.regex(r'^buy_(True|False)_(\d+)$'))
async def buy_account(client: Client, callback_query: CallbackQuery):
    is_old, index = callback_query.data.split("_")[1:]
    is_old = is_old == "True"
    index = int(index)
    
    year = None
    if is_old:
        year = int(callback_query.message.caption.split("\n")[-1].split(": ")[-1])
    
    accounts = await fetch_otp_data(is_old=is_old, year=year)
    if not accounts or index >= len(accounts):
        await callback_query.answer("⚠️ Account unavailable!", show_alert=True)
        return
    
    account = accounts[index]
    user_data = await fetch_user_data(callback_query.from_user.id)
    
    if user_data['balance'] <= account['price']:
        await callback_query.answer("❌ Insufficient Balance!\nDeposit funds first!", show_alert=True)
        await client.send_message(chat_id=callback_query.from_user.id, text="**❌ Insufficient Balance!\nDeposit funds first!**", reply_markup=deposit_amount_keyboard(), parse_mode=ParseMode.MARKDOWN)
        return
    
    confirmation_text = (
        "**⚠️ Confirm Purchase**\n\n"
        f"📱 Number: `{account['number']}`\n"
        f"💵 Price: `${account['price']}`\n\n"
        "⚠️ Important Notice!\n\n"
        "Before Clicking get OTP, please make sure you have sent an OTP request to the number.\n\n"
        )
    
    if is_old:
        confirmation_text += f"\n📅 Year: {account['year']}"
    
    await callback_query.edit_message_text(
        confirmation_text,
        reply_markup=confirmation_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )

@Client.on_callback_query(filters.regex(r'^confirm_buy$'))
async def confirm_buy(_, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    user_data = await fetch_user_data(user_id)
    
    message_lines = callback_query.message.caption.split('\n')
    number = None
    for line in message_lines:
        if line.startswith("📱 Number:"):
            number = line.split(": ", 1)[1].strip()
            break
    
    accounts = await fetch_otp_number(number)
    if not accounts:
        await callback_query.answer("⚠️ Account no longer available!", show_alert=True)
        return
    
    account = accounts
    
    if user_data['balance'] < account['price']:
        unlock_number(account['number'])
        await callback_query.answer("❌ Transaction Failed!\nInsufficient balance!", show_alert=True)
        return

    SESSION = account['session']

    async def start_new_client():
        client_name = f"user_{user_id}"
        kela = Client(client_name, API_ID, API_HASH, session_string=SESSION, in_memory=True)
        try:
            await kela.start()
            
            await asyncio.sleep(35)
                 
            
            # Get chat history from the official Telegram bot
            async for message in kela.get_chat_history(777000, limit=1):
                if "Login code" in message.text:
                    match = re.search(r'Login code: (\d+)', message.text)
                    if match:
                        otp = match.group(1)
                        return otp
            return None
        except SessionPasswordNeeded:
            return "2FA_NEEDED"
        
        except Exception as e:
            print(f"Error in client session: {str(e)}")
            return None
        
    await callback_query.edit_message_text(
        "**⏳ Processing...**\n\nSend OTP to the number. Auto-detection enabled!\n\n**Pleas Wait Up Too 35 sec**",
        parse_mode=ParseMode.MARKDOWN
    )
    otp = await start_new_client()

    if otp == "2FA_NEEDED":
        unlock_number(account['number'])
        await callback_query.edit_message_text(
            "🔒 **2FA Required!**\nContact @plusotpsupport",
            reply_markup=None,
            parse_mode=ParseMode.MARKDOWN
        )
    elif otp:
        await update_user_data(user_id, {
            "balance": user_data['balance'] - account['price'],
            "number_bought": user_data['number_bought'] + 1,
            "transaction_count": user_data['transaction_count'] + 1
        })
        
        await delete_otp_data(account['number'])
        
        success_message = f"**✅ Purchase Complete!**\n\n📱 Number: `{account['number']}`\n🔑 OTP: `{otp}`\n🔒 2FA: `{account['twofa']}`\n💵 Deducted: `${account['price']}`"
        
        await callback_query.edit_message_text(
            success_message,
            reply_markup=otp_received_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        unlock_number(account['number'])
        await callback_query.edit_message_text(
            "⚠️ **OTP Retrieval Failed!**\nContact support immediately!",
            reply_markup=None,
            parse_mode=ParseMode.MARKDOWN
        )

@Client.on_callback_query(filters.regex(r'^cancel_buy$'))
async def cancel_buy(client: Client, callback_query: CallbackQuery):
    await callback_query.edit_message_text(
        "❌ **Purchase Cancelled**",
        reply_markup=None,
        parse_mode=ParseMode.MARKDOWN
    )

@Client.on_callback_query(filters.regex(r'^done_otp$'))
async def done_otp(client: Client, callback_query: CallbackQuery):
    await callback_query.edit_message_text(
        "**🎉 Transaction Completed!**\n\n"
        "✅ In Your Account session`s has been generated **automatically** by the system, not manually by any other user—so no need to panic!\n"
        "⚠️ If needed, you can terminate other bot sessions in **Settings > Devices** after 24 hours.\n\n"
        "**Payment Made By:** 💵 USD\n\n"
        "Thank you for purchasing!\n\n"
        "Need help? Contact @plusotpsupport",
        reply_markup=None,
        parse_mode=ParseMode.MARKDOWN
    )

