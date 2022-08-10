"""unittest tests that require a live Drupal at http://localhost:8000. In most cases, the URL, credentials,
   etc. are in a configuration file referenced in the test.

   Files islandora_tests_check.py, islandora_tests_paged_content.py, and islandora_tests_hooks.py also
   contain tests that interact with an Islandora instance.
"""

import sys
import os
from ruamel.yaml import YAML
import tempfile
import subprocess
import argparse
import requests
import json
import urllib.parse
import unittest
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import workbench_utils
from WorkbenchConfig import WorkbenchConfig


class TestCreate(unittest.TestCase):

    def setUp(self):
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        create_config_file_path = os.path.join(self.current_dir, 'assets', 'create_test', 'create.yml')
        self.create_cmd = ["./workbench", "--config", create_config_file_path]

        self.temp_dir = tempfile.gettempdir()
        self.nid_file = os.path.join(self.temp_dir, 'workbenchcreatetestnids.txt')

    def test_create(self):
        nids = list()
        create_output = subprocess.check_output(self.create_cmd)
        create_output = create_output.decode().strip()
        create_lines = create_output.splitlines()
        with open(self.nid_file, "a") as fh:
            fh.write("node_id\n")
            for line in create_lines:
                if 'created at' in line:
                    nid = line.rsplit('/', 1)[-1]
                    nid = nid.strip('.')
                    nids.append(nid)
                    fh.write(nid + "\n")

        self.assertEqual(len(nids), 5)

    def tearDown(self):
        delete_config_file_path = os.path.join(self.current_dir, 'assets', 'create_test', 'delete.yml')
        delete_cmd = ["./workbench", "--config", delete_config_file_path]
        delete_output = subprocess.check_output(delete_cmd)
        delete_output = delete_output.decode().strip()
        delete_lines = delete_output.splitlines()
        os.remove(self.nid_file)

        self.rollback_file_path = os.path.join(self.current_dir, 'assets', 'create_test', 'rollback.csv')
        if os.path.exists(self.rollback_file_path):
            os.remove(self.rollback_file_path)

        self.preprocessed_file_path = os.path.join(self.current_dir, 'assets', 'create_test', 'metadata.csv.prepocessed')
        if os.path.exists(self.preprocessed_file_path):
            os.remove(self.preprocessed_file_path)


class TestCreateFromFiles(unittest.TestCase):

    def setUp(self):
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        create_config_file_path = os.path.join(self.current_dir, 'assets', 'create_from_files_test', 'create.yml')
        self.create_cmd = ["./workbench", "--config", create_config_file_path]

        self.temp_dir = tempfile.gettempdir()
        self.nid_file = os.path.join(self.temp_dir, 'workbenchcreatefromfilestestnids.txt')

    def test_create_from_files(self):
        nids = list()
        create_output = subprocess.check_output(self.create_cmd)
        create_output = create_output.decode().strip()
        create_lines = create_output.splitlines()
        with open(self.nid_file, "a") as fh:
            fh.write("node_id\n")
            for line in create_lines:
                if 'created at' in line:
                    nid = line.rsplit('/', 1)[-1]
                    nid = nid.strip('.')
                    nids.append(nid)
                    fh.write(nid + "\n")

        self.assertEqual(len(nids), 3)

    def tearDown(self):
        delete_config_file_path = os.path.join(self.current_dir, 'assets', 'create_from_files_test', 'delete.yml')
        delete_cmd = ["./workbench", "--config", delete_config_file_path]
        delete_output = subprocess.check_output(delete_cmd)
        os.remove(self.nid_file)

        self.rollback_file_path = os.path.join(self.current_dir, 'assets', 'create_from_files_test', 'files', 'rollback.csv')
        if os.path.exists(self.rollback_file_path):
            os.remove(self.rollback_file_path)


