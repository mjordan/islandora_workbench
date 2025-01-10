"""Utility script to replace host, username, and password values in
   Islandora Workbench test config files.

   Usage (run from within the workbench directory):

   python scripts/make_local_tests.py

   or, with any of the optional arguments:

   python scripts/make_local_tests.py --host http://localhost:8080 --username mark --password islandora
"""

import os
import sys
import shutil
import glob
import argparse

current_dir = os.getcwd()
path_to_workbench = os.path.join(current_dir, "workbench")
if os.path.isfile(path_to_workbench) is False:
    sys.exit(f"This script must be run from the workbench directory.")

parser = argparse.ArgumentParser()

parser.add_argument(
    "--host",
    help='The "host" setting value to use in your local test config files.',
    default="https://islandora.traefik.me",
)
parser.add_argument(
    "--username",
    help='The "username" setting value to use in your local test config files.',
    default="admin",
)
parser.add_argument(
    "--password",
    help='The "password" setting value to use in your local test config files.',
    default="password",
)
args = parser.parse_args()

tests_dir = "tests"
local_tests_dir = "tests_local"

if os.path.exists(local_tests_dir):
    shutil.rmtree(local_tests_dir)

shutil.copytree(tests_dir, local_tests_dir, dirs_exist_ok=True)

for filepath in glob.iglob(f"{local_tests_dir}/**/*.yml", recursive=True):
    f = open(filepath)
    config = f.read()
    if args.host != "https://islandora.traefik.me":
        config = config.replace("https://islandora.dev", args.host)
    if args.username != "admin":
        config = config.replace("admin", args.username)
    if args.password != "password":
        config = config.replace("password", args.password)
    config = config.replace("tests/assets/", "tests_local/assets/")
    f = open(filepath, "w")
    f.write(config)
