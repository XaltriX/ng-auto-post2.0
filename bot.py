"""
Main entry point — starts Pyrogram bot + background scheduler.
"""
import asyncio
from pyrogram import Client
from config import API_ID, API_HASH, BOT_TOKEN
import handlers
import scheduler


async def main():
    app = Client(
        "linkz_wallah_bot",
        api_id=API_ID,
        api_hash=API_HASH,
        bot_token=BOT_TOKEN,
    )

    handlers.register_handlers(app)

    async with app:
        print("[BOT] Running...")
        # Start background scheduler as concurrent task
        asyncio.create_task(scheduler.scheduler_loop(app))
        await asyncio.Event().wait()  # Run forever


if __name__ == "__main__":
    asyncio.run(main())