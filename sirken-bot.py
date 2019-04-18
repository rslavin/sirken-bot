import config
import logging
import logging.config
import asyncio
import discord
from discord.ext import commands
import timehandler as timeh
import messagecomposer
import inputhandler
import outputhandler
import npc
import watch
import helper


################################################
# BACKGROUND MINUTE DIGEST : Tic every minute  #
################################################
async def minute_digest():
    tic = 60
    while True:
        await asyncio.sleep(tic)
        now = timeh.now()
        for merb in merbs.merbs:
            # update merb eta
            merb.eta = merb.get_eta()
            minutes_diff = (merb.eta - now).total_seconds() // 60.0

            for user in watch.users:
                destination = discord.utils.get(client.get_all_members(), id=user)
                if watch.check(user, merb.name, minutes_diff) and not merb.in_window():
                    await destination.send(messagecomposer.prettify(merb.print_short_info(), "CSS"))
                    logging.debug("ALARM TO %s: %s | ETA: %s | DIFF MINUTES: %s" %
                                  (user, merb.name, merb.eta, minutes_diff))


################################################
# BACKGROUND DAILY DIGEST: Tic every hour      #
################################################
async def daily_digest():
    # tic every hour
    tic = 60*60
    while True:
        now = timeh.now()
        # tic only one time per day
        if int(now.hour) == config.DAILY_HOUR:
            print_list = merbs.get_all("CET", "countdown", limit_hours=24)
            if print_list:
                counter = len(print_list)
                print_list = messagecomposer.output_list(print_list)
                pre_message = "Good morning nerds! %d merbs are expected today, %s.\n\n" %\
                              (counter, timeh.now().strftime("%d %b %Y"))
                post_message = "\n{Type !hi to start to interact with me}\n"
                raw_output = out_h.process(pre_message + print_list + post_message)
                for message in raw_output:
                    await send_spam(messagecomposer.prettify(message, "CSS"), config.BROADCAST_DAILY_DIGEST_CHANNELS)

        await asyncio.sleep(tic)


########
# MAIN #
########
if __name__ == "__main__":

    logging.config.dictConfig({
        'version': 1,
        'disable_existing_loggers': False,
    })
    logging.basicConfig(filename=config.LOG_FILE,
                        level=logging.INFO,
                        format='%(asctime)s - %(message)s',
                        datefmt='%d-%b-%y %H:%M:%S')
    # Initialize Merbs List
    merbs = npc.MerbList(config.FILE_ENTITIES, config.FILE_TIMERS, config.DATE_FORMAT, config.DATE_FORMAT_PRINT)
    merbs.order()
    # Load Helper
    helper = helper.Helper(config.HELP_FILE)
    # Load Watcher
    watch = watch.Watch(config.FILE_WATCH)
    # Initialize Output Handler
    out_h = outputhandler.OutputHandler(config.MAX_MESSAGE_LENGTH)
    # Initialize Input Handler
    in_h = inputhandler.InputHandler(merbs, helper, out_h, watch)
    # Bot Stuff
    client = commands.Bot(command_prefix="!")  # Initialise client bot

    @client.event
    async def on_ready():
        print("Sirken Bot is online and connected to Discord")
        logging.info("Sirken Bot Connected to Discord")
        # Create Background Loops

    @client.event
    async def on_message(message):
        # Skip self messages
        if message.author == client.user:
            return
        # Process messages
        raw_output = in_h.process(message.author, message.channel, message.content)

        if raw_output:
            # split the output if too long
            output_message = out_h.process(raw_output["content"])
            for message in output_message:
                await raw_output["destination"].send(messagecomposer.prettify(message, "CSS"))
                if raw_output['broadcast']:
                    await send_spam(messagecomposer.prettify(message, "CSS"), raw_output['broadcast'])

            # send PM Alerts
            if 'merb_alert' in raw_output:
                await send_pop_alerts(raw_output['merb_alert'], raw_output["content"])
            # send EQ Alerts
            if 'earthquake' in raw_output:
                await send_eq_alert(raw_output['earthquake'])

    # Send Spam to Broadcast Channel
    @client.event
    async def send_spam(message, channels):
        for channel in channels:
            destination = client.get_channel(channel)
            await destination.send(message)

    # Send Earthquake Messages
    @client.event
    async def send_eq_alert(author):
        # for user in watch.users:
        #   destination = discord.utils.get(client.get_all_members(), id=user)
        #    await client.send_message(destination,
        #                              messagecomposer.prettify("%s BROADCAST: Minions gather, their forms appearing"
        #                                                       " as time and space coalesce." % author, "CSS"))
        #    logging.info("EARTHQUAKE!")
        pass

    # Send Pop Message
    @client.event
    async def send_pop_alerts(merb: npc.Merb, message):
        # for user in watch.users:
        #    destination = discord.utils.get(client.get_all_members(), id=user)
        #    if merb.name in watch.users[user]:
        #        await client.send_message(destination, messagecomposer.prettify(message, "CSS"))
        #        logging.info("SEND ALERT. %s pop TO: %s" % (merb.name, user))
        pass

    # Run the Bot
    client.loop.create_task(minute_digest())
    client.loop.create_task(daily_digest())
    client.run(config.DISCORD_TOKEN)
