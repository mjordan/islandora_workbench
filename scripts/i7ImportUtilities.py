from ruamel.yaml import YAML
import mimetypes
import requests
import os
import re
import logging

class i7ImportUtilities:

    def __init__(self, config_location):
        self.config_location = config_location
        self.config = self.get_config()
        logging.basicConfig(
            filename=self.config['log_file_path'],
            level=logging.INFO,
            filemode='a',
            format='%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%d-%b-%y %H:%M:%S')


    default_config = {
        'solr_base_url': 'http://localhost:8080/solr',
        'islandora_base_url': 'http://localhost:8000',
        'csv_output_path': 'islandora7_metadata.csv',
        'obj_directory': '/tmp/objs',
        'log_file_path': 'islandora_content.log',
        'fetch_files': True,
        'namespace': '*',
        'standard_fields': ['PID', 'RELS_EXT_hasModel_uri_s', 'RELS_EXT_isMemberOfCollection_uri_ms',
                            'RELS_EXT_isMemberOf_uri_ms', 'RELS_EXT_isConstituentOf_uri_ms',
                            'RELS_EXT_isPageOf_uri_ms'],
        'field_pattern': 'mods_.*(_s|_ms)$',
        'field_pattern_do_not_want': '(marcrelator|isSequenceNumberOf)',
        'id_field': 'PID',
        'id_start_number': 1
    }

    def get_config(self):
        yaml = YAML()
        config = self.default_config
        with open(self.config_location, 'r') as stream:
            try:
                loaded = yaml.load(stream)
            except yaml.YAMLError as exc:
                print(exc)
        for key, value in loaded.items():
            config[key] = value
        return config

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

    def get_child_sequence_number(self, pid):
        '''For a given Islandora 7.x PID, get the object's sequence number in relation
           to its parent from the RELS-EXT datastream. Assumes child objects are only
           children of a single parent.
        '''
        rels_ext_url = self.config['islandora_base_url'] + '/islandora/object/' + pid + '/datastream/RELS-EXT/download'
        try:
            rels_ext_download_response = requests.get(url=rels_ext_url, allow_redirects=True)
            if rels_ext_download_response.status_code == 200:
                rels_ext_xml = rels_ext_download_response.content.decode()
                matches = re.findall('<(islandora:isPageOf|fedora:isConstituentOf)\s+rdf:resource="info:fedora/(.*)">',
                                     rels_ext_xml, re.MULTILINE)
                # matches contains tuples, but we only want the values from the second value in each tuple,
                # pids corresponding to the second set of () in the pattern.
                parent_pids = [pids[1] for pids in matches]
                if len(parent_pids) > 0:
                    parent_pid = parent_pids[0].replace(':', '_')
                    sequence_numbers = re.findall('<islandora:isSequenceNumberOf' + parent_pid + '>(\d+)', rels_ext_xml,
                                                  re.MULTILINE)
                    # Paged content stores sequence values in <islandora:isSequenceNumber>, so we look there
                    # if we didn't get any in isSequenceNumberOfxxx.
                    if len(sequence_numbers) == 0:
                        sequence_numbers = re.findall('<islandora:isSequenceNumber>(\d+)', rels_ext_xml, re.MULTILINE)
                    if len(sequence_numbers) > 0:
                        return sequence_numbers[0]
                    else:
                        logging.warning("Can't get sequence number for " + pid)
                        return ''
                else:
                    logging.warning("Can't get parent PID for " + pid)
                    return ''
        except requests.exceptions.RequestException as e:
            raise SystemExit(e)

    def get_percentage(self,part, whole):
        return 100 * float(part) / float(whole)
