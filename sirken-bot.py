import errno
import os
import config
import auth
import logging
import logging.config
import asyncio
import discord
from discord.ext import commands
import timehandler as timeh
import messagecomposer
from sirken_commands import SirkenCommands
import npc
import watch
import helper
from timeit import default_timer as timer


################################################
# BACKGROUND MINUTE DIGEST : Tic every minute  #
################################################
async def minute_digest():
    tic = 60
    while True:
        await asyncio.sleep(tic)
        now = timeh.now()

        for mob in mobs.mobs:
            # update mob eta
            mob.eta = mob.get_eta()
            minutes_diff = (mob.eta - now).total_seconds() // 60.0

            for user in watch.users:
                destination = discord.utils.get(client.get_all_members(), id=user)
                if watch.check(user, mob.name, minutes_diff) and not mob.in_window():
                    await destination.send(messagecomposer.prettify(mob.print_short_info(), "CSS")[0])
                    logging.debug("ALARM TO %s: %s | ETA: %s | DIFF MINUTES: %s" %
                                  (user, mob.name, mob.eta, minutes_diff))


################################################
# BACKGROUND DAILY DIGEST: Tic every hour      #
################################################
async def hour_digest():
    # tic every hour
    tic = 60 * 60
    while True:
        await asyncio.sleep(tic)

        # Reload Roles and Users
        authenticator.reload_discord_roles()
        logger_sirken.info("Roles Reloaded")
        authenticator.reload_discord_users()
        logger_sirken.info("Users Reloaded")

        # tic only one time per day
        # now = timeh.now()
        # if int(now.hour) == config.DAILY_HOUR:
        #    mobs_print_list = mobs.get_all("EST", "countdown", limit_hours=24)
        #    if mobs_print_list:
        #        counter = len(mobs_print_list)
        #        output_content = messagecomposer.output_list(mobs_print_list)
        #        pre_content = "Good morning nerds! %d mobs are expected today, %s.\n\n" %\
        #                      (counter, timeh.now().strftime("%d %b %Y"))
        #        post_content = "\n{Type !hi to start to interact with me}\n"
        #        raw_output = out_h.process(pre_content + output_content + post_content)
        #        for message in raw_output:
        #            await send_spam(messagecomposer.prettify(message, "CSS"), config.BROADCAST_DAILY_DIGEST_CHANNELS)


def setup_logger(name, log_file, level=logging.INFO):
    formatter = logging.Formatter('[%(asctime)s] - %(message)s')
    try:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
    except OSError as e:
        if e.errno == errno.EEXIST and os.path.isdir(os.path.dirname(log_file)):
            pass
        else:
            print("[ERROR] Unable to create log file!")
            print(e)
            exit(-1)
    handler = logging.FileHandler(log_file)
    handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)

    return logger


########
# MAIN #
########
if __name__ == "__main__":

    # Generic Sirken-Bot file logger
    logger_sirken = setup_logger('Sirken-Bot', config.LOG_FILE)

    # Input file logger
    logger_input = setup_logger('Input', config.LOG_INPUT_FILE)

    logging.config.dictConfig({
        'version': 1,
        'disable_existing_loggers': False,
    })

    # Initialize the Bot
    t_start = timer()
    intents = discord.Intents.default()
    intents.members = True

    client = commands.Bot(command_prefix="!", intents=intents)  # Initialise client bot
    t_end = timer()
    logger_sirken.info("Loading Bot. Done in (%s)" % (round(t_end - t_start, 5)))

    # Initialize Auth
    authenticator = auth.Auth(client)

    # Initialize Mobs List
    t_start = timer()

    mobs = npc.MobList(config.FILE_ENTITIES,
                       config.FILE_TIMERS,
                       config.FILE_TARGETS,
                       config.DATE_FORMAT,
                       config.DATE_FORMAT_PRINT)
    mobs.order()
    t_end = timer()
    logger_sirken.info("Loading mobs. Done in %s seconds" % (round(t_end - t_start, 5)))

    # Load Helper
    t_start = timer()
    helper = helper.Helper(config.HELP_DIR)
    t_end = timer()
    logger_sirken.info("Loading Help. Done in %s seconds" % (round(t_end - t_start, 5)))

    # Load Watcher
    t_start = timer()
    watch = watch.Watch(config.FILE_WATCH)
    t_end = timer()
    logger_sirken.info("Loading Watcher. Done in %s seconds" % (round(t_end - t_start, 5)))

    # Initialize Sirken Commands
    sirken_cmds = SirkenCommands(client, authenticator, mobs, helper, watch)
    t_end = timer()
    logger_sirken.info("Loading IO. Done in %s seconds" % (round(t_end - t_start, 5)))


    @client.event
    async def on_ready():
        logger_sirken.info("Sirken Bot is online and connected to Discord")
        # Load Discord Roles
        t_start = timer()
        authenticator.load_discord_roles()
        t_end = timer()
        logger_sirken.info("Loading Discord Roles. Done in %s seconds" % (round(t_end - t_start, 5)))
        t_start = timer()
        authenticator.load_discord_users()
        t_end = timer()
        logger_sirken.info("Loading Discord Users. Done in %s seconds" % (round(t_end - t_start, 5)))


    @client.event
    async def on_message(message):
        # Skip self messages
        if message.author == client.user:
            return

        messages_output = sirken_cmds.process(message.author, message.channel, message.content)
        if not messages_output:
            return

        for message in messages_output["content"]:
            await messages_output["destination"].send(message)
            if messages_output['broadcast']:
                await send_spam(message, messages_output['broadcast'])

            if 'action' in messages_output:
                if messages_output["action"] == 'leave_all_guilds':
                    await leave_guild(authenticator.discord_guilds)

            # send PM Alerts
            if 'mob_alert' in messages_output:
                await send_pop_alerts(messages_output['mob_alert'], messages_output["content"])
            # send EQ Alerts
            if 'earthquake' in messages_output:
                await send_eq_alert(messages_output['earthquake'])


    # Leave Guild
    @client.event
    async def leave_guild(guilds):
        for guild in guilds:
            logger_sirken.info("Leaving %s server" % guild.name)
            await guild.leave()


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
    async def send_pop_alerts(mob: npc.Mob, message):
        # for user in watch.users:
        #    destination = discord.utils.get(client.get_all_members(), id=user)
        #    if mob.name in watch.users[user]:
        #        await client.send_message(destination, messagecomposer.prettify(message, "CSS"))
        #        logging.info("SEND ALERT. %s pop TO: %s" % (mob.name, user))
        pass


    # Run the Bot
    client.loop.create_task(minute_digest())
    client.loop.create_task(hour_digest())
    client.run(config.DISCORD_TOKEN)
