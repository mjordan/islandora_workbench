#!/usr/bin/env python3

"""Islandora Workbench shutdown script to send a the log file to someone
if it contains any ERROR entries.
"""

import smtplib
import re
import sys
from ruamel.yaml import YAML

workbench_config_file_path = sys.argv[1]

yaml = YAML()
config_yaml = open(workbench_config_file_path, "r")
config = yaml.load(config_yaml)
if "log_file_path" in config:
    workbench_log_file_path = config["log_file_path"]
else:
    log_file_path = "workbench.log"

fromaddr = "someaddr@example.com"
toaddrs = "anotheraddr@example.com"
# toaddrs  = "anotheraddr@example.com,yetanotheraddr@example.com"

msg = (
    "Subject: Islandora Workbench log file - there were errors!\r\nFrom: %s\r\nTo: %s\r\n\r\n"
    % (fromaddr, toaddrs)
)

# If the log contains any ERROR entries, mail it.
log_file = open(workbench_log_file_path, "r")
log_file_text = log_file.read()
log_file.close()
matches = re.findall("ERROR", log_file_text)

if len(matches) > 0:
    msg = msg + log_file_text
    server = smtplib.SMTP("localhost")
    server.sendmail(fromaddr, toaddrs, msg.encode("utf-8"))
    server.quit()
