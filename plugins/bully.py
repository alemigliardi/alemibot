import asyncio
import traceback
import logging
import re
import json
import time

from pyrogram import filters
from pyrogram.errors import BadRequest
from pyrogram.raw.functions.contacts import ResolveUsername

from bot import alemiBot

from util.permission import is_allowed, is_superuser
from util.message import is_me, edit_or_reply
from util.user import get_username
from util.command import filterCommand
from util.time import parse_timedelta

from plugins.help import HelpCategory

logger = logging.getLogger(__name__)

HELP = HelpCategory("BULLY")

censoring = {"MASS": [],
             "FREE": [],
             "SPEC" : {} }
try: # TODO THIS IS BAD MAYBE DON'T USE JSON FFS NICE CODE BRUUH
    with open("data/censoring.json") as f:
        buf = json.load(f)
        for k in buf["SPEC"]:
            censoring["SPEC"][int(k)] = buf["SPEC"][k]
        censoring["MASS"] = [ int(e) for e in buf["MASS"] ]
        censoring["FREE"] = [ int(u) for u in buf["FREE"] ]
except FileNotFoundError:
    with open("data/censoring.json", "w") as f:
        json.dump(censoring, f)
except:
    traceback.print_exc()
    # ignore

HELP.add_help(["censor", "c"], "immediately delete messages",
            "Start censoring someone in current chat. Use flag `-mass` to toggle mass censorship in current chat. " +
            "Users made immune (`free` cmd) will not be affected by mass censoring, use flag `-i` to revoke immunity from someone. "+
            "Use flag `-list` to get censored users in current chat. Messages from self will never be censored. " +
            "More than one target can be specified. To free someone from censorship, use `.free` command.",
            args="[-list] [-mass] [-i] <targets>")
@alemiBot.on_message(is_superuser & filterCommand(["censor", "c"], list(alemiBot.prefixes), flags=["-list", "-i", "-mass"]))
async def censor_cmd(client, message):
    global censoring
    args = message.command
    out = ""
    changed = False
    try:
        if "-list" in args["flags"]:
            if message.chat.id not in censoring["SPEC"]:
                out += "` → ` Nothing to display\n"
            else:
                usr_list = await client.get_users(censoring["SPEC"][message.chat.id])
                for u in usr_list:
                    out += "` → ` {get_username(u)}\n"
        elif "-mass" in args["flags"]:
            logger.info("Mass censoring chat")
            if message.chat.id not in censoring["MASS"]:
                censoring["MASS"].append(message.chat.id)
                out += "` → ` Mass censoring\n"
                changed = True
        elif "cmd" in args:
            logger.info("Censoring users")
            users_to_censor = []
            for target in args["cmd"]:
                usr = await client.get_users(target)
                if usr is None:
                    out += f"`[!] → ` {target} not found\n"
                else:
                    users_to_censor.append(usr)
            if "-i" in args["flags"]:
                for u in users_to_censor:
                    if u.id in censoring["FREE"]:
                        censoring["FREE"].remove(u.id)
                        out += f"` → ` {get_username(u)} is no longer immune\n"
                        changed = True
            else:
                for u in users_to_censor:
                    if message.chat.id not in censoring["SPEC"]:
                        censoring["SPEC"][message.chat.id] = []
                    censoring["SPEC"][message.chat.id].append(u.id)
                    out += f"` → ` Censoring {get_username(u)}\n"
                    changed = True
        if out != "":
            await edit_or_reply(message, out)
        else:
            await edit_or_reply(message, "` → ` Nothing to display")
    except Exception as e:
        traceback.print_exc()
        await edit_or_reply(message, out + "\n`[!] → ` " + str(e))
    if changed:
        with open("data/censoring.json", "w") as f:
            json.dump(censoring, f)
    await client.set_offline()

HELP.add_help(["free", "f", "stop"], "stop censoring someone",
            "Stop censoring someone in current chat. Use flag `-mass` to stop mass censorship current chat. " +
            "You can add `-i` to make target immune to mass censoring. More than one target can be specified (separate with spaces). " +
            "Add `-list` flag to list immune users (censor immunity is global but doesn't bypass specific censorship)",
            args="[-list] [-mass] [-i] <targets>")
