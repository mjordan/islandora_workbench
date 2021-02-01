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
        node = simple.create(self.config, self.field_definitions, self.node, csv_record, "field_foo")
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
        self.assertDictEqual(node, expected_node)

        # Create a node with a simple field of cardinality 1, with subdelimiters.
        simple = workbench_fields.Simple()
        csv_record = collections.OrderedDict()
        csv_record['id'] = "002"
        csv_record['field_foo'] = "Field foo value|Extraneous value"
        node = simple.create(self.config, self.field_definitions, self.node, csv_record, "field_foo")
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
        self.assertDictEqual(node, expected_node)

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
        node = simple.create(self.config, self.field_definitions, self.node, csv_record, "field_foo")
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
        self.assertDictEqual(node, expected_node)

        # Create a node with a simple field of cardinality unlimited, with subdelimiters.
        simple = workbench_fields.Simple()
        csv_record = collections.OrderedDict()
        csv_record['id'] = "004"
        csv_record['field_foo'] = "First value|Second value"
        node = simple.create(self.config, self.field_definitions, self.node, csv_record, "field_foo")
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
        self.assertDictEqual(node, expected_node)

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
        node = simple.create(self.config, self.field_definitions, self.node, csv_record, "field_foo")
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
        self.assertDictEqual(node, expected_node)

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
        # Update a node with a simple field of cardinality 1, no subdelimiters. Fields with cardinality of 1 are
        # always replaced with incoming values, they are never appended to.
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
        node = simple.update(self.config, self.field_definitions, self.node, csv_record, "field_foo", node_field_values)
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
        self.assertDictEqual(node, expected_node)

        # Update a node with a simple field of cardinality 1, with subdelimiters. Fields with cardinality of 1 are
        # always replaced with incoming values, they are never appended to.
        simple = workbench_fields.Simple()
        csv_record = collections.OrderedDict()
        csv_record['field_foo'] = "Field foo new value|Second foo new value"
        csv_record['node_id'] = 2
        node_field_values = [{'value': "Field foo original value"}]
        node = simple.update(self.config, self.field_definitions, self.node, csv_record, "field_foo", node_field_values)
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
        self.assertDictEqual(node, expected_node)

        # Update a node with a simple field of cardinality unlimited, no subdelimiters. update_mode is 'replace'.
        self.field_definitions = {
            'field_foo': {
                'cardinality': -1,
            }
        }

        simple = workbench_fields.Simple()
        csv_record = collections.OrderedDict()
        csv_record['node_id'] = 3
        csv_record['field_foo'] = "New value"
        node_field_values = [{'value': "Field foo original value"}]
        self.config['update_mode'] = 'replace'
        node = simple.update(self.config, self.field_definitions, self.node, csv_record, "field_foo", node_field_values)
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
                {'value': "New value"}
            ]
        }
        self.assertDictEqual(node, expected_node)

        # Update a node with a simple field of cardinality unlimited, with subdelimiters. update_mode is 'replace'.
        self.field_definitions = {
            'field_foo': {
                'cardinality': -1,
            }
        }

        simple = workbench_fields.Simple()
        csv_record = collections.OrderedDict()
        csv_record['node_id'] = 4
        csv_record['field_foo'] = "New value 1|New value 2"
        node_field_values = [{'value': "Field foo original value"}]
        self.config['update_mode'] = 'replace'
        node = simple.update(self.config, self.field_definitions, self.node, csv_record, "field_foo", node_field_values)
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
                {'value': "New value 1"},
                {'value': "New value 2"}
            ]
        }
        self.assertDictEqual(node, expected_node)

        # Update a node with a simple field of cardinality unlimited, no subdelimiters. update_mode is 'append'.
        self.field_definitions = {
            'field_foo': {
                'cardinality': -1,
            }
        }

        simple = workbench_fields.Simple()
        csv_record = collections.OrderedDict()
        csv_record['node_id'] = 5
        csv_record['field_foo'] = "New value"
        node_field_values = [{'value': "Field foo original value"}]
        self.config['update_mode'] = 'append'
        node = simple.update(self.config, self.field_definitions, self.node, csv_record, "field_foo", node_field_values)
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
                {'value': "Field foo original value"},
                {'value': "New value"}

            ]
        }
        self.assertDictEqual(node, expected_node)

        # Update a node with a simple field of cardinality unlimited, with subdelimiters. update_mode is 'append'.
        self.field_definitions = {
            'field_foo': {
                'cardinality': -1,
            }
        }

        simple = workbench_fields.Simple()
        csv_record = collections.OrderedDict()
        csv_record['node_id'] = 6
        csv_record['field_foo'] = "New value 1|New value 2"
        node_field_values = [{'value': "Field foo original value"}]
        self.config['update_mode'] = 'append'
        node = simple.update(self.config, self.field_definitions, self.node, csv_record, "field_foo", node_field_values)
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
                {'value': "Field foo original value"},
                {'value': "New value 1"},
                {'value': "New value 2"}

            ]
        }
        self.assertDictEqual(node, expected_node)

        # Update a node with a simple field of cardinality limited, no subdelimiters. update_mode is 'replace'.
        self.field_definitions = {
            'field_foo': {
                'cardinality': 2,
            }
        }

        simple = workbench_fields.Simple()
        csv_record = collections.OrderedDict()
        csv_record['node_id'] = 7
        csv_record['field_foo'] = "New value"
        node_field_values = [{'value': "Field foo original value"}]
        self.config['update_mode'] = 'replace'
        node = simple.update(self.config, self.field_definitions, self.node, csv_record, "field_foo", node_field_values)
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
                {'value': "New value"}
            ]
        }
        self.assertDictEqual(node, expected_node)

        # Update a node with a simple field of cardinality limited, no subdelimiters. update_mode is 'append'.
        self.field_definitions = {
            'field_foo': {
                'cardinality': 2,
            }
        }

        simple = workbench_fields.Simple()
        csv_record = collections.OrderedDict()
        csv_record['node_id'] = 8
        csv_record['field_foo'] = "New value"
        node_field_values = [{'value': "Field foo original value"}]
        self.config['update_mode'] = 'append'
        node = simple.update(self.config, self.field_definitions, self.node, csv_record, "field_foo", node_field_values)
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
                {'value': "Field foo original value"},
                {'value': "New value"}
            ]
        }
        self.assertDictEqual(node, expected_node)

        # Update a node with a simple field of cardinality limited, with subdelimiters. update_mode is 'replace'.
        simple = workbench_fields.Simple()
        csv_record = collections.OrderedDict()
        csv_record['node_id'] = 9
        csv_record['field_foo'] = "First 009 value|Second 009 value|Third 009 value"
        node_field_values = [{'value': "Field foo original value"}]
        self.config['update_mode'] = 'replace'
        node = simple.update(self.config, self.field_definitions, self.node, csv_record, "field_foo", node_field_values)
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
                {'value': "First 009 value"},
                {'value': "Second 009 value"}
            ]
        }
        self.assertDictEqual(node, expected_node)

        # Update a node with a simple field of cardinality limited, with subdelimiters. update_mode is 'append'.
        self.field_definitions = {
            'field_foo': {
                'cardinality': 3,
            }
        }

        simple = workbench_fields.Simple()
        csv_record = collections.OrderedDict()
        csv_record['node_id'] = 10
        csv_record['field_foo'] = "First 009 value|Second 009 value|Third 009 value"
        node_field_values = [{'value': "Field foo original value"}]
        self.config['update_mode'] = 'append'
        node = simple.update(self.config, self.field_definitions, self.node, csv_record, "field_foo", node_field_values)
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
                {'value': "Field foo original value"},
                {'value': "First 009 value"},
                {'value': "Second 009 value"}
            ]
        }
        self.assertDictEqual(node, expected_node)


if __name__ == '__main__':
    unittest.main()
