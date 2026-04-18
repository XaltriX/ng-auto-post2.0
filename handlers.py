"""
All bot handlers — wired with Pyrogram filters.
"""
from pyrogram import Client, filters
from pyrogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
)
from datetime import datetime, timezone, timedelta
import re

IST = timezone(timedelta(hours=5, minutes=30))

def to_ist(dt: datetime) -> str:
    """Convert any datetime to IST string."""
    return dt.astimezone(IST).strftime("%d-%m-%Y %H:%M IST")

import database as db
import helpers
import state
from config import ADMIN_IDS

# ── Admin guard ───────────────────────────────────────────────────────────────

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


# ── /start ────────────────────────────────────────────────────────────────────

def register_handlers(app: Client):

    @app.on_message(filters.command("start") & filters.private)
    async def cmd_start(client: Client, msg: Message):
        if not is_admin(msg.from_user.id):
            return await msg.reply("⛔ Unauthorized.")
        state.clear(msg.from_user.id)
        await msg.reply(
            "Welcome to **Linkz_Wallah Bot** 🤖",
            reply_markup=main_menu(),
        )

    # ── Callback router ───────────────────────────────────────────────────────

    @app.on_callback_query()
    async def cb_router(client: Client, cb: CallbackQuery):
        uid = cb.from_user.id
        if not is_admin(uid):
            return await cb.answer("⛔ Unauthorized.", show_alert=True)
        data = cb.data
        await cb.answer()

        # ── Main menu ─────────────────────────────────────────────────────────
        if data == "main_menu":
            state.clear(uid)
            await cb.message.edit_text(
                "Welcome to **Linkz_Wallah Bot** 🤖",
                reply_markup=main_menu(),
            )

        elif data == "create_post":
            state.clear(uid)
            state.set_key(uid, "step", "title")
            await cb.message.edit_text("📝 Send the **Title** of your post:")

        # ── Post Now / Schedule ───────────────────────────────────────────────
        elif data == "post_now":
            channels = await db.get_all_channels()
            if not channels:
                return await cb.message.edit_text(
                    "❌ No channels added yet.\n\nAdd channels first.",
                    reply_markup=back_btn(),
                )
            state.set_key(uid, "post_mode", "now")
            await cb.message.edit_text(
                "📢 **Choose channels to post:**",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ All Channels", callback_data="pn_ch_all")],
                    [InlineKeyboardButton("🎯 Select Channels", callback_data="pn_ch_select")],
                ]),
            )

        elif data == "pn_ch_all":
            channels = await db.get_all_channels()
            cids = [c["channel_id"] for c in channels]
            state.set_key(uid, "pn_selected", cids)
            await do_post_now(client, cb.message, uid)

        elif data == "pn_ch_select":
            channels = await db.get_all_channels()
            state.set_key(uid, "pn_toggle", {c["channel_id"]: False for c in channels})
            state.set_key(uid, "pn_channel_list", channels)
            await show_pn_toggle_list(cb.message, uid)

        elif data.startswith("pn_toggle_"):
            cid = int(data.split("_", 2)[2])
            toggles = state.get_key(uid, "pn_toggle", {})
            toggles[cid] = not toggles.get(cid, False)
            state.set_key(uid, "pn_toggle", toggles)
            await show_pn_toggle_list(cb.message, uid)

        elif data == "pn_confirm_select":
            toggles = state.get_key(uid, "pn_toggle", {})
            selected = [cid for cid, chosen in toggles.items() if chosen]
            if not selected:
                return await cb.answer("⚠️ Select at least one channel.", show_alert=True)
            state.set_key(uid, "pn_selected", selected)
            await do_post_now(client, cb.message, uid)

        elif data == "schedule_post":
            state.set_key(uid, "step", "sched_type")
            await cb.message.edit_text(
                "⏰ Choose schedule type:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⚡ Quick Schedule", callback_data="quick_sched"),
                     InlineKeyboardButton("🕒 Custom Time", callback_data="custom_sched")],
                    [InlineKeyboardButton("🔙 Back", callback_data="main_menu")],
                ]),
            )

        # ── Quick Schedule ────────────────────────────────────────────────────
        elif data == "quick_sched":
            await cb.message.edit_text(
                "⚡ Choose mode:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⏱ Minutes", callback_data="qs_minutes"),
                     InlineKeyboardButton("🕐 Hours", callback_data="qs_hours")],
                    [InlineKeyboardButton("📅 Today", callback_data="qs_today"),
                     InlineKeyboardButton("🌅 Tomorrow", callback_data="qs_tomorrow")],
                    [InlineKeyboardButton("🔙 Back", callback_data="schedule_post")],
                ]),
            )

        elif data == "qs_minutes":
            await cb.message.edit_text(
                "⏱ Choose minutes:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("+5m", callback_data="qst_5m"),
                     InlineKeyboardButton("+10m", callback_data="qst_10m"),
                     InlineKeyboardButton("+15m", callback_data="qst_15m")],
                    [InlineKeyboardButton("+30m", callback_data="qst_30m"),
                     InlineKeyboardButton("+60m", callback_data="qst_60m")],
                    [InlineKeyboardButton("🔙 Back", callback_data="quick_sched")],
                ]),
            )

        elif data == "qs_hours":
            await cb.message.edit_text(
                "🕐 Choose hours:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("+1h", callback_data="qst_1h"),
                     InlineKeyboardButton("+2h", callback_data="qst_2h"),
                     InlineKeyboardButton("+3h", callback_data="qst_3h")],
                    [InlineKeyboardButton("+6h", callback_data="qst_6h"),
                     InlineKeyboardButton("+12h", callback_data="qst_12h")],
                    [InlineKeyboardButton("🔙 Back", callback_data="quick_sched")],
                ]),
            )

        elif data == "qs_today":
            await cb.message.edit_text(
                "📅 Choose time today (IST):",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("6 PM", callback_data="qst_today_18"),
                     InlineKeyboardButton("7 PM", callback_data="qst_today_19"),
                     InlineKeyboardButton("8 PM", callback_data="qst_today_20")],
                    [InlineKeyboardButton("9 PM", callback_data="qst_today_21"),
                     InlineKeyboardButton("10 PM", callback_data="qst_today_22")],
                    [InlineKeyboardButton("🔙 Back", callback_data="quick_sched")],
                ]),
            )

        elif data == "qs_tomorrow":
            await cb.message.edit_text(
                "🌅 Choose time tomorrow (IST):",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("9 AM", callback_data="qst_tmrw_9"),
                     InlineKeyboardButton("12 PM", callback_data="qst_tmrw_12")],
                    [InlineKeyboardButton("6 PM", callback_data="qst_tmrw_18"),
                     InlineKeyboardButton("9 PM", callback_data="qst_tmrw_21")],
                    [InlineKeyboardButton("🔙 Back", callback_data="quick_sched")],
                ]),
            )

        elif data == "custom_sched":
            state.set_key(uid, "step", "custom_time")
            await cb.message.edit_text(
                "🕒 Send date & time in format:\n`DD-MM HH:MM`\n\nExample: `25-07 21:00`"
            )

        # ── Quick schedule time resolution ────────────────────────────────────
        elif data.startswith("qst_"):
            sched_time = resolve_quick_time(data)
            if not sched_time:
                return await cb.message.edit_text("❌ Invalid option.")
            state.set_key(uid, "schedule_time", sched_time)
            await show_channel_selection(cb.message, uid)

        # ── Channel selection ─────────────────────────────────────────────────
        elif data == "ch_all":
            channels = await db.get_all_channels()
            cids = [c["channel_id"] for c in channels]
            state.set_key(uid, "selected_channels", cids)
            await show_schedule_confirm(cb.message, uid)

        elif data == "ch_select":
            channels = await db.get_all_channels()
            if not channels:
                return await cb.message.edit_text("❌ No channels found.", reply_markup=back_btn())
            state.set_key(uid, "toggle_channels", {c["channel_id"]: False for c in channels})
            state.set_key(uid, "channel_list", channels)
            await show_toggle_list(cb.message, uid)

        elif data.startswith("toggle_"):
            cid = int(data.split("_", 1)[1])
            toggles = state.get_key(uid, "toggle_channels", {})
            toggles[cid] = not toggles.get(cid, False)
            state.set_key(uid, "toggle_channels", toggles)
            await show_toggle_list(cb.message, uid)

        elif data == "ch_confirm_select":
            toggles = state.get_key(uid, "toggle_channels", {})
            selected = [cid for cid, chosen in toggles.items() if chosen]
            if not selected:
                return await cb.answer("⚠️ Select at least one channel.", show_alert=True)
            state.set_key(uid, "selected_channels", selected)
            await show_schedule_confirm(cb.message, uid)

        # ── Schedule confirm/cancel ───────────────────────────────────────────
        elif data == "sched_confirm":
            sess = state.get(uid)
            await db.save_scheduled_post({
                "title": sess["title"],
                "thumbnail": sess["thumbnail"],
                "main_link": sess["main_link"],
                "preview": sess.get("preview"),
                "is_video": sess.get("is_video", False),
                "channels": sess["selected_channels"],
                "schedule_time": sess["schedule_time"],
            })
            state.clear(uid)
            await cb.message.edit_text("✅ Post scheduled!", reply_markup=back_btn())

        elif data == "sched_cancel":
            state.clear(uid)
            await cb.message.edit_text("❌ Scheduling cancelled.", reply_markup=back_btn())

        # ── Channel Manager ───────────────────────────────────────────────────
        elif data == "manage_channels":
            await cb.message.edit_text(
                "📢 **Channel Manager**",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("➕ Add Channel", callback_data="add_channel")],
                    [InlineKeyboardButton("➖ Remove Channel", callback_data="remove_channel")],
                    [InlineKeyboardButton("📋 List Channels", callback_data="list_channels")],
                    [InlineKeyboardButton("🔙 Back", callback_data="main_menu")],
                ]),
            )

        elif data == "add_channel":
            state.set_key(uid, "step", "add_channel")
            await cb.message.edit_text(
                "➕ Send the **Channel ID** (e.g. `-1001234567890`)\nor forward any message from the channel:"
            )

        elif data == "remove_channel":
            channels = await db.get_all_channels()
            if not channels:
                return await cb.message.edit_text("No channels found.", reply_markup=back_btn())
            buttons = [
                [InlineKeyboardButton(f"❌ {c['title']} ({c['channel_id']})", callback_data=f"del_ch_{c['channel_id']}")]
                for c in channels
            ]
            buttons.append([InlineKeyboardButton("🔙 Back", callback_data="manage_channels")])
            await cb.message.edit_text("Select channel to remove:", reply_markup=InlineKeyboardMarkup(buttons))

        elif data.startswith("del_ch_"):
            cid = int(data.split("_", 2)[2])
            await db.remove_channel(cid)
            await cb.message.edit_text("✅ Channel removed.", reply_markup=back_btn())

        elif data == "list_channels":
            channels = await db.get_all_channels()
            if not channels:
                text = "No channels added yet."
            else:
                lines = [f"• **{c['title']}** — `{c['channel_id']}`" for c in channels]
                text = "📋 **Channels:**\n\n" + "\n".join(lines)
            await cb.message.edit_text(text, reply_markup=back_btn())

        # ── Dashboard ─────────────────────────────────────────────────────────
        elif data == "dashboard":
            await show_dashboard(cb.message)

        elif data == "view_scheduled":
            posts = await db.get_all_pending_posts()
            if not posts:
                return await cb.message.edit_text("No scheduled posts.", reply_markup=back_btn())
            lines = []
            for p in posts:
                t = to_ist(p["schedule_time"])
                lines.append(f"• {t} — {p['title'][:30]}")
            await cb.message.edit_text(
                "📅 **All Scheduled:**\n\n" + "\n".join(lines),
                reply_markup=back_btn(),
            )

        elif data == "cancel_post_menu":
            posts = await db.get_all_pending_posts()
            if not posts:
                return await cb.message.edit_text("No pending posts.", reply_markup=back_btn())
            buttons = [
                [InlineKeyboardButton(
                    f"❌ {p['title'][:25]} ({p['schedule_time'].astimezone(IST).strftime('%d-%m %H:%M IST')})",
                    callback_data=f"do_cancel_{p['_id']}"
                )]
                for p in posts
            ]
            buttons.append([InlineKeyboardButton("🔙 Back", callback_data="dashboard")])
            await cb.message.edit_text("Select post to cancel:", reply_markup=InlineKeyboardMarkup(buttons))

        elif data.startswith("do_cancel_"):
            post_id = data.split("_", 2)[2]
            await db.cancel_post(post_id)
            await cb.message.edit_text("✅ Post cancelled.", reply_markup=back_btn())

    # ── Message handler (multi-step text/media input) ─────────────────────────

    @app.on_message(filters.private & ~filters.command(["start"]))
    async def msg_handler(client: Client, msg: Message):
        uid = msg.from_user.id
        if not is_admin(uid):
            return

        step = state.get_key(uid, "step")

        if step == "title":
            state.set_key(uid, "title", msg.text.strip())
            state.set_key(uid, "step", "thumbnail")
            await msg.reply("📸 Now send the **Thumbnail** (photo or video):")

        elif step == "thumbnail":
            if msg.photo:
                state.set_key(uid, "thumbnail", msg.photo.file_id)
                state.set_key(uid, "is_video", False)
            elif msg.video:
                state.set_key(uid, "thumbnail", msg.video.file_id)
                state.set_key(uid, "is_video", True)
            else:
                return await msg.reply("⚠️ Please send a photo or video.")
            state.set_key(uid, "step", "main_link")
            await msg.reply("🔗 Send the **Main Link**:")

        elif step == "main_link":
            state.set_key(uid, "main_link", msg.text.strip())
            state.set_key(uid, "step", "preview")
            await msg.reply("👀 Send **Preview Link** or type /skip:")

        elif step == "preview":
            if msg.text and msg.text.strip() == "/skip":
                state.set_key(uid, "preview", None)
            else:
                state.set_key(uid, "preview", msg.text.strip() if msg.text else None)
            state.set_key(uid, "step", None)
            await msg.reply(
                "✅ **Post Ready!**",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🚀 Post Now", callback_data="post_now")],
                    [InlineKeyboardButton("⏰ Schedule Post", callback_data="schedule_post")],
                ]),
            )

        elif step == "add_channel":
            channel_id = None
            title = "Unknown"

            if msg.forward_from_chat:
                channel_id = msg.forward_from_chat.id
                title = msg.forward_from_chat.title or "Unknown"
            elif msg.text:
                text = msg.text.strip()
                # Invite link
                if "t.me/" in text:
                    try:
                        chat = await client.get_chat(text)
                        channel_id = chat.id
                        title = chat.title or "Unknown"
                    except Exception as e:
                        return await msg.reply(f"❌ Could not resolve link: {e}")
                else:
                    try:
                        channel_id = int(text)
                        chat = await client.get_chat(channel_id)
                        title = chat.title or str(channel_id)
                    except Exception as e:
                        return await msg.reply(f"❌ Invalid channel ID: {e}")

            if channel_id is None:
                return await msg.reply("❌ Could not extract channel ID. Try forwarding a message.")

            added = await db.add_channel(channel_id, title)
            state.set_key(uid, "step", None)
            if added:
                await msg.reply(f"✅ Channel **{title}** (`{channel_id}`) added.", reply_markup=back_btn())
            else:
                await msg.reply(f"⚠️ Channel already exists.", reply_markup=back_btn())

        elif step == "custom_time":
            text = msg.text.strip() if msg.text else ""
            try:
                # Parse DD-MM HH:MM as IST (UTC+5:30)
                dt = datetime.strptime(text, "%d-%m %H:%M")
                now = datetime.now(timezone.utc)
                ist_offset = timedelta(hours=5, minutes=30)
                # Use current year
                dt = dt.replace(year=now.year)
                # Convert IST to UTC
                sched_time = dt.replace(tzinfo=timezone(ist_offset)).astimezone(timezone.utc)
                if sched_time <= now:
                    return await msg.reply("⚠️ Time must be in the future.")
                state.set_key(uid, "schedule_time", sched_time)
                state.set_key(uid, "step", None)
                await show_channel_selection_msg(msg, uid)
            except ValueError:
                await msg.reply("❌ Wrong format. Use `DD-MM HH:MM` e.g. `25-07 21:00`")


# ── Helper UI functions ───────────────────────────────────────────────────────

def main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📝 Create Post", callback_data="create_post")],
        [InlineKeyboardButton("📢 Manage Channels", callback_data="manage_channels")],
        [InlineKeyboardButton("📊 Dashboard", callback_data="dashboard")],
    ])


async def do_post_now(client, message, uid: int):
    sess = state.get(uid)
    cids = sess.get("pn_selected", [])
    sent = await helpers.send_post_to_channels(
        app=client,
        title=sess["title"],
        thumbnail=sess["thumbnail"],
        main_link=sess["main_link"],
        preview=sess.get("preview"),
        channel_ids=cids,
        is_video=sess.get("is_video", False),
    )
    state.clear(uid)
    await message.edit_text(
        f"✅ Posted successfully in **{sent}** channel(s).",
        reply_markup=back_btn(),
    )


async def show_pn_toggle_list(message, uid: int):
    toggles: dict = state.get_key(uid, "pn_toggle", {})
    channel_list: list = state.get_key(uid, "pn_channel_list", [])
    buttons = []
    for c in channel_list:
        cid = c["channel_id"]
        mark = "☑" if toggles.get(cid) else "☐"
        buttons.append([InlineKeyboardButton(
            f"{mark} {c['title']}",
            callback_data=f"pn_toggle_{cid}"
        )])
    buttons.append([InlineKeyboardButton("✅ Confirm & Post", callback_data="pn_confirm_select")])
    try:
        await message.edit_text("Select channels to post:", reply_markup=InlineKeyboardMarkup(buttons))
    except Exception:
        pass


