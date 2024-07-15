import asyncio
import logging
import sys
from io import BytesIO
from os import environ
from typing import Any

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import ChatMemberOwner, ChatMemberAdministrator
from aiogram.types import Message as TMessage

from discord import Client, Intents, File, CustomActivity, Status
from discord import Message as DMessage

from json import loads

from markdownify import markdownify

from bs4 import Tag

from jmessages import mload, mwrite


TELEGRAM_TOKEN = environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = -1002174772013

DISCORD_TOKEN = environ["DISCORD_TOKEN"]
DISCORD_DEVLOG_CHANNEL_ID = 1142537004542857336
DISCORD_DEVLOG_ROLE_ID = 1146435141045076048  # Set to `None` to disable /ping command

# Auto reactions settings
DISCORD_GUILD_ID: int | bool = 1141324357432528998  # if you want to use unicode emojis set to False
LIKE_EMOJI_ID: int | str = 1262322255342600265  # Type here unicode emoji if DISCORD_GUILD_ID = False (also for DISLIKE_EMOJI_ID)
DISLIKE_EMOJI_ID: int | str | bool = 1262322230554136627  # Set to False if you don't want to bot will send two reactions


# Settings
DISCORD_AUTO_PUBLISH = False
DISCORD_MESSAGE_FOOTER = True
DISCORD_PRESENCE_TELEGRAM_LINK = True
ENABLE_AUTO_REACTIONS_IN_DISCORD = True

# Messages
START_MESSAGE = 'Привет, %s!'  # %s - name of user who used /start command

PING_SUCCESFUL = 'Пинг девлога успешно отправлен!'
PING_NOT_ENABLED = 'В этом боте выключена возможность пинговать роль девлога!'
PING_YOURE_NOT_ADMIN = 'Вы не администратор девлога!'

DISCORD_CONTENT_TELEGRAM_MESSAGE_LINK_TEXT = 'Сообщения'

tbot = Bot(token=TELEGRAM_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
dbot = Client(intents=Intents.default())
dp = Dispatcher()

with open('members.json', encoding='utf-8') as f:
    members: dict[str, Any] = loads(f.read())

def md(html: str, **options):
    def callback(el):
        code = el.code
        res = str(code['class'][0]).replace('language-', '') if code.has_attr('class') else None
        return res
    return markdownify(html, code_language_callback=callback, **options)

@dp.message(CommandStart())
async def command_start_handler(message: TMessage):
    await message.answer(START_MESSAGE % message.from_user.full_name)

@dp.message(Command('ping'))
async def command_ping_handler(message: TMessage):
    member = await tbot.get_chat_member(TELEGRAM_CHAT_ID, message.from_user.id)
    if isinstance(member, (ChatMemberOwner, ChatMemberAdministrator)) or member.is_chat_admin():
        if DISCORD_DEVLOG_ROLE_ID:
            ch = dbot.get_channel(DISCORD_DEVLOG_CHANNEL_ID)
            await ch.send(f'<@&{DISCORD_DEVLOG_ROLE_ID}>')

            await message.answer(PING_SUCCESFUL)
        else:
            await message.answer(PING_NOT_ENABLED)
    else:
        await message.answer(PING_YOURE_NOT_ADMIN)

async def send_message_to_devlog_in_discord(content: str, dfile: File) -> DMessage:
    ch = dbot.get_channel(DISCORD_DEVLOG_CHANNEL_ID)
    sended_message = await ch.send(content, file=dfile)
    if DISCORD_AUTO_PUBLISH and ch.is_news():
        await sended_message.publish()
    if ENABLE_AUTO_REACTIONS_IN_DISCORD:
        if DISCORD_GUILD_ID is not False:
            guild = dbot.get_guild(DISCORD_GUILD_ID)
            like_emoji = guild.get_emoji(LIKE_EMOJI_ID)
            await sended_message.add_reaction(like_emoji)

            if DISLIKE_EMOJI_ID is not False:
                dislike_emoji = guild.get_emoji(DISLIKE_EMOJI_ID)
                await sended_message.add_reaction(dislike_emoji)
        else:
            await sended_message.add_reaction(LIKE_EMOJI_ID)

            if DISLIKE_EMOJI_ID is not False:
                await sended_message.add_reaction(DISLIKE_EMOJI_ID)

    return sended_message

async def edit_message_in_devlog_in_discord(telegram_message_id: int, new_content: str) -> DMessage:
    # Get discord message id
    m = mload()
    discord_id = m[str(telegram_message_id)]

    # Get message and edit it
    ch = dbot.get_channel(DISCORD_DEVLOG_CHANNEL_ID)
    message = await ch.fetch_message(discord_id)

    return await message.edit(content=new_content)

async def get_content_and_dfile(message: TMessage) -> tuple[str, File]:
    if message.photo:
        file_id = message.photo[-1].file_id
        file = await tbot.get_file(file_id)
        file_path = file.file_path
        file_binary: BytesIO = await tbot.download_file(file_path)
        dfile = File(fp=file_binary, filename='image.png')

        content = message.caption
    else:
        dfile = None

        html = message.html_text
        content = md(html)

        if content.endswith('\n'):
            content = content.removesuffix('\n')

    author = message.author_signature
    author = members.get(author, author)

    if DISCORD_MESSAGE_FOOTER and content:
        content += f'\n-# {author}・[{DISCORD_CONTENT_TELEGRAM_MESSAGE_LINK_TEXT}](<{message.get_url()}>)'
    return content, dfile

@dp.channel_post()
async def channel_post_handler(message: TMessage):
    if message.chat.id != TELEGRAM_CHAT_ID:
        return

    content, dfile = await get_content_and_dfile(message)

    if content or dfile:
        sended_message = await send_message_to_devlog_in_discord(content, dfile)

        m = mload()
        m[str(message.message_id)] = sended_message.id
        mwrite(m)

@dp.edited_channel_post()
async def edited_channel_post_handler(message: TMessage):
    if message.chat.id != TELEGRAM_CHAT_ID:
        return

    content, _ = await get_content_and_dfile(message)

    await edit_message_in_devlog_in_discord(message.message_id, content)

@dbot.event
async def on_ready() -> None:
    if DISCORD_PRESENCE_TELEGRAM_LINK:
        chat = await tbot.get_chat(TELEGRAM_CHAT_ID)

        if chat.username:
            url = f'https://t.me/{chat.username}'
        else:
            url = chat.invite_link

        activity = CustomActivity(name=url)
        await dbot.change_presence(activity=activity, status=Status.dnd)

@dbot.event
async def on_message_delete(message: DMessage):
    m = mload()

    try:
        i = list(m.values()).index(message.id)
    except ValueError:
        return  # Deleted message which there isn't in telegram channel
    tmessage_id = int(list(m.keys())[i])

    await tbot.delete_message(TELEGRAM_CHAT_ID, tmessage_id)

    del m[str(tmessage_id)]
    mwrite(m)

async def main() -> None:
    await asyncio.gather(dp.start_polling(tbot), dbot.start(DISCORD_TOKEN))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
