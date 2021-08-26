

# field_subject on islandora 8 is configured to map to the following vocabs: Corporate, Family, Geographic Location,
# Person, Subject

class MemberOf:

    def __init__(self):

        self.drupal_fieldnames = {'memberof': 'field_member_of'}
        self.memberof = 'Repository Item'

    def getmemberof(self):

        return self.memberof

