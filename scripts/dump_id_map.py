'''Utility script to dump the CSV ID to Node ID map from its SQLite database,
   or to remove entries from the database prior to a provided timestamp.

   Usage: python dump_id_map.py --db_path csv_id_to_node_id_map.db --csv_path /tmp/test.csv
          python dump_id_map.py --db_path csv_id_to_node_id_map.db --remove_entries_before "2023-05-29 19:17"
'''

import os
import sys
import csv
import sqlite3
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--db_path', required=True, help='Relative or absolute path to the SQLite database file.')
parser.add_argument('--csv_path', help='Relative or absolute path to the output CSV file.')
parser.add_argument('--remove_entries_before', help='Relative or absolute path to the output CSV file.')
args = parser.parse_args()

if args.csv_path is None and args.remove_entries_before is None:
    sys.exit("You need to provide either the --csv_path or --remove_entries_before option.")

#######################################
# Check existence of specified files. #
#######################################

if os.path.isabs(args.db_path):
    db_path = args.db_path
else:
    db_path = os.path.join(os.getcwd(), args.db_path)
if not os.path.exists(db_path):
    message = f"Can't find SQLite database path ({os.path.abspath(db_path)}). Please confirm that it exsits."
    sys.exit('Error: ' + message)

if args.csv_path is not None:
    if os.path.isabs(args.csv_path):
        csv_path = args.csv_path
        csv_path_dir = os.path.dirname(csv_path)
    else:
        csv_path = os.path.join(os.getcwd(), args.csv_path)
        csv_path_dir = os.path.dirname(csv_path)
    if not os.path.exists(csv_path_dir):
        message = f"Can't find directory specified for output CSV file path ({csv_path_dir}). Please confirm that it exsits."
        sys.exit('Error: ' + message)

#########################################################
# Get contents of the db, then write them out to a CSV. #
#########################################################

if args.csv_path is not None:
    try:
        query = "select * from csv_id_to_node_id_map"
        con = sqlite3.connect(db_path)
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        res = cur.execute(query, ()).fetchall()
        con.close()
    except sqlite3.OperationalError as e:
        sys.exit(f"Error executing database query: {e}")

    csv_writer_file_handle = open(csv_path, 'w+', newline='', encoding='utf-8')
    csv_headers = ['Timestamp', 'Config file', 'Parent CSV ID', 'Parent node ID', 'CSV ID', "Node ID"]
    csv_writer = csv.DictWriter(csv_writer_file_handle, fieldnames=csv_headers)
    csv_writer.writeheader()

    for row in res:
        csv_row = dict()
        csv_row['Timestamp'] = row[0]
        csv_row['Config file'] = row[1]
        csv_row['Parent CSV ID'] = row[2]
        csv_row['Parent node ID'] = row[3]
        csv_row['CSV ID'] = row[4]
        csv_row['Node ID'] = row[5]
        csv_writer.writerow(csv_row)

    print(f"Your CSV is available at {csv_path}.")
    sys.exit()

if args.remove_entries_before is not None:
    try:
        query = "delete from csv_id_to_node_id_map where timestamp < ?"
        con = sqlite3.connect(db_path)
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        res = cur.execute(query, (args.remove_entries_before,))
        num_rows_deleted = cur.rowcount
        con.commit()
        con.close()
    except sqlite3.OperationalError as e:
        sys.exit(f"Error executing database query: {e}")

    print(f"Removed {num_rows_deleted} entries.")
