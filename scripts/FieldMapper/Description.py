

class Description:

    def __init__(self):
        self.drupal_fieldnames = {'abstract': 'field_description'}
        self.mods_xpaths = {'abstract': 'mods/abstract_ms'}
        self.dc_designators = {'abstract': 'dc.abstract'}
        self.abstract = ''
        self.description_fieldname = ''

    def set_description(self, abstract):
        if isinstance(abstract, str) and abstract != '':
            self.abstract = abstract

    def get_description(self):
        return self.abstract

    def get_description_fieldname(self):
        return self.drupal_fieldnames['abstract']



