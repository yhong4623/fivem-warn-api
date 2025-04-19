import asyncio
import logging
from api.api import start_api
from bot.bot import start_bot

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Discord Bot Token
BOT_TOKEN = "MTA5OTMzMTUyNDYxODM3NTI0OA.GhY9Be.pDATyf43F4EGM8Xyy8ZfOT34NgkgXD5pVWNd9U"

async def main():
    api_task = asyncio.create_task(start_api())
    bot_task = asyncio.create_task(start_bot(BOT_TOKEN))
    
    await asyncio.gather(api_task, bot_task)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("程式正在關閉...")
    except Exception as e:
        logger.error(f"啟動失敗: {str(e)}")