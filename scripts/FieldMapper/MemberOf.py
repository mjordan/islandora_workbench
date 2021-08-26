

# field_subject on islandora 8 is configured to map to the following vocabs: Corporate, Family, Geographic Location,
# Person, Subject

class MemberOf:

    def __init__(self):

        self.drupal_fieldnames = {'memberof': 'field_member_of'}
        self.memberof = 'Repository Item'

    def get_memberof(self):

        return self.memberof

    def get_memberoffieldname(self):

        return self.drupal_fieldnames['memberof']