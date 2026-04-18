"""
MongoDB database layer using motor (async).
"""
from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGO_URI, MONGO_DB_NAME
from datetime import datetime, timezone

client = AsyncIOMotorClient(MONGO_URI)
db = client[MONGO_DB_NAME]

channels_col = db["channels"]
scheduled_col = db["scheduled_posts"]
logs_col = db["posted_logs"]


# ── Channels ──────────────────────────────────────────────────────────────────

async def add_channel(channel_id: int, title: str):
    existing = await channels_col.find_one({"channel_id": channel_id})
    if existing:
        return False
    await channels_col.insert_one({
        "channel_id": channel_id,
        "title": title,
        "added_at": datetime.now(timezone.utc)
    })
    return True


async def remove_channel(channel_id: int):
    result = await channels_col.delete_one({"channel_id": channel_id})
    return result.deleted_count > 0


async def get_all_channels():
    return await channels_col.find({}).to_list(length=None)


# ── Scheduled Posts ───────────────────────────────────────────────────────────

async def save_scheduled_post(data: dict):
    data["created_at"] = datetime.now(timezone.utc)
    data["status"] = "pending"
    result = await scheduled_col.insert_one(data)
    return result.inserted_id


async def get_pending_posts():
    now = datetime.now(timezone.utc)
    return await scheduled_col.find({
        "status": "pending",
        "schedule_time": {"$lte": now}
    }).to_list(length=None)


async def get_all_pending_posts():
    return await scheduled_col.find({"status": "pending"}).sort("schedule_time", 1).to_list(length=None)


async def mark_post_sent(post_id):
    from bson import ObjectId
    await scheduled_col.update_one(
        {"_id": ObjectId(str(post_id))},
        {"$set": {"status": "sent"}}
    )


async def cancel_post(post_id):
    from bson import ObjectId
    await scheduled_col.update_one(
        {"_id": ObjectId(str(post_id))},
        {"$set": {"status": "cancelled"}}
    )


# ── Posted Logs ───────────────────────────────────────────────────────────────

async def save_log(title: str, channels: list):
    await logs_col.insert_one({
        "title": title,
        "channels": channels,
        "posted_at": datetime.now(timezone.utc)
    })


async def get_today_sent_count():
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    return await logs_col.count_documents({"posted_at": {"$gte": today}})


async def get_last_5_logs():
    return await logs_col.find({}).sort("posted_at", -1).limit(5).to_list(length=None)