"""unittest tests for Drupal field handlers.
"""

import sys
import os
import unittest
import collections

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import workbench_fields


class TestSimple(unittest.TestCase):

    def setUp(self):
        self.config = {
            'content_type': 'islandora_object',
            'subdelimiter': '|',
            'id_field': 'id'
        }

        self.field_definitions = {
            'field_foo': {
                'cardinality': 1,
            }
        }

        self.node = {
            'type': [
                {'target_id': self.config['content_type'],
                 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ]
        }

    def test_create_with_simple_field(self):
        simple = workbench_fields.Simple()
        # Create a node with a simple field of cardinality 1, no subdelimiters.
        csv_record = collections.OrderedDict()
        csv_record['id'] = "001"
        csv_record['field_foo'] = "Field foo value"
        self.node = simple.create(self.config, self.field_definitions, self.node, csv_record, "field_foo")
        expected_node = {
            'type': [
                {'target_id': self.config['content_type'],
                 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {'value': "Field foo value"}
            ]
        }
        self.assertDictEqual(self.node, expected_ node)
        # Create a node with a simple field of cardinality 1, with subdelimiters.
        # Create a node with a simple field of cardinality unlimited, no subdelimiters.
        # Create a node with a simple field of cardinality unlimited, with subdelimiters.
        # Create a node with a simple field of cardinality limited, no subdelimiters.
        # Create a node with a simple field of cardinality limited, with subdelimiters.

    def test_update(self):
        pass


if __name__ == '__main__':
    unittest.main()
