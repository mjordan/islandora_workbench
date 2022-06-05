"""unittest tests for the 'remove_invalid_values' methods in Drupal REST JSON field handlers.

   Incomplete. Tracking issue is https://github.com/mjordan/islandora_workbench/issues/424.
"""

import sys
import os
import unittest

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import workbench_fields


class TestSimpleField(unittest.TestCase):

    def test_simple_field_edtf_validate(self):
        config = dict()
        field_definitions = {
            'field_foo': {
                'field_type': 'edtf'
            }
        }

        with self.assertLogs() as message:
            input = ['1900', '1xxx', '1901', '1902']
            field = workbench_fields.SimpleField()
            output = field.remove_invalid_values(config, field_definitions, 'field_foo', input)
            self.assertEqual(output, ['1900', '1901', '1902'])
            self.assertRegex(str(message.output), r'is not a valid EDTF field value.')


'''
class TestGeolocationField(unittest.TestCase):

    def test_simple_field_geolocation_validate(self):
        config = dict()
        field_definitions = {
            'field_foo': {
                'field_type': 'geolocation'
            }
        }

        with self.assertLogs() as message:
            input = ['49.16667,-123.93333', '42.44-5.8', '49.25,-124.8']
            field = workbench_fields.SimpleField()
            output = field.remove_invalid_values(config, field_definitions, 'field_foo', input)
            self.assertEqual(output, ['49.16667,-123.93333', '49.25,-124.8'])
            self.assertRegex(str(message.output), r'is not a valid Geolocation field value')


class TestLinkField(unittest.TestCase):

    def test_simple_field_link_validate(self):
        config = dict()
        field_definitions = {
            'field_foo': {
                'field_type': 'link'
            }
        }

        with self.assertLogs() as message:
            input = ['www.example.com', 'https://example.com/foo', 'http://example.com%%bar']
            field = workbench_fields.SimpleField()
            output = field.remove_invalid_values(config, field_definitions, 'field_foo', input)
            self.assertEqual(output, ['https://example.com/foo', 'http://example.com%%bar'])
            self.assertRegex(str(message.output), r'is not a valid Link field value')
'''

class TestAuthorityLinkField(unittest.TestCase):

    def test_authority_link_field_validate(self):
        config = dict()
        field_definitions = {
            'field_foo': {
                'field_type': 'authority_link',
                'authority_sources': ['foo', 'bar']
            }
        }

        with self.assertLogs() as message:
            input = ['foo%%https://foo.com%%Foo authority record', 'xxx%%https://xxx.com']
            field = workbench_fields.AuthorityLinkField()
            output = field.remove_invalid_values(config, field_definitions, 'field_foo', input)
            self.assertEqual(output, ['foo%%https://foo.com%%Foo authority record'])
            self.assertRegex(str(message.output), r'xxx.*not a valid Authority Link field value')

if __name__ == '__main__':
    unittest.main()
