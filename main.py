import asyncio
import logging
import sys
from io import BytesIO
from os import environ
from typing import Any

from aiogram import Bot, Dispatcher, html
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, ChatMemberOwner, ChatMemberAdministrator

from discord import Client, Intents, File

from json import loads


TELEGRAM_TOKEN = environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = -1002174772013
DISCORD_TOKEN = environ.get("DISCORD_TOKEN")
DEVLOG_CHANNEL_ID = 1259486814620614778
DEVLOG_ROLE_ID = 1146435141045076048

tbot = Bot(token=TELEGRAM_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
dbot = Client(intents=Intents.default())
dp = Dispatcher()

with open('members.json', encoding='utf-8') as f:
    members: dict[str, Any] = loads(f.read())


@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    await message.answer(f"Hello, {html.bold(message.from_user.full_name)}!")

@dp.message(Command('ping'))
async def command_ping_handler(message: Message):
    member = await tbot.get_chat_member(TELEGRAM_CHAT_ID, message.from_user.id)
    if isinstance(member, (ChatMemberOwner, ChatMemberAdministrator)) or member.is_chat_admin():
        ch = dbot.get_channel(DEVLOG_CHANNEL_ID)
        await ch.send(f'<@&{DEVLOG_ROLE_ID}>')

        await message.answer('Пинг девлога успешно отправлен!')
    else:
        await message.answer('Вы не администратор девлога!')

@dp.channel_post()
async def channel_post_handler(mes: Message):
    if mes.chat.id != TELEGRAM_CHAT_ID:
        return

    if mes.photo:
        file_id = mes.photo[-1].file_id
        file = await tbot.get_file(file_id)
        file_path = file.file_path
        file_binary: BytesIO = await tbot.download_file(file_path)
        dfile = File(fp=file_binary, filename='image.png')

        content = mes.caption
    else:
        dfile = None

        content = mes.md_text
        content = content.replace('\\', '')

    author = mes.author_signature
    author = members.get(author, author)

    if content:
        content += f'\n\nАвтор: {author}\n[Ссылка на сообщение в Telegram]({mes.get_url()})'

    if content or dfile:
        ch = dbot.get_channel(DEVLOG_CHANNEL_ID)
        await ch.send(content, file=dfile)

async def main() -> None:
    await asyncio.gather(dp.start_polling(tbot), dbot.start(DISCORD_TOKEN))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
