
# In Islandora 8 maps to Repository Item Content Type -> field_resource_type field
# The field_resource_type field is a pointer to the Resource Types taxonomy
#

class ResourceType:

    def __init__(self):

        self.drupal_fieldname = 'field_resource_type'
        self.islandora_taxonomy = 'Resource Types'
        self.mods_xpath = 'mods/typeOfResource'
        self.dc_designator = 'type'

    def set_resourcetype(self, resourcetype):

        if isinstance(resourcetype, str) and resourcetype != '':
            self.resourcetype = resourcetype

    def get_resourcetype(self):

        return self.resourcetype

    def get_resourcetype_fieldname(self):

        return self.drupal_fieldname