'''
class TestCreateFromFilesDrupal8(unittest.TestCase):

    def setUp(self):
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        create_config_file_path = os.path.join(self.current_dir, 'assets', 'create_from_files_test', 'create_drupal_8.yml')
        self.create_cmd = ["./workbench", "--config", create_config_file_path]

        self.temp_dir = tempfile.gettempdir()
        self.nid_file = os.path.join(self.temp_dir, 'workbenchcreatefromfilestestnids.txt')

    def test_create_from_files_drupal_8(self):
        nids = list()
        create_output = subprocess.check_output(self.create_cmd)
        create_output = create_output.decode().strip()
        create_lines = create_output.splitlines()
        with open(self.nid_file, "a") as fh:
            fh.write("node_id\n")
            for line in create_lines:
                if 'created at' in line:
                    nid = line.rsplit('/', 1)[-1]
                    nid = nid.strip('.')
                    nids.append(nid)
                    fh.write(nid + "\n")

        self.assertEqual(len(nids), 3)

    def tearDown(self):
        delete_config_file_path = os.path.join(self.current_dir, 'assets', 'create_from_files_test', 'delete.yml')
        delete_cmd = ["./workbench", "--config", delete_config_file_path]
        delete_output = subprocess.check_output(delete_cmd)
        os.remove(self.nid_file)

        self.rollback_file_path = os.path.join(self.current_dir, 'assets', 'create_from_files_test', 'files', 'rollback.csv')
        if os.path.exists(self.rollback_file_path):
            os.remove(self.rollback_file_path)
'''


class TestCreateWithNewTypedRelation(unittest.TestCase):
    # Note: You can't run this test class on its own, e.g.,
    # python3 tests/islandora_tests.py TestCreateWithNewTypedRelation.
    # because passing "TestCreateWithNewTypedRelation" as an argument
    # will cause the argparse parser to fail.

    def setUp(self):
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        config_file_path = os.path.join(self.current_dir, 'assets', 'typed_relation_test', 'create_with_new_typed_relation.yml')
        self.create_cmd = ["./workbench", "--config", config_file_path]

        self.temp_dir = tempfile.gettempdir()
        self.nid_file = os.path.join(self.temp_dir, 'workbenchcreatewithnewtypedrelationtestnids.txt')

        parser = argparse.ArgumentParser()
        parser.add_argument('--config')
        parser.add_argument('--check')
        parser.add_argument('--get_csv_template')
        parser.set_defaults(config=config_file_path, check=False)
        args = parser.parse_args()
        workbench_config = WorkbenchConfig(args)
        config = workbench_config.get_config()
        self.config = config

    def test_create_with_new_typed_relation(self):
        nids = list()
        create_output = subprocess.check_output(self.create_cmd)
        create_output = create_output.decode().strip()
        create_lines = create_output.splitlines()
        with open(self.nid_file, "a") as fh:
            fh.write("node_id\n")
            for line in create_lines:
                if 'created at' in line:
                    nid = line.rsplit('/', 1)[-1]
                    nid = nid.strip('.')
                    nids.append(nid)
                    fh.write(nid + "\n")

        self.assertEqual(len(nids), 1)

        self.new_term_id = workbench_utils.find_term_in_vocab(self.config, 'person', 'Kirk, James T.')
        self.assertTrue(self.new_term_id)

    def tearDown(self):
        delete_config_file_path = os.path.join(self.current_dir, 'assets', 'typed_relation_test', 'create_with_new_typed_relation_delete.yml')
        delete_cmd = ["./workbench", "--config", delete_config_file_path]
        delete_output = subprocess.check_output(delete_cmd)
        delete_output = delete_output.decode().strip()
        delete_lines = delete_output.splitlines()
        os.remove(self.nid_file)

        preprocessed_csv_path = os.path.join(self.current_dir, 'assets', 'typed_relation_test', 'input_data', 'create_with_new_typed_relation.csv.prepocessed')
        if os.path.exists(preprocessed_csv_path):
            os.remove(preprocessed_csv_path)

        term_endpoint = self.config['host'] + '/taxonomy/term/' + str(self.new_term_id) + '?_format=json'
        delete_term_response = workbench_utils.issue_request(self.config, 'DELETE', term_endpoint)


