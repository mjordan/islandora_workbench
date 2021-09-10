
import os
import re
import requests
from requests.auth import HTTPBasicAuth
import mimetypes
import logging
import urllib3
import urllib.parse
import config


class MultiPageMedia:

    def __init__(self):

        self.filenames = []
        self.risearch_url = "http://128.206.4.208:8080/fedora/risearch?"
        self.preset_params = "type=tuples&lang=+sparql&format=CSV&limit=1000&dt=on&query="
        self.sparql_query = ''
        self.request_uri = ''
        self.sparql_query_results = ''
        self.parsed_sparql_query_results = ''
        self.multipage_file_list = {}
        self.pid_list = []
        self.islandora_base_url = 'https://dl.mospace.umsystem.edu/'
        self.obj_directory = '/home/borwickja/PhpstormProjects/islandoraworkbench/islandora_workbench/input_data'
        self.parent_pid = ''
        self.username = ''
        self.password = ''

    def set_username(self,username):

        self.username = username


    def set_password(self,password):

        self.password = password


    def set_parent_pid(self,pid):

        self.parent_pid = pid


    def set_sparql_query(self):

        if self.parent_pid != '':

            self.sparql_query = "select  ?o ?s from <#risearch> where { ?o <http://islandora.ca/ontology/relsext#isPageOf> <info:fedora/" + self.parent_pid + "> ." + "\n" + " $o <http://islandora.ca/ontology/relsext#isPageNumber> ?s .  } ORDER BY ASC(?s)"
            self.sparql_query = urllib.parse.quote(self.sparql_query)



    def set_request_uri(self):


        self.request_uri = self.risearch_url + self.preset_params + self.sparql_query


    def get_request_uri(self):

        return self.request_uri


    def request_data(self):

        res = requests.post(self.request_uri, verify=False, auth=HTTPBasicAuth(self.username, self.password))
        self.sparql_query_results = res.text


    def parse_results(self):

        results_list = self.sparql_query_results.splitlines()
        # remove the first item, which are the placeholders for the subject and object
        results_list.remove(results_list[0])
        self.parsed_sparql_query_results = [child_pid.replace('info:fedora/', '') for child_pid in results_list]

    def build_filename_lookup(self):

        for item in self.parsed_sparql_query_results:

            self.create_filename_list(item)

    def create_pid_list(self,pid):


        self.pid_list.append(pid)


    def get_pid_list(self):

        for pid in self.pid_list:

            print(pid)

    def create_filename_list(self,list_item):

        list_item_string = str(list_item)
        pid_pagenumber = list_item_string.split(',')
        pid = pid_pagenumber[0]

        self.create_pid_list(pid)

        pagenumber = pid_pagenumber[1]
        pnumber = " ".join(pagenumber.split())

        try:

            pnumber = int(pnumber)
            pn = self.transform_pagenumber(pnumber)
            filename_pid = pid.replace(':', '_')
            filename = filename_pid + "-" + pn
            self.multipage_file_list[filename_pid] = filename

        except ValueError:

            print("This pagenumber is not numeric " + pnumber)

    def transform_pagenumber(self,page_number):

        if page_number <= 9:

            pn = "00" + str(page_number)


        elif page_number > 9 and page_number < 100:

            pn = "0" + str(page_number)

        else:

            pn = str(page_number)

        return pn




    def fetch_files(self):

        for pid in self.pid_list:


            campus_code = self.get_campuscodefrompid(pid)
            campus_code_pid = pid

            encoded_pid = pid.replace(':', '%3A')


            obj_url = self.islandora_base_url + campus_code + '/islandora/object/' + encoded_pid + '/datastream/OBJ/download'

            print(obj_url)
            try:

                obj_download_response = requests.get(url=obj_url, allow_redirects=True)

                if obj_download_response.status_code == 200:
                    # Get MIMETYPE from 'Content-Type' header
                    obj_mimetype = obj_download_response.headers['content-type']
                    obj_extension = self.get_extension_from_mimetype(obj_mimetype)
                    obj_tmp_filename = pid.replace(':', '_')

                    obj_filename = self.multipage_file_list.get(obj_tmp_filename)
                    obj_basename = obj_filename + obj_extension
                # row = obj_basename + ',' + row
                # Save to file with name based on PID and extension based on MIMETYPE
                    obj_file_path = os.path.join(self.obj_directory, obj_basename)
                    open(obj_file_path, 'wb+').write(obj_download_response.content)

                if obj_download_response.status_code == 404:
                    logging.warning(obj_url + " not found.")

            except requests.exceptions.RequestException as e:
                logging.info(e)
                continue

    def get_campuscodefrompid(self, pid):


        campus_prefix = self.get_pidcampusprefix(pid)


        return_val = ''
        campus_codes = ['umkc', 'umkclaw', 'umsl', 'mu']

        for code in campus_codes:
            if campus_prefix == code:
             return_val = code
             break

        return return_val

    def get_pidcampusprefix(self, pid):

        pid_pieces = pid.split(':')
        return pid_pieces[0]

    def get_extension_from_mimetype(self, mimetype):

        # mimetypes.add_type() is not working, e.g. mimetypes.add_type('image/jpeg', '.jpg')
        # Maybe related to https://bugs.python.org/issue4963? In the meantime, provide our own
        # MIMETYPE to extension mapping for common types, then let mimetypes guess at others.
        map = {'image/jpeg': '.jpg',
               'image/jp2': '.jp2',
               'image/png': '.png'
               }
        if mimetype in map:
            return map[mimetype]
        else:
            return mimetypes.guess_extension(mimetype)
