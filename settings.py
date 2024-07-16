from os import environ

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

DISCORD_CONTENT_TELEGRAM_MESSAGE_LINK_TEXT = 'Сообщение'
