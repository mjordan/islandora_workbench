

class Model:

    #taxonomy terms in Islandora Models taxonomy not yet mapped to current Islandora 7 models
    # Binary, Compound Object, Digital Document, Page, Publication Issue

    def __init__(self):

        self.drupal_fieldnames = {'model': 'field_model'}
        self.mods_xpaths = {'model': 'RELS_EXT_hasModel_uri_ms'}
        self.dc_designators = {'model': ''}
        self.model = ''
        self.model_fieldname = ''

    def set_model(self, model):

        if isinstance(model, str) and model != '':
            self.model = model

    def get_model(self):
        return self.model

    def get_model_fieldname(self):
        return self.drupal_fieldnames['model']

    def translate_model_fieldname(self, model_string):

        if isinstance(model_string, str) and model_string != '':

            if model_string == 'info:fedora/islandora:sp_videoCModel':
                self.model = 'Video'
            elif model_string == 'info:fedora/islandora:sp-audioCModel':
                self.model = 'Audio'
            elif model_string == 'info:fedora/islandora:sp_basic_image' or model_string == 'info:fedora/islandora:sp_large_image_cmodel':
                self.model = 'Image'
            elif model_string == 'info:fedora/islandora:collectionCModel':
                self.model = 'Collection'
            elif model_string == 'info:fedora/islandora:newspaperCModel':
                self.model = 'Newspaper'
            elif model_string == 'info:fedora/islandora:bookCModel':
                self.model = 'Paged Content'

            return self.model

