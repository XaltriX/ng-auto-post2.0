"""
Helpers: build caption, buttons, and send post to channels.
"""
from pyrogram import Client
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import database as db


def build_caption(title: str) -> str:
    return (
        f"🔥 **{title}** 😈💦\n\n"
        f"⚡ @Linkz_Wallah\n\n"
        f"👇 Open Link Below"
    )


def build_buttons(main_link: str, preview: str | None) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton("🚀 Watch & Download", url=main_link)]]
    if preview:
        rows.append([InlineKeyboardButton("👀 See Preview", url=preview)])
    return InlineKeyboardMarkup(rows)


async def send_post_to_channels(
    app: Client,
    title: str,
    thumbnail: str,
    main_link: str,
    preview: str | None,
    channel_ids: list[int],
    is_video: bool = False,
) -> int:
    caption = build_caption(title)
    buttons = build_buttons(main_link, preview)
    success = 0

    for cid in channel_ids:
        try:
            if is_video:
                await app.send_video(
                    chat_id=cid,
                    video=thumbnail,
                    caption=caption,
                    reply_markup=buttons,
                )
            else:
                await app.send_photo(
                    chat_id=cid,
                    photo=thumbnail,
                    caption=caption,
                    reply_markup=buttons,
                )
            success += 1
        except Exception as e:
            print(f"[ERROR] channel {cid}: {e}")

    await db.save_log(title, channel_ids)
    return success