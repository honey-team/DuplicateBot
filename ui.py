from io import BytesIO

from aiogram.exceptions import TelegramBadRequest
from markdownify import markdownify

from aiogram.types import Message as TMessage
from aiogram import Bot as TBot

from discord import NotFound
from discord import Client as DClient
from discord import File as DFile
from discord import Message as DMessage

from jmessages import mload, mwrite

__all__ = (
    'Localisation',
    'Settings',
    'Handler'
)

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

    if res.endswith('\n'):
        return res.removesuffix('\n')
    return res

class Localisation:
    def __init__(self):
        self.start_message: str = 'Hello, %s!'
        self.ping_select_handler = 'Select handler (click on button).'
        self.ping_succesful: str = '%d: The devlog ping has been successfully sent!'
        self.ping_not_enabled: str = '%d: The ability to ping the role of a devlog is disabled in this bot!'
        self.ping_youre_not_admin: str = 'You are not a devlog administrator!'
        self.footer_message_link_text: str = 'Message'

class Settings:
    def __init__(
            self, *,
            loc: Localisation = Localisation(),
            reactions: list[int | str] = None,
            guild_id: int | None = None,
            tgc_link_id: str | None = None,
            # booleans
            enable_auto_publish: bool = True,
            enable_message_footer: bool = False,
            enable_post_author: bool = True,
    ):
        self.loc = loc
        self.reactions = reactions if reactions else []
        self.guild_id = guild_id
        self.presence_telegram_link = f'https://t.me/{tgc_link_id}'

        self.auto_publish = enable_auto_publish
        self.message_footer = enable_message_footer
        self.post_author = enable_post_author

