#!/usr/bin/env python3

'''Example shutdown script that logs sys.args.

   These scripts must be executable.
'''

import sys
import logging

logging.basicConfig(
    filename='shutdown_example.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%d-%b-%y %H:%M:%S')

logging.info(sys.argv)
