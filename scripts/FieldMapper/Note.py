

class Note:

    def __init__(self):
        self.drupal_fieldnames = {'note': 'field_note'}
        self.mods_xpaths = {'note': 'mods/note'}
        self.dc_designators = {'note': 'skos.note'}
        self.note = ''
        self.note_fieldname = ''

        # date created

    def set_note(self, note):

        if isinstance(note, str) and note != '':
            self.note = note

    def get_description(self):

        return self.note

    def get_description_fieldname(self):
        return self.drupal_fieldnames

