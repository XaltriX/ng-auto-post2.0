"""
Helpers: build caption, buttons, and send post to channels.
"""
from pyrogram import Client
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import database as db


def build_caption(title: str, preview_link: str | None, main_link: str) -> str:
    """
    Builds the final post caption.
    - No thumbnail is used anymore (text-only post).
    - Preview / Download links are shown twice each (visual emphasis),
      even though the user only provides one link for each.
    """
    lines = [
        "┏━━━━━ 𝗡𝗘𝗪 𝗣𝗢𝗦𝗧 ━━━━━┓",
        "",
        f"🎬 **{title}**",
        "",
    ]

    if preview_link:
        lines += [
            "👀 **PREVIEW**",
            f"➥ __[Click Here]({preview_link})__",
            f"➥ __[Click Here]({preview_link})__",
            "",
        ]

    lines += [
        "📥 **DOWNLOAD & WATCH**",
        f"➥ __[Click Here]({main_link})__",
        f"➥ __[Click Here]({main_link})__",
        "",
        "┗━━━━ **@Linkz_wallah** ━━━━┛",
    ]

    return "\n".join(lines)


def build_buttons() -> InlineKeyboardMarkup:
    """Only the Buy Premium / Remove Ads button remains inline now."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💎 Buy Premium / Remove Ads", url="https://t.me/NgPremiumX/14")],
    ])


async def send_post_to_channels(
    app: Client,
    title: str,
    main_link: str,
    preview: str | None,
    channel_ids: list[int],
) -> int:
    """
    Sends a text-only post (no photo/video, no link preview) to the given
    channel ids. Returns count of successful sends.
    """
    caption = build_caption(title, preview, main_link)
    buttons = build_buttons()
    success = 0
    for cid in channel_ids:
        try:
            await app.send_message(
                chat_id=cid,
                text=caption,
                reply_markup=buttons,
                disable_web_page_preview=True,
            )
            success += 1
        except Exception as e:
            print(f"[ERROR] channel {cid}: {e}")
    await db.save_log(title, channel_ids)
    return success
