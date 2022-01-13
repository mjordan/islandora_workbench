#!/usr/bin/env python3

'''Script for exporting Islandora 7 content (metadata and OBJ datastreams). See
   https://mjordan.github.io/islandora_workbench_docs/exporting_islandora_7_content/
   for more info.
'''

import os
import re
import requests
import logging
import argparse
from progress_bar import InitBar
from i7ImportUtilities import i7ImportUtilities
import csv

############################
# Configuration variables. #
############################

parser = argparse.ArgumentParser()
parser.add_argument('--config', required=True, help='Configuration file to use.')
args = parser.parse_args()
config = args.config
utils = i7ImportUtilities(config)
config = utils.config

#######################
# Main program logic. #
#######################

logging.basicConfig(
    filename=config['log_file_path'],
    level=logging.INFO,
    filemode='a',
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%d-%b-%y %H:%M:%S')

# This query gets all fields in the index. Does not need to be user-configurable.
fields_solr_query = '/select?q=*:*&wt=csv&rows=0&fl=*'
fields_solr_url = config['solr_base_url'] + fields_solr_query

# Get the complete field list from Solr and filter it. The filtered field list is
# then used in another query to get the populated CSV data.
try:
    field_list_response = requests.get(url=fields_solr_url, allow_redirects=True)
    raw_field_list = field_list_response.content.decode()
except requests.exceptions.RequestException as e:
    raise SystemExit(e)

field_list = raw_field_list.split(',')
filtered_field_list = [keep for keep in field_list if re.search(config['field_pattern'], keep)]
filtered_field_list = [discard for discard in filtered_field_list if
                       not re.search(config['field_pattern_do_not_want'], discard)]

# Add required fieldnames.
config['standard_fields'].reverse()
for standard_field in config['standard_fields']:
    filtered_field_list.insert(0, standard_field)
fields_param = ','.join(filtered_field_list)

# Get the populated CSV from Solr, with the object namespace and field list filters applied.
metadata_solr_request = f"{config['solr_base_url']}/select?q=PID:{config['namespace']}*&wt=csv&rows=1000000&fl={fields_param}"
try:
    metadata_solr_response = requests.get(url=metadata_solr_request, allow_redirects=True)
except requests.exceptions.RequestException as e:
    raise SystemExit(e)

rows = metadata_solr_response.content.decode().splitlines()
reader = csv.DictReader(rows)
headers = reader.fieldnames
# We add a 'sequence' column to store the Islandora 7.x property "isSequenceNumberOfxxx"/"isSequenceNumber".
headers.append('sequence')
# Add a column to store the files
headers.append('file')
if config['id_field'] not in headers:
    headers.append(config['id_field'])
    index = config['id_start_number']

if config['fetch_files'] is True:
    if not os.path.exists(config['obj_directory']):
        os.makedirs(config['obj_directory'])

row_count = 0
pbar = InitBar()
num_csv_rows = len(rows)
with open(config['csv_output_path'], 'w', newline='') as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=headers)
    writer.writeheader()
    for row in reader:
        rels_ext = utils.parse_rels_ext(row['PID'])
        for key,value in rels_ext.items():
            if 'isSequenceNumber' in key:
                row['sequence'] = str(value)
        if config['fetch_files'] is True:
            obj_url = f"{config['islandora_base_url']}/islandora/object/{row['PID']}/datastream/OBJ/download"
            row_count += 1
            row_position = utils.get_percentage(row_count, num_csv_rows)
            pbar(row_position)
            try:
                obj_download_response = requests.get(url=obj_url, allow_redirects=True)
                if obj_download_response.status_code == 200:
                    # Get MIMETYPE from 'Content-Type' header
                    obj_mimetype = obj_download_response.headers['content-type']
                    obj_extension = utils.get_extension_from_mimetype(obj_mimetype)
                    obj_filename = row['PID'].replace(':', '_')
                    obj_basename = obj_filename + obj_extension
                    # Save to file with name based on PID and extension based on MIMETYPE
                    obj_file_path = os.path.join(config['obj_directory'], obj_basename)
                    open(obj_file_path, 'wb+').write(obj_download_response.content)
                    row['file'] = obj_basename
                if obj_download_response.status_code == 404:
                    logging.warning(f"{obj_url} not found.")

            except requests.exceptions.RequestException as e:
                logging.info(e)
                continue

            if config['id_field'] in headers:
                row[config['id_field']] = index + reader.line_num - 2
            writer.writerow(row)

pbar(100)
