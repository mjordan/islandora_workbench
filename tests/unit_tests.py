"""unittest tests that do not require a live Drupal.
"""

import sys
import os
from ruamel.yaml import YAML
import unittest

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import workbench_utils


class TestCompareStings(unittest.TestCase):

    def test_strings_match(self):
        res = workbench_utils.compare_strings('foo', 'foo  ')
        self.assertTrue(res)
        res = workbench_utils.compare_strings('foo', 'Foo')
        self.assertTrue(res)
        res = workbench_utils.compare_strings('foo', 'Foo#~^.')
        self.assertTrue(res)
        res = workbench_utils.compare_strings('foo bar baz', 'foo   bar baz')
        self.assertTrue(res)

    def test_strings_do_not_match(self):
        res = workbench_utils.compare_strings('foo', 'foot')
        self.assertFalse(res)


class TestSplitGeolocationString(unittest.TestCase):

    def test_split_geolocation_string_single(self):
        config = {'subdelimiter': '|'}
        res = workbench_utils.split_geolocation_string(
            config, '49.16667, -123.93333')
        self.assertDictEqual(res[0], {'lat': '49.16667', 'lng': '-123.93333'})

    def test_split_geolocation_string_multiple(self):
        config = {'subdelimiter': '|'}
        res = workbench_utils.split_geolocation_string(
            config, '30.16667, -120.93333|50.1,-120.5')
        self.assertDictEqual(res[0], {'lat': '30.16667', 'lng': '-120.93333'})
        self.assertDictEqual(res[1], {'lat': '50.1', 'lng': '-120.5'})

    def test_split_geolocation_string_multiple_at_sign(self):
        config = {'subdelimiter': '@'}
        res = workbench_utils.split_geolocation_string(
            config, '49.16667, -123.93333@50.1,-120.5')
        self.assertDictEqual(res[0], {'lat': '49.16667', 'lng': '-123.93333'})
        self.assertDictEqual(res[1], {'lat': '50.1', 'lng': '-120.5'})

    def test_split_geolocation_string_with_leading_slash(self):
        config = {'subdelimiter': '@'}
        res = workbench_utils.split_geolocation_string(
            config, r'\+49.16667, -123.93333@\+50.1,-120.5')
        self.assertDictEqual(res[0], {'lat': '+49.16667', 'lng': '-123.93333'})
        self.assertDictEqual(res[1], {'lat': '+50.1', 'lng': '-120.5'})


class TestSplitTypedRelationString(unittest.TestCase):

    def test_split_typed_relation_string_single(self):
        config = {'subdelimiter': '|'}
        res = workbench_utils.split_typed_relation_string(
            config, 'relators:pht:5', 'foo')
        self.assertDictEqual(res[0],
                             {'target_id': int(5),
                              'rel_type': 'relators:pht',
                              'target_type': 'foo'})

    def test_split_typed_relation_string_multiple(self):
        config = {'subdelimiter': '|'}
        res = workbench_utils.split_typed_relation_string(
            config, 'relators:pht:5|relators:con:10', 'bar')
        self.assertDictEqual(res[0],
                             {'target_id': int(5),
                              'rel_type': 'relators:pht',
                              'target_type': 'bar'})
        self.assertDictEqual(res[1],
                             {'target_id': int(10),
                              'rel_type': 'relators:con',
                              'target_type': 'bar'})

    def test_split_typed_relation_string_multiple_at_sign(self):
        config = {'subdelimiter': '@'}
        res = workbench_utils.split_typed_relation_string(
            config, 'relators:pht:5@relators:con:10', 'baz')
        self.assertDictEqual(res[0],
                             {'target_id': int(5),
                              'rel_type': 'relators:pht',
                              'target_type': 'baz'})
        self.assertDictEqual(res[1],
                             {'target_id': int(10),
                              'rel_type': 'relators:con',
                              'target_type': 'baz'})


class TestValidateLanguageCode(unittest.TestCase):

    def test_validate_code_in_list(self):
        res = workbench_utils.validate_language_code('es')
        self.assertTrue(res)

    def test_validate_code_not_in_list(self):
        res = workbench_utils.validate_language_code('foo')
        self.assertFalse(res)


