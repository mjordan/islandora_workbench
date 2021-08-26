

# Fields in Repository Content Object represented in this class
# field_edtf_date_created, field_edtf_date_issued, field_publisher, field_place_published, field_edition
#

class OriginInfo:

    def __init__(self):
        self.drupal_fieldnames = {'dateCreated': 'field_edtf_date_created', 'dateIssued': 'field_edtf_date_issued', 'publisher': 'field_publisher', 'place_published': 'field_place_published', 'edition': 'field_edition'}
        self.mods_xpaths = {'dateIssued': 'mods/OriginInfo/dateIssued', 'dateCreated': 'mods/OriginInfo/dateCreated', 'publisher': 'mods/OriginInfo/publisher', 'placeTerm': 'mods/originInfo/place/placeTerm'}
        self.dc_designators = {'dateIssued': 'dc.issued', 'dateCreated': 'dc.created', 'publisher': 'relators:pbl', 'placeTerm': 'relators:pup'}
        self.date_created = ''
        self.date_created_fieldname = ''
        self.date_issued = ''
        self.date_issued_fieldname = ''
        self.publisher = ''
        self.publisher_fieldname = ''
        self.place_published = ''
        self.place_published_fieldname = ''
        self.edition = ''
        self.edition_fieldname = ''

# date created

    def set_datecreated(self, datecreated):

        if isinstance(datecreated, str) and datecreated != '':
            self.date_created = datecreated

    def get_datecreated(self):

        return self.date_created

    def set_datecreated_fieldname(self):

        self.datecreated_fieldname = self.drupalfieldnames['dateCreated']

    def get_datecreated_fieldname(self):

        return self.datecreated_fieldname

    def set_dateissued(self, dateissued):

        if isinstance(dateissued, str) and dateissued != '':
            self.date_issued = dateissued

    def get_dateissued(self):

        return self.date_issued

    def set_dateissued_fieldname(self):

        self.dateissued_fieldname = self.drupalfieldnames['dateIssued']

    def get_dateissued_fieldname(self):

        return self.dateissued_fieldname

    def set_publisher(self, publisher):

        if isinstance(publisher, str) and publisher != '':
            self.publisher = publisher

    def get_publisher(self):

        return self.publisher

    def set_publisher_fieldname(self):

        self.publisher_fieldname =  self.drupalfieldnames['publisher']

    def get_publisher_fieldname(self):

        return self.publisher_fieldname

    def set_place_published(self, place_published):

        if isinstance(place_published, str) and place_published != '':
            self.place_published = place_published

    def get_place_published(self):

        return self.place_published

    def set_place_published_fieldname(self):

        self.place_published_fieldname = self.drupalfieldnames['place_published']

    def get_place_published_fieldname(self):

        return self.place_published_fieldname

    def set_edition(self, edition):

        if isinstance(edition, str) and edition != '':
            self.edition = edition

    def get_edition(self):
        return self.edition

    def set_edition_fieldname(self):
        self.edition_fieldname = self.drupalfieldnames['edition']

    def get_edition_fieldname(self):
        return self.edition_fieldname

