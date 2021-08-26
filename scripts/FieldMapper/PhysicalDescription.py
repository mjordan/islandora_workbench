

class PhysicalDescription:

    def __init__(self):

        self.drupal_fieldnames = {'form': 'field_physical_form', 'extent': 'field_extent'}
        self.mods_xpaths = {'form': 'mods/physicalDescription/form', 'extent': 'mods/physicalDescription/extent'}
        self.dc_designators = {'form': 'dc.format', 'extent': 'dc.extent'}
        self.format = ''
        self.format_fieldname = ''
        self.extent = ''
        self.extent_fieldname = ''

    def set_format(self, format):
        if isinstance(format, str) and format != '':
            self.format = format

    def get_format(self):

        return self.format

    def get_format_fieldname(self):

        return self.drupal_fieldnames['form']

    def set_extent(self, extent):

        if isinstance(extent, str) and extent != '':
            self.extent = extent

    def get_extent(self):

        return self.extent

    def get_extent_fieldname(self):

        return self.extent_fieldname