class TestDelete(unittest.TestCase):

    def setUp(self):
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        create_config_file_path = os.path.join(self.current_dir, 'assets', 'delete_test', 'create.yml')
        self.create_cmd = ["./workbench", "--config", create_config_file_path]

        self.temp_dir = tempfile.gettempdir()
        self.nid_file = os.path.join(self.temp_dir, 'workbenchdeletetesttnids.txt')

        nids = list()
        create_output = subprocess.check_output(self.create_cmd)
        create_output = create_output.decode().strip()
        create_lines = create_output.splitlines()
        with open(self.nid_file, "a") as fh:
            fh.write("node_id\n")
            for line in create_lines:
                if 'created at' in line:
                    nid = line.rsplit('/', 1)[-1]
                    nid = nid.strip('.')
                    nids.append(nid)
                    fh.write(nid + "\n")

    def test_delete(self):
        delete_config_file_path = os.path.join(self.current_dir, 'assets', 'delete_test', 'delete.yml')
        delete_cmd = ["./workbench", "--config", delete_config_file_path]
        delete_output = subprocess.check_output(delete_cmd)
        delete_output = delete_output.decode().strip()
        delete_lines = delete_output.splitlines()

        self.assertEqual(len(delete_lines), 7)

    def tearDown(self):
        if os.path.exists(self.nid_file):
            os.remove(self.nid_file)
        if os.path.exists(self.nid_file + ".preprocessed"):
            os.remove(self.nid_file + ".preprocessed")


class TestUpdate(unittest.TestCase):

    def setUp(self):
        self.maxDiff = None
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        create_config_file_path = os.path.join(self.current_dir, 'assets', 'update_test', 'create.yml')
        self.create_cmd = ["./workbench", "--config", create_config_file_path]

        self.temp_dir = tempfile.gettempdir()
        self.nid_file = os.path.join(self.temp_dir, 'workbenchupdatetestnids.txt')
        self.update_metadata_file = os.path.join(self.current_dir, 'assets', 'update_test', 'workbenchupdatetest.csv')

        yaml = YAML()
        with open(create_config_file_path, 'r') as f:
            config_file_contents = f.read()
        config_data = yaml.load(config_file_contents)
        config = {}
        for k, v in config_data.items():
            config[k] = v
        self.islandora_host = config['host']

        self.nids = list()
        create_output = subprocess.check_output(self.create_cmd)
        create_output = create_output.decode().strip()
        create_lines = create_output.splitlines()

        with open(self.nid_file, "a") as nids_fh:
            nids_fh.write("node_id\n")
            for line in create_lines:
                if 'created at' in line:
                    nid = line.rsplit('/', 1)[-1]
                    nid = nid.strip('.')
                    nids_fh.write(nid + "\n")
                    self.nids.append(nid)

        # Add some values to the update CSV file to test against.
        with open(self.update_metadata_file, "a") as update_fh:
            update_fh.write("node_id,field_identifier,field_coordinates\n")
            update_fh.write(f'{self.nids[0]},identifier-0001,"99.1,-123.2"')

    def test_update(self):
        # Run update task.
        time.sleep(5)
        update_config_file_path = os.path.join(self.current_dir, 'assets', 'update_test', 'update.yml')
        self.update_cmd = ["./workbench", "--config", update_config_file_path]
        subprocess.check_output(self.update_cmd)

        # Confirm that fields have been updated.
        url = self.islandora_host + '/node/' + str(self.nids[0]) + '?_format=json'
        response = requests.get(url)
        node = json.loads(response.text)
        identifier = str(node['field_identifier'][0]['value'])
        self.assertEqual(identifier, 'identifier-0001')
        coodinates = str(node['field_coordinates'][0]['lat'])
        self.assertEqual(coodinates, '99.1')

    def tearDown(self):
        delete_config_file_path = os.path.join(self.current_dir, 'assets', 'update_test', 'delete.yml')
        delete_cmd = ["./workbench", "--config", delete_config_file_path]
        subprocess.check_output(delete_cmd)

        os.remove(self.nid_file)
        os.remove(self.update_metadata_file)


