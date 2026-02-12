#!/usr/bin/env python3

import os
import re
import sys
import uuid

import requests
from faker import Faker

# Hackerdom exit codes
OK = 101
CORRUPT = 102
MUMBLE = 103
DOWN = 104
CHECKER_ERROR = 110


SERVICENAME = "avitoff"
PORT = int(os.environ.get("PORT", 8000))


def close(code, public="", private=""):
    if public:
        print(public)
    if private:
        print(private, file=sys.stderr)
    print(f"Exit with code {code}", file=sys.stderr)
    sys.exit(code)


def check(*args):
    host = args[0]
    url = f"http://{host}:{PORT}"
    try:
        # Visit main and registration
        r = requests.get(f"{url}/", timeout=5)
        if r.status_code != 200:
            close(MUMBLE, "Service main page is not responding correctly")

        if "register" not in requests.get(f"{url}/register/", timeout=5).text.lower():
            close(MUMBLE, "Service layout is corrupted")

        close(OK)
    except Exception as e:
        close(DOWN, "Connection error", str(e))


def put(*args):
    # args: [host, flag_id, flag, vuln]
    host, flag_id, flag = args[:3]
    url = f"http://{host}:{PORT}"
    s = requests.Session()

    u_name = f"user_{uuid.uuid4().hex[:8]}"
    u_email = fake.email()
    u_pass = fake.password()
    u_phone = fake.msisdn()

    try:
        # 1. Registration
        reg_data = {
            "nickname": u_name,
            "email": u_email,
            "phone": u_phone,
            "password": u_pass,
        }
        r = s.post(f"{url}/register/", data=reg_data, timeout=7)
        if "/profile/" not in r.url:
            close(MUMBLE, "Could not register new user")

        # 2. Upload Ad with flag
        ad_data = {
            "header": f"Item {uuid.uuid4().hex[:6]}",
            "description": flag,
            "price": "500",
        }
        r = s.post(f"{url}/upload/", data=ad_data, timeout=7)
        if "/profile/" not in r.url:
            close(MUMBLE, "Could not upload advertisement")

        # 3. Extract ad_id
        r = s.get(f"{url}/profile/", timeout=5)
        ids = re.findall(r"/ads/edit_privacy/(\d+)", r.text)
        if not ids:
            close(CORRUPT, "Ad not found in profile after upload")

        target_id = ids[-1]

        # 4. Set Private (toggle)
        s.post(f"{url}/ads/edit_privacy/{target_id}", timeout=5)

        # Output the flag_id for future GET requests
        # We store all credentials needed to retrieve the flag
        close(OK, f"{u_email}:{u_pass}:{target_id}")

    except Exception as e:
        close(MUMBLE, "PUT failed due to internal error", str(e))


def get(*args):
    # args: [host, flag_id, flag, vuln]
    host, flag_id, flag = args[:3]
    url = f"http://{host}:{PORT}"

    try:
        u_email, u_pass, ad_id = flag_id.split(":")
    except ValueError:
        close(CHECKER_ERROR, "Invalid flag_id format in GET")

    s = requests.Session()
    try:
        # 1. Auth
        r = s.post(
            f"{url}/login/", data={"email": u_email, "password": u_pass}, timeout=7
        )
        if "/profile/" not in r.url:
            close(MUMBLE, "Login failed for stored credentials")

        # 2. Check Ad
        r = s.get(f"{url}/ads/{ad_id}/", timeout=7)
        if r.status_code == 404:
            close(CORRUPT, "Advertisement disappeared")

        if flag not in r.text:
            close(CORRUPT, "Flag not found in the advertisement")

        close(OK)
    except Exception as e:
        close(MUMBLE, "GET failed", str(e))


def info(*args):
    close(OK, "vulns: 1")


def error_arg(*args):
    close(CHECKER_ERROR, "Unknown command")


COMMANDS = {
    "check": check,
    "put": put,
    "get": get,
    "info": info,
}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        close(CHECKER_ERROR, "No command provided")

    cmd = sys.argv[1]
    # Standard Hackerdom dispatching
    try:
        COMMANDS.get(cmd, error_arg)(*sys.argv[2:])
    except Exception as ex:
        close(CHECKER_ERROR, f"INTERNAL ERROR: {ex}")
