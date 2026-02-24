"""
Migration 001: Add user scoping to existing documents.

- Adds `user_id: "legacy"` to all existing watchlist, portfolio, ai_analyses,
  and chart_analyses documents that lack a user_id field.
- Creates indexes for user-scoped queries.

Run:
    python migrations/001_add_user_scoping.py
"""
import asyncio
import os
import logging
from pathlib import Path

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]


async def migrate():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]

    # ------------------------------------------------------------------
    # 1. Backfill user_id = "legacy" on existing documents
    # ------------------------------------------------------------------
    collections = ["watchlist", "portfolio", "ai_analyses", "chart_analyses"]
    for col_name in collections:
        col = db[col_name]
        result = await col.update_many(
            {"user_id": {"$exists": False}},
            {"$set": {"user_id": "legacy"}},
        )
        logger.info(
            "%-20s  matched=%d  modified=%d",
            col_name,
            result.matched_count,
            result.modified_count,
        )

    # ------------------------------------------------------------------
    # 2. Create indexes
    # ------------------------------------------------------------------
    # Watchlist: unique per user + symbol
    await db.watchlist.create_index(
        [("user_id", 1), ("symbol", 1)],
        unique=True,
        name="idx_user_symbol_unique",
    )
    logger.info("Created index idx_user_symbol_unique on watchlist")

    # Portfolio: query by user
    await db.portfolio.create_index(
        [("user_id", 1)],
        name="idx_user_id",
    )
    logger.info("Created index idx_user_id on portfolio")

    # Usage tracking: unique per user + date
    await db.usage_tracking.create_index(
        [("user_id", 1), ("date", 1)],
        unique=True,
        name="idx_user_date_unique",
    )
    logger.info("Created index idx_user_date_unique on usage_tracking")

    # Users: unique firebase uid
    await db.users.create_index(
        [("firebase_uid", 1)],
        unique=True,
        name="idx_firebase_uid_unique",
    )
    logger.info("Created index idx_firebase_uid_unique on users")

    client.close()
    logger.info("Migration 001 complete.")


if __name__ == "__main__":
    asyncio.run(migrate())
