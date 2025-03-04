#!/usr/bin/env python3

"""Script to generate simple image files based on a list of titles.
Requires ImageMagik's convert command.
"""

import os
import sys
import subprocess
import random
import re

# Change the variables below.

# Must exist and be absolute.
dest_dir = "/tmp/colors"
# Must exist. Relative to this script
title_file_path = "sample_filenames.txt"
num_images_to_generate = 10
# @todo: Check for path to convert; if not found, bail.
path_to_convert = "/usr/bin/convert"

# Change the variables above.

# Program logic starts here.
if os.path.exists(dest_dir) is False:
    sys.exit("Error: output directory " + dest_dir + " does not exist.")

colors = [
    "crimson",
    "orchid",
    "DarkViolet",
    "SlateBlue",
    "navy",
    "SlateGrey",
    "black",
    "burlywood4",
    "SeaGreen",
    "DeepSkyBlue",
]

with open(title_file_path) as f:
    lines = f.read().splitlines()
    if len(lines) >= num_images_to_generate:
        lines = lines[:num_images_to_generate]
    for line in lines:
        line = re.sub(r"[^\w\s]", " ", line)
        line = re.sub(r"\s", "_", line)
        line = re.sub(r"_{2,5}", "_", line)
        filename = line.rstrip("_")
        words = line.split("_")
        first_three_words = words[:3]
        first_three_words_string = "\n".join(first_three_words)
        color = random.choice(colors)
        cmd = (
            path_to_convert
            + " -size 1000x1000 xc:"
            + color
            + " "
            + os.path.join(dest_dir, filename + ".png")
            + "; "
        )
        cmd += path_to_convert + " -size 1000x1000 xc:" + color
        cmd += (
            "  -pointsize 100 -fill white -gravity center -annotate +0+0 "
            + '"'
            + first_three_words_string
            + '"'
        )
        cmd += " " + os.path.join(dest_dir, filename + ".png")
        subprocess.call(cmd, shell=True)
