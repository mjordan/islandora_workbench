#!/usr/bin/env python3

"""Utility script to dump the CSV ID to Node ID map from its SQLite database, or to remove
   entries from the database with specificed config files names or prior to/before a provided timestamp.

   Usage: python dump_id_map.py --db_path csv_id_to_node_id_map.db --csv_path /tmp/test.csv
          python dump_id_map.py --db_path csv_id_to_node_id_map.db --csv_path /tmp/test.csv --nonunique csv_id

          python dump_id_map.py --db_path csv_id_to_node_id_map.db --remove_entries_before "2023-05-29 19:17"
          python dump_id_map.py --db_path csv_id_to_node_id_map.db --remove_entries_after "2023-05-22"
          python dump_id_map.py --db_path csv_id_to_node_id_map.db --remove_entries_with_config_files create.yml,test_dir/create_testing.yml
          python dump_id_map.py --db_path csv_id_to_node_id_map.db --remove_entries_for_deleted_nodes https://islandora.traefik.me
"""

import os
import sys
import csv
import sqlite3
import argparse
import requests

parser = argparse.ArgumentParser()
parser.add_argument(
    "--db_path",
    required=True,
    help="Relative or absolute path to the SQLite database file.",
)
parser.add_argument(
    "--csv_path", help="Relative or absolute path to the output CSV file."
)
parser.add_argument(
    "--nonunique", help="Name of the column that contains nonunique/duplicate values."
)
parser.add_argument(
    "--remove_entries_before",
    help="Date string in yyyy:mm:dd hh:mm:ss (or truncated for of that pattern).",
)
parser.add_argument(
    "--remove_entries_after",
    help="Date string in yyyy:mm:dd hh:mm:ss (or truncated for of that pattern).",
)
parser.add_argument(
    "--remove_entries_with_config_files",
    help="comma-separated list of Workbench config files (exactly as passed to Workbench).",
)
parser.add_argument(
    "--remove_entries_for_deleted_nodes",
    help="Hostname (and port if applicable) of your Islandora.",
)
args = parser.parse_args()

if (
    args.csv_path is None
    and args.remove_entries_before is None
    and args.remove_entries_after is None
    and args.remove_entries_with_config_files is None
    and args.remove_entries_for_deleted_nodes is None
):
    sys.exit(
        "You need to provide either --csv_path, --remove_entries_before, --remove_entries_after, --remove_entries_with_config_files, or --remove_entries_for_deleted_nodes option."
    )

#######################################
# Check existence of specified paths. #
#######################################

if os.path.isabs(args.db_path):
    db_path = args.db_path
else:
    db_path = os.path.join(os.getcwd(), args.db_path)
if not os.path.exists(db_path):
    message = f"Can't find SQLite database path ({os.path.abspath(db_path)}). Please confirm that it exsits."
    sys.exit("Error: " + message)

if args.csv_path is not None:
    if os.path.isabs(args.csv_path):
        csv_path = args.csv_path
        csv_path_dir = os.path.dirname(csv_path)
    else:
        csv_path = os.path.join(os.getcwd(), args.csv_path)
        csv_path_dir = os.path.dirname(csv_path)
    if not os.path.exists(csv_path_dir):
        message = f"Can't find directory specified for output CSV file path ({csv_path_dir}). Please confirm that it exsits."
        sys.exit("Error: " + message)

#########################################################
# Get contents of the db, then write them out to a CSV. #
#########################################################

