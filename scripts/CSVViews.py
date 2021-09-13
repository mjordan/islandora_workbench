import os
from os.path import exists


class CSVViews:

    def __init__(self):

        self.file = ''
        self.header_data_dict = {}
        self.list = []

    def set_file(self, filename):

        self.file = filename

    def read_file(self, filename):

        file_exists = exists(filename)

        if file_exists:

            self.file = filename

    def parse_file(self):

        with open(self.filename) as file:
            for line in file:
               line = line.rstrip()
               self.list.append(line)

    def display_headersdata(self):

        print(self.list)


