import os

import config
import json
import datetime
import timehandler as timeh
import messagecomposer


# Class that define mob info and a bunch of utilities
class Mob:
    def __init__(self, name, alias, respawn_time, plus_minus, recurring, windows, tag, tod, pop,
                 author_tod, author_pop, accuracy, target, date_rec, date_print):

        self.d_rec = date_rec
        self.d_print = date_print
        # Complete name of the Mob
        self.name = name
        # Aliases
        self.alias = alias
        # Respawn Time
        self.respawn_time = respawn_time
        # Variance
        self.plus_minus = plus_minus
        # Windows 
        self.windows = windows
        # Current window
        if len(self.windows) > 0:
            self.current_window = 1
        else:
            self.current_window = 0
        # If the spawn is recurring. (ex scout)
        self.recurring = recurring
        # Tag of the mob
        self.tag = tag
        # Bool, True if target
        self.target = target
        # Time of Death
        self.tod = datetime.datetime.strptime(tod, self.d_rec)
        # Pop Time
        self.pop = datetime.datetime.strptime(pop, self.d_rec)
        # Author of the last ToD
        self.signed_tod = author_tod
        # Author of the last pop
        self.signed_pop = author_pop
        # Accuracy. 0 for approx time, 1 for exact time, -1 when pop > tod
        self.accuracy = accuracy
        # Number of spawns since last tod (for recurring mobs)
        self.spawns = 0
        # Spawn Windows {"start"} {"end"}
        if self.tod > self.pop:
            self.window = self.get_window(self.tod)
        else:
            self.window = self.get_window(self.pop)
            self.accuracy = -2
        # Eta
        self.eta = self.get_eta()

    def get_window(self, from_date, skipped=False):
        if not skipped:
            w_start = from_date + datetime.timedelta(hours=self.respawn_time) - datetime.timedelta(
                hours=self.plus_minus)
            w_end = from_date + datetime.timedelta(hours=self.respawn_time) + datetime.timedelta(hours=self.plus_minus)
        else:
            adjusted_eta = self.eta
            if self.current_window - 2 >= 0:
                adjusted_eta = self.eta + datetime.timedelta(hours=self.windows[self.current_window - 2])

            w_start = adjusted_eta + datetime.timedelta(hours=self.respawn_time) - datetime.timedelta(
                hours=self.windows[self.current_window - 1])
            w_end = adjusted_eta + datetime.timedelta(hours=self.respawn_time) + datetime.timedelta(
                hours=self.windows[self.current_window - 1])

        return {"start": w_start, "end": w_end}

    def update_tod(self, new_tod, author, approx=1):
        self.tod = new_tod
        self.signed_tod = author
        self.accuracy = approx
        self.window = self.get_window(new_tod)
        self.eta = self.get_eta()
        self.target = False
        if len(self.windows) > 0:
            self.plus_minus = self.windows[0]
            self.current_window = 1

    def update_pop(self, new_pop, author):
        self.pop = new_pop
        self.signed_pop = author
        self.window = self.get_window(new_pop)
        self.eta = self.get_eta()
        if len(self.windows) > 0:
            self.plus_minus = self.windows[0]
            self.current_window = 1

    def update_skip(self, skip_time, author):
        if len(self.windows) > 0 and self.current_window + 1 <= len(self.windows):
            self.signed_tod = author
            self.eta = self.get_eta()
            self.target = False
            self.plus_minus = self.windows[self.current_window]
            self.current_window = self.current_window + 1
            self.window = self.get_window(skip_time, True)
        else:
            return {"Trying to skip last cycle"}

    def get_eta(self, virtual_tod=None):
        eta = datetime.datetime.strptime(config.DATE_DEFAULT, config.DATE_FORMAT)

        # virtual tod is last saved tod if this function is directly called
        if not virtual_tod:
            virtual_tod = self.tod
            self.spawns = 0

        # virtual tod is last saved pop if the latter is newer than the former
        if self.pop > virtual_tod:
            self.accuracy = -1
            virtual_tod = self.pop

        # get now date to calculate the timeframe
        now = datetime.datetime.utcnow()
        delta_hour = datetime.timedelta(hours=self.respawn_time)

        # mob has no window and spawn in the future
        if self.plus_minus == 0 and now < (virtual_tod + delta_hour):
            eta = virtual_tod + delta_hour

        # mob has window and we are before window opens
        if now < self.window["start"] and self.plus_minus:
            eta = self.window["start"]

        # we are in window
        if self.window["start"] < now < self.window["end"]:
            eta = self.window["end"]

        # if the mob is a recurring one and we are past the calculated eta...
        # set a new tod for recurring mob (scout)
        if self.recurring and self.plus_minus == 0 and now >= virtual_tod + delta_hour and self.spawns < 12:
            self.spawns += 1
            eta = self.get_eta(virtual_tod + delta_hour)

        return eta

    def in_window(self):
        now = timeh.now()
        if (self.window['start'] < now < self.window['end']) and self.plus_minus:
            return True
        else:
            return False

    def print_short_info(self, timezone="EST"):
        self.eta = self.get_eta()
        tod_tz = timeh.change_naive_to_tz(self.tod, timezone) if self.recurring else None
        if tod_tz:
            tod_tz = tod_tz.strftime(self.d_print)
        return messagecomposer.time_remaining(self.name, self.eta, self.plus_minus, self.window, self.spawns,
                                              self.accuracy, self.target, self.current_window, tod_tz)

    def print_long_info(self, timezone):
        self.eta = self.get_eta()
        if self.eta == datetime.datetime.strptime(config.DATE_DEFAULT, config.DATE_FORMAT):
            eta = "N/A"
        else:
            eta = timeh.change_naive_to_tz(self.eta, timezone)
            eta = eta.strftime(self.d_print)

        tod_tz = timeh.change_naive_to_tz(self.tod, timezone)
        pop_tz = timeh.change_naive_to_tz(self.pop, timezone)
        w_start_tz = timeh.change_naive_to_tz(self.window["start"], timezone)
        w_end_tz = timeh.change_naive_to_tz(self.window["end"], timezone)

        tz_print = "Timezone %s\n\n" % timezone

        return tz_print + messagecomposer.detail(self.name,
                                                 tod_tz.strftime(self.d_print),
                                                 pop_tz.strftime(self.d_print),
                                                 self.signed_tod,
                                                 self.signed_pop,
                                                 self.respawn_time,
                                                 self.plus_minus,
                                                 self.tag,
                                                 w_start_tz.strftime(self.d_print),
                                                 w_end_tz.strftime(self.d_print),
                                                 self.accuracy,
                                                 eta,
                                                 self.current_window,
                                                 self.windows
                                                 )

    def print_meta(self):
        return messagecomposer.meta(self.name, self.alias, self.tag)

    # serialize data
    def serialize(self):
        return ({self.name: {
            "tod": self.tod.strftime(self.d_rec),
            "pop": self.pop.strftime(self.d_rec),
            "signed_tod": self.signed_tod,
            "signed_pop": self.signed_pop,
            "accuracy": self.accuracy
        }
        })

    # Check tag
    def check_tag(self, tag):
        for i in self.tag:
            if i.lower() == tag.lower():
                return True
        return False