@alemiBot.on_message(is_superuser & filterCommand(["free", "f", "stop"], list(alemiBot.prefixes), flags=["-list", "-i", "-mass"]))
async def free_cmd(client, message):
    global censoring
    args = message.command
    out = ""
    changed = False
    try:
        if "-list" in args["flags"]:
            if censoring["FREE"] == []:
                out += "` → ` Nothing to display\n"
            else:
                immune_users = await client.get_users(censoring["FREE"])
                for u in immune_users:
                    out += f"` → ` {get_username(u)}\n"
        elif "-mass" in args["flags"]:
            logger.info("Disabling mass censorship")
            censoring["MASS"].remove(message.chat.id)
            out += "` → ` Restored freedom of speech\n"
            changed = True
        elif "cmd" in args:
            logger.info("Freeing censored users")
            users_to_free = []
            for target in args["cmd"]:
                usr = await client.get_users(target)
                if usr is None:
                    out += f"`[!] → ` {target} not found\n"
                else:
                    users_to_free.append(usr)
            if "-i" in args["flags"]:
                for u in users_to_free:
                    censoring["FREE"].append(u.id)
                    out += f"` → ` {get_username(u)} is now immune\n"
                    changed = True
            else:
                for u in users_to_free:
                    if u.id in censoring["SPEC"][message.chat.id]:
                        censoring["SPEC"][message.chat.id].remove(u.id)
                        out += f"` → ` Freeing {get_username(u)}\n"
                        changed = True
        if out != "":
            await edit_or_reply(message, out)
        else:
            await edit_or_reply(message, "` → ` Nothing to display")
    except Exception as e:
        traceback.print_exc()
        await edit_or_reply(message, out + "\n`[!] → ` " + str(e))
    if changed:
        with open("data/censoring.json", "w") as f:
            json.dump(censoring, f)
    await client.set_offline()

@alemiBot.on_message(group=9)
async def bully(client, message):
    if message.edit_date is not None:
        return # pyrogram gets edit events as message events!
    if message.chat is None or is_me(message):
        return # can't censor messages outside of chats or from self
    if message.from_user is None:
        return # Don't censory anonymous msgs
    if message.chat.id in censoring["MASS"] \
    and message.from_user.id not in censoring["FREE"]:
        await message.delete()
        logger.info("Get bullied")
    else:
        if message.chat.id not in censoring["SPEC"] \
        or message.from_user.id not in censoring["SPEC"][message.chat.id]:
            return # Don't censor innocents!
        await message.delete()
        logger.info("Get bullied noob")
    await client.set_offline()

INTERRUPT_STEALER = False

async def attack_username(client, message, chat, username, interval, limit):
    global INTERRUPT_STEALER
    attempts = 0
    while not INTERRUPT_STEALER and time.time() < limit:
        try:
            attempts += 1
            await client.send(ResolveUsername(username=username)) # this should bypass cache and will get me floodwaited very reliably (:
            await message.edit(f"` → ` Attempting to steal --@{username}-- (**{attempts}** attempts)")
            await asyncio.sleep(interval)
        except BadRequest as e: # Username not occupied!
            await client.update_chat_username(chat.id, username)
            await message.edit(f"` → ` Successfully stolen --@{username}-- in **{attempts}** attempts")
            INTERRUPT_STEALER = False
            return
    INTERRUPT_STEALER = False
    await message.edit(f"`[!] → ` Failed to steal --@{username}-- (made **{attempts}** attempts)")
    await client.delete_channel(chat.id)

HELP.add_help(["username"], "tries to steal an username",
            "Will create an empty channel and then attempt to rename it to given username until it succeeds or " +
            "max time is reached. Attempts interval can be specified (`-i`), defaults to 30 seconds. By default " +
            "it will give up after 1h of attempts. Manually stop attempts with `-stop`. This is very aggressive and " +
            "will cause FloodWaits super easily if abused, be wary!", args="[-stop] [-i <n>] [-lim <time>] <username>")
@alemiBot.on_message(is_superuser & filterCommand("username", list(alemiBot.prefixes), options={
    "interval" : ["-i", "-int"],
    "limit" : ["-lim", "-limit"]
}, flags=["-stop"]))
async def steal_username_cmd(client, message):
    global INTERRUPT_STEALER
    if "-stop" in message.command["flags"]:
        INTERRUPT_STEALER = True
        return await edit_or_reply(message, "` → ` Interrupted")
    try:
        if "cmd" not in message.command:
            return await edit_or_reply(message, "`[!] → ` No username given")
        uname = message.command["cmd"][0]
        if uname.startswith("@"):
            uname = uname[1:]
        chan = await client.create_channel(f"getting {uname}", "This channel was automatically created to occupy an username")
        time_limit = time.time() + parse_timedelta(message.command["limit"] if "limit" in message.command else "1h").total_seconds()
        interval = float(message.command["interval"]) if "interval" in message.command else 30
        await edit_or_reply(message, "` → ` Created channel")
        asyncio.get_event_loop().create_task(attack_username(client, message, chan, uname, interval, time_limit))
    except Exception as e:
        traceback.print_exc()
        await edit_or_reply(message, "`[!] → ` " + str(e))
    await client.set_offline()


