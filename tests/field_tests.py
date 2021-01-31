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
        # Create a node with a simple field of cardinality 1, no subdelimiters.
        self.field_definitions = {
            'field_foo': {
                'cardinality': 1,
            }
        }

        simple = workbench_fields.Simple()
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
        self.assertDictEqual(self.node, expected_node)

        # Create a node with a simple field of cardinality 1, with subdelimiters.
        simple = workbench_fields.Simple()
        csv_record = collections.OrderedDict()
        csv_record['id'] = "002"
        csv_record['field_foo'] = "Field foo value|Extraneous value"
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
        self.assertDictEqual(self.node, expected_node)

        # Create a node with a simple field of cardinality unlimited, no subdelimiters.
        self.field_definitions = {
            'field_foo': {
                'cardinality': -1,
            }
        }

        simple = workbench_fields.Simple()
        csv_record = collections.OrderedDict()
        csv_record['id'] = "003"
        csv_record['field_foo'] = "First value"
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
                {'value': "First value"}
            ]
        }
        self.assertDictEqual(self.node, expected_node)

        # Create a node with a simple field of cardinality unlimited, with subdelimiters.
        simple = workbench_fields.Simple()
        csv_record = collections.OrderedDict()
        csv_record['id'] = "004"
        csv_record['field_foo'] = "First value|Second value"
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
                {'value': "First value"},
                {'value': "Second value"}
            ]
        }
        self.assertDictEqual(self.node, expected_node)

        # Create a node with a simple field of cardinality limited, no subdelimiters.
        self.field_definitions = {
            'field_foo': {
                'cardinality': 2,
            }
        }

        simple = workbench_fields.Simple()
        csv_record = collections.OrderedDict()
        csv_record['id'] = "005"
        csv_record['field_foo'] = "First value"
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
                {'value': "First value"}
            ]
        }
        self.assertDictEqual(self.node, expected_node)

        # Create a node with a simple field of cardinality limited, with subdelimiters.
        simple = workbench_fields.Simple()
        csv_record = collections.OrderedDict()
        csv_record['id'] = "006"
        csv_record['field_foo'] = "First 006 value|Second 006 value|Third 006 value"
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
                {'value': "First 006 value"},
                {'value': "Second 006 value"}
            ]
        }
        self.assertDictEqual(self.node, expected_node)

    def test_update_with_simple_field(self):
        # Update a node with a simple field of cardinality 1, no subdelimiters.
        self.field_definitions = {
            'field_foo': {
                'cardinality': 1,
            }
        }

        simple = workbench_fields.Simple()
        csv_record = collections.OrderedDict()
        csv_record['field_foo'] = "Field foo new value"
        csv_record['node_id'] = 1
        node_field_values = [{'value': "Field foo original value"}]
        self.node = simple.update(self.config, self.field_definitions, self.node, csv_record, "field_foo", node_field_values)
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
                {'value': "Field foo new value"}
            ]
        }
        self.assertDictEqual(self.node, expected_node)

        # Update a node with a simple field of cardinality 1, with subdelimiters.
        simple = workbench_fields.Simple()
        csv_record = collections.OrderedDict()
        csv_record['field_foo'] = "Field foo new value|Second foo new value"
        csv_record['node_id'] = 2
        node_field_values = [{'value': "Field foo original value"}]
        self.node = simple.update(self.config, self.field_definitions, self.node, csv_record, "field_foo", node_field_values)
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
                {'value': "Field foo new value"}
            ]
        }
        self.assertDictEqual(self.node, expected_node)
'''
        # Update a node with a simple field of cardinality unlimited, no subdelimiters.
        self.field_definitions = {
            'field_foo': {
                'cardinality': -1,
            }
        }

        simple = workbench_fields.Simple()
        csv_record = collections.OrderedDict()
        csv_record['id'] = "003"
        csv_record['field_foo'] = "First value"
        self.node = simple.update(self.config, self.field_definitions, self.node, csv_record, "field_foo")
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
                {'value': "First value"}
            ]
        }
        self.assertDictEqual(self.node, expected_node)

        # Update a node with a simple field of cardinality unlimited, with subdelimiters.
        simple = workbench_fields.Simple()
        csv_record = collections.OrderedDict()
        csv_record['id'] = "004"
        csv_record['field_foo'] = "First value|Second value"
        self.node = simple.update(self.config, self.field_definitions, self.node, csv_record, "field_foo")
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
                {'value': "First value"},
                {'value': "Second value"}
            ]
        }
        self.assertDictEqual(self.node, expected_node)

        # Create a node with a simple field of cardinality limited, no subdelimiters.
        self.field_definitions = {
            'field_foo': {
                'cardinality': 2,
            }
        }

        simple = workbench_fields.Simple()
        csv_record = collections.OrderedDict()
        csv_record['id'] = "005"
        csv_record['field_foo'] = "First value"
        self.node = simple.update(self.config, self.field_definitions, self.node, csv_record, "field_foo")
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
                {'value': "First value"}
            ]
        }
        self.assertDictEqual(self.node, expected_node)

        # Update a node with a simple field of cardinality limited, with subdelimiters.
        simple = workbench_fields.Simple()
        csv_record = collections.OrderedDict()
        csv_record['id'] = "006"
        csv_record['field_foo'] = "First 006 value|Second 006 value|Third 006 value"
        self.node = simple.update(self.config, self.field_definitions, self.node, csv_record, "field_foo")
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
                {'value': "First 006 value"},
                {'value': "Second 006 value"}
            ]
        }
        self.assertDictEqual(self.node, expected_node)
'''


if __name__ == '__main__':
    unittest.main()
