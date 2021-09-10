#!/usr/bin/env python3

'''Script for exporting Islandora 7 content (metadata and OBJ datastreams). See
   https://mjordan.github.io/islandora_workbench_docs/exporting_islandora_7_content/
   for more info.
'''

import os
import config
import re
import requests
from requests.auth import HTTPBasicAuth
import mimetypes
import logging
import urllib3
import urllib.parse
from FieldMapper.FieldMapper import FieldMapper
#from FieldTransformer.FieldValueTransformer import FieldValueTransformer
from requests_futures.sessions import FuturesSession
from progress_bar import InitBar
from MultiPageMedia import MultiPageMedia

############################
# Configuration variables. #
############################

# Change to False to only fetch CSV metadata.
fetch_files = True

#starting unique identifier
starting_unique_id = 1

# URLs, paths, etc.
solr_base_url = 'http://128.206.4.208:8080/solr42/collection1'
islandora_base_url = 'https://dl.mospace.umsystem.edu/'
csv_output_path = '/home/borwickja/PhpstormProjects/islandoraworkbench/islandora_workbench/input_data/metadata.csv'
# Will be created if it doesn't exist.
#obj_directory = '/tmp/objs'
obj_directory = '/home/borwickja/PhpstormProjects/islandoraworkbench/islandora_workbench/input_data'
log_file_path = 'islandora_content.log'
field_mapper = FieldMapper()
#field_value_transformer = FieldValueTransformer()
# Solr filter criteria. 'namespace' allows you to limit the metadata retrieved
# from Solr to be limtited to objects with a specific namespace (or namespaces
# if multiple namespaces start with the same characters). Valid values for the
# 'namespace' variabe are a single namespace, a right-truncated string (e.g., island*),
# or an ansterisk (*).
#namespace = 'testing'
namespace = 'mu'
# 'field_pattern' is a regex pattern that matches Solr field names to include in the
# CSV. For example,  'mods_.*(_s|_ms)$' will include fields that start with mods_ and
# end with _s or _ms.
field_pattern = 'mods_.*(_s|_ms)$'
# 'field_pattern_do_not_want' is a regex pattern that matches Solr field names
# to not include in the CSV. For example, '(SFU_custom_metadata|marcrelator)' will remove
# fieldnames that contain 'SFU_custom_metadata' or the string 'marcrelator.
field_pattern_do_not_want = '(SFU_custom_metadata|marcrelator|isSequenceNumberOf)'
# 'standard_fields' is a list of fieldnames we always want in fields list. They are
# added added to the field list after list is filtered down using 'field_pattern'.
# Columns for these fields will appear at the start of the CSV.
standard_fields = ['PID', 'RELS_EXT_hasModel_uri_s', 'RELS_EXT_isMemberOfCollection_uri_ms', 'RELS_EXT_isConstituentOf_uri_ms', 'RELS_EXT_isPageOf_uri_ms']

displayhint_csvheaderposition = ''



multipage_file_list = {}
multipage_pid_list = []

##############
# Functions. #
##############

def addStandardFields(modsfields_list):

    fields_param = standard_fields + modsfields_list
    return fields_param

def add_displayhintsfield():

    custom_field = ['displayhint']


#function added by Jim Borwick to get around the mongo SOLR query for all fields
def getFieldListFromFile():
    #bypasses part of main program logic, some of which isn't encapsulated in functions
    #might think about rewriting
    if os.path.exists('/home/borwickja/PycharmProjects/parseIslandoraCSV/umkclaw_modsfields_sorted.txt'):
        filehandle =  open('/home/borwickja/PycharmProjects/parseIslandoraCSV/umkclaw_modsfields_sorted.txt','r')
        modsfields_list = filehandle.readlines()
        stripped_modsfield_list = list(map(str.strip, modsfields_list))
        fields_param = addStandardFields(stripped_modsfield_list)
        return fields_param


def get_extension_from_mimetype(mimetype):
    # mimetypes.add_type() is not working, e.g. mimetypes.add_type('image/jpeg', '.jpg')
    # Maybe related to https://bugs.python.org/issue4963? In the meantime, provide our own
    # MIMETYPE to extension mapping for common types, then let mimetypes guess at others.
    map = {'image/jpeg': '.jpg',
           'image/jp2': '.jp2',
           'image/png': '.png'
           }
    if mimetype in map:
        return map[mimetype]
    else:
        return mimetypes.guess_extension(mimetype)

