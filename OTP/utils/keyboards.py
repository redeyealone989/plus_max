from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime

def start_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔑 Buy OTP", callback_data="buy_otp")],
        [InlineKeyboardButton("🛟 Support", url="https://t.me/plusotpsupport"),
         InlineKeyboardButton("📢 Updates", url="https://t.me/plusotpupdates")],
        [InlineKeyboardButton("💰 Refer & Earn", callback_data="refer_stats")]
    ])

def buy_otp_keyboard(fresh_count, old_count):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"🌱 Fresh Accounts ({fresh_count})", callback_data="fresh_accounts")],
        [InlineKeyboardButton(f"🕰 Old Accounts ({old_count})", callback_data="old_accounts")]
    ])

def account_navigation_keyboard(is_old, current_index, total_accounts):
    buttons = []
    buttons.append([InlineKeyboardButton("💳 Buy Now", callback_data=f"buy_{is_old}_{current_index}")])

    if is_old:
        buttons.append([InlineKeyboardButton("↩️ Back to Years", callback_data="old_accounts")])

    return InlineKeyboardMarkup(buttons)
    
def confirmation_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Get OTP", callback_data="confirm_buy")],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel_buy")]
    ])

def otp_received_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏁 Finish Session", callback_data="done_otp")]
    ])


def years_keyboard(old_count):
    current_year = datetime.now().year
    years = range(current_year - 10, current_year + 1)
    buttons = [InlineKeyboardButton(f"📅 {year} ({old_count.get(year, 0)})", callback_data=f"year_{year}") for year in years]
    year_buttons = [buttons[i:i+3] for i in range(0, len(buttons), 3)]
    year_buttons.append([InlineKeyboardButton("↩️ Back", callback_data="back_to_main")])
    return InlineKeyboardMarkup(year_buttons)

def deposit_amount_keyboard():
    buttons = [
        [
            InlineKeyboardButton("💵 $5", callback_data="deposit_5"),
            InlineKeyboardButton("💵 $10", callback_data="deposit_10")
        ],
        [
            InlineKeyboardButton("💵 $15", callback_data="deposit_15"),
            InlineKeyboardButton("💵 $20", callback_data="deposit_20")
        ],
        [InlineKeyboardButton("💵 Custom Deposit", callback_data="custom_deposit")]
    ]
    return InlineKeyboardMarkup(buttons)
