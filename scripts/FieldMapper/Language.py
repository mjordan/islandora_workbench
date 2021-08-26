


# Fields in Repository Content Object represented in this class
# field_language
#

class Language:

    def __init__(self):
        self.drupal_fieldnames = {'language': 'field_language'}
        self.mods_xpaths = {'language': 'mods/language'}
        self.dc_designators = {'language': 'dc.language'}
        self.language = ''


# date created

def set_language(self, language):
    if isinstance(language, str) and language != '':
        self.language = language


def get_language(self):
    return self.language


def get_language_fieldname(self):
    return self.drupalfieldnames['language']