class TestValidateLatlongValue(unittest.TestCase):

    def test_validate_good_latlong_values(self):
        values = ['+90.0, -127.554334', '90.0, -127.554334', '-90,-180', '+50.25,-117.8', '+48.43333,-123.36667']
        for value in values:
            res = workbench_utils.validate_latlong_value(value)
            self.assertTrue(res)

    def test_validate_bad_latlong_values(self):
        values = ['+90.1 -100.111', '045, 180', '+5025,-117.8', '-123.36667']
        for value in values:
            res = workbench_utils.validate_latlong_value(value)
            self.assertFalse(res)


class TestValidateNodeCreatedDateValue(unittest.TestCase):

    def test_validate_good_date_string_values(self):
        values = ['2020-11-15T23:49:22+00:00']
        for value in values:
            res = workbench_utils.validate_node_created_date_string(value)
            self.assertTrue(res)

    def test_validate_bad_date_string_values(self):
        values = ['2020-11-15:23:49:22+00:00', '2020-11-15T:23:49:22', '2020-11-15']
        for value in values:
            res = workbench_utils.validate_node_created_date_string(value)
            self.assertFalse(res)


class TestValidateEdtfValue(unittest.TestCase):

    def test_validate_good_edtf_values(self):
        good_values = ['1900',
                       '2000?',
                       '2020-10',
                       '2021-01~',
                       '2021-10-12',
                       '[1900..1920]',
                       '[1899,1902..1909]',
                       '[1900-12-01..1923]',
                       '2000/2020',
                       '2020-11-15T23:11:05',
                       '[..1760-12-03]',
                       '[1760-12-03..]'
                       ]
        for good_value in good_values:
            res, message = workbench_utils.validate_edtf_value(good_value)
            self.assertTrue(res, good_value)

    def test_validate_bad_edtf_values(self):
        bad_values = ['190', '1900..1920]', '2021-01?', '2020-1', '2000~', '[1900..923]', '200/2020', '2020-11-15-23:11:05']
        for bad_value in bad_values:
            res, message = workbench_utils.validate_edtf_value(bad_value)
            self.assertFalse(res, bad_value)


class TestSetMediaType(unittest.TestCase):

    def setUp(self):
        yaml = YAML()
        dir_path = os.path.dirname(os.path.realpath(__file__))

        # Media types are mapped from extensions.
        types_config_file_path = os.path.join(
            dir_path, 'assets', 'set_media_type_test', 'multi_types_config.yml')
        with open(types_config_file_path, 'r') as f:
            multi_types_config_file_contents = f.read()
        self.multi_types_config_yaml = yaml.load(
            multi_types_config_file_contents)

        # Media type is set for all media.
        type_config_file_path = os.path.join(
            dir_path,
            'assets',
            'set_media_type_test',
            'single_type_config.yml')
        with open(type_config_file_path, 'r') as f:
            single_type_config_file_contents = f.read()
        self.single_type_config_yaml = yaml.load(
            single_type_config_file_contents)

    def test_multi_types_set_media_type(self):
        res = workbench_utils.set_media_type(
            '/tmp/foo.txt', self.multi_types_config_yaml)
        self.assertEqual(res, 'extracted_text')

        res = workbench_utils.set_media_type(
            '/tmp/foo.tif', self.multi_types_config_yaml)
        self.assertEqual(res, 'file')

        res = workbench_utils.set_media_type(
            '/tmp/foo.mp4', self.multi_types_config_yaml)
        self.assertEqual(res, 'video')

        res = workbench_utils.set_media_type(
            '/tmp/foo.png', self.multi_types_config_yaml)
        self.assertEqual(res, 'image')

        res = workbench_utils.set_media_type(
            '/tmp/foo.pptx', self.multi_types_config_yaml)
        self.assertEqual(res, 'document')

        res = workbench_utils.set_media_type(
            '/tmp/foo.xxx', self.multi_types_config_yaml)
        self.assertEqual(res, 'file')

    def test_single_type_set_media_type(self):
        res = workbench_utils.set_media_type(
            '/tmp/foo.bar', self.single_type_config_yaml)
        self.assertEqual(res, 'barmediatype')


if __name__ == '__main__':
    unittest.main()
