import asyncio
import urllib.parse
import base64
from pyrogram import filters, Client
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait

from referral_handler import referral_manager
from bot import Bot
from config import ADMINS, CHANNEL_ID, DISABLE_CHANNEL_BUTTON, USER_REPLY_TEXT


# ============================================================
# ✅ FIXED ENCODER (now fully working)
# ============================================================
def encode(text: str) -> str:
    text_bytes = text.encode("utf-8")
    base64_bytes = base64.urlsafe_b64encode(text_bytes)
    return base64_bytes.decode("utf-8")


# ============================================================
# ✅ Admins private messages handler
# ============================================================
@Bot.on_message(
    filters.private
    & filters.user(ADMINS)
    & ~filters.command([
        'start', 'users', 'broadcast', 'batch', 'genlink', 'stats',
        'auth_secret', 'deauth_secret', 'auth', 'sbatch', 'exit',
        'add_admin', 'del_admin', 'admins', 'add_prem', 'ping',
        'restart', 'ch2l', 'cancel'
    ])
)
async def channel_post(client: Client, message: Message):

    reply_text = await message.reply_text("Please Wait...! 🫷", quote=True)

    # --- Copy post to channel ---
    try:
        post_message = await message.copy(
            chat_id=client.db_channel.id,
            disable_notification=True
        )
    except FloodWait as e:
        await asyncio.sleep(e.value)
        post_message = await message.copy(
            chat_id=client.db_channel.id,
            disable_notification=True
        )
    except Exception as e:
        print("Copy Error:", e)
        await reply_text.edit_text("Something went Wrong..! ❌")
        return

    # --- Encode Link ---
    converted_id = post_message.id * abs(client.db_channel.id)
    string = f"get-{converted_id}"
    base64_string = encode(string)

    link = f"https://t.me/{client.username}?start={base64_string}"

    # --- SAFE URL ---
    encoded_link = urllib.parse.quote(link, safe="")

    reply_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔁 Share URL", url=f"https://telegram.me/share/url?url={encoded_link}")]
    ])

    await reply_text.edit(
        f"<b>🧑‍💻 Here is your code : </b>\n<code>{base64_string}</code>\n\n"
        f"<b>🔗 Here is your link :</b>\n{link}",
        reply_markup=reply_markup,
        disable_web_page_preview=True
    )

    if not DISABLE_CHANNEL_BUTTON:
        try:
            await post_message.edit_reply_markup(reply_markup)
        except FloodWait as e:
            await asyncio.sleep(e.value)
            await post_message.edit_reply_markup(reply_markup)
        except Exception:
            pass


# ============================================================
# ✅ Channel new post handler
# ============================================================
@Bot.on_message(filters.channel & filters.incoming & filters.chat(CHANNEL_ID))
async def new_post(client: Client, message: Message):

    if DISABLE_CHANNEL_BUTTON:
        return

    converted_id = message.id * abs(client.db_channel.id)
    string = f"get-{converted_id}"
    base64_string = encode(string)

    link = f"https://t.me/{client.username}?start={base64_string}"
    encoded_link = urllib.parse.quote(link, safe="")

    reply_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔁 Share URL", url=f"https://telegram.me/share/url?url={encoded_link}")]
    ])

    try:
        await message.edit_reply_markup(reply_markup)
    except FloodWait as e:
        await asyncio.sleep(e.value)
        await message.edit_reply_markup(reply_markup)
    except Exception:
        pass