def get_child_pids_using_parent(pid):

    risearch_url = "http://128.206.4.208:8080/fedora/risearch?"
    preset_params = "type=tuples&lang=+sparql&format=CSV&limit=1000&dt=on&query="

    sparql_query = "select  ?o ?s from <#risearch> where { ?o <http://islandora.ca/ontology/relsext#isPageOf> <info:fedora/" + pid + "> ."+"\n"+" $o <http://islandora.ca/ontology/relsext#isPageNumber> ?s .  } ORDER BY ASC(?s)"
    sparql_query = urllib.parse.quote(sparql_query)
    request_uri = risearch_url + preset_params + sparql_query

    res = requests.post(request_uri, verify=False, auth=HTTPBasicAuth(config.username, config.password))
    sparql_query_results = res.text
    results_list = sparql_query_results.splitlines()


    clean_results_list = [child_pid.replace('info:fedora/', '') for child_pid in results_list]

    for item in clean_results_list:
        #
        rename_multipage_file(item)

def transform_pagenumber(page_number):


    if page_number <= 9:

        pn = "00"+str(page_number)


    elif page_number > 9 and page_number < 100:

        pn = "0"+str(page_number)

    else:

        pn = str(page_number)


    return pn



def rename_multipage_file(list_item):


    list_item_string = str(list_item)
    pid_pagenumber = list_item_string.split(',')
    pid = pid_pagenumber[0]
    pagenumber = pid_pagenumber[1]
    pnumber = " ".join(pagenumber.split())

    try:

        pnumber = int(pnumber)
        pn = transform_pagenumber(pnumber)
        filename_pid = pid.replace(':','_')
        filename = filename_pid + "-" + pn
        multipage_file_list[filename_pid] = filename


    except ValueError:

        print("This pagenumber is not numeric " + pnumber)




#     transformed_pagenumber = transform_pagenumber(pagenumber)
#     print(transformed_pagenumber)






#     pid_pagenumber = ','.split(list_item_string)
#     pagenumber = pid_pagenumber[1]
#     pid = pid_pagenumber[0]
#     print(pagenumber)




def get_child_sequence_number(pid):
    '''For a given Islandora 7.x PID, get the object's sequence number in relation
       to its parent from the RELS-EXT datastream. Assumes child objects are only
       children of a single parent.
    '''
    encoded_pid = pid.replace(':','%3A')
    rels_ext_url = islandora_base_url + 'islandora/object/' + encoded_pid + '/datastream/RELS-EXT/download'

    try:
        rels_ext_download_response = requests.get(url=rels_ext_url, allow_redirects=True)

        if rels_ext_download_response.status_code == 200:
            rels_ext_xml = rels_ext_download_response.content.decode()
            matches = re.findall('<(islandora:isPageOf|fedora:isConstituentOf)\s+rdf:resource="info:fedora/(.*)">', rels_ext_xml, re.MULTILINE)

            # matches contains tuples, but we only want the values from the second value in each tuple,
            # pids corresponding to the second set of () in the pattern.
            parent_pids = [pids[1] for pids in matches]
            if len(parent_pids) > 0:
                parent_pid = parent_pids[0].replace(':', '_')
                sequence_numbers = re.findall('<islandora:isSequenceNumberOf' + parent_pid + '>(\d+)', rels_ext_xml, re.MULTILINE)
                # Paged content stores sequence values in <islandora:isSequenceNumber>, so we look there
                # if we didn't get any in isSequenceNumberOfxxx.
                if len(sequence_numbers) == 0:
                    sequence_numbers = re.findall('<islandora:isSequenceNumber>(\d+)', rels_ext_xml, re.MULTILINE)
                if len(sequence_numbers) > 0:
                    return sequence_numbers[0]
                else:
                    logging.warning("Can't get sequence number for " + pid)
                    return ''
            else:
                logging.warning("Can't get parent PID for " + pid)
                return ''
    except requests.exceptions.RequestException as e:
        raise SystemExit(e)

def get_percentage(part, whole):
    return 100 * float(part) / float(whole)

def getFieldListFromSolr():
    # This query gets all fields in the index. Does not need to be user-configurable.
    fields_solr_query = '/select?q=*:*&wt=csv&rows=0&fl=*'
    fields_solr_url = solr_base_url + fields_solr_query
    # Get the complete field list from Solr and filter it. The filtered field list is
    # then used in another query to get the populated CSV data.
    try:
        field_list_response = requests.get(url=fields_solr_url, allow_redirects=True)
        raw_field_list = field_list_response.content.decode()
    except requests.exceptions.RequestException as e:
        raise SystemExit(e)

    field_list = raw_field_list.split(',')
    filtered_field_list = [keep for keep in field_list if re.search(field_pattern, keep)]
    filtered_field_list = [discard for discard in filtered_field_list if not re.search(field_pattern_do_not_want, discard)]

    # Add required fieldnames.
    standard_fields.reverse()
    for standard_field in standard_fields:
        filtered_field_list.insert(0, standard_field)
    fields_param = ','.join(filtered_field_list)

    return fields_param

