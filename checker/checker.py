#!/usr/bin/env python3

import sys
import os
import copy
import requests

argv = copy.deepcopy(sys.argv)

# Hackerdom exit codes
OK = 101
CORRUPT = 102
MUMBLE = 103
DOWN = 104
CHECKER_ERROR = 110

SERVICENAME = "avitoff"

# PORT из env или дефолт
PORT = int(os.environ.get("PORT", 8000))


def close(code, public="", private=""):
    if public:
        print(public)
    if private:
        print(private, file=sys.stderr)
    print(f"Exit with code {code}", file=sys.stderr)
    sys.exit(code)


def check(*args):
    if len(args) < 1:
        close(CHECKER_ERROR, private="No IP provided")

    team_addr = args[0]
    url = f"http://{team_addr}:{PORT}/"

    try:
        r = requests.get(url, timeout=5)

        if r.status_code != 200:
            close(DOWN, public="Service is not OK")

        close(OK, public="OK")

    except requests.exceptions.ConnectionError:
        close(DOWN, public="Connection failed")

    except Exception as e:
        close(MUMBLE, private=str(e))


def put(*args):
    close(OK)


def get(*args):
    close(OK)


def info(*args):
    close(OK, "vulns: 1")


def init(*args):
    close(OK)


def error_arg(*args):
    close(CHECKER_ERROR, private=f"Unknown command {argv[1]}")


COMMANDS = {
    "check": check,
    "put": put,
    "get": get,
    "info": info,
    "init": init
}


if __name__ == "__main__":
    try:
        if len(argv) < 2:
            close(CHECKER_ERROR, private="No command")

        COMMANDS.get(argv[1], error_arg)(*argv[2:])

    except Exception as ex:
        close(CHECKER_ERROR, private=f"INTERNAL ERROR: {ex}")
