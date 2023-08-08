# Errors

def error_auth(cmd):
    return "You don't have the right permission to use !%s command" % cmd


def error_command():
    return "Command not found! Type !help for help!"


def error_param(cmd, error):
    return error + "For the correct syntax type `!help " + str(cmd) + "`"


def error_time():
    return "Time syntax error. Type `!help tod`"


def error_mob_not_found():
    return "Mob not found. For a list of mobs type `!mobs`"