def createSOLRRequest():

    return solr_base_url + '/select?q=PID:' + namespace + '*&wt=csv&rows=1000&fl=' + fields_param


def runSOLRRequest():

    try:
        metadata_solr_response = requests.get(url=metadata_solr_request, allow_redirects=True)
        print(metadata_solr_response)
        raise SystemExit(e)
    except requests.exceptions.RequestException as e:
        raise SystemExit(e)

def getpidcampusprefix(pid):

    pid_pieces = pid.split(':')
    return pid_pieces[0]


def getcampuscodefrompid(pid):

    campus_prefix = getpidcampusprefix(pid)
    print(campus_prefix)

    returnval = ''
    campus_codes = ['umkc','umkclaw','umsl','mu']
    for code in campus_codes:
        if campus_prefix == code:
            returnval = code
            break

    return returnval


def transformFields(row):

    print("Placeholder")


def fetch_multipagemediafiles(pids):

    #     for pid in pids:
    for pid in multipage_pid_list:

        campus_code = getcampuscodefrompid(pid)
        campus_code_pid = pid
        #     params = {value_to_encode}
        #     campus_code_params = urllib.parse.urlencode(params)
        print("campus_code is " + campus_code)
        print("pid is " + pid)
        encoded_pid = pid.replace(':','%3A')
        obj_url = islandora_base_url + campus_code + '/islandora/object/' + encoded_pid + '/datastream/OBJ/download'

        try:

            obj_download_response = requests.get(url=obj_url, allow_redirects=True)

            if obj_download_response.status_code == 200:

                # Get MIMETYPE from 'Content-Type' header
                obj_mimetype = obj_download_response.headers['content-type']
                obj_extension = get_extension_from_mimetype(obj_mimetype)
                obj_tmp_filename = pid.replace(':', '_')
                #                 obj_filename = multipage_file_list.get(obj_tmp_filename)

            obj_filename =  multipage_file_list.get(obj_tmp_filename)
            obj_basename = obj_filename + obj_extension
            #row = obj_basename + ',' + row
            # Save to file with name based on PID and extension based on MIMETYPE
            obj_file_path = os.path.join(obj_directory, obj_basename)
            open(obj_file_path, 'wb+').write(obj_download_response.content)

            if obj_download_response.status_code == 404:

                logging.warning(obj_url + " not found.")


        except requests.exceptions.RequestException as e:
            logging.info(e)
            continue


# def getFileNameToSaveToUsingPid(pid):






def getRequestStatus(requestObject):

    response_one = requestObject.result()
    print(response_one.status_code)
    if response_one.status_code != 200:
        print(response_one.status_code)
        getRequestStatus(requestObject)
    elif response_one.status_code == 200:
        return 'success'


#######################
# Main program logic. #
#######################

