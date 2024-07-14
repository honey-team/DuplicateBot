import json
import ujson

MessagesPath = "messages.json"


def mload() -> dict:
    with open(MessagesPath, "r", encoding="utf-8") as file:
        raw_json = file.read()
    return ujson.loads(raw_json)


def mwrite(new_messages: dict):
    with open(MessagesPath, "w", encoding="utf-8") as file:
        file.write(json.dumps(new_messages, indent=4))
