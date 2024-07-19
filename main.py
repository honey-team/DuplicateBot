import asyncio
import logging
import sys
from typing import Any

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import ChatMemberOwner, ChatMemberAdministrator
from aiogram.types import Message as TMessage

from discord import Client, Intents, CustomActivity, Status
from discord import Message as DMessage

from json import loads

from settings import loc, handlers, TELEGRAM_TOKEN, DISCORD_TOKEN, st

tbot = Bot(token=TELEGRAM_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
dbot = Client(intents=Intents.default())
dp = Dispatcher()

with open('members.json', encoding='utf-8') as f:
    members: dict[str, Any] = loads(f.read())


@dp.message(CommandStart())
async def command_start_handler(message: TMessage):
    await message.answer(loc.start_message % message.from_user.full_name)

async def check_for_admin(telegram_channels: list[int], user_id: int) -> bool:
    for chat_id in telegram_channels:
        member = await tbot.get_chat_member(chat_id, user_id)
        if isinstance(member, (ChatMemberOwner, ChatMemberAdministrator)) or member.is_chat_admin():
            return True
    return False

@dp.message(Command('ping'))
async def command_ping_handler(message: TMessage):
    await message.answer('Выберите хэндлер (dev)')
    handler = handlers[0]

    is_admin = await check_for_admin(handler.telegram_channels, message.from_user.id)
    if is_admin:
        for i, ch_id in enumerate(handler.discord_channels):
            if handler.ping_role_ids[i]:
                ch = dbot.get_channel(ch_id)
                await ch.send(f'<@&{handler.ping_role_ids[i]}>')

                await message.answer(f'{ch_id}: {handler.settings.loc.ping_succesful}')
            else:
                await message.answer(f'{ch_id}: {handler.settings.loc.ping_not_enabled}')
    else:
        await message.answer(handler.settings.loc.ping_youre_not_admin)


@dp.channel_post()
async def channel_post_handler(message: TMessage):
    for h in handlers:
        await h.channel_post(message)

@dp.edited_channel_post()
async def edited_channel_post_handler(message: TMessage):
    for h in handlers:
        await h.edited_channel_post(message)

@dbot.event
async def on_ready() -> None:
    for h in handlers:
        h.init(dbot, tbot, members)

    if st.presence_telegram_link:
        activity = CustomActivity(name=st.presence_telegram_link)
        await dbot.change_presence(activity=activity, status=Status.dnd)

@dbot.event
async def on_message_delete(message: DMessage):
    for h in handlers:
        await h.message_delete(message)

async def main() -> None:
    await asyncio.gather(dp.start_polling(tbot), dbot.start(DISCORD_TOKEN))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
