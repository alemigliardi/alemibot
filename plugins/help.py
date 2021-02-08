from typing import Callable

from bot import alemiBot

from pyrogram import filters

from util.permission import is_allowed
from util.message import edit_or_reply, is_me
from util.command import filterCommand

import logging
logger = logging.getLogger(__name__)

CATEGORIES = {}
ALIASES = {}

class HelpEntry:
    def __init__(self, title, shorttext, longtext, public=False, args=""):
        self.shorttext = shorttext
        self.longtext = longtext
        self.args = args
        if isinstance(title, list):
            self.title = title[0]
            for a in title[1:]:
                ALIASES[a] = title[0]
        else:
            self.title = title
        if public:
            self.shorttext += " *"

class HelpCategory: 
    def __init__(self, title):
        self.title = title.upper()
        self.HELP_ENTRIES = {}
        CATEGORIES[self.title] = self

    def register_entry(self, title, shorttext, longtext, public=False, args=""):
        h = HelpEntry(title, shorttext, longtext, public=public, args=args)
        self.HELP_ENTRIES[h.title] = h

    def add(self, title, shorttext, public=False, args=""):
        def decorator(func: Callable) -> Callable:
            longtext = func.__doc__
            self.register_entry(title, shorttext, longtext, public, args)
        return decorator

def get_all_short_text():
    out = ""
    for k in CATEGORIES:
        out += f"`━━┫ {k}`\n"
        cat = CATEGORIES[k]
        for cmd in cat.HELP_ENTRIES:
            entry = cat.HELP_ENTRIES[cmd]
            out += f"`→ .{entry.title} ` {entry.shorttext}\n"
    return out

# The help command
@alemiBot.on_message(is_allowed & filterCommand(["help", "h"], list(alemiBot.prefixes)))
async def help_cmd(client, message):
    logger.info("Help!")
    if "cmd" in message.command:
        arg = message.command["cmd"][0]
        for k in CATEGORIES:
            cat = CATEGORIES[k]
            if arg in cat.HELP_ENTRIES:
                e = cat.HELP_ENTRIES[arg]
                return await edit_or_reply(message, f"`→ {e.title} {e.args} `\n{e.longtext}", parse_mode="markdown")
            elif arg in ALIASES and ALIASES[arg] in cat.HELP_ENTRIES:
                e = cat.HELP_ENTRIES[ALIASES[arg]]
                return await edit_or_reply(message, f"`→ {e.title} {e.args} `\n{e.longtext}", parse_mode="markdown")
        return await edit_or_reply(message, f"`[!] → ` No command named `{arg}`")
    await edit_or_reply(message, f"`ᚨᛚᛖᛗᛁᛒᛟᛏ v{client.app_version}`\n" +
                        "`→ .help [cmd] ` get cmd help or cmd list\n" +
                        get_all_short_text() +
                        f"__Commands with * are available to trusted users__", parse_mode="markdown")
    await client.set_offline()
