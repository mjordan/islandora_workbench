#!/usr/bin/env python3

'''Proof of concept script for https://github.com/mjordan/islandora_workbench/issues/209.
'''

import re
import requests


solr_base_url = 'http://localhost:8080/solr'

# This query gets all fields in the index.
fields_solr_query = '/select?q=*:*&wt=csv&rows=0&fl=*'
fields_solr_request = solr_base_url + fields_solr_query

# Get field list from Solr.
field_list_response = requests.get(url=fields_solr_request, allow_redirects=True)
raw_field_list = field_list_response.content.decode()

# Filter field list down to field names that start with mods_ and end with _s or _ms.
field_list = raw_field_list.split(',')
filtered_field_list = [f for f in field_list if re.search('mods_.*(_s|_ms)$', f)]
# Insert PID into the fields list.
filtered_field_list.insert(0, 'PID')
fields_param = ','.join(filtered_field_list)

# Get the populated CSV from Solr. In this example, we include namespace in the query to
# only retrieve metadata from objects with that namespace.
namespace = 'islandora'
metadata_solr_request = solr_base_url + '/select?q=PID:' + namespace + '*&wt=csv&rows=1000000&fl=' + fields_param
metadata_solr_response = requests.get(url=metadata_solr_request, allow_redirects=True)

# Write the CSV file.
csv_file = open('i7_metadata.csv', 'w+')
csv_file.write(metadata_solr_response.content.decode())
csv_file.close()

# @todo: Fetch each object's OBJ (or equivalent) and save it using the PID.