# Class container of Mobs, load from JSON
class MobList:

    def __init__(self, url_entities, url_timers, url_targets, date_format_rec, date_format_print):
        self.url_entities = url_entities
        self.url_timers = url_timers
        self.url_targets = url_targets
        self.max_respawn_time = 0

        if not os.path.exists(url_entities):
            print("[ERROR] %s does not exist!")
            exit(-1)
        with open(url_entities) as f:
            json_entities = json.load(f)

        if not os.path.exists(url_timers):
            with open(url_timers, 'x') as f:
                f.write("{}")
        with open(url_timers) as f:
            json_timers = json.load(f)

        if not os.path.exists(url_targets):
            with open(url_targets, 'x') as f:
                f.write("{}")
        with open(url_targets) as f:
            json_targets = json.load(f)

        self.mobs = list()
        self.tags = list()
        for i in json_entities:
            # CALCULATE LIMIT HOURS FOR GET ALL REQUESTS
            limit_respawn_time = json_entities[i]["respawn_time"] + json_entities[i]["plus_minus"]
            if limit_respawn_time > self.max_respawn_time:
                self.max_respawn_time = limit_respawn_time
            if i in json_timers:
                tod = json_timers[i]["tod"]
                pop = json_timers[i]["pop"]
                print(json_timers[i])
                signed_tod = json_timers[i]["signed_tod"]
                if "signed_pop" not in json_timers[i]:
                    signed_pop = signed_tod
                else:
                    signed_pop = json_timers[i]["signed_pop"]

                accuracy = json_timers[i]["accuracy"]
            else:
                tod = config.DATE_DEFAULT
                pop = config.DATE_DEFAULT
                signed_tod = "Default"
                signed_pop = "Default"
                accuracy = 0
            if i in json_targets:
                target = True
            else:
                target = False
            if "windows" in json_entities[i]:
                windows = json_entities[i]["windows"]
            else:
                windows = []
            self.mobs.append(Mob(i,
                                 json_entities[i]["alias"],
                                 json_entities[i]["respawn_time"],
                                 json_entities[i]["plus_minus"],
                                 json_entities[i]["recurring"],
                                 windows,
                                 json_entities[i]["tag"],
                                 tod,
                                 pop,
                                 signed_tod,
                                 signed_pop,
                                 accuracy,
                                 target,
                                 date_format_rec,
                                 date_format_print
                                 ))
            # Create a list of tag
            for tag in json_entities[i]["tag"]:
                if not tag.lower() in self.tags and tag:
                    self.tags.append(tag.lower())
            self.tags.sort()

    def save_timers(self):
        with open(self.url_timers, 'w') as outfile:
            json.dump(self.serialize(), outfile, indent=4)

    def save_targets(self):
        with open(self.url_targets, 'w') as outfile:
            self.order('eta')
            output = list()
            for mob in self.mobs:
                if mob.target:
                    output.append(mob.name)
            json.dump(output, outfile, indent=4)

    def order(self, order='name'):
        if order == 'name':
            self.mobs.sort(key=lambda mob: mob.name.lower())
        if order == 'eta':
            self.mobs.sort(key=lambda mob: mob.eta)
            self.mobs.sort(key=lambda mob: mob.in_window(), reverse=True)

    def get_all_window(self):
        self.order('eta')
        output = list()

        for mob in self.mobs:
            if mob.window['start'] <= timeh.now() <= mob.window['end']:
                output.append(mob.print_short_info())

        return output

    def get_all(self, timezone, mode="countdown", limit_hours=None):
        if not limit_hours:
            limit_hours = self.max_respawn_time
        now = timeh.now()
        self.order('eta')
        output = list()

        for mob in self.mobs:
            date_limit = now + datetime.timedelta(hours=limit_hours)
            date_diff = date_limit - mob.eta
            hour_diff = date_diff.total_seconds() / 3600
            if timeh.now() < mob.eta and hour_diff >= 0:
                # Show online mob eta in the future
                if mode == "countdown":
                    output.append(mob.print_short_info())
                else:
                    output.append(mob.print_long_info(timezone))
        return output

    def get_all_by_tag(self, tag):
        self.order('eta')
        output = list()
        for mob in self.mobs:
            if mob.check_tag(tag) and timeh.now() < mob.eta:
                output.append(mob.print_short_info())
        return output

    def get_all_targets(self):
        self.order('eta')
        output = list()
        for mob in self.mobs:
            if mob.target:
                output.append(mob.print_short_info())
        return output

    def get_all_meta(self):
        self.order('name')
        output = list()
        for mob in self.mobs:
            output.append(mob.print_meta())
        return output

    def get_all_tags(self):
        output = list()
        for tag in self.tags:
            output.append("%s\n" % tag)
        return output

    def get_re_tags(self):
        output = ""
        for tag in self.tags:
            output += "%s|" % tag
        output = output[:-1]
        return output

    def serialize(self):
        json_output = {}
        for mob in self.mobs:
            json_output.update(mob.serialize())
        return json_output
