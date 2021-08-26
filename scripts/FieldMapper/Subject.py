

# field_subject on islandora 8 is configured to map to the following vocabs: Corporate, Family, Geographic Location,
# Person, Subject

class Subject:

    def __init__(self):

        self.drupal_fieldnames = {'subject_topic': 'field_subject', 'geographic_subject': 'field_geographic_subject',
                                  'subject_temporal': 'field_temporal_subject', 'subject_name': 'field_subjects_name'

                                  }
        # for the name subject you need to get attributes like personal, corporate, etc
        # for geographic_subject you'll need to grab mods for geographicCode and hierarchicalGeographic
        self.mods_xpaths = {'subject-topic': 'mods/subject/topic', 'subject_name': 'mods/subject/name', 'geographic_subject': 'mods/subject/geographicCode', 'subject_temporal': 'mods/subject/temporal'}
        self.dc_designators = {'subject-topic': 'dc.subject', 'subject_name': 'dc.subject', 'geographic_subject': 'dc.spatial', 'subject_temporal': 'dc.temporal'}
        self.subject_topic = ''
        self.geographic_subject = ''
        self.subject_temporal = ''
        self.subject_name = ''

    def setsubject_topic(self, subject_topic):

        if isinstance(subject_topic, str) and subject_topic != '':
            self.subject_topic = subject_topic

    def getsubject_topic(self):

        return self.subject_topic

    def getsubject_topic_fieldname(self):

        return self.drupal_fieldnames['subject_topic']

    def setsubject_geographic(self, subject_geographic):

        if isinstance(subject_geographic, str) and subject_geographic != '':
            self.subject_geographic = subject_geographic

    def getsubject_geographic(self):

        return self.subject_geographic

    def getsubject_geographic_fieldname(self):

        return self.drupal_fieldnames['subject_geographic']

    def setsubject_temporal(self, subject_temporal):

        if isinstance(subject_temporal, str) and subject_temporal != '':
            self.subject_temporal = subject_temporal

    def getsubject_temporal(self):

        return self.subject_temporal

    def getsubject_temporal_fieldname(self):

        return self.drupal_fieldnames['subject_temporal']

    def setsubject_name(self, subject_name):

        if isinstance(subject_name, str) and subject_name != '':
            self.subject_name = subject_name

    def getsubject_name(self):

        return self.subject_name

    def getsubject_name_fieldname(self):

        return self.drupal_fieldnames['subject_name']



