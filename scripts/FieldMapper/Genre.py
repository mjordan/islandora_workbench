
# In Islandora 8 maps to Repository Item Content Type -> field_resource_type field
# The field_resource_type field is a pointer to the Resource Types taxonomy
#

class Genre:

    def __init__(self):

        self.drupal_fieldname = 'field_genre'
        self.islandora_taxonomy = ['tags','genre']
        self.mods_xpath = 'mods/genre'
        self.dc_designator = 'type'
        self.genre = ''

    def set_genre(self, genre):

        if isinstance(genre, str) and genre != '':
            self.genre = genre

    def get_genre(self):

        return self.genre

    def get_genre_fieldname(self):

        return self.drupal_fieldname



