


class TitleInfo:

    def __init__(self):

        self.drupal_fieldnames = {'mods_titleInfo_title_alternative_ms':'field_alternative_title'}
        self.mods_xpath = 'mods/titleInfo/title'


    def set_titleinfo(self, titleinfo):

        if isinstance(titleinfo, str) and resourcetype != '':
            self.titleinfo = titleinfo

    def get_titleinfo(self):

        return self.titleinfo

    def get_titleInfo_alternative_title_fieldname(self):

        return self.drupal_fieldnames['mods_titleInfo_title_alternative_ms']




