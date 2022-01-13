from ruamel.yaml import YAML
import mimetypes
import requests
import re
import logging
import xml.etree.ElementTree as ET

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

    def get_metadata_solr_request(self, location):
        with open(location, 'r') as file:
            solr_metadata_request = file.read()
        return solr_metadata_request

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

    def get_percentage(self, part, whole):
        return 100 * float(part) / float(whole)

    def parse_rels_ext(self, pid):
        rels_ext_url = f"{self.config['islandora_base_url']}/islandora/object/{pid}/datastream/RELS-EXT/download"
        try:
            rels_ext_download_response = requests.get(url=rels_ext_url, allow_redirects=True)
            if rels_ext_download_response.status_code == 200:
                rel_ext = {}
                rels_ext_xml = rels_ext_download_response.content.decode()
                root = ET.fromstring(rels_ext_xml)
                description = root.find('.//{http://www.w3.org/1999/02/22-rdf-syntax-ns#}Description')
                for x in description:
                    tag = x.tag[x.tag.find('}') + 1:]
                    text = x.text
                    if x.attrib.items():
                        text = next(iter(x.attrib.items()))[1]
                        text = text[text.find('/') + 1:]
                    rel_ext[tag] = text
                return rel_ext
        except requests.exceptions.RequestException as e:
            raise SystemExit(e)

    def get_default_metadata_solr_request(self):
        # This query gets all fields in the index. Does not need to be user-configurable.
        fields_solr_query = '/select?q=*:*&wt=csv&rows=0&fl=*'
        fields_solr_url = f"{self.config['solr_base_url']}{fields_solr_query}"

        # Get the complete field list from Solr and filter it. The filtered field list is
        # then used in another query to get the populated CSV data.
        try:
            field_list_response = requests.get(url=fields_solr_url, allow_redirects=True)
            raw_field_list = field_list_response.content.decode()
        except requests.exceptions.RequestException as e:
            raise SystemExit(e)

        field_list = raw_field_list.split(',')
        filtered_field_list = [keep for keep in field_list if re.search(self.config['field_pattern'], keep)]
        filtered_field_list = [discard for discard in filtered_field_list if
                               not re.search(self.config['field_pattern_do_not_want'], discard)]

        # Add required fieldnames.
        self.config['standard_fields'].reverse()
        for standard_field in self.config['standard_fields']:
            filtered_field_list.insert(0, standard_field)
        fields_param = ','.join(filtered_field_list)

        # Get the populated CSV from Solr, with the object namespace and field list filters applied.
        return f"{self.config['solr_base_url']}/select?q=PID:{self.config['namespace']}*&wt=csv&rows=1000000&fl={fields_param}"
