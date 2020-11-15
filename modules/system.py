import asyncio
import subprocess
import time
import io
import traceback

from termcolor import colored

from telethon import events

from util import set_offline, batchify
from util.parse import cleartermcolor
from util.globals import PREFIX
from util.permission import is_allowed

# Repy to .asd with "a sunny day" (and calculate ping)
@events.register(events.NewMessage(pattern=r"{p}asd".format(p=PREFIX), outgoing=True))
async def ping(event):
    msg = event.raw_text
    before = time.time()
    await event.message.edit(msg + "\n` → ` a sunny day")
    after = time.time()
    latency = (after - before) * 1000
    await event.message.edit(msg + f"\n` → ` a sunny day `({latency:.0f}ms)`")
    await set_offline(event.client)


# Update userbot (git pull + restart)
@events.register(events.NewMessage(pattern=r"{p}update".format(p=PREFIX), outgoing=True))
async def update(event):
    msg = event.raw_text
    try:
        print(f" [ Updating bot ]")
        msg += "\n` → ` Updating"
        await event.message.edit(msg) 
        result = subprocess.run(["git", "pull"], capture_output=True, timeout=60)
        msg += " [OK]\n` → ` Bot will now restart"
        await event.message.edit(msg) 
        await event.client.disconnect()
    except Exception as e:
        msg += " [FAIL]\n`[!] → ` " + str(e)
        await event.message.edit(msg) 
    await set_offline(event.client)


# Get info about a message
@events.register(events.NewMessage(pattern=r"{p}info".format(p=PREFIX)))
async def info_cmd(event):
    if not event.out and not is_allowed(event.sender_id):
        return
    msg = event.message
    if event.is_reply:
        msg = await event.get_reply_message()
    print(f" [ getting info of msg ]")
    try:
        out = " → Data : \n" + msg.stringify()
        for m in batchify(out, 4080):
            await event.message.reply("```" + m + "```")
    except Exception as e:
        traceback.print_exc()
        await event.message.edit(event.raw_text + "\n`[!] → ` " + str(e))
    await set_offline(event.client)

# Run command
@events.register(events.NewMessage(pattern=r"{p}(?:run|r) (?P<cmd>.*)".format(p=PREFIX), outgoing=True))
async def runit(event):
    try:
        args = event.pattern_match.group("cmd")
        print(f" [ running command \"{args}\" ]")
        result = subprocess.run(args, shell=True, capture_output=True, timeout=60)
        output = f"$ {args}\n" + cleartermcolor(result.stdout.decode())
        if len(output) > 4080:
            with open("output", "w") as f:
                f.write(output) # lmaoooo there must be a better way
            out = io.BytesIO(output.encode("utf-8"))
            out.name = "output.txt"
            await event.message.reply("``` → Output too long to display```", file=out)
        else:
            await event.message.reply("```" + output + "```")
    except Exception as e:
        await event.message.reply("`[!] → ` " + str(e))
    await set_offline(event.client)

class SystemModules:
    def __init__(self, client, limit=False):
        self.helptext = "`━━┫ SYSTEM `\n"

        if not limit:
            client.add_event_handler(runit)
            self.helptext += "`→ .run <cmd> ` execute command on server\n"

        client.add_event_handler(ping)
        self.helptext += "`→ .asd ` a sunny day (+ get latency)\n"

        client.add_event_handler(info_cmd)
        self.helptext += "`→ .info ` print data of a message\n"

        client.add_event_handler(update)
        self.helptext += "`→ .update ` (git) pull changes and reboot bot\n"

        print(" [ Registered System Modules ]")