class TestTermFromUri(unittest.TestCase):
    # Note: You can't run this test class on its own, e.g.,
    # python3 tests/islandora_tests.py TestTermFromUri.
    # because passing "TestTermFromUri" as an argument
    # will cause the argparse parser to fail.

    def test_term_from_uri(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        config_file_path = os.path.join(current_dir, 'assets', 'create_test', 'create.yml')

        parser = argparse.ArgumentParser()
        parser.add_argument('--config')
        parser.add_argument('--check')
        parser.add_argument('--get_csv_template')
        parser.set_defaults(config=config_file_path, check=False)
        args = parser.parse_args()
        workbench_config = WorkbenchConfig(args)
        config = workbench_config.get_config()

        tid = workbench_utils.get_term_id_from_uri(config, 'http://mozilla.github.io/pdf.js')
        self.assertEqual(tid, 3)


class TestCreateWithNonLatinText(unittest.TestCase):

    def setUp(self):
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        create_config_file_path = os.path.join(self.current_dir, 'assets', 'non_latin_text_test', 'create.yml')
        self.create_cmd = ["./workbench", "--config", create_config_file_path]

        yaml = YAML()
        with open(create_config_file_path, 'r') as f:
            config_file_contents = f.read()
        config_data = yaml.load(config_file_contents)
        config = {}
        for k, v in config_data.items():
            config[k] = v
        self.islandora_host = config['host']

        self.temp_dir = tempfile.gettempdir()
        self.nid_file = os.path.join(self.temp_dir, 'workbenchcreatenonlatintestnids.txt')
        self.rollback_file_path = os.path.join(self.current_dir, 'assets', 'non_latin_text_test', 'rollback.csv')

    def test_create_with_non_latin_text(self):
        nids = list()
        create_output = subprocess.check_output(self.create_cmd)
        create_output = create_output.decode().strip()
        create_lines = create_output.splitlines()
        with open(self.nid_file, "a") as fh:
            fh.write("node_id\n")
            for line in create_lines:
                if 'created at' in line:
                    nid = line.rsplit('/', 1)[-1]
                    nid = nid.strip('.')
                    nids.append(nid)
                    fh.write(nid + "\n")

        self.assertEqual(len(nids), 3)

        url = self.islandora_host + '/node/' + str(nids[0]) + '?_format=json'
        response = requests.get(url)
        node = json.loads(response.text)
        title = str(node['title'][0]['value'])
        self.assertEqual(title, '一九二四年六月十二日')

        url = self.islandora_host + '/node/' + str(nids[1]) + '?_format=json'
        response = requests.get(url)
        node = json.loads(response.text)
        title = str(node['title'][0]['value'])
        self.assertEqual(title, 'सरकारी दस्तावेज़')

        url = self.islandora_host + '/node/' + str(nids[2]) + '?_format=json'
        response = requests.get(url)
        node = json.loads(response.text)
        title = str(node['title'][0]['value'])
        self.assertEqual(title, 'ᐊᑕᐅᓯᖅ ᓄᓇ, ᐅᓄᖅᑐᑦ ᓂᐲᑦ')

    def tearDown(self):
        delete_config_file_path = os.path.join(self.current_dir, 'assets', 'non_latin_text_test', 'delete.yml')
        delete_cmd = ["./workbench", "--config", delete_config_file_path]
        delete_output = subprocess.check_output(delete_cmd)
        delete_output = delete_output.decode().strip()
        delete_lines = delete_output.splitlines()
        os.remove(self.nid_file)

        if os.path.exists(self.rollback_file_path):
            os.remove(self.rollback_file_path)

        preprocessed_csv_path = os.path.join(self.current_dir, 'assets', 'non_latin_text_test', 'metadata.csv.prepocessed')
        if os.path.exists(preprocessed_csv_path):
            os.remove(preprocessed_csv_path)


class TestSecondaryTask(unittest.TestCase):

    def setUp(self):
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        create_config_file_path = os.path.join(self.current_dir, 'assets', 'secondary_task_test', 'create.yml')

        yaml = YAML()
        with open(create_config_file_path, 'r') as f:
            config_file_contents = f.read()
        config_data = yaml.load(config_file_contents)
        config = {}
        for k, v in config_data.items():
            config[k] = v
        self.islandora_host = config['host']

        self.create_cmd = ["./workbench", "--config", create_config_file_path]

        self.temp_dir = tempfile.gettempdir()
        self.nid_file = os.path.join(self.temp_dir, 'workbenchsecondarytasktestnids.txt')
        self.nid_file_preprocessed = os.path.join(self.temp_dir, 'workbenchsecondarytasktestnids.txt.prepocessed')

    def test_secondary_task(self):
        nids = list()
        create_output = subprocess.check_output(self.create_cmd)
        create_output = create_output.decode().strip()

        # Write a file to the system's temp directory containing the node IDs of the
        # nodes created during this test so they can be deleted in tearDown().
        create_lines = create_output.splitlines()
        with open(self.nid_file, "a") as fh:
            fh.write("node_id\n")
            for line in create_lines:
                if 'created at' in line:
                    nid = line.rsplit('/', 1)[-1]
                    nid = nid.strip('.')
                    nids.append(nid)
                    fh.write(nid + "\n")

        self.assertEqual(len(nids), 5)

        for nid in nids:
            node_url = self.islandora_host + '/node/' + nid + '?_format=json'
            response = requests.get(node_url)
            node_json = json.loads(response.text)
            # Get the node ID of the parent node.
            if node_json['title'][0]['value'].startswith('Tester'):
                parent_nid = node_json['nid'][0]['value']
                break

        for nid in nids:
            node_url = self.islandora_host + '/node/' + nid + '?_format=json'
            response = requests.get(node_url)
            node_json = json.loads(response.text)
            if node_json['title'][0]['value'].startswith('Secondary task test child 1'):
                self.assertEqual(int(node_json['field_member_of'][0]['target_id']), int(parent_nid))
            elif node_json['title'][0]['value'].startswith('Secondary task test child 2'):
                self.assertEqual(int(node_json['field_member_of'][0]['target_id']), int(parent_nid))
            else:
                self.assertEqual(node_json['field_member_of'], [])

    def tearDown(self):
        delete_config_file_path = os.path.join(self.current_dir, 'assets', 'secondary_task_test', 'delete.yml')
        delete_cmd = ["./workbench", "--config", delete_config_file_path]
        delete_output = subprocess.check_output(delete_cmd)
        delete_output = delete_output.decode().strip()
        delete_lines = delete_output.splitlines()
        os.remove(self.nid_file)

        preprocessed_csv_path = os.path.join(self.current_dir, 'assets', 'secondary_task_test', 'metadata.csv.prepocessed')
        if os.path.exists(preprocessed_csv_path):
            os.remove(preprocessed_csv_path)
        secondary_preprocessed_csv_path = os.path.join(self.current_dir, 'assets', 'secondary_task_test', 'secondary.csv.prepocessed')
        if os.path.exists(secondary_preprocessed_csv_path):
            os.remove(secondary_preprocessed_csv_path)

        map_file_path = os.path.join(self.current_dir, 'assets', 'secondary_task_test', 'id_to_node_map.tsv')
        if os.path.exists(map_file_path):
            os.remove(map_file_path)

        rollback_file_path = os.path.join(self.current_dir, 'assets', 'secondary_task_test', 'rollback.csv')
        if os.path.exists(rollback_file_path):
            os.remove(rollback_file_path)

        if os.path.exists(self.nid_file_preprocessed):
            os.remove(self.nid_file_preprocessed)


class TestAdditionalFilesCreate(unittest.TestCase):

    def setUp(self):
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        create_config_file_path = os.path.join(self.current_dir, 'assets', 'additional_files_test', 'create.yml')

        yaml = YAML()
        with open(create_config_file_path, 'r') as f:
            config_file_contents = f.read()
        config_data = yaml.load(config_file_contents)
        self.config = {}
        for k, v in config_data.items():
            self.config[k] = v
        self.islandora_host = self.config['host']
        self.islandora_username = self.config['username']
        self.islandora_password = self.config['password']

        self.create_cmd = ["./workbench", "--config", create_config_file_path]
        create_output = subprocess.check_output(self.create_cmd)
        create_output = create_output.decode().strip()

        self.rollback_file_path = os.path.join(self.current_dir, 'assets', 'additional_files_test', 'rollback.csv')
        with open(self.rollback_file_path, 'r') as rbf:
            rollback_file_contents = rbf.read()

        # There will only be one nid in the rollback.csv file.
        nid = rollback_file_contents.replace('node_id', '')
        self.nid = nid.strip()

        media_list_url = self.islandora_host + '/node/' + self.nid + '/media?_format=json'
        media_list_response = requests.get(media_list_url, auth=(self.islandora_username, self.islandora_password))
        media_list_json = json.loads(media_list_response.text)
        self.media_sizes = dict()
        self.media_use_tids = dict()
        for media in media_list_json:
            self.media_use_tids[media['mid'][0]['value']] = media['field_media_use'][0]['target_id']
            if 'field_file_size' in media:
                self.media_sizes[media['mid'][0]['value']] = media['field_file_size'][0]['value']
            # We don't use the transcript file's size here since it's not available via REST. Instead, since this
            # file will be the only media with 'field_edited_text' (the transcript), we tack its value onto media_sizes
            # for testing below.
            if 'field_edited_text' in media:
                self.media_sizes['transcript'] = media['field_edited_text'][0]['value']

    def test_media_creation(self):
        # This is the original file's size.
        self.assertTrue(217504 in self.media_sizes.values())
        # This is the preservation file's size.
        self.assertTrue(286445 in self.media_sizes.values())
        # This is the transcript.
        self.assertIn('This is a transcript.', self.media_sizes['transcript'])

    def test_media_use_tids(self):
        '''Doesn't associate media use terms to nodes, but at least it confirms that the intended
           media use tids are present in the media created by this test.
        '''
        preservation_media_use_tid = self.get_term_id_from_uri("http://pcdm.org/use#PreservationMasterFile")
        self.assertTrue(preservation_media_use_tid in self.media_use_tids.values())
        transcript_media_use_tid = self.get_term_id_from_uri("http://pcdm.org/use#Transcript")
        self.assertTrue(transcript_media_use_tid in self.media_use_tids.values())

    def tearDown(self):
        delete_config_file_path = os.path.join(self.current_dir, 'assets', 'additional_files_test', 'rollback.yml')
        delete_cmd = ["./workbench", "--config", delete_config_file_path]
        delete_output = subprocess.check_output(delete_cmd)
        delete_output = delete_output.decode().strip()
        delete_lines = delete_output.splitlines()

        if os.path.exists(self.rollback_file_path):
            os.remove(self.rollback_file_path)

        preprocessed_csv_path = os.path.join(self.current_dir, 'assets', 'additional_files_test', 'create.csv.prepocessed')
        if os.path.exists(preprocessed_csv_path):
            os.remove(preprocessed_csv_path)

        rollback_csv_path = os.path.join(self.current_dir, 'assets', 'additional_files_test', 'rollback.csv')
        if os.path.exists(rollback_csv_path):
            os.remove(rollback_csv_path)

        preprocessed_rollback_csv_path = os.path.join(self.current_dir, 'assets', 'additional_files_test', 'rollback.csv.prepocessed')
        if os.path.exists(preprocessed_rollback_csv_path):
            os.remove(preprocessed_rollback_csv_path)

    def get_term_id_from_uri(self, uri):
        '''We don't use get_term_from_uri() from workbench_utils because it requires a full config object.
        '''
        term_from_authority_link_url = self.islandora_host + '/term_from_uri?_format=json&uri=' + uri.replace('#', '%23')
        response = requests.get(term_from_authority_link_url, auth=(self.islandora_username, self.islandora_password))
        response_body = json.loads(response.text)
        tid = response_body[0]['tid'][0]['value']
        return tid


if __name__ == '__main__':
    unittest.main()
