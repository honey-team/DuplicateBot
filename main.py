import asyncio
import logging
import sys
from os import getenv

from aiogram import Bot, Dispatcher, html
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message

from discord import Client, Intents

TELEGRAM_TOKEN = getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = int(getenv("TELEGRAM_CHAT_ID"))
DISCORD_TOKEN = getenv("DISCORD_TOKEN")
DEVLOG_GUILD_ID = int(getenv("DEVLOG_GUILD_ID"))
DEVLOG_CHANNEL_ID = int(getenv("DEVLOG_CHANNEL_ID"))

tbot = Bot(token=TELEGRAM_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dbot = Client(intents=Intents.default())
dp = Dispatcher()


@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    await message.answer(f"Hello, {html.bold(message.from_user.full_name)}!")

@dp.channel_post()
async def channel_post_handler(mes: Message):
    if mes.chat.id != TELEGRAM_CHAT_ID:
        return

    content = mes.text
    photos = mes.photo[-1]
    print(content)
    print(photos)

    ch = dbot.get_channel(DEVLOG_CHANNEL_ID)
    await ch.send(content)

async def main() -> None:
    await asyncio.gather(dp.start_polling(tbot), dbot.start(DISCORD_TOKEN))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