def back_btn() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")]])


async def show_channel_selection(message, uid: int):
    channels = await db.get_all_channels()
    if not channels:
        await message.edit_text("❌ No channels found.", reply_markup=back_btn())
        return
    await message.edit_text(
        "📢 Choose channels:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ All Channels", callback_data="ch_all")],
            [InlineKeyboardButton("🎯 Select Channels", callback_data="ch_select")],
        ]),
    )


async def show_channel_selection_msg(message: Message, uid: int):
    channels = await db.get_all_channels()
    if not channels:
        await message.reply("❌ No channels found.", reply_markup=back_btn())
        return
    await message.reply(
        "📢 Choose channels:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ All Channels", callback_data="ch_all")],
            [InlineKeyboardButton("🎯 Select Channels", callback_data="ch_select")],
        ]),
    )


async def show_toggle_list(message, uid: int):
    toggles: dict = state.get_key(uid, "toggle_channels", {})
    channel_list: list = state.get_key(uid, "channel_list", [])
    buttons = []
    for c in channel_list:
        cid = c["channel_id"]
        mark = "☑" if toggles.get(cid) else "☐"
        buttons.append([InlineKeyboardButton(
            f"{mark} {c['title']}",
            callback_data=f"toggle_{cid}"
        )])
    buttons.append([InlineKeyboardButton("✅ Confirm Selection", callback_data="ch_confirm_select")])
    try:
        await message.edit_text("Select channels:", reply_markup=InlineKeyboardMarkup(buttons))
    except Exception:
        pass