async def fake_typing(client, tgt, cycle_n, message):
    for _ in range(cycle_n):
        await client.send_chat_action(tgt, "typing")
        await asyncio.sleep(4) # Do steps of 4 to compensate eventual lag
    await edit_or_reply(message, "` → ` Done")

HELP.add_help(["typing"], "will show as typing on chat",
            "makes you show as typing on a certain chat. You can specify an username or a chat/user id. If none is " +
            "given, it will work in current chat. The amount of time can be given as a packed string like this : " +
            "`8y3d4h15m3s` (years, days, hours, minutes, seconds), any individual token can be given in any position " +
            "and all are optional, it can just be `30s` or `5m`. If you want to include spaces, wrap the 'time' string in `\"`.",
            args="[-t <target>] <time>]")
@alemiBot.on_message(is_superuser & filterCommand("typing", list(alemiBot.prefixes), options={
    "target" : ["-t"]
}))
async def typing_cmd(client, message):
    try:
        if "cmd" not in message.command:
            return await edit_or_reply(message, "`[!] → ` No amount of time given")
        number_of_cycles = int(parse_timedelta(message.command["cmd"][0]).total_seconds() / 4)# Do steps of 4 to compensate eventual lag
        tgt = message.chat.id
        if "target" in message.command:
            tgt = message.command["target"]
            if tgt.startswith("@"):
                tgt = (await client.get_chat(tgt)).id
            elif tgt.isnumeric():
                tgt = int(tgt)
        asyncio.get_event_loop().create_task(fake_typing(client, tgt, number_of_cycles, message))
        await edit_or_reply(message, "` → ` typing ...")
    except Exception as e:
        traceback.print_exc()
        await edit_or_reply(message, "`[!] → ` " + str(e))
    await client.set_offline()
    
HELP.add_help(["everyone"], "will mention everyone in the chat",
            "for every user in current chat, it will mention him. Message will be edited " +
            "to add further mentions to not spam chat. When done mentioning, message will become `@all`. " +
            "This is super lame, don't abuse.")
@alemiBot.on_message(is_superuser & filterCommand("everyone", list(alemiBot.prefixes)))
async def mass_mention(client, message):
    try:
        msg = await edit_or_reply(message, "` → ` Looking up members")
        n = 0
        text = ""
        async for member in message.chat.iter_members():
            if len(text + member.user.mention) >= 4096 or n >= 100: # I think you can mention max 100 ppl per message?
                await msg.edit(text)
                n = 0
                text = ""
            text += member.user.mention + " "
            n += 1
        if len(text) > 0:
            await msg.edit(text)
        await msg.edit("`@all`")
    except Exception as e:
        traceback.print_exc()
        await edit_or_reply(message, "`[!] → ` " + str(e))
    await client.set_offline()

INTERRUPT_SPAM = False

HELP.add_help(["spam", "flood"], "pretty self explainatory",
            "will send many (`-n`) messages in this chat at a specific (`-t`) interval. " +
            "If no number is given, will default to 3. If no interval is specified, " +
            "messages will be sent as soon as possible. You can reply to a message and " +
            "all spammed msgs will reply to that one too. If you add `-delme`, messages will be " +
            "immediately deleted. To stop an ongoing spam, you can do `.spam -cancel`.",
            args="[-cancel] [-n <n>] [-t <t>] <text>")
@alemiBot.on_message(is_superuser & filterCommand("spam", list(alemiBot.prefixes), options={
    "number" : ["-n"],
    "time" : ["-t"],
}, flags=["-cancel"]))
async def spam(client, message):
    global INTERRUPT_SPAM
    args = message.command
    if "-cancel" in args["flags"]:
        INTERRUPT_SPAM = True
        return
    wait = 0
    number = 3
    text = "."
    delme = False
    try:
        if "arg" in args:
            delme = args["arg"].endswith("-delme")
            text = args["arg"].replace("-delme", "") # in case
        if "time" in args:
            wait = float(args["time"])
        if "number" in args:
            number = int(args["number"])
        elif text.split(" ", 1)[0].isnumeric(): # this is to support how it worked originally
            number = int(text.split(" ", 1)[0])
            text = text.split(" ", 1)[1]
        logger.info(f"Spamming \"{text}\" for {number} times")
        extra = {}
        if message.reply_to_message is not None:
            extra["reply_to_message_id"] = message.reply_to_message.message_id
        for i in range(number):
            msg = await client.send_message(message.chat.id, text, **extra)
            await asyncio.sleep(wait)
            if delme:
                await msg.delete()
            if INTERRUPT_SPAM:
                INTERRUPT_SPAM = False
                await edit_or_reply(message, f"` → ` Canceled after {i + 1} events")
                break
    except Exception as e:
        traceback.print_exc()
        await edit_or_reply(message, "`[!] → ` " + str(e))
    await client.set_offline()

