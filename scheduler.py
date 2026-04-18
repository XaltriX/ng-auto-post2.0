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
                channels = post.get("channels", [])
                is_video = post.get("is_video", False)
                sent = await helpers.send_post_to_channels(
                    app=app,
                    title=post["title"],
                    thumbnail=post["thumbnail"],
                    main_link=post["main_link"],
                    preview=post.get("preview"),
                    channel_ids=channels,
                    is_video=is_video,
                )
                await db.mark_post_sent(post["_id"])
                print(f"[SCHEDULER] Sent '{post['title']}' to {sent} channels.")
        except Exception as e:
            print(f"[SCHEDULER ERROR] {e}")
        await asyncio.sleep(20)