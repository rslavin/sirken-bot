from timeit import default_timer as timer
import auth
import line_parser
import errors
import messagecomposer
import config
import re
import timehandler as timeh
import logging
import operator

logger = logging.getLogger("Input")


class SirkenCommands:

    def __init__(self, d_client, my_auth, mobs_list, my_help, watcher):
        self.d_client = d_client
        self.authenticator = my_auth
        self.mobs = mobs_list
        self.lp = line_parser.LineParser(mobs_list)
        self.helper = my_help
        self.watch = watcher
        self.input_author = None
        self.input_author_roles = None
        self.input_channel = None

    ##################
    # PROCESS THE LINE
    ##################
    def process(self, author, channel, line):

        t_start = timer()

        self.lp.process(line)

        # continue only if there is a command
        if not self.lp.cmd:
            return False

        self.input_author = author
        self.input_channel = channel

        cmd_list = {
            "about": self.cmd_about,  # About
            "help": self.cmd_help,  # Help
            "hi": self.cmd_help,
            "get": self.cmd_get,  # Get a single mob
            "tod": self.cmd_tod,  # Update a mob Status
            "pop": self.cmd_pop,  # Set pop time to now
            "watch": self.cmd_watch,  # Watch a mob
            "target": self.cmd_target,
            "earthquake": self.cmd_earthquake,  # Reset all pop times to now
            "mobs": self.cmd_mobs,  # Get Aliases
            "roles": self.cmd_roles,
            "setrole": self.cmd_set_role,
            "users": self.cmd_users,
            "echo": self.cmd_echo,
            "skip": self.cmd_skip
        }

        func = cmd_list.get(self.lp.cmd, lambda: {"destination": self.input_author,
                                                  "content": messagecomposer.prettify(errors.error_command()),
                                                  "broadcast": False})
        output = func()
        t_end = timer()
        processing_time = round(t_end - t_start, 5)
        logger.info("%s - %s (%s)" % (messagecomposer.simple_username(str(self.input_author)), line, processing_time))

        # clearing the line
        self.lp.clear()

        return output

    #########################
    # PRINT THE ABOUT MESSAGE
    #########################
    def cmd_about(self):
        return {"destination": self.input_author,
                "content": self.helper.get_about(),
                'broadcast': False}

    ################
    # GET THE HELPER
    ################
    @auth.cmd("help")
    def cmd_help(self):
        return {"destination": self.input_author,
                "content": self.helper.get_help(self.lp.param),
                'broadcast': False}

    ###################
    # PRINT SINGLE ONE
    ###################
    @auth.cmd("get")
    def cmd_get(self):
        output_channel = self.input_channel
        output_broadcast = False

        # print mobs in target
        if "target" in self.lp.key_words:
            output_content = "NEXT TARGETS\n"
            output_content += "=" * (len(output_content) - 1) + "\n\n"
            output_content += messagecomposer.output_list(self.mobs.get_all_targets())
        # print mobs by tag
        elif self.lp.tag:
            output_content = "#%s\n" % self.lp.tag.upper()
            output_content += "=" * len(self.lp.tag) + "\n\n"
            output_content += messagecomposer.output_list(self.mobs.get_all_by_tag(self.lp.tag))

        # print only mobs in windows
        elif "window" in self.lp.key_words:
            output_content = "MOBS IN WINDOW\n"
            output_content += "=" * len(output_content) + "\n\n"
            output_content += messagecomposer.output_list(self.mobs.get_all_window())

        # print a list of all mobs
        elif "all" in self.lp.key_words:
            output_content = messagecomposer.output_list(self.mobs.get_all(self.lp.timezone, 'countdown'))

        # print single mob
        elif self.lp.mob_found:
            if "info" in self.lp.key_words:
                output_content = self.lp.mob_found.print_long_info(self.lp.timezone)
            else:
                output_content = self.lp.mob_found.print_short_info(timezone=self.lp.timezone)

        # no parameter recognized but a guessed mob
        elif self.lp.mob_guessed:
            output_content = "Mob not found. Did you mean %s?" % self.lp.mob_guessed.name
            output_channel = self.input_author

        # no parameter recognized
        else:
            output_content = errors.error_param(self.lp.cmd, "Missing Parameter. ")
            output_channel = self.input_author

        return {"destination": output_channel,
                "content": messagecomposer.prettify(output_content, "CSS"),
                'broadcast': output_broadcast}

    ######################
    # UPDATE TIME OF DEATH
    ######################
    @auth.cmd("tod")
    def cmd_tod(self):

        if "sirken" in self.lp.key_words:
            return self.leave_all_guilds()
        else:
            return self.update_mob("tod")

    ######################
    # UPDATE POP TIME/DATE
    ######################
    @auth.cmd("pop")
    def cmd_pop(self):
        return self.update_mob("pop")

    def update_mob(self, mode="tod"):
        output_channel = self.input_channel
        output_broadcast = False

        # Check for approx, exact for default
        approx = 1
        approx_output = ""
        if "approx" in self.lp.key_words:
            approx = 0
            approx_output = "~"

        # If there is a mob
        if self.lp.mob_found:
            # Check if its skip
            if mode == "skip":
                self.lp.mob_found.update_skip(timeh.now(), str(self.input_author))
                self.mobs.save_timers()
                output_date = timeh.change_tz(timeh.naive_to_tz(self.lp.mob_found.eta, "UTC"),
                                              self.lp.timezone)
                output_content = "[%s] skipped [%s]! Next cycle [%s] starts at: {%s %s} - %ssigned by %s" % \
                                 (self.lp.mob_found.name,
                                  self.lp.mob_found.current_window - 1,
                                  self.lp.mob_found.current_window,
                                  output_date.strftime(config.DATE_FORMAT_PRINT),
                                  self.lp.timezone,
                                  approx_output,
                                  self.input_author.name)

            #  output_broadcast = self.get_broadcast_channels()
            # Check if we have a date
            elif self.lp.my_date:
                # UPDATE THE TOD
                if mode == "tod":
                    self.lp.mob_found.update_tod(self.lp.my_date, str(self.input_author), approx)
                if mode == "pop":
                    self.lp.mob_found.update_pop(self.lp.my_date, str(self.input_author))

                # save mobs
                self.mobs.save_timers()
                output_date = timeh.change_tz(timeh.naive_to_tz(self.lp.my_date, "UTC"),
                                              self.lp.timezone)
                output_content = "[%s] updated! New %s: {%s %s} - %ssigned by %s" % \
                                 (self.lp.mob_found.name,
                                  mode,
                                  output_date.strftime(config.DATE_FORMAT_PRINT),
                                  self.lp.timezone,
                                  approx_output,
                                  self.input_author.name)

                output_broadcast = self.get_broadcast_channels()

            else:
                output_content = errors.error_param(self.lp.cmd, "Time Syntax Error. ")
                output_channel = self.input_author

        # If there is a guessed mob
        elif self.lp.mob_guessed:
            output_content = "Mob not found. Did you mean %s?" % self.lp.mob_guessed.name
            output_channel = self.input_author
        # If no mob
        else:
            output_channel = self.input_author
            output_content = errors.error_mob_not_found()

        return {"destination": output_channel,
                "content": messagecomposer.prettify(output_content, "CSS"),
                'broadcast': output_broadcast}

    ##################
    # SET UP A WATCHER
    ##################
    @auth.cmd("watch")
    def cmd_watch(self):
        output_channel = self.input_author
        output_broadcast = False

        if self.lp.mob_found:
            # search for minutes param
            minutes = 30
            reg_min = re.search(r"\b(\d+)\b", self.lp.param)
            if reg_min:
                minutes = int(reg_min.group(0))
            off = False
            if "off" in self.lp.key_words:
                off = True
                output_content = "Track OFF for [%s]" % self.lp.mob_found.name
            else:
                output_content = "Track ON for [%s], I will alert you %d before ETA" % \
                                 (self.lp.mob_found.name, minutes)

            self.watch.switch(self.input_author.id, self.lp.mob_found.name, minutes, off)

        # If there is a guessed mob
        elif self.lp.mob_guessed:
            output_content = "Mob not found. Did you mean %s?" % self.lp.mob_guessed.name
            output_channel = self.input_author

        # if no mob is passed but OFF parameter is, toggle off all alarms
        elif "off" in self.lp.key_words:
            self.watch.all_off(self.input_author.id)
            output_content = "All alarms are set to OFF"

        # If not params are passed get the full list of tracked mobs
        else:
            tracked_mobs = self.watch.get_all(self.input_author.id)
            if not tracked_mobs:
                output_content = "No mobs tracked :("
            else:
                output_content = ""
                for tmob in tracked_mobs:
                    output_content += '[%s] will alert %d minutes before ETA\n' % (tmob, tracked_mobs[tmob])

        return {"destination": output_channel,
                "content": messagecomposer.prettify(output_content, "CSS"),
                "broadcast": output_broadcast}

    ##################
    # SET A TARGET
    ##################
    @auth.cmd("target")
    def cmd_target(self):
        output_channel = self.input_channel
        output_broadcast = False

        if self.lp.mob_found:
            if "off" in self.lp.key_words:
                self.lp.mob_found.target = False
                output_content = "Target OFF for [%s] " % self.lp.mob_found.name
            else:
                self.lp.mob_found.target = True
                output_content = "Target ON for [%s]" % self.lp.mob_found.name
            output_content += "- signed by %s" % self.input_author.name
            self.mobs.save_targets()
            output_broadcast = self.get_broadcast_channels()
        # If there is a guessed mob
        elif self.lp.mob_guessed:
            output_content = "Mob not found. Did you mean %s?" % self.lp.mob_guessed.name
            output_channel = self.input_author
        else:
            output_content = errors.error_param(self.lp.cmd, "Missing Parameter. ")
            output_channel = self.input_author

        return {"destination": output_channel,
                "content": messagecomposer.prettify(output_content, "CSS"),
                "broadcast": output_broadcast}

    ############
    # EARTHQUAKE
    ############
    @auth.cmd("earthquake")
    def cmd_earthquake(self):
        output_channel = self.input_channel
        output_broadcast = False

        if self.lp.my_date:
            for mob in self.mobs.mobs:
                mob.update_pop(self.lp.my_date, str(self.input_author))

            self.mobs.save_timers()

            output_date = timeh.change_tz(timeh.naive_to_tz(self.lp.my_date, "UTC"), self.lp.timezone)
            output_content = "Earthquake! All pop times updated [%s] %s, signed by %s" % \
                             (output_date.strftime(config.DATE_FORMAT_PRINT),
                              self.lp.timezone,
                              self.input_author
                              )
            output_broadcast = self.get_broadcast_channels()

        else:
            output_content = errors.error_param(self.lp.cmd, "Time Syntax Error. ")
            output_channel = self.input_author

        return {"destination": output_channel,
                "content": messagecomposer.prettify(output_content, "CSS"),
                'broadcast': output_broadcast}

    ########################
    # PRINT ALIASES OF MOBS
    ########################
    @auth.cmd("mobs")
    def cmd_mobs(self):
        output_content = messagecomposer.output_list(self.mobs.get_all_meta())

        return {"destination": self.input_author,
                "content": messagecomposer.prettify(output_content, "CSS"),
                'broadcast': False}

    ########################
    # ROLES LIST/RELOAD
    ########################
    @auth.cmd("roles")
    def cmd_roles(self):
        output_channel = self.input_author
        output_broadcast = False
        output_content = ""

        # Reload Roles
        if "reload" in self.lp.key_words:
            self.authenticator.reload_discord_roles()
            self.authenticator.reload_discord_users()
            output_content += "{Roles Reloaded}\n\n"

        output_discord_roles_content = "DISCORD ROLES\n=============\n"
        for d_role in self.authenticator.roles.discord_roles:
            converted_role = self.authenticator.roles.convert_discord_role_into_bot_role(str(d_role.id))

            output_discord_roles_content += "- [%s server] %s (%d) -> %s\n" % \
                                            (d_role.guild,
                                             d_role.name,
                                             d_role.id,
                                             converted_role)

        output_bot_roles_content = "\nBOT ROLES\n=========\n"
        for b_role in self.authenticator.roles.bot_roles:
            output_bot_roles_content += "- %s\n" % b_role
            for resource in self.authenticator.roles.bot_roles[b_role]:
                output_bot_roles_content += "    - %s " % resource
                for permission in self.authenticator.roles.bot_roles[b_role][resource]:
                    output_bot_roles_content += "[%s] " % permission
                output_bot_roles_content += "\n"
            output_bot_roles_content += "\n"

        return {"destination": output_channel,
                "content": messagecomposer.prettify(output_discord_roles_content + output_bot_roles_content),
                'broadcast': output_broadcast}

    ##########
    # ROLE SET
    ##########
    @auth.cmd("setrole")
    def cmd_set_role(self):
        output_channel = self.input_author
        output_broadcast = False
        output_content = ""

        b_role = d_role = False
        if self.lp.param:

            # Find the discord_role_id
            reg = re.search(r"\b(\d+)\b", self.lp.param)
            if reg:
                d_role = self.authenticator.roles.check_discord_role(reg.group(0))

            # Find the Bot_Roles
            bot_roles_list = self.authenticator.roles.get_bot_roles_list()
            regex = ""
            for role in bot_roles_list:
                regex += "%s|" % role
            regex = r"\b(" + regex[:-1] + r")\b"
            reg = re.search(regex, self.lp.param)
            if reg:
                b_role = reg.group(0)

            if not isinstance(d_role, auth.DiscordRole):
                output_content = "Discord Role ID not found! Type !roles to list them"
            elif not b_role:
                output_content = "Bot Role not found! Type !roles to list them"
            else:
                self.authenticator.roles.assign_discord_role_to_bot_role(str(d_role.id), b_role)
                output_content += "Discord Role [%s] {%s} assigned to Bot Role [%s]\n\n" % \
                                  (d_role.name, d_role.id, b_role)
                output_content += "Commands for this new role:\n%s" % \
                                  self.authenticator.acl.which_permissions_any([b_role], "command")
                self.authenticator.reload_discord_roles()
                self.authenticator.reload_discord_users()

        else:
            output_content = errors.error_param(self.lp.cmd, "Missing Parameter. ")

        return {"destination": output_channel,
                "content": messagecomposer.prettify(output_content, "CSS"),
                'broadcast': output_broadcast}

    ########################
    # USERS LIST/RELOAD
    ########################
    @auth.cmd("users")
    def cmd_users(self):
        output_channel = self.input_author
        output_broadcast = False

        if "reload" in self.lp.key_words:
            self.authenticator.reload_discord_users()
            return {"destination": output_channel,
                    "content": messagecomposer.prettify("Users Reloaded!\n", "CSS"),
                    'broadcast': output_broadcast}

        # Find the Bot_Roles
        b_role = False
        bot_roles_list = self.authenticator.roles.get_bot_roles_list()
        regex = ""
        if self.lp.param:
            for role in bot_roles_list:
                regex += "%s|" % role
            regex = r"\b(" + regex[:-1] + r")\b"
            reg = re.search(regex, self.lp.param)
            if reg:
                b_role = reg.group(0)

        if "all" not in self.lp.key_words and b_role not in bot_roles_list:
            output_content = "Bot Role not found! Type !roles to list them or !users all"
            return {"destination": output_channel,
                    "content": messagecomposer.prettify(output_content, "CSS"),
                    'broadcast': output_broadcast}

        output_content = "USERS\n=====\n"
        get_key = operator.attrgetter("name")
        for user in (sorted(self.authenticator.users.values(), key=lambda mbr: get_key(mbr).lower())):
            if "all" in self.lp.key_words or b_role in user.b_roles:
                user_name = user.name
                user_bot_roles = ""
                for user_b_role in user.b_roles:
                    user_bot_roles += ".%s " % user_b_role
                user_guilds = ""
                for guild in user.guilds:
                    user_guilds += "{%s} " % guild
                user_guilds = user_guilds[:-1]
                output_content += "- [%s] %s - %s\n" % (user_name, user_guilds, user_bot_roles)

        return {"destination": output_channel,
                "content": messagecomposer.prettify(output_content, "CSS"),
                'broadcast': output_broadcast}

    ###########
    # BROADCAST
    ###########
    @auth.cmd("echo")
    def cmd_echo(self):

        return {"destination": self.input_channel,
                "content": messagecomposer.prettify(self.lp.param, "CSS"),
                'broadcast': self.get_broadcast_channels()}

    ########################
    # LEAVE ALL SERVERS
    ########################
    @auth.cmd("guild")
    def leave_all_guilds(self):

        return {"destination": self.input_channel,
                "content": messagecomposer.prettify("Farewell!", "CSS"),
                'broadcast': self.get_broadcast_channels(),
                'action': 'leave_all_guilds'}

    #########################
    # GET BROADCAST CHANNELS
    #########################
    def get_broadcast_channels(self):
        broadcast_channels = list()
        for channel in config.BROADCAST_TOD_CHANNELS:
            if not self.input_channel.id == channel:
                broadcast_channels.append(channel)
        return broadcast_channels

    ######################
    # MOB SKIPPED UPDATE TIMERS
    ######################
    @auth.cmd("skip")
    def cmd_skip(self):
        return self.update_mob("skip")
