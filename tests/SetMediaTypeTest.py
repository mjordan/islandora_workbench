import os
import sys
import unittest
from ruamel.yaml import YAML

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from workbench_utils import set_media_type


class TestSetMediaType(unittest.TestCase):

    def setUp(self):
        yaml = YAML()
        dir_path = os.path.dirname(os.path.realpath(__file__))

        # Media types are mapped from extensions.
        types_config_file_path = os.path.join(dir_path, 'assets', 'set_media_type_test', 'multi_types_config.yml')
        with open(types_config_file_path, 'r') as f:
            multi_types_config_file_contents = f.read()
        self.multi_types_config_yaml = yaml.load(multi_types_config_file_contents)

        # Media type is set for all media.
        type_config_file_path = os.path.join(dir_path, 'assets', 'set_media_type_test', 'single_type_config.yml')
        with open(type_config_file_path, 'r') as f:
            single_type_config_file_contents = f.read()
        self.single_type_config_yaml = yaml.load(single_type_config_file_contents)

    def test_multi_types_set_media_type(self):
        res = set_media_type('/tmp/foo.txt', self.multi_types_config_yaml)
        self.assertEqual(res, 'extracted_text')

        res = set_media_type('/tmp/foo.tif', self.multi_types_config_yaml)
        self.assertEqual(res, 'file')

        res = set_media_type('/tmp/foo.mp4', self.multi_types_config_yaml)
        self.assertEqual(res, 'video')

        res = set_media_type('/tmp/foo.png', self.multi_types_config_yaml)
        self.assertEqual(res, 'image')

        res = set_media_type('/tmp/foo.pptx', self.multi_types_config_yaml)
        self.assertEqual(res, 'document')

        res = set_media_type('/tmp/foo.xxx', self.multi_types_config_yaml)
        self.assertEqual(res, 'file')

    def test_single_type_set_media_type(self):
        res = set_media_type('/tmp/foo.bar', self.single_type_config_yaml)
        self.assertEqual(res, 'barmediatype')


if __name__ == '__main__':
    unittest.main()
