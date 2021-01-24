#!/usr/bin/env python3

'''Script for https://github.com/mjordan/islandora_workbench/issues/209.
'''

import os
import re
import requests
import mimetypes
from progress_bar import InitBar


# Change to False to only fetch CSV metadata.
fetch_files = True

# URLs, paths, etc.
solr_base_url = 'http://localhost:8080/solr'
islandora_base_url = 'http://localhost:8000'
csv_output_path = 'islandora7_metadata.csv'
# Will be created if it doesn't exist.
obj_directory = '/tmp/objs'

# Solr filter criteria. 'namespace' allows you to limit the metadata retrieved
# from Solr to be limtited to objects with a specific namespace (or namespaces
# if multiple namespaces start with the same characters). Valid valudes for the
# 'namespace' varialbe are a single namespace, a right-truncated string (island*),
# or an ansterisk (*).
namespace = 'islandora'
# 'field_pattern' is a regex pattern that matches Solr field names to include in the
# CSV. For example,  'mods_.*(_s|_ms)$' will include fields that start with mods_ and
# end with _s or _ms.
field_pattern = 'mods_.*(_s|_ms)$'
# 'field_pattern_do_not_want' is a negative regex pattern that matches Solr field names
# to not include in the CSV. For example, '(SFU_custom_metadata|marcrelator)' will remove
# fieldnames that contain 'SFU_custom_metadata' or the string 'marcrelator.
field_pattern_do_not_want = '(SFU_custom_metadata|marcrelator)'
# 'standard_fields' is a list of fieldnames we always want in fields list. They are
# added added to the field list after list is filtered down using 'field_pattern'.
# @todo: Add compound properties.
standard_fields = ['RELS_EXT_isMemberOfCollection_uri_ms', 'RELS_EXT_hasModel_uri_s', 'PID']


# Functions.

def get_extension_from_mimetype(mimetype):
    # @todo: add_type() is not working, e.g. mimetypes.add_type('image/jpeg', '.jpg')
    # Maybe related to https://bugs.python.org/issue4963? In the meantime, provide our
    # own MIMETYPE to extension mapping for commone types, then let Python guess at others.
    map = {'image/jpeg': '.jpg',
        'image/jp2': '.jp2',
        'image/png': '.png'
    }
    if mimetype in map:
        return map[mimetype]
    else:
        return mimetypes.guess_extension(mimetype)

def get_percentage(part, whole):
    return 100 * float(part) / float(whole)


# Main program logic.

# This query gets all fields in the index. Does not need to be user-configurable.
fields_solr_query = '/select?q=*:*&wt=csv&rows=0&fl=*'
fields_solr_request = solr_base_url + fields_solr_query

# Get field list from Solr, filter it. The field list is then used in the query
# to Solr to get the CSV data from Solr.
field_list_response = requests.get(url=fields_solr_request, allow_redirects=True)
raw_field_list = field_list_response.content.decode()

field_list = raw_field_list.split(',')
filtered_field_list = [keep for keep in field_list if re.search(field_pattern, keep)]
filtered_field_list = [discard for discard in filtered_field_list if not re.search(field_pattern_do_not_want, discard)]

for standard_field in standard_fields:
    filtered_field_list.insert(0, standard_field)
fields_param = ','.join(filtered_field_list)

# Get the populated CSV from Solr, with the object namespace and field list filters applied.
metadata_solr_request = solr_base_url + '/select?q=PID:' + namespace + '*&wt=csv&rows=1000000&fl=' + fields_param
metadata_solr_response = requests.get(url=metadata_solr_request, allow_redirects=True)

csv_output = list()
# csv_header_row = ','.join(filtered_field_list)
rows = metadata_solr_response.content.decode().splitlines()
rows[0] = 'file,' + rows[0]

if fetch_files is True:
    if not os.path.exists(obj_directory):
	    os.makedirs(obj_directory)

# @todo: Add exception handling for requests, log problems.
row_count = 0
pbar = InitBar()
csv_header_row = rows.pop(0)
num_csv_rows = len(rows)
for row in rows:
    pid = row.split(',')[0]
    if fetch_files is True:
        obj_url = islandora_base_url + '/islandora/object/' + pid + '/datastream/OBJ/download'
        row_count += 1
        row_position = get_percentage(row_count, num_csv_rows)
        pbar(row_position)
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
    else:
        # If we're not fetching files, add an empty file' column.
        row = ',' + row
    csv_output.append(row)

csv_output.insert(0, csv_header_row)

# Write the CSV file.
csv_fileh = open(csv_output_path, 'w+')
csv_fileh.write("\n".join(csv_output))
csv_fileh.close()
pbar(100)