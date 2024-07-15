import asyncio
import logging
import sys
from io import BytesIO
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

from jmessages import mload, mwrite
from settings import *

tbot = Bot(token=TELEGRAM_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
dbot = Client(intents=Intents.default())
dp = Dispatcher()

with open('members.json', encoding='utf-8') as f:
    members: dict[str, Any] = loads(f.read())

def md(html: str) -> str:
    def callback(el):
        code = el.code
        res = str(code['class'][0]).replace('language-', '') if code.has_attr('class') else None
        return res

    res = markdownify(html, code_language_callback=callback)

    replaces = {
        '\\-': '-',
        '/-': '-'
    }

    for k, v in replaces.items():
        res = res.replace(k, v)

    return res

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

async def send_reactions_to_message(sent_message: DMessage):
    if ENABLE_AUTO_REACTIONS_IN_DISCORD:
        if DISCORD_GUILD_ID is not False:
            guild = dbot.get_guild(DISCORD_GUILD_ID)
            like_emoji = guild.get_emoji(LIKE_EMOJI_ID)
            await sent_message.add_reaction(like_emoji)

            if DISLIKE_EMOJI_ID is not False:
                dislike_emoji = guild.get_emoji(DISLIKE_EMOJI_ID)
                await sent_message.add_reaction(dislike_emoji)
        else:
            await sent_message.add_reaction(LIKE_EMOJI_ID)

            if DISLIKE_EMOJI_ID is not False:
                await sent_message.add_reaction(DISLIKE_EMOJI_ID)

async def send_message_to_devlog_in_discord(content: str, dfile: File) -> DMessage:
    ch = dbot.get_channel(DISCORD_DEVLOG_CHANNEL_ID)

    sent_message = await ch.send(content, file=dfile)
    if DISCORD_AUTO_PUBLISH and ch.is_news():
        await sent_message.publish()
    await send_reactions_to_message(sent_message)

    return sent_message

async def reply_to_message_in_devlog_in_discord(reply_telegram_message_id: int, content: str, dfile: File) -> DMessage:
    # Get discord message id to reply
    m = mload()
    discord_message_id_to_reply = m[str(reply_telegram_message_id)]

    # Get and reply to this message
    ch = dbot.get_channel(DISCORD_DEVLOG_CHANNEL_ID)
    discord_message_to_reply = await ch.fetch_message(discord_message_id_to_reply)

    sent_message = await discord_message_to_reply.reply(content, file=dfile)
    await send_reactions_to_message(sent_message)

    return sent_message

async def edit_message_in_devlog_in_discord(telegram_message_id: int, new_content: str) -> DMessage:
    # Get discord message id
    m = mload()
    discord_message_id = m[str(telegram_message_id)]

    # Get message and edit it
    ch = dbot.get_channel(DISCORD_DEVLOG_CHANNEL_ID)
    message = await ch.fetch_message(discord_message_id)

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
        if message.reply_to_message:  # Is reply
            reply_to_id = message.reply_to_message.message_id

            sent_message = await reply_to_message_in_devlog_in_discord(reply_to_id, content, dfile)
        else:
            sent_message = await send_message_to_devlog_in_discord(content, dfile)

        m = mload()
        m[str(message.message_id)] = sent_message.id
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
