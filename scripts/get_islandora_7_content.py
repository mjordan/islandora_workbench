#!/usr/bin/env python3

'''Script for exporting Islandora 7 content (metadata and OBJ datastreams). See
   https://mjordan.github.io/islandora_workbench_docs/exporting_islandora_7_content/
   for more info.
'''

import os
import re
import requests
import mimetypes
import logging
from progress_bar import InitBar

############################
# Configuration variables. #
############################

# Change to False to only fetch CSV metadata.
fetch_files = True

# URLs, paths, etc.
solr_base_url = 'http://localhost:8080/solr'
islandora_base_url = 'http://localhost:8000'
csv_output_path = 'islandora7_metadata.csv'
# Will be created if it doesn't exist.
obj_directory = '/tmp/objs'
log_file_path = 'islandora_content.log'

# Solr filter criteria. 'namespace' allows you to limit the metadata retrieved
# from Solr to be limtited to objects with a specific namespace (or namespaces
# if multiple namespaces start with the same characters). Valid values for the
# 'namespace' variabe are a single namespace, a right-truncated string (e.g., island*),
# or an ansterisk (*).
namespace = 'testing'
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

##############
# Functions. #
##############

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

def get_child_sequence_number(pid):
    '''For a given Islandora 7.x PID, get the object's sequence number in relation
       to its parent from the RELS-EXT datastream. Assumes child objects are only
       children of a single parent.
    '''
    rels_ext_url = islandora_base_url + '/islandora/object/' + pid + '/datastream/RELS-EXT/download'
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

#######################
# Main program logic. #
#######################

logging.basicConfig(
    filename=log_file_path,
    level=logging.INFO,
    filemode='a',
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%d-%b-%y %H:%M:%S')

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

# Get the populated CSV from Solr, with the object namespace and field list filters applied.
metadata_solr_request = solr_base_url + '/select?q=PID:' + namespace + '*&wt=csv&rows=1000000&fl=' + fields_param
try:
    metadata_solr_response = requests.get(url=metadata_solr_request, allow_redirects=True)
except requests.exceptions.RequestException as e:
    raise SystemExit(e)

csv_output = list()
rows = metadata_solr_response.content.decode().splitlines()
# We add a 'sequence' column to store the Islandora 7.x property "isSequenceNumberOfxxx"/"isSequenceNumber".
rows[0] = 'file,' + rows[0] + ',sequence'

if fetch_files is True:
    if not os.path.exists(obj_directory):
	    os.makedirs(obj_directory)

row_count = 0
pbar = InitBar()
csv_header_row = rows.pop(0)
num_csv_rows = len(rows)
for row in rows:
    pid = row.split(',')[0]
    sequence_number = get_child_sequence_number(pid)
    row = row + ',' + str(sequence_number)
    if fetch_files is True:
        obj_url = islandora_base_url + '/islandora/object/' + pid + '/datastream/OBJ/download'
        row_count += 1
        row_position = get_percentage(row_count, num_csv_rows)
        pbar(row_position)
        try:
            obj_download_response = requests.get(url=obj_url, allow_redirects=True)
            if obj_download_response.status_code == 200:
	            # Get MIMETYPE from 'Content-Type' header
	            obj_mimetype = obj_download_response.headers['content-type']
	            obj_extension = get_extension_from_mimetype(obj_mimetype)
	            obj_filename = pid.replace(':', '_')
	            obj_basename = obj_filename + obj_extension
	            # Save to file with name based on PID and extension based on MIMETYPE
	            obj_file_path = os.path.join(obj_directory, obj_basename)
	            open(obj_file_path, 'wb+').write(obj_download_response.content)
	            row = obj_basename + ',' + row
            if obj_download_response.status_code == 404:
                logging.warning(obj_url + " not found.")
        except requests.exceptions.RequestException as e:
            logging.info(e)
            continue
    else:
        # If we're not fetching files, add an empty 'file' column.
        row = ',' + row
    csv_output.append(row)

csv_output.insert(0, csv_header_row)

# Write the CSV file.
csv_fileh = open(csv_output_path, 'w+')
csv_fileh.write("\n".join(csv_output))
csv_fileh.close()
pbar(100)
