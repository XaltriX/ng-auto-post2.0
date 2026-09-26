"""
Background async worker — checks pending posts every 20 seconds.
"""
import asyncio
from pyrogram import Client
import database as db
import helpers


async def scheduler_loop(app: Client):
    print("[SCHEDULER] Started.")
    while True:
        try:
            posts = await db.get_pending_posts()
            for post in posts:
                # "all" mode → resolve channels LIVE at send time, so any
                # channel added after scheduling (but before send time) is
                # included automatically.
                if post.get("channels_mode") == "all":
                    all_channels = await db.get_all_channels()
                    channel_ids = [c["channel_id"] for c in all_channels]
                else:
                    channel_ids = post.get("channels", [])

                sent = await helpers.send_post_to_channels(
                    app=app,
                    title=post["title"],
                    main_link=post["main_link"],
                    preview=post.get("preview"),
                    channel_ids=channel_ids,
                )
                await db.mark_post_sent(post["_id"])
                print(f"[SCHEDULER] Sent '{post['title']}' to {sent} channels.")
        except Exception as e:
            print(f"[SCHEDULER ERROR] {e}")
        await asyncio.sleep(20)