if args.csv_path is not None:
    try:
        if args.nonunique is None:
            query = "select * from csv_id_to_node_id_map"
            params = ()
        else:
            # Using parameterized fieldnames wraps them in '', which interferes with the query.
            # So we revert to (very likely low risk) string interpolation.
            query = (
                f"SELECT * FROM csv_id_to_node_id_map WHERE {args.nonunique} IN "
                + f"(SELECT {args.nonunique} FROM csv_id_to_node_id_map GROUP BY {args.nonunique} HAVING COUNT(*) > 1)"
            )
            params = ()
        con = sqlite3.connect(db_path)
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        res = cur.execute(query, params).fetchall()
        con.close()
    except sqlite3.OperationalError as e:
        sys.exit(f"Error executing database query: {e}")

    csv_writer_file_handle = open(csv_path, "w+", newline="", encoding="utf-8")
    csv_headers = [
        "Timestamp",
        "Config file",
        "Parent CSV ID",
        "Parent node ID",
        "CSV ID",
        "Node ID",
    ]
    csv_writer = csv.DictWriter(csv_writer_file_handle, fieldnames=csv_headers)
    csv_writer.writeheader()

    for row in res:
        csv_row = dict()
        csv_row["Timestamp"] = row[0]
        csv_row["Config file"] = row[1]
        csv_row["Parent CSV ID"] = row[2]
        csv_row["Parent node ID"] = row[3]
        csv_row["CSV ID"] = row[4]
        csv_row["Node ID"] = row[5]
        csv_writer.writerow(csv_row)

    print(f"Dumped {len(res)} rows into CSV file {csv_path}.")
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

    print(
        f"Removed {num_rows_deleted} entries added to the database before {args.remove_entries_before}."
    )

if args.remove_entries_after is not None:
    try:
        query = "delete from csv_id_to_node_id_map where timestamp > ?"
        con = sqlite3.connect(db_path)
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        res = cur.execute(query, (args.remove_entries_after,))
        num_rows_deleted = cur.rowcount
        con.commit()
        con.close()
    except sqlite3.OperationalError as e:
        sys.exit(f"Error executing database query: {e}")

    print(
        f"Removed {num_rows_deleted} entries added to the database after {args.remove_entries_after}."
    )

if args.remove_entries_with_config_files is not None:
    config_files = args.remove_entries_with_config_files.split(",")
    config_files_tuple = tuple(config_files)
    placeholders = ", ".join("?" for x in config_files)
    try:
        query = (
            f"delete from csv_id_to_node_id_map where config_file in ({placeholders})"
        )
        con = sqlite3.connect(db_path)
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        res = cur.execute(query, config_files_tuple)
        num_rows_deleted = cur.rowcount
        con.commit()
        con.close()
    except sqlite3.OperationalError as e:
        sys.exit(f"Error executing database query: {e}")

    print(
        f"Removed {num_rows_deleted} entries added to the database using config file(s) {args.remove_entries_with_config_files}."
    )

if args.remove_entries_for_deleted_nodes is not None:
    try:
        query = "select * from csv_id_to_node_id_map"
        params = ()
        con = sqlite3.connect(db_path)
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        res = cur.execute(query, params).fetchall()
        con.close()
    except sqlite3.OperationalError as e:
        sys.exit(f"Error executing database query: {e}")

    deleted_nodes = []
    for row in res:
        url = args.remove_entries_for_deleted_nodes.rstrip("/") + "/node/" + str(row[5])
        ping_response = requests.head(url, allow_redirects=True)
        if ping_response.status_code == 404:
            deleted_nodes.append(row[5])

    if len(deleted_nodes) > 0:
        deleted_nodes_tuple = tuple(deleted_nodes)
        try:
            placeholders = ", ".join("?" for x in deleted_nodes)
            query = (
                f"delete from csv_id_to_node_id_map where node_id in ({placeholders})"
            )
            con = sqlite3.connect(db_path)
            con.row_factory = sqlite3.Row
            cur = con.cursor()
            res = cur.execute(query, deleted_nodes_tuple)
            num_rows_deleted = cur.rowcount
            con.commit()
            con.close()
        except sqlite3.OperationalError as e:
            sys.exit(f"Error executing database query: {e}")

    print(f"Removed {len(deleted_nodes)} rows from CSV ID to node ID map {db_path}.")
    sys.exit()
