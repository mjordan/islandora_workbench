from ruamel.yaml import YAML
import mimetypes

class i7ImportUtilities:

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

    def get_config(self, config_location):
        yaml = YAML()
        config = self.default_config
        with open(config_location, 'r') as stream:
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
