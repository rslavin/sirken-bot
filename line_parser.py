from fuzzywuzzy import fuzz
import config
import operator
import re
import timehandler as timeh


class LineParser:

    def __init__(self, mobs_list):
        # list of common keywords used
        self.key_words = list()
        self.mobs_list = mobs_list
        self.param = None
        self.cmd = None
        self.mob_found = None
        self.mob_guessed = None
        self.timezone = None
        self.days_back = 0
        self.parsed_time = None
        self.parsed_date = None
        self.my_date = None
        self.tag = None

    def process(self, line):
        if not line:
            return False
        # deal only with lines that start with !
        if line[0] != "!":
            return False
        else:
            line = line[1:].lower()

        splitted_line = line.split(" ", 1)
        self.cmd = splitted_line[0]

        try:
            self.param = splitted_line[1]
        except IndexError:
            self.param = None

        if self.cmd == "help":
            return True

        if self.param:
            # check if reload parameter is provided
            self.find_word_reload()
            # check if timezone parameter is provided
            self.set_tz()
            # check if info parameter is provided
            self.find_word_info()
            # check if off is provided
            self.find_word_off()
            # check if all is provided
            self.find_word_all()
            # check if target is provided
            self.find_word_target()
            # check if tag is provided
            self.find_tag()
            # check if window is provided
            self.find_word_window()
            # check if approx is provided
            self.find_word_approx()
            # check if time is provided
            self.find_word_sirken()
            # check if time is provided
            self.find_time()
            # check if date is provided
            self.find_date()
            # check if "now" is provided
            if self.find_now():
                self.my_date = timeh.now()
            # check if "yesterday" is provided
            self.find_yesterday()
            # check if "xx minutes ago are provided
            mins_ago = self.find_mins_ago()
            if mins_ago:
                self.my_date = timeh.from_mins_ago(mins_ago)
            if not self.my_date:
                self.my_date = timeh.assemble_date(self.parsed_time, self.parsed_date, self.timezone, self.days_back)
            # find mobs
            self.find_mob()

        return True

    def find_word_reload(self):
        reg = re.search(r"\b(reload)\b", self.param)
        if reg:
            self.key_words.append("reload")
            # Strip the parameter
            self.param = self.param[:reg.start()] + self.param[reg.end():]
            self.polish_line()

    def set_tz(self):
        self.timezone = "EST"
        reg = re.search(r"\b(pst|pdt|cst|cdt|est|edt|cet|gmt)\b", self.param)
        if reg:
            timezone = reg.group(1).upper()
            if timezone == "PST" or timezone == "PDT":
                timezone = "US/Pacific"
            if timezone == "CST" or timezone == "CDT":
                timezone = "US/Central"
            if timezone == "EST" or timezone == "EDT":
                timezone = "US/Eastern"
            self.timezone = timezone
            # Strip the parameter
            self.param = self.param[:reg.start()] + self.param[reg.end():]
            self.polish_line()

    def find_word_info(self):
        # search the parameter info for detailed information
        reg = re.search(r"\b(info)\b", self.param)
        if reg:
            self.key_words.append("info")
            # Strip the parameter
            self.param = self.param[:reg.start()] + self.param[reg.end():]
            self.polish_line()

    # Time stuff (boring!)
    def find_date(self):
        reg = re.search(r"(([12]\d{3})-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01]))", self.param)
        if reg:
            self.parsed_date = {"year": int(reg.group(2)), "month": int(reg.group(3)), "day": int(reg.group(4))}
            # Strip the parameter
            self.param = self.param[:reg.start()] + self.param[reg.end():]
            self.polish_line()

    def find_time(self):
        reg = re.search(r"\b(([0-9]|0[0-9]|1[0-9]|2[0-3])([:\.])([0-5][0-9])\s?([AaPp].?[Mm]\b)?)\b", self.param)
        if reg:
            time = {"hour": int(reg.group(2)), "minute": int(reg.group(4))}
            # If time is am/format, convert it to 24h
            if reg.group(5):
                self.parsed_time = timeh.convert24(time, reg.group(5).replace(".", "").lower())
            else:
                self.parsed_time = time

            # Strip the paramater
            self.param = self.param[:reg.start()] + self.param[reg.end():]
            self.polish_line()

    def find_now(self):
        reg = re.search(r"\b(now)\b", self.param)
        if reg:
            # Strip the parameter
            self.param = self.param[:reg.start()] + self.param[reg.end():]
            self.polish_line()
            return True
        else:
            return False

    def find_yesterday(self):
        reg = re.search(r"\b(yesterday)\b", self.param)
        if reg:
            self.days_back = 1
            # Strip the parameter
            self.param = self.param[:reg.start()] + self.param[reg.end():]
            self.polish_line()

    def find_mins_ago(self):
        regex_str = r"\b(\d+) ?(mins?|minutes?) ago"
        reg = re.search(regex_str, self.param)
        if reg:
            # Strip the paramater
            self.param = self.param[:reg.start()] + self.param[reg.end():]
            self.polish_line()
            return reg.group(1)
        else:
            return False

    def find_word_off(self):
        reg = re.search(r"\b(off)\b", self.param)
        if reg:
            self.key_words.append("off")
            # Strip the parameter
            self.param = self.param[:reg.start()] + self.param[reg.end():]
            self.polish_line()
            return True
        else:
            return False

    def find_word_all(self):
        reg = re.search(r"\b(all)\b", self.param)
        if reg:
            self.key_words.append("all")
            # Strip the parameter
            self.param = self.param[:reg.start()] + self.param[reg.end():]
            self.polish_line()
            return True
        else:
            return False

    def find_word_target(self):
        reg = re.search(r"\b(targets?)\b", self.param)
        if reg:
            self.key_words.append("target")
            # Strip the parameter
            self.param = self.param[:reg.start()] + self.param[reg.end():]
            self.polish_line()
            return True
        else:
            return False

    def find_word_window(self):
        reg = re.search(r"\b(windows?)\b", self.param)
        if reg:
            self.key_words.append("window")
            # Strip the parameter
            self.param = self.param[:reg.start()] + self.param[reg.end():]
            self.polish_line()
            return True
        else:
            return False

    def find_word_approx(self):
        reg = re.search(r"\b(approx|around)\b", self.param)
        if reg:
            self.key_words.append("approx")
            # Strip the parameter
            self.param = self.param[:reg.start()] + self.param[reg.end():]
            self.polish_line()
            return True
        else:
            return False

    def find_word_sirken(self):
        reg = re.search(r"\b(sirken)\b", self.param)
        if reg:
            self.key_words.append("sirken")
            # Strip the parameter
            self.param = self.param[:reg.start()] + self.param[reg.end():]
            self.polish_line()
            return True
        else:
            return False

    def find_tag(self):
        tags = r"\b(" + self.mobs_list.get_re_tags().lower() + r")\b"
        reg = re.search(tags, self.param.lower())
        if reg:
            self.tag = reg.group(0)
            # Strip the parameter
            self.param = self.param[:reg.start()] + self.param[reg.end():]
            self.polish_line()
            return True
        else:
            return False

    def find_mob(self):
        result = {}
        for mob in self.mobs_list.mobs:

            hey = fuzz.token_set_ratio(self.param, mob.name)
            result[mob] = hey

            for alias in mob.alias:
                sub_hey = fuzz.token_set_ratio(self.param, alias)
                if sub_hey > result[mob]:
                    result[mob] = sub_hey

        sorted_result = sorted(result.items(), key=operator.itemgetter(1), reverse=True)
        first_result_mob = next(iter(sorted_result))[0]
        first_result_value = next(iter(sorted_result))[1]
        if first_result_value >= config.FUZZY_THRESHOLD:
            self.mob_found = first_result_mob
        if first_result_value >= config.FUZZY_GUESSED_THRESHOLD:
            self.mob_guessed = first_result_mob

    def polish_line(self):
        self.param = re.sub(' +', ' ', self.param)

    def clear(self):
        del self.key_words[:]
        self.cmd = None
        self.param = None
        self.timezone = None
        self.days_back = 0
        self.parsed_time = None
        self.parsed_date = None
        self.my_date = None
        self.tag = None
        self.mob_found = None
        self.mob_guessed = None
