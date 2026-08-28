"""Robust Long-Polling Worker for SwaraSetu Telegram Bot.
Eliminates webhook/tunnel dependencies (localtunnel/ngrok) and runs 24/7 reliably.
"""

import asyncio
import logging
import os
import signal
import sys
import httpx

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.config import settings
from app.database import init_db
from app.routers.channels import _process_telegram_update

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("telegram_poller")


async def run_poller():
    token = settings.telegram_bot_token
    if not token:
        logger.error("❌ TELEGRAM_BOT_TOKEN is not set in environment or .env file.")
        sys.exit(1)

    # Initialize DB tables if not already created
    try:
        init_db()
    except Exception as e:
        logger.warning(f"Database init warning: {e}")

    logger.info("🤖 Starting SwaraSetu Telegram Bot in Long-Polling Mode...")

    # 1. Reset any existing webhook so Telegram routes updates to getUpdates
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            res = await client.post(
                f"https://api.telegram.org/bot{token}/deleteWebhook",
                json={"drop_pending_updates": False},
            )
            data = res.json()
            if data.get("ok"):
                logger.info("✅ Cleared any existing Telegram webhook.")
            else:
                logger.warning(f"Webhook delete response: {data}")
        except Exception as e:
            logger.warning(f"Could not reach Telegram API to delete webhook: {e}")

        # Get Bot info
        try:
            me_res = await client.get(f"https://api.telegram.org/bot{token}/getMe")
            me_data = me_res.json()
            if me_data.get("ok"):
                bot_user = me_data.get("result", {})
                logger.info(f"🚀 Bot connected: @{bot_user.get('username')} ({bot_user.get('first_name')})")
            else:
                logger.error(f"❌ Failed to authenticate bot: {me_data}")
                sys.exit(1)
        except Exception as e:
            logger.error(f"❌ Error fetching bot profile: {e}")
            sys.exit(1)

    offset = None
    logger.info("👂 Polling for incoming Telegram messages & voice notes (Press Ctrl+C to stop)...")

    limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
    timeout = httpx.Timeout(connect=10.0, read=40.0, write=10.0, pool=10.0)

    async with httpx.AsyncClient(limits=limits, timeout=timeout) as client:
        while True:
            try:
                params = {"timeout": 25}
                if offset is not None:
                    params["offset"] = offset

                response = await client.get(
                    f"https://api.telegram.org/bot{token}/getUpdates",
                    params=params,
                )

                if response.status_code != 200:
                    logger.warning(f"getUpdates returned HTTP {response.status_code}: {response.text}")
                    await asyncio.sleep(2)
                    continue

                data = response.json()
                if not data.get("ok"):
                    logger.error(f"Telegram API error: {data}")
                    await asyncio.sleep(2)
                    continue

                updates = data.get("result", [])
                for update in updates:
                    update_id = update.get("update_id")
                    if update_id is not None:
                        offset = update_id + 1

                    # Process in background task so poller never blocks
                    asyncio.create_task(_process_update_safe(update))

            except httpx.ReadTimeout:
                # Normal for long-polling when no messages arrive
                continue
            except httpx.ConnectError as e:
                logger.warning(f"Network connection error, retrying in 3s: {e}")
                await asyncio.sleep(3)
            except Exception as e:
                logger.error(f"Unexpected error in polling loop: {e}", exc_info=True)
                await asyncio.sleep(2)


async def _process_update_safe(update: dict):
    try:
        await _process_telegram_update(update)
    except Exception as e:
        logger.error(f"Error processing update {update.get('update_id')}: {e}", exc_info=True)


if __name__ == "__main__":
    try:
        asyncio.run(run_poller())
    except (KeyboardInterrupt, SystemExit):
        logger.info("🛑 SwaraSetu Telegram Bot stopped.")