class Handler:
    def __init__(
            self,
            discord_channels: list[int] | int,
            telegram_channels: list[int] | int,
            settings: Settings = Settings(),
            ping_role_ids: list[int] | None = None
    ):
        if isinstance(discord_channels, int):
            discord_channels = [discord_channels]
        if isinstance(telegram_channels, int):
            telegram_channels = [telegram_channels]

        self.discord_channels = discord_channels
        self.telegram_channels = telegram_channels
        self.settings = settings
        self.ping_role_ids = ping_role_ids if ping_role_ids else []

        self.dbot: DClient | None = None
        self.tbot: TBot | None = None
        self.members = {}

        self.__current_message: TMessage | None = None

    async def __send_reactions_to_message(self, sent_message: DMessage):
        try:
            if self.settings.reactions:
                for reaction_id in self.settings.reactions:
                    if isinstance(reaction_id, int):
                        guild = self.dbot.get_guild(self.settings.guild_id)
                        emoji = guild.get_emoji(reaction_id)
                        await sent_message.add_reaction(emoji)
                    else:
                        await sent_message.add_reaction(reaction_id)
        except NotFound:
            return

    async def __send_message_to_devlog_in_discord(self, content: str, dfile: DFile) -> list[DMessage]:
        sent_messages = []
        for ch_id in self.discord_channels:
            ch = self.dbot.get_channel(ch_id)

            sent_message = await ch.send(content, file=dfile)
            if self.settings.auto_publish and ch.is_news():
                await sent_message.publish()
            await self.__send_reactions_to_message(sent_message)
            sent_messages.append(sent_message)
        return sent_messages

    async def __reply_to_message_in_devlog_in_discord(
            self, reply_telegram_message_id: int, content: str, dfile: DFile) -> list[DMessage]:
        m = mload()
        messages_ids_to_reply = m[str(self.__current_message.chat.id)][str(reply_telegram_message_id)]

        sent_messages = []
        for i, ch_id in enumerate(self.discord_channels):
            ch = self.dbot.get_channel(ch_id)
            message_to_reply = await ch.fetch_message(messages_ids_to_reply[i])

            sent_message = await message_to_reply.reply(content, file=dfile)
            await self.__send_reactions_to_message(sent_message)
            sent_messages.append(sent_message)
        return sent_messages

    async def __edit_message_in_devlog_in_discord(self, telegram_message_id: int, new_content: str) -> list[DMessage]:
        m = mload()
        messages_ids = m[str(self.__current_message.chat.id)][str(telegram_message_id)]

        sent_messages = []
        for i, ch_id in enumerate(self.discord_channels):
            ch = self.dbot.get_channel(ch_id)
            message = await ch.fetch_message(messages_ids[i])
            sent_message = await message.edit(content=new_content)
            sent_messages.append(sent_message)
        return sent_messages

    async def __get_dfile_from_file_id(self, file_id: str, spoiler: bool = False) -> DFile:
        file = await self.tbot.get_file(file_id)
        file_path = file.file_path
        extension = file_path.split('.')[-1]
        file_binary: BytesIO = await self.tbot.download_file(file_path)

        return DFile(fp=file_binary, filename=f'file.{extension}', spoiler=spoiler)

    async def __get_content_and_dfile(self, message: TMessage) -> tuple[str, DFile]:
        spoiler = False
        if message.photo:
            file_id = message.photo[-1].file_id
            content = message.caption

            if message.has_media_spoiler:
                spoiler = True
        elif message.sticker:
            file_id = message.sticker.file_id
            content = None
        elif message.document:
            file_id = message.document.file_id
            content = message.caption
        else:
            file_id = None
            content = md(message.html_text)

        dfile = await self.__get_dfile_from_file_id(file_id, spoiler) if file_id else None

        if self.settings.message_footer and content:
            content += '\n-# '

            if self.settings.post_author:
                username = message.from_user.username
                author = self.members.get(username, message.author_signature)

                content += f'[{author}](<https://t.me/{username}>)・'
            content += f'[{self.settings.loc.footer_message_link_text}](<{message.get_url()}>)'
        return content, dfile

    def init(self, dbot: DClient, tbot: TBot, members: dict[str, str]) -> None:
        self.dbot = dbot
        self.tbot = tbot
        self.members = members

    async def channel_post(self, message: TMessage) -> None:
        self.__current_message = message

        if message.chat.id not in self.telegram_channels:
            print(f'Message not in handler channels: {message.chat.id}')
            return
        print(f'Message in handler channels: {message.chat.id}')

        content, dfile = await self.__get_content_and_dfile(message)

        if content or dfile:
            if message.reply_to_message:  # Is reply
                reply_to_id = message.reply_to_message.message_id

                sent_messages = await self.__reply_to_message_in_devlog_in_discord(reply_to_id, content, dfile)
            else:
                sent_messages = await self.__send_message_to_devlog_in_discord(content, dfile)

            m = mload()
            if not m.get(str(message.chat.id)):
                m[str(message.chat.id)] = {}
            m[str(message.chat.id)][str(message.message_id)] = [i.id for i in sent_messages]
            mwrite(m)

    async def edited_channel_post(self, message: TMessage) -> None:
        self.__current_message = message

        if message.chat.id not in self.telegram_channels:
            print(f'Message not in handler channels: {message.chat.id}')
            return
        print(f'Message in handler channels: {message.chat.id}')

        content, _ = await self.__get_content_and_dfile(message)

        await self.__edit_message_in_devlog_in_discord(message.message_id, content)

    async def message_delete(self, message: DMessage) -> None:
        if message.channel.id not in self.discord_channels:
            return

        m = mload()

        for chat_id in self.telegram_channels:
            try:
                i = list(m[str(chat_id)].values()).index(message.id)
            except ValueError:
                continue  # wrong telegram channel or message not in messages.json

            tmessage_id = int(list(m[str(chat_id)].keys())[i])

            try:
                await self.tbot.delete_message(chat_id, tmessage_id)
            except TelegramBadRequest:  # Deleted message which there isn't in telegram channel, but in messages.json
                pass

            del m[str(chat_id)][str(tmessage_id)]
            mwrite(m)
