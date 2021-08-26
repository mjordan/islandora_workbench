

# Fields in Repository Content Object represented in this class
# field_language
#

class Identifier:

    def __init__(self):
        self.drupal_fieldnames = {'identifier': 'field_identifier', 'identifier_local': 'field_local_identifier'}
        self.mods_xpaths = {'identifier': 'mods/identifier', 'identifier_local': 'mods/identifier_local_ms'}
        self.dc_designators = {'identifier': 'dc.identifier'}
        self.identifier = ''
        self.identifier_local = ''

    def set_identifier(self, identifier):
        if isinstance(identifier, str) and identifier != '':
            self.identifier = identifier

    def get_identifier(self):
        return self.identifier

    def get_identifier_fieldname(self):
        return self.drupal_fieldnames['identifier']


    def set_identifier_local(self, identifier_local):
        if isinstance(identifier_local, str) and identifier_local != '':
            self.identifier_local = identifier_local

    def get_identifier_local(self):
        return self.identifier_local

    def get_identifier_local_fieldname(self):
        return self.drupal_fieldnames['identifier_local']