logging.basicConfig(
    filename=log_file_path,
    level=logging.INFO,
    filemode='a',
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%d-%b-%y %H:%M:%S')

fields_param = '%2C'.join(getFieldListFromFile())

#  commented out while fetching data
# mapSearchFieldsToCSVHeaderFields(fields_param)


# This query gets all fields in the index. Does not need to be user-configurable.
# fields_solr_query = '/select?q=*:*&wt=csv&rows=0&fl=*'
# fields_solr_url = solr_base_url + fields_solr_query



# Get the complete field list from Solr and filter it. The filtered field list is
# then used in another query to get the populated CSV data.
# try:
#     field_list_response = requests.get(url=fields_solr_url, allow_redirects=True)
#     raw_field_list = field_list_response.content.decode()
# except requests.exceptions.RequestException as e:
#     raise SystemExit(e)
#
# field_list = raw_field_list.split(',')
# filtered_field_list = [keep for keep in field_list if re.search(field_pattern, keep)]
# filtered_field_list = [discard for discard in filtered_field_list if not re.search(field_pattern_do_not_want, discard)]

# Add required fieldnames.
# standard_fields.reverse()
# for standard_field in standard_fields:
#     filtered_field_list.insert(0, standard_field)
# fields_param = ','.join(filtered_field_list)

# Get the populated CSV from Solr, with the object namespace and field list filters applied.
#metadata_solr_request = solr_base_url + '/select?q=PID:' + namespace + '*&wt=csv&rows=&fl=' + fields_param
#metadata_solr_request = solr_base_url + '/select?q=PID%3A' + namespace + '*&wt=csv&rows=&fl=' + fields_param
search_string = "%22An+account+of+upper+Louisiana%22"
metadata_solr_request = solr_base_url + '/select?q=dc.title%3A'+ search_string + '&fl=' + fields_param + '&wt=csv&indent=true'



try:
    metadata_solr_response = requests.get(url=metadata_solr_request, allow_redirects=True)
    print(metadata_solr_response)
except requests.exceptions.RequestException as e:
    raise SystemExit(e)

csv_output = list()
rows = metadata_solr_response.content.decode().splitlines()


# We add a 'sequence' column to store the Islandora 7.x property "isSequenceNumberOfxxx"/"isSequenceNumber".
rows[0] = 'id,' + 'file,' + rows[0] + ',sequence'
headers_fields = rows[0]

header_field_list = rows[0].split(',')


for index, field in enumerate(header_field_list):
    print(index, field)
    if field == 'mods_titleInfo_title_ms':
        header_field_list[index] = 'title'

rows[0] = ','.join(header_field_list)


if fetch_files is True:
    if not os.path.exists(obj_directory):
        os.makedirs(obj_directory)

row_count = 0
pbar = InitBar()
csv_header_row = rows.pop(0)
num_csv_rows = len(rows)

multipage_fetcher = MultiPageMedia()


for row in rows:
    pid = row.split(',')[0]
    campus_code = getcampuscodefrompid(pid)
    campus_code_pid = pid
    #     params = {value_to_encode}
    #     campus_code_params = urllib.parse.urlencode(params)
    print("campus_code is " + campus_code)
    print("pid is " + pid)
    encoded_pid = pid.replace(':','%3A')
    sequence_number = get_child_sequence_number(pid)
    multipage_fetcher.set_parent_pid(pid)
    #how is generating multipage docs for migration going to be wrapped into main code logic?

    is_string = isinstance(row,str)
    row = row + ',' + str(sequence_number)
    transformFields(row)

    if fetch_files is True:
        #obj_url = islandora_base_url + '/islandora/object/' + pid + '/datastream/OBJ/download'
        obj_url = islandora_base_url + campus_code + '/islandora/object/' + encoded_pid + '/datastream/OBJ/download'
        print(obj_url)

        row_count += 1
        row_position = get_percentage(row_count, num_csv_rows)
        pbar(row_position)
        try:
            #             session = FuturesSession()

            obj_download_response = requests.get(url=obj_url, allow_redirects=True)
            #             obj_download_response = session.get(url=obj_url, allow_redirects=True)
            #             if(obj_download_response.status_code != 200):
            #                 response = getRequestStatus(obj_download_response)

            if obj_download_response.status_code == 200:

                # Get MIMETYPE from 'Content-Type' header
                obj_mimetype = obj_download_response.headers['content-type']
                obj_extension = get_extension_from_mimetype(obj_mimetype)
                obj_filename = pid.replace(':', '_')
                obj_basename = obj_filename + obj_extension
                #row = obj_basename + ',' + row
                # Save to file with name based on PID and extension based on MIMETYPE
                obj_file_path = os.path.join(obj_directory, obj_basename)
                open(obj_file_path, 'wb+').write(obj_download_response.content)
                row = str(starting_unique_id) + ','+ obj_basename + ',' + row


            if obj_download_response.status_code == 404:
                row = str(starting_unique_id) + ',' + ',' + row
                logging.warning(obj_url + " not found.")
        except requests.exceptions.RequestException as e:
            logging.info(e)
            continue
    else:
        # If we're not fetching files, add an empty 'file' column.
        row = str(starting_unique_id) + ',' + ',' + row


    # before you output the row you need to add values
    # for non-search columns like field_display_hints




    csv_output.append(row)
    starting_unique_id = starting_unique_id + 1
csv_header_row.replace('mods_titleInfo_title_ms','title')
csv_output.insert(0, csv_header_row)

# Write the CSV file.
csv_fileh = open(csv_output_path, 'w+')
csv_fileh.write("\n".join(csv_output))
csv_fileh.close()
pbar(100)
multipage_fetcher.set_username(config.username)
multipage_fetcher.set_password(config.password)

multipage_fetcher.set_sparql_query()
multipage_fetcher.set_request_uri()
multipage_fetcher.request_data()
multipage_fetcher.parse_results()
multipage_fetcher.build_filename_lookup()
multipage_fetcher.get_pid_list()
multipage_fetcher.fetch_files()




