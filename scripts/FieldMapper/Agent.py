
# person_name_fieldname maps to field_person in drupal, and that points to the Person vocabulary
# linked_agent_fieldname maps to field_linked_agent in drupal, and that points to several vocabularies - not sure how that one works
# not sure how role fits into all this

class Agent:

    def __init__(self):

        self.role = ''
        self.role_fieldname = ''

        self.person_name = ''
        self.person_name_fieldname = 'field_person'

        self.linked_agent = ''
        self.linked_agent_fieldname = 'field_linked_agent'

        self.predefined_roles = ['author', 'contributor']

    def set_person_name(self, person_name):

        if isinstance(person_name, str) and person_name != '':
            self.person_name = person_name

    def get_person_name(self):

        return self.person_name

    def get_person_name_fieldname(self):

        return self.person_name_fieldname

    def set_role(self, role):

        if isinstance(role, str) and role != '':
            self.role = role

    def get_role(self):

        return self.role

    def set_linked_agent(self, linked_agent):

        self.linked_agent = linked_agent

    def get_linked_agent(self):

        return self.linked_agent

    def get_linked_agent_fieldname(self):

        return self.linked_agent_fieldname

