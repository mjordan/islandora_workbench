#!/usr/bin/env python3

"""Sample field preprocessor script. Takes input, converts it to upper case,
   then prints it to stdout. Back in workbench, the printed output replaces
   the field's original value.
"""

import sys

subdelimiter = sys.argv[1].strip()
input = sys.argv[2].strip()

# Preprocessor scripts must check to see if the subdelimiter is present,
# and if so, split the input and manipulate each subvalue separately, then
# reassemble the subvalues back into a string to print().
if subdelimiter in input:
    joiner = subdelimiter
    subvalues = input.split(subdelimiter)
    for key, value in enumerate(subvalues):
        subvalues[key] = value.upper()

    new_value = joiner.join(subvalues)
    print(new_value)
else:
    print(input.upper())
