from os import environ
from ui import *

TELEGRAM_TOKEN = environ["TELEGRAM_TOKEN"]  # Don't change this name!!!
DISCORD_TOKEN = environ["DISCORD_TOKEN"]  # Don't change this name!!!

# Localisation's settings
loc = Localisation()  # Don't change this name!!! Used for localisation in telegram bot
loc.start_message = 'Привет, %s!'  # %s - name of user who used /start command
loc.ping_succesful = 'Пинг девлога успешно отправлен!'
loc.ping_not_enabled = 'В этом боте выключена возможность пинговать роль девлога!'
loc.ping_youre_not_admin = 'Вы не администратор девлога!'
loc.footer_message_link_text = 'Сообщение'

# Auto reaction's settings
like_id: int | str = 1263694114088685669  # Type here unicode emoji if you want to use unicode emojies
dislike_id: int | str = 1262322230554136627  # Also for dislike_id

st = Settings(  # Also don't change this name! Used as global settings, but you can use it in handlers
    loc=loc,
    reactions=[like_id, dislike_id],
    guild_id=1141324357432528998,  # guild_id is required if one and more reactions are integers (custom emojies)
    presence_telegram_link='https://t.me/HoneyTeamC',
    enable_auto_publish=True,
    enable_message_footer=True
)

handlers: list[Handler] = [
    Handler(
        1142537004542857336,
        -1002174772013,
        st,
        [1146435141045076048]
    ),
]  # Don't change this name!!!
