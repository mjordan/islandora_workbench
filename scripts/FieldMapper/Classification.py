
class Classification:

    def __init__(self):
        self.drupal_fieldnames = {'classification': 'field_classification'}
        self.mods_xpaths = {'classification': 'mods/classification'}
        self.dc_designators = {'': 'dc.'}
        self.classification = ''

    def set_classification(self, classification):
        if isinstance(date, str) and date != '':
            self.classification = classification

    def get_classification(self):
        return self.classification

    def get_classification_fieldname(self):
        return self.drupal_fieldnames['classification']

