


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

    def add_csv_header_row_mapping(self, key, value):

        self.csv_header_row_mappings[key] = value

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

