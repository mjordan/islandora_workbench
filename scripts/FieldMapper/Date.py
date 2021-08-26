

# Fields in Repository Content Object represented in this class
# field_language
#

class Date:

    def __init__(self):
        self.drupal_fieldnames = {'date': 'field_date'}
        self.mods_xpaths = {'date': 'mods/date'}
        self.dc_designators = {'date': 'dc.date'}
        self.date = ''

    def set_date(self, date):
        if isinstance(date, str) and date != '':
            self.date = date

    def get_date(self):
        return self.date

    def get_date_fieldname(self):
        return self.drupal_fieldnames['date']



