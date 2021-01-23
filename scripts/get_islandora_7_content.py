#!/usr/bin/env python3

'''Proof of concept script for https://github.com/mjordan/islandora_workbench/issues/209.
'''

import os
import re
import requests

solr_base_url = 'http://localhost:8080/solr'
islandora_base_url = 'http://localhost:8000'
csv_output_path = 'islandora7_metadata.csv'
# Must exist.
obj_directory = '/tmp/objs'


# Functions.

def get_extension_from_mimetype(mimetype):
	map = {'image/jpeg': 'jpg',
	       'image/jp2': 'jp2',
	       'application/pdf': 'pdf',
	       'image/png': 'png'
	}
	if mimetype in map:
		return map[mimetype]
	else:
		return 'unknown'


# Main program logic.

# This query gets all fields in the index. Does not need to be user-configurable.
fields_solr_query = '/select?q=*:*&wt=csv&rows=0&fl=*'
fields_solr_request = solr_base_url + fields_solr_query

# Get field list from Solr.
field_list_response = requests.get(url=fields_solr_request, allow_redirects=True)
raw_field_list = field_list_response.content.decode()

# Filter field list down to field names that start with mods_ and end with _s or _ms.
# Configuring this query needs to be well documented.
field_list = raw_field_list.split(',')
filtered_field_list = [f for f in field_list if re.search('mods_.*(_s|_ms)$', f)]

# Insert some fields we always want in th results into the fields list.
# @todo: Add compound properties.
standard_fields = ['RELS_EXT_isMemberOfCollection_uri_ms', 'RELS_EXT_hasModel_uri_s', 'PID']
for standard_field in standard_fields:
    filtered_field_list.insert(0, standard_field)
fields_param = ','.join(filtered_field_list)

# Get the populated CSV from Solr. In this example, we include namespace in the query to
# only retrieve metadata from objects with that namespace. Configuring this query needs
# to be well documented.
namespace = 'islandora'
metadata_solr_request = solr_base_url + '/select?q=PID:' + namespace + '*&wt=csv&rows=1000000&fl=' + fields_param
metadata_solr_response = requests.get(url=metadata_solr_request, allow_redirects=True)

csv_with_filenames = list()
filtered_field_list.insert(0, 'file')
csv_header_row = ','.join(filtered_field_list)
csv_with_filenames.append(csv_header_row)

rows = metadata_solr_response.content.decode().splitlines()

for row in rows:
	pid = row.split(',')[0]
	obj_url = islandora_base_url + '/islandora/object/' + pid + '/datastream/OBJ/download'
	obj_download_response = requests.get(url=obj_url, allow_redirects=True)
	if obj_download_response.status_code == 200:
		# Get MIMETYPE from 'Content-Type' header
		obj_mimetype = obj_download_response.headers['content-type']
		obj_extension = get_extension_from_mimetype(obj_mimetype)
		obj_filename = pid.replace(':', '_')
		obj_basename = obj_filename + '.' + obj_extension
		# Save to file with name based on PID and extension based on MIMETYPE
		obj_file_path = os.path.join(obj_directory, obj_basename)
		open(obj_file_path, 'wb+').write(obj_download_response.content)
		row_with_pid = obj_basename + ',' + row
		csv_with_filenames.append(row_with_pid)

# Write the CSV file.
csv_fileh = open(csv_output_path, 'w+')
csv_fileh.write("\n".join(csv_with_filenames))
csv_fileh.close()