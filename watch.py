import json
import os


class Watch:
    def __init__(self, url_json):
        self.url_json = url_json
        self.users = {}

        if not os.path.exists(url_json):
            with open(url_json, "x") as f:
                f.write("{}")
        with open(url_json) as f:
            json_watch = json.load(f)
        # Transform string key into key ones
        for key in json_watch:
            self.users[int(key)] = json_watch[key]

    def __str__(self):
        return self.users

    def check(self, user, mob, minute):
        if user not in self.users:
            return False
        if mob not in self.users[user]:
            return False
        if not self.users[user][mob] == minute:
            return False
        return True

    def get_single(self, user, mob):
        if user not in self.users:
            return False
        else:
            if mob not in self.users[user]:
                return False
            else:
                return self.users[user][mob]

    def get_all(self, user):
        output = {}
        if user not in self.users:
            return False
        else:
            for mob in self.users[user]:
                output[mob] = self.users[user][mob]
        return output

    def switch(self, user, mob, minutes=30, off=True):
        if user not in self.users:
            self.users[user] = {}
        if off:
            self.users[user].pop(mob, None)
        else:
            self.users[user][mob] = minutes
        self.save()

    def all_off(self, user):
        if user in self.users:
            self.users.pop(user, None)
        self.save()

    def save(self):
        with open(self.url_json, 'w') as outfile:
            json.dump(self.users, outfile, indent=2)