async def show_schedule_confirm(message, uid: int):
    sess = state.get(uid)
    sched_time: datetime = sess.get("schedule_time")
    channels = sess.get("selected_channels", [])

    ist_offset = timedelta(hours=5, minutes=30)
    ist_time = sched_time.astimezone(timezone(ist_offset))
    time_str = ist_time.strftime("%d-%m-%Y %H:%M IST")

    await message.edit_text(
        f"📋 **Confirm Schedule**\n\n"
        f"🕒 Time: `{time_str}`\n"
        f"📢 Channels: {len(channels)}",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Confirm", callback_data="sched_confirm"),
             InlineKeyboardButton("❌ Cancel", callback_data="sched_cancel")],
        ]),
    )


async def show_dashboard(message):
    pending = await db.get_all_pending_posts()
    today_count = await db.get_today_sent_count()
    last5 = await db.get_last_5_logs()

    lines = [
        f"📊 **Dashboard**\n",
        f"⏳ Pending posts: **{len(pending)}**",
        f"✅ Sent today: **{today_count}**\n",
    ]

    upcoming = pending[:3]
    if upcoming:
        lines.append("🗓 **Upcoming (next 3):**")
        for p in upcoming:
            t = to_ist(p["schedule_time"])
            lines.append(f"  • {t} — {p['title'][:25]}")
        lines.append("")

    if last5:
        lines.append("📜 **Last 5 sent:**")
        for l in last5:
            lines.append(f"  • {l['title'][:30]}")

    await message.edit_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📅 View All Scheduled", callback_data="view_scheduled")],
            [InlineKeyboardButton("❌ Cancel a Post", callback_data="cancel_post_menu")],
            [InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")],
        ]),
    )


def resolve_quick_time(data: str) -> datetime | None:
    now = datetime.now(timezone.utc)
    ist_offset = timedelta(hours=5, minutes=30)

    # Minutes: qst_5m, qst_10m etc.
    m = re.match(r"qst_(\d+)m$", data)
    if m:
        return now + timedelta(minutes=int(m.group(1)))

    # Hours: qst_1h, qst_2h etc.
    m = re.match(r"qst_(\d+)h$", data)
    if m:
        return now + timedelta(hours=int(m.group(1)))

    # Today IST hour: qst_today_18
    m = re.match(r"qst_today_(\d+)$", data)
    if m:
        hour = int(m.group(1))
        today_ist = now.astimezone(timezone(ist_offset))
        target = today_ist.replace(hour=hour, minute=0, second=0, microsecond=0)
        return target.astimezone(timezone.utc)

    # Tomorrow IST hour: qst_tmrw_9
    m = re.match(r"qst_tmrw_(\d+)$", data)
    if m:
        hour = int(m.group(1))
        tmrw_ist = (now + timedelta(days=1)).astimezone(timezone(ist_offset))
        target = tmrw_ist.replace(hour=hour, minute=0, second=0, microsecond=0)
        return target.astimezone(timezone.utc)

    return None