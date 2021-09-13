


###
# Map MODS fields to Islandora 8 content type fields
#
#
##
from FieldMapper.Agent import Agent
from FieldMapper.ResourceType import ResourceType
from FieldMapper.Genre import Genre
from FieldMapper.OriginInfo import OriginInfo
from FieldMapper.Language import Language
from FieldMapper.PhysicalDescription import PhysicalDescription
from FieldMapper.Description import Description
from FieldMapper.Note import Note
from FieldMapper.Model import Model
from FieldMapper.MemberOf import MemberOf
from FieldMapper.Subject import Subject
from FieldMapper.Identifier import Identifier
from FieldMapper.Date import Date

class FieldMapper:

    def __init__(self):
        self.rowdata = {}
        self.xmlfile = ''
        self.tree = ''
        self.title =''
        self.title_field_name = 'title'
        self.campus_code = ''
        self.approved_campus_codes = ['mu','umkc','umkclaw','umsl']
        self.description = ''
        #self.agent = ''
        #self.agent_field_name = ''
        self.resourcetype = ResourceType()
        self.agent = Agent()
        self.genre = Genre()
        self.origin_info = OriginInfo()
        self.language = Language()
        self.physicalDescription = PhysicalDescription()
        self.abstract = Description()
        self.note = Note()
        self.model = Model()
        self.memberof = MemberOf()
        self.subject = Subject()
        self.identifier = Identifier()
        self.csv_header_row_mappings = {}
        self.csv_header_row = []
        self.displayhint_field_headerposition = ''
        self.date = Date()
        self.classification = Classification()


    def set_displayhintfield_csvheaderposition(self):

        key_list = list(self.csv_header_row_mappings)
        keys_of_interest = ['display_hints']

        for key in keys_of_interest:

            display_hint_array_position = key_list.index(key)


        self.displayhint_field_headerposition = display_hint_array_position + 1


    def get_displayhintfield_csvheaderposition(self):

        return self.displayhint_field_headerposition

    def add_csv_header_row_mapping(self, key, value):

        self.csv_header_row_mappings[key] = value

    # add mappings of fields either to the beginning or end of the field dictionary

    def update_csv_header_row_mapping(self, fields_to_add, position):

          if position == 'prepend':

            fields_to_add.update(self.csv_header_row_mappings)
            self.csv_header_row_mappings = fields_to_add

          elif position == "append":

            self.csv_header_row_mappings.update(fields_to_add)


    def get_csvheader_row_map(self):

        print(self.csv_header_row_mappings)

    def set_title(self, title):
        if isinstance(str, title) and title != '':
            self.title = title

    def get_title(self):

        return self.title

    def check_titlelength(self,title):

        if isinstance(str, title) and title != '' and len(title) > 255:
            return "The title exceeds 255 characters in length. Migration of this " \
               "record into Drupal will fail unless the title is shortened"

    def set_campuscode(self, campus_code):

        if isinstance(campus_code, str) and campus_code != '':
            self.campus_code = campus_code

    def get_campuscode(self):

        return self.campus_code

    def set_titlefieldname(self,source_field_name):

        if source_field_name == 'mods_titleInfo_title_ms' or source_field_name == 'dc.title':
            return self.title_field_name

    def get_titlefieldname(self):

        return self.title_field_name

    def set_agent(self, agent):

        if isinstance(agent, str) and agent != '':
            self.agent = agent

    def get_agent(self):

        return self.agent

    def get_agentfieldname(self):

        return self.agent_field_name

    def set_agentfieldname(self, source_field_name):

        if isinstance(source_field_name, str) and source_field_name != '':
            self.agent_field_name = source_field_name

    def set_subjects(self, subject_values):

        if isinstance(subject_values, dict) and len(subject_values) > 0:
            subject = Subject()
            subject.subject_topic = subject_values['subject_topic']
            subject.geographic_subject = subject_values['geographic_subject']
            subject.subject_name = subject_values['subject_name']
            subject.subject_temporal = subject_values['subject_temporal']

    def get_subjects(self):

        return self.subject

    def get_subjectfieldnames(self):

        subject = Subject()
        return subject.drupal_fieldnames

    def get_modelfieldname(self):

        model = Model()
        return model.get_model_fieldname()

    def get_descriptionfieldname(self):

        description = Description()
        return description.get_description_fieldname()

    def get_genrefieldname(self):

        genre = Genre()
        return genre.get_genre_fieldname()

    def get_identifierfieldname(self):

        identifier = Identifier()
        return identifier.get_identifier_fieldname()

    def get_identifierlocalfieldname(self):

        identifier = Identifier()
        return identifier.get_identifier_local_fieldname()

    def get_dcdatefieldname(self):

        dc_date = Date()
        return dc_date.get_date_fieldname()

    def get_dateissuedfieldname(self):

        origin_info = OriginInfo()
        return origin_info.get_dateissued_fieldname()

    def get_datecreatedfieldname(self):

        origin_info = OriginInfo()
        return origin_info.get_datecreated_fieldname()

    def get_publisherfieldname(self):

        origin_info = OriginInfo()
        return origin_info.get_publisher_fieldname()

    def get_placepublishedfieldname(self):

        origin_info = OriginInfo()
        return origin_info.get_place_published_fieldname()

    def get_editionfieldname(self):

        origin_info = OriginInfo()
        return origin_info.get_edition_fieldname()

    def get_resourcetypefieldname(self):

        resource_type = ResourceType()
        return resource_type.get_resourcetype_fieldname()

    def get_languagefieldname(self):

        language = Language()
        return language.get_language_fieldname()

    def get_memberoffieldname(self):

        member_of = MemberOf()
        return member_of.get_memberoffieldname()

    def get_notefieldname(self):

        note = Note()
        return note.get_note_fieldname()

    #gets extent fieldname from Physical Description object
    def get_extentfieldname(self):

        physical_description = PhysicalDescription()
        return physical_description.get_extent_fieldname()

    def get_subject_topic_fieldname(self):

        subject = Subject()
        return subject.getsubject_topic_fieldname()

    def get_subject_geographic_fieldname(self):

        subject = Subject()
        return subject.getsubject_geographic_fieldname()


    def get_subject_temporal_fieldname(self):

        subject = Subject()
        return subject.getsubject_temporal_fieldname()

    def get_physicalform_fieldname(self):

        physical_description = PhysicalDescription()
        return physical_description.get_format_fieldname()

    def get_edtf_date_fieldname(self):

        resource_date = Date()
        return resource_date.get_edtfdate_fieldname()

    def get_classification_fieldname(self):

        classification = Classification()
        return classification.get_classification_fieldname()

    def get_cartographic_coordinates_fieldname(self):

        subject = Subject()
        return subject.get_cartographic_coordinates_fieldname()

