"""unittest tests for Drupal REST JSON field handlers.
"""

import sys
import os
import io
import unittest
import collections

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import workbench_fields


class TestSimpleField(unittest.TestCase):

    def setUp(self):
        self.config = {
            'subdelimiter': '|',
            'id_field': 'id'
        }

    def test_create_with_simple_field(self):
        existing_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ]
        }

        # Create a node with a simple field of cardinality 1, no subdelimiters.
        self.field_definitions = {
            'field_foo': {
                'cardinality': 1,
            }
        }

        field = workbench_fields.SimpleField()
        csv_record = collections.OrderedDict()
        csv_record['id'] = "simple_001"
        csv_record['field_foo'] = "Field foo value"
        node = field.create(self.config, self.field_definitions, existing_node, csv_record, "field_foo")
        expected_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
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
        with self.assertLogs() as message:
            field = workbench_fields.SimpleField()
            csv_record = collections.OrderedDict()
            csv_record['id'] = "simple_002"
            csv_record['field_foo'] = "Field foo value|Extraneous value"
            node = field.create(self.config, self.field_definitions, existing_node, csv_record, "field_foo")
            expected_node = {
                'type': [
                    {'target_id': 'islandora_object', 'target_type': 'node_type'}
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
            self.assertRegex(str(message.output), r'simple_002 would exceed maximum number of allowed values \(1\)')

        # Create a node with a simple field of cardinality unlimited, no subdelimiters.
        self.field_definitions = {
            'field_foo': {
                'cardinality': -1,
            }
        }

        field = workbench_fields.SimpleField()
        csv_record = collections.OrderedDict()
        csv_record['id'] = "simple_003"
        csv_record['field_foo'] = "First value"
        node = field.create(self.config, self.field_definitions, existing_node, csv_record, "field_foo")
        expected_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
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
        field = workbench_fields.SimpleField()
        csv_record = collections.OrderedDict()
        csv_record['id'] = "simple_004"
        csv_record['field_foo'] = "First value|Second value|First value"
        node = field.create(self.config, self.field_definitions, existing_node, csv_record, "field_foo")
        expected_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
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

        field = workbench_fields.SimpleField()
        csv_record = collections.OrderedDict()
        csv_record['id'] = "simple_005"
        csv_record['field_foo'] = "First value"
        node = field.create(self.config, self.field_definitions, existing_node, csv_record, "field_foo")
        expected_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
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
        with self.assertLogs() as message:
            field = workbench_fields.SimpleField()
            csv_record = collections.OrderedDict()
            csv_record['id'] = "simple_006"
            csv_record['field_foo'] = "First 006 value|First 006 value|Second 006 value|Third 006 value"
            # csv_record['field_foo'] = "First 006 value|Second 006 value|Third 006 value"
            self.node = field.create(self.config, self.field_definitions, existing_node, csv_record, "field_foo")
            expected_node = {
                'type': [
                    {'target_id': 'islandora_object', 'target_type': 'node_type'}
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
            self.assertRegex(str(message.output), r'simple_006 would exceed maximum number of allowed values \(2\)')

    def test_simple_field_title_update_replace(self):
        # Update the node title, first with an 'update_mode' of replace.
        existing_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Old title - replace."}
            ],
            'status': [
                {'value': 1}
            ]
        }

        self.field_definitions = {
            'title': {
                'cardinality': 1,
            }
        }

        self.config['update_mode'] = 'replace'

        field = workbench_fields.SimpleField()
        csv_record = collections.OrderedDict()
        csv_record['title'] = "New title - replace."
        csv_record['node_id'] = 1
        node = field.update(self.config, self.field_definitions, existing_node, csv_record, "title", existing_node["title"])
        expected_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "New title - replace."}
            ],
            'status': [
                {'value': 1}
            ]
        }
        self.assertDictEqual(node, expected_node)

    def test_simple_field_title_update_append(self):
        # Update the node title, first with an update_mode of 'append'.
        existing_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Old title - append."}
            ],
            'status': [
                {'value': 1}
            ]
        }

        self.field_definitions = {
            'title': {
                'cardinality': 1,
            }
        }

        self.config['update_mode'] = 'append'

        with self.assertLogs() as message:
            field = workbench_fields.SimpleField()
            csv_record = collections.OrderedDict()
            csv_record['title'] = "New title - append."
            csv_record['node_id'] = 1
            node = field.update(self.config, self.field_definitions, existing_node, csv_record, "title", existing_node["title"])
            expected_node = {
                'type': [
                    {'target_id': 'islandora_object', 'target_type': 'node_type'}
                ],
                'title': [
                    {'value': "Old title - append."}
                ],
                'status': [
                    {'value': 1}
                ]
            }
            self.assertDictEqual(node, expected_node)
            self.assertRegex(str(message.output), r'record 1 would exceed maximum number of allowed values \(1\)')

    def test_simple_field_update_replace_cardinality_1_no_subdelims(self):
        existing_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {'value': "Field foo original value"}
            ]
        }

        self.field_definitions = {
            'field_foo': {
                'cardinality': 1,
            }
        }

        self.config['update_mode'] = 'replace'

        field = workbench_fields.SimpleField()
        csv_record = collections.OrderedDict()
        csv_record['field_foo'] = "Field foo new value"
        csv_record['node_id'] = 1
        node = field.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", existing_node["field_foo"])
        expected_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
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

    def test_simple_field_update_append_cardinality_1_no_subdelims(self):
        existing_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {'value': "Field foo original value"}
            ]
        }

        self.field_definitions = {
            'field_foo': {
                'cardinality': 1,
            }
        }

        self.config['update_mode'] = 'append'

        with self.assertLogs() as message:
            field = workbench_fields.SimpleField()
            csv_record = collections.OrderedDict()
            csv_record['field_foo'] = "Field foo new value"
            csv_record['node_id'] = 1
            node = field.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", existing_node["field_foo"])
            expected_node = {
                'type': [
                    {'target_id': 'islandora_object', 'target_type': 'node_type'}
                ],
                'title': [
                    {'value': "Test node"}
                ],
                'status': [
                    {'value': 1}
                ],
                'field_foo': [
                    {'value': "Field foo original value"}
                ]
            }
            self.assertDictEqual(node, expected_node)
            self.assertRegex(str(message.output), r'record 1 would exceed maximum number of allowed values \(1\)')

    def test_simple_field_update_replace_cardinality_1_with_subdelims(self):
        existing_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {'value': "Field foo original value"}
            ]
        }

        self.field_definitions = {
            'field_foo': {
                'cardinality': 1,
            }
        }

        self.config['update_mode'] = 'replace'

        with self.assertLogs() as message:
            field = workbench_fields.SimpleField()
            csv_record = collections.OrderedDict()
            csv_record['field_foo'] = "Field foo new value|Second foo new value"
            csv_record['node_id'] = 2
            node_field_values = [{'value': "Field foo original value"}]
            node = field.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", node_field_values)
            expected_node = {
                'type': [
                    {'target_id': 'islandora_object', 'target_type': 'node_type'}
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
            self.assertRegex(str(message.output), r'record 2 would exceed maximum number of allowed values \(1\)')

    def test_simple_field_update_replace_cardinality_unlimited_no_subdelims(self):
        existing_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {'value': "Field foo original value"}
            ]
        }

        self.field_definitions = {
            'field_foo': {
                'cardinality': -1,
            }
        }

        self.config['update_mode'] = 'replace'

        field = workbench_fields.SimpleField()
        csv_record = collections.OrderedDict()
        csv_record['node_id'] = 3
        csv_record['field_foo'] = "New value"
        self.config['update_mode'] = 'replace'
        node = field.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", existing_node["field_foo"])
        expected_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
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

    def test_simple_field_update_replace_cardinality_unlimited_with_subdelims(self):
        existing_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {'value': "Field foo original value"}
            ]
        }

        self.field_definitions = {
            'field_foo': {
                'cardinality': -1,
            }
        }

        self.config['update_mode'] = 'replace'

        field = workbench_fields.SimpleField()
        csv_record = collections.OrderedDict()
        csv_record['node_id'] = 4
        csv_record['field_foo'] = "New value 1|New value 2|New value 2"
        node = field.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", existing_node["field_foo"])
        expected_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
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

    def test_simple_field_update_append_cardinality_unlimited_no_subdelims(self):
        self.field_definitions = {
            'field_foo': {
                'cardinality': -1,
            }
        }

        self.config['update_mode'] = 'append'

        existing_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {'value': "Field foo original value"}
            ]
        }

        field = workbench_fields.SimpleField()
        csv_record = collections.OrderedDict()
        csv_record['node_id'] = 5
        csv_record['field_foo'] = "New value"
        node = field.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", existing_node["field_foo"])
        expected_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
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

        existing_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
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

        field = workbench_fields.SimpleField()
        csv_record = collections.OrderedDict()
        csv_record['node_id'] = 55
        csv_record['field_foo'] = "New value"
        node = field.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", existing_node["field_foo"])
        expected_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
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

    def test_simple_field_update_append_cardinality_unlimited_with_subdelims(self):
        existing_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {'value': "Field foo original value"}
            ]
        }

        self.field_definitions = {
            'field_foo': {
                'cardinality': -1,
            }
        }

        self.config['update_mode'] = 'append'

        field = workbench_fields.SimpleField()
        csv_record = collections.OrderedDict()
        csv_record['node_id'] = 6
        csv_record['field_foo'] = "New value 1|New value 2|New value 1"
        node = field.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", existing_node["field_foo"])
        expected_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
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

    def test_simple_field_update_replace_cardinality_limited_no_subdelims(self):
        existing_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {'value': "Field foo original value"}
            ]
        }

        self.field_definitions = {
            'field_foo': {
                'cardinality': 2,
            }
        }

        self.config['update_mode'] = 'replace'

        field = workbench_fields.SimpleField()
        csv_record = collections.OrderedDict()
        csv_record['node_id'] = 7
        csv_record['field_foo'] = "New value"
        node = field.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", existing_node["field_foo"])
        expected_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
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

    def test_simple_field_update_append_cardinality_limited_no_subdelims(self):
        existing_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {'value': "Field foo original value 1"},
                {'value': "Field foo original value 2"}
            ]
        }

        self.field_definitions = {
            'field_foo': {
                'cardinality': 2,
            }
        }

        self.config['update_mode'] = 'append'

        with self.assertLogs() as message:
            field = workbench_fields.SimpleField()
            csv_record = collections.OrderedDict()
            csv_record['node_id'] = 8
            csv_record['field_foo'] = "New value 3"
            node = field.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", existing_node["field_foo"])
            expected_node = {
                'type': [
                    {'target_id': 'islandora_object', 'target_type': 'node_type'}
                ],
                'title': [
                    {'value': "Test node"}
                ],
                'status': [
                    {'value': 1}
                ],
                'field_foo': [
                    {'value': "Field foo original value 1"},
                    {'value': "Field foo original value 2"}
                ]
            }
            self.assertDictEqual(node, expected_node)
            self.assertRegex(str(message.output), r'record 8 would exceed maximum number of allowed values \(2\)')

    def test_simple_field_update_replace_cardinality_limited_with_subdelims(self):
        existing_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {'value': "Field foo original value 1"},
                {'value': "Field foo original value 2"}
            ]
        }

        self.field_definitions = {
            'field_foo': {
                'cardinality': 2,
            }
        }

        self.config['update_mode'] = 'replace'

        with self.assertLogs() as message:
            field = workbench_fields.SimpleField()
            csv_record = collections.OrderedDict()
            csv_record['node_id'] = 9
            csv_record['field_foo'] = "First node 9 value|Second node 9 value|Third node 9 value"
            node = field.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", existing_node["field_foo"])
            expected_node = {
                'type': [
                    {'target_id': 'islandora_object', 'target_type': 'node_type'}
                ],
                'title': [
                    {'value': "Test node"}
                ],
                'status': [
                    {'value': 1}
                ],
                'field_foo': [
                    {'value': "First node 9 value"},
                    {'value': "Second node 9 value"}
                ]
            }
            self.assertDictEqual(node, expected_node)
            self.assertRegex(str(message.output), r'record 9 would exceed maximum number of allowed values \(2\)')

    def test_simple_field_update_append_cardinality_limited_with_subdelims(self):
        existing_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {'value': "Field foo original value 1"}
            ]
        }

        self.field_definitions = {
            'field_foo': {
                'cardinality': 3,
            }
        }

        self.config['update_mode'] = 'append'

        with self.assertLogs() as message:
            field = workbench_fields.SimpleField()
            csv_record = collections.OrderedDict()
            csv_record['node_id'] = 10
            csv_record['field_foo'] = "First node 10 value|First node 10 value|Second node 10 value|Third node 10 value"
            node = field.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", existing_node["field_foo"])
            expected_node = {
                'type': [
                    {'target_id': 'islandora_object', 'target_type': 'node_type'}
                ],
                'title': [
                    {'value': "Test node"}
                ],
                'status': [
                    {'value': 1}
                ],
                'field_foo': [
                    {'value': "Field foo original value 1"},
                    {'value': "First node 10 value"},
                    {'value': "Second node 10 value"}
                ]
            }
            self.assertDictEqual(node, expected_node)
            self.assertRegex(str(message.output), r'record 10 would exceed maximum number of allowed values \(3\)')

    def test_simple_field_update_delete(self):
        existing_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {'value': "Field foo original value 1"},
                {'value': "Field foo original value 2"}
            ]
        }

        self.field_definitions = {
            'field_foo': {
                'cardinality': 3,
            }
        }

        self.config['update_mode'] = 'delete'

        field = workbench_fields.SimpleField()
        csv_record = collections.OrderedDict()
        csv_record['node_id'] = 11
        csv_record['field_foo'] = "First node 11 value|Second node 11 value"
        node = field.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", existing_node["field_foo"])
        expected_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': []
        }
        self.assertDictEqual(node, expected_node)

    def test_simple_field_dudupe_values(self):
        # First, split values from CSV.
        input = ['first value', 'first value', 'second value', 'second value', 'third value']
        field = workbench_fields.SimpleField()
        output = field.dedupe_values(input)
        self.assertEqual(output, ['first value', 'second value', 'third value'])

        # Then fully formed dictionaries.
        input = [{'value': 'First string'}, {'value': 'Second string'}, {'value': 'First string'}, {'value': 'Second string'}, {'value': 'Third string'}]
        field = workbench_fields.SimpleField()
        output = field.dedupe_values(input)
        self.assertEqual(output, [{'value': 'First string'}, {'value': 'Second string'}, {'value': 'Third string'}])


class TestGeolocationField(unittest.TestCase):

    def setUp(self):
        self.maxDiff = None
        self.config = {
            'subdelimiter': '|',
            'id_field': 'id'
        }

    def test_create_with_geolocation_field(self):
        existing_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ]
        }

        # Create a node with a geolocation field of cardinality 1, no subdelimiters.
        self.field_definitions = {
            'field_foo': {
                'cardinality': 1,
            }
        }

        field = workbench_fields.GeolocationField()
        csv_record = collections.OrderedDict()
        csv_record['id'] = "geo_001"
        csv_record['field_foo'] = "48.16667,-123.93333"
        node = field.create(self.config, self.field_definitions, existing_node, csv_record, "field_foo")
        expected_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {'lat': '48.16667', 'lng': '-123.93333'}
            ]
        }
        self.assertDictEqual(node, expected_node)

        # Create a node with a geolocation field of cardinality 1, with subdelimiters.
        with self.assertLogs() as message:
            field = workbench_fields.GeolocationField()
            csv_record = collections.OrderedDict()
            csv_record['id'] = "geo_002"
            csv_record['field_foo'] = "47.16667,-123.93333|49.1222,-123.99999"
            node = field.create(self.config, self.field_definitions, existing_node, csv_record, "field_foo")
            expected_node = {
                'type': [
                    {'target_id': 'islandora_object', 'target_type': 'node_type'}
                ],
                'title': [
                    {'value': "Test node"}
                ],
                'status': [
                    {'value': 1}
                ],
                'field_foo': [
                    {'lat': '47.16667', 'lng': '-123.93333'}
                ]
            }
            self.assertDictEqual(node, expected_node)
            self.assertRegex(str(message.output), r'for record geo_002 would exceed maximum number of allowed values \(1\)')

        # Create a node with a geolocation field of cardinality unlimited, no subdelimiters.
        self.field_definitions = {
            'field_foo': {
                'cardinality': -1,
            }
        }

        field = workbench_fields.GeolocationField()
        csv_record = collections.OrderedDict()
        csv_record['id'] = "geo_003"
        csv_record['field_foo'] = "59.16667,-123.93333"
        node = field.create(self.config, self.field_definitions, existing_node, csv_record, "field_foo")
        expected_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {'lat': '59.16667', 'lng': '-123.93333'}
            ]
        }
        self.assertDictEqual(node, expected_node)

        # Create a node with a geolocation field of cardinality unlimited, with subdelimiters.
        self.field_definitions = {
            'field_foo': {
                'cardinality': -1,
            }
        }

        field = workbench_fields.GeolocationField()
        csv_record = collections.OrderedDict()
        csv_record['id'] = "geo_004"
        csv_record['field_foo'] = "59.16667,-123.93333|69.16667,-123.93333|69.16667,-123.93333"
        node = field.create(self.config, self.field_definitions, existing_node, csv_record, "field_foo")
        expected_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {'lat': '59.16667', 'lng': '-123.93333'},
                {'lat': '69.16667', 'lng': '-123.93333'}
            ]
        }
        self.assertDictEqual(node, expected_node)

        # Create a node with a geolocation field of cardinality limited, no subdelimiters.
        self.field_definitions = {
            'field_foo': {
                'cardinality': 2,
            }
        }

        field = workbench_fields.GeolocationField()
        csv_record = collections.OrderedDict()
        csv_record['id'] = "geo_005"
        csv_record['field_foo'] = "58.16667,-123.93333"
        node = field.create(self.config, self.field_definitions, existing_node, csv_record, "field_foo")
        expected_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {'lat': '58.16667', 'lng': '-123.93333'}
            ]
        }
        self.assertDictEqual(node, expected_node)

        # Create a node with a geolocation field of cardinality limited, with subdelimiters.
        self.field_definitions = {
            'field_foo': {
                'cardinality': 3,
            }
        }

        with self.assertLogs() as message:
            field = workbench_fields.GeolocationField()
            csv_record = collections.OrderedDict()
            csv_record['id'] = "geo_006"
            csv_record['field_foo'] = "51.16667,-123.93333|61.16667,-123.93333|61.16667,-123.93333|63.16667,-123.93333|61.16667,-123.93334"
            node = field.create(self.config, self.field_definitions, existing_node, csv_record, "field_foo")
            expected_node = {
                'type': [
                    {'target_id': 'islandora_object', 'target_type': 'node_type'}
                ],
                'title': [
                    {'value': "Test node"}
                ],
                'status': [
                    {'value': 1}
                ],
                'field_foo': [
                    {'lat': '51.16667', 'lng': '-123.93333'},
                    {'lat': '61.16667', 'lng': '-123.93333'},
                    {'lat': '63.16667', 'lng': '-123.93333'}
                ]
            }
            self.assertDictEqual(node, expected_node)
            self.assertRegex(str(message.output), r'for record geo_006 would exceed maximum number of allowed values \(3\)')

    def test_geolocation_field_update_replace_cardinality_1_no_subdelims(self):
        existing_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ]
        }

        self.field_definitions = {
            'field_foo': {
                'cardinality': 1,
            }
        }

        self.config['update_mode'] = 'replace'

        geolocation = workbench_fields.GeolocationField()
        csv_record = collections.OrderedDict()
        csv_record['node_id'] = 100
        csv_record['field_foo'] = "50.16667,-123.93333"
        node_field_values = [{"lat": "49.16667", "lng": "-122.93333"}]
        node = geolocation.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", node_field_values)
        expected_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {'lat': '50.16667', 'lng': '-123.93333'}
            ]
        }
        self.assertDictEqual(node, expected_node)

    def test_geolocation_field_update_replace_cardinality_1_with_subdelims(self):
        existing_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ]
        }

        self.field_definitions = {
            'field_foo': {
                'cardinality': 1,
            }
        }

        self.config['update_mode'] = 'replace'

        with self.assertLogs() as message:
            geolocation = workbench_fields.GeolocationField()
            csv_record = collections.OrderedDict()
            csv_record['node_id'] = 101
            csv_record['field_foo'] = "50.16667,-123.93333|46.16667,-113.93333"
            node_field_values = [{"lat": "49.16667", "lng": "-122.93333"}]
            node = geolocation.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", node_field_values)
            expected_node = {
                'type': [
                    {'target_id': 'islandora_object', 'target_type': 'node_type'}
                ],
                'title': [
                    {'value': "Test node"}
                ],
                'status': [
                    {'value': 1}
                ],
                'field_foo': [
                    {'lat': '50.16667', 'lng': '-123.93333'}
                ]
            }
            self.assertDictEqual(node, expected_node)
            self.assertRegex(str(message.output), r'for record 101 would exceed maximum number of allowed values \(1\)')

    def test_geolocation_field_update_replace_cardinality_unlimited_no_subdelims(self):
        existing_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ]
        }

        self.field_definitions = {
            'field_foo': {
                'cardinality': -1,
            }
        }

        self.config['update_mode'] = 'replace'

        geolocation = workbench_fields.GeolocationField()
        csv_record = collections.OrderedDict()
        csv_record['node_id'] = 102
        csv_record['field_foo'] = "55.26667,-113.93333"
        node_field_values = [{"lat": "49.16667", "lng": "-122.93333"}]
        node = geolocation.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", node_field_values)
        expected_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {'lat': '55.26667', 'lng': '-113.93333'}
            ]
        }
        self.assertDictEqual(node, expected_node)

    def test_geolocation_field_update_replace_cardinality_unlimited_with_subdelims(self):
        existing_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ]
        }

        self.config['update_mode'] = 'replace'
        self.field_definitions = {
            'field_foo': {
                'cardinality': -1,
            }
        }

        geolocation = workbench_fields.GeolocationField()
        csv_record = collections.OrderedDict()
        csv_record['node_id'] = 103
        csv_record['field_foo'] = "55.26661,-113.93331|51.26667,-111.93333|55.26661,-113.93331"
        node_field_values = [{"lat": "49.16667", "lng": "-122.93333"}]
        node103 = geolocation.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", node_field_values)
        expected_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {'lat': '55.26661', 'lng': '-113.93331'},
                {'lat': '51.26667', 'lng': '-111.93333'}
            ]
        }
        self.assertDictEqual(node103, expected_node)

    def test_geolocation_field_update_append_cardinality_unlimited_no_subdelims(self):
        existing_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {"lat": "49.1", "lng": "-122.9"}
            ]
        }

        self.field_definitions = {
            'field_foo': {
                'cardinality': -1,
            }
        }

        self.config['update_mode'] = 'append'

        geolocation = workbench_fields.GeolocationField()
        csv_record = collections.OrderedDict()
        csv_record['node_id'] = 104
        csv_record['field_foo'] = "35.2,-99.9"
        node = geolocation.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", existing_node["field_foo"])
        expected_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {'lat': '49.1', 'lng': '-122.9'},
                {'lat': '35.2', 'lng': '-99.9'}
            ]
        }
        self.assertDictEqual(node, expected_node)

    def test_geolocation_field_update_append_cardinality_unlimited_with_subdelims(self):
        existing_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {'lat': "49.1", 'lng': "-122.9"}
            ]
        }

        self.field_definitions = {
            'field_foo': {
                'cardinality': -1,
            }
        }

        geolocation = workbench_fields.GeolocationField()
        csv_record = collections.OrderedDict()
        self.config['update_mode'] = 'append'
        csv_record['node_id'] = 105
        csv_record['field_foo'] = "56.2,-113.9|51.2,-100.9|51.2,-100.9"
        node = geolocation.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", existing_node["field_foo"])
        expected_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {'lat': '49.1', 'lng': '-122.9'},
                {'lat': '56.2', 'lng': '-113.9'},
                {'lat': '51.2', 'lng': '-100.9'}
            ]
        }
        self.assertDictEqual(node, expected_node)

    def test_geolocation_field_update_replace_cardinality_limited_no_subdelims(self):
        existing_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ]
        }

        self.field_definitions = {
            'field_foo': {
                'cardinality': 2,
            }
        }

        self.config['update_mode'] = 'replace'

        geolocation = workbench_fields.GeolocationField()
        csv_record = collections.OrderedDict()
        csv_record['node_id'] = 106
        csv_record['field_foo'] = "53.26667,-133.93333"
        node_field_values = [{"lat": "43.16667", "lng": "-123.63"}]
        node = geolocation.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", node_field_values)
        expected_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {'lat': '53.26667', 'lng': '-133.93333'}
            ]
        }
        self.assertDictEqual(node, expected_node)

    def test_geolocation_field_update_replace_cardinality_limited_with_subdelims(self):
        existing_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {"lat": "43.16667", "lng": "-123.63"}
            ]
        }

        self.field_definitions = {
            'field_foo': {
                'cardinality': 2,
            }
        }

        self.config['update_mode'] = 'replace'

        with self.assertLogs() as message:
            geolocation = workbench_fields.GeolocationField()
            csv_record = collections.OrderedDict()
            csv_record['node_id'] = 106
            csv_record['field_foo'] = "53.26667,-133.93333|51.34,-111.1|51.51,-111.999|53.26667,-133.93333"
            node = geolocation.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", existing_node["field_foo"])
            expected_node = {
                'type': [
                    {'target_id': 'islandora_object', 'target_type': 'node_type'}
                ],
                'title': [
                    {'value': "Test node"}
                ],
                'status': [
                    {'value': 1}
                ],
                'field_foo': [
                    {'lat': '53.26667', 'lng': '-133.93333'},
                    {'lat': '51.34', 'lng': '-111.1'}
                ]
            }
            self.assertDictEqual(node, expected_node)
            self.assertRegex(str(message.output), r'for record 106 would exceed maximum number of allowed values \(2\)')

    def test_geolocation_field_update_append_cardinality_limited_no_subdelims(self):
        existing_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {"lat": "47.1", "lng": "-127.6"}
            ]
        }

        self.field_definitions = {
            'field_foo': {
                'cardinality': 1,
            }
        }

        self.config['update_mode'] = 'append'

        with self.assertLogs() as message:
            geolocation = workbench_fields.GeolocationField()
            csv_record = collections.OrderedDict()
            csv_record['node_id'] = 107
            csv_record['field_foo'] = "57.2,-133.7"
            node_107 = geolocation.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", existing_node["field_foo"])
            expected_node = {
                'type': [
                    {'target_id': 'islandora_object', 'target_type': 'node_type'}
                ],
                'title': [
                    {'value': "Test node"}
                ],
                'status': [
                    {'value': 1}
                ],
                'field_foo': [
                    {'lat': '47.1', 'lng': '-127.6'}
                ]
            }
            self.assertDictEqual(node_107, expected_node)
            self.assertRegex(str(message.output), r'for record 107 would exceed maximum number of allowed values \(1\)')

        self.config['update_mode'] = 'append'
        self.field_definitions = {
            'field_foo': {
                'cardinality': 3,
            }
        }

    def test_geolocation_field_update_replace_cardinality_limited_with_subdelims(self):
        existing_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {"lat": "49.16667", "lng": "-122.93333"}
            ]
        }

        self.field_definitions = {
            'field_foo': {
                'cardinality': 2,
            }
        }

        self.config['update_mode'] = 'replace'

        with self.assertLogs() as message:
            geolocation = workbench_fields.GeolocationField()
            csv_record = collections.OrderedDict()
            csv_record['node_id'] = 108
            csv_record['field_foo'] = "55.80,-113.80|55.82,-113.82|55.82,-113.82|55.83,-113.83"
            node = geolocation.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", existing_node["field_foo"])
            expected_node = {
                'type': [
                    {'target_id': 'islandora_object', 'target_type': 'node_type'}
                ],
                'title': [
                    {'value': "Test node"}
                ],
                'status': [
                    {'value': 1}
                ],
                'field_foo': [
                    {'lat': '55.80', 'lng': '-113.80'},
                    {'lat': '55.82', 'lng': '-113.82'}
                ]
            }
            self.assertDictEqual(node, expected_node)
            self.assertRegex(str(message.output), r'for record 108 would exceed maximum number of allowed values \(2\)')

    def test_geolocation_field_update_append_cardinality_limited_with_subdelims(self):
        existing_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {"lat": "49.9", "lng": "-122.9"}
            ]
        }

        self.field_definitions = {
            'field_foo': {
                'cardinality': 2,
            }
        }

        self.config['update_mode'] = 'append'

        with self.assertLogs() as message:
            geolocation = workbench_fields.GeolocationField()
            csv_record = collections.OrderedDict()
            csv_record['node_id'] = 109
            csv_record['field_foo'] = "55.90,-113.90|55.92,-113.92|55.92,-113.92|55.93,-113.93"
            node = geolocation.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", existing_node['field_foo'])
            expected_node = {
                'type': [
                    {'target_id': 'islandora_object', 'target_type': 'node_type'}
                ],
                'title': [
                    {'value': "Test node"}
                ],
                'status': [
                    {'value': 1}
                ],
                'field_foo': [
                    {'lat': '49.9', 'lng': '-122.9'},
                    {'lat': '55.90', 'lng': '-113.90'}
                ]
            }
            self.assertDictEqual(node, expected_node)
            self.assertRegex(str(message.output), r'for record 109 would exceed maximum number of allowed values \(2\)')

    def test_geolocation_field_update_delete(self):
        existing_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {"lat": "49.9", "lng": "-122.9"}
            ]
        }

        # Update a node with update_mode of 'delete'.
        self.field_definitions = {
            'field_foo': {
                'cardinality': 2,
            }
        }

        self.config['update_mode'] = 'delete'

        geolocation = workbench_fields.GeolocationField()
        csv_record = collections.OrderedDict()
        csv_record['node_id'] = 110
        csv_record['field_foo'] = "55.90,-113.90|55.92,-113.92|55.93,-113.93"
        node = geolocation.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", existing_node["field_foo"])
        expected_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': []
        }
        self.assertDictEqual(node, expected_node)

    def test_geolocation_field_dudupe_values(self):
        # Split values from CSV.
        input = ['49.16667,-123.93333', '49.25,-124.8', '49.16667,-123.93333', '49.25,-124.8', '49.16667,-123.93333']
        field = workbench_fields.GeolocationField()
        output = field.dedupe_values(input)
        self.assertEqual(output, ['49.16667,-123.93333', '49.25,-124.8'])

        # Dictionaries.
        input = [
            {"lat": "51.9", "lng": "-22.9"},
            {"lat": "58.8", "lng": "-125.3"},
            {"lat": "12.5", "lng": "-122.9"},
            {"lat": "58.8", "lng": "-125.3"},
            {"lat": "58.8", "lng": "-125.3"}]
        field = workbench_fields.GeolocationField()
        output = field.dedupe_values(input)
        self.assertEqual(output, [
            {"lat": "51.9", "lng": "-22.9"},
            {"lat": "58.8", "lng": "-125.3"},
            {"lat": "12.5", "lng": "-122.9"}])


class TestLinkField(unittest.TestCase):

    def setUp(self):
        self.maxDiff = None
        self.config = {
            'subdelimiter': '|',
            'id_field': 'id'
        }

    def test_create_with_link_field(self):
        existing_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ]
        }

        # Create a node with a link field of cardinality 1, no subdelimiters.
        self.field_definitions = {
            'field_foo': {
                'cardinality': 1,
            }
        }

        field = workbench_fields.LinkField()
        csv_record = collections.OrderedDict()
        csv_record['id'] = "link_001"
        csv_record['field_foo'] = "http://www.foo.com%%Foo's website"
        node = field.create(self.config, self.field_definitions, existing_node, csv_record, "field_foo")
        expected_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {'uri': 'http://www.foo.com', 'title': "Foo's website"}
            ]
        }
        self.assertDictEqual(node, expected_node)

        # Create a node with a link field of cardinality 1, with subdelimiters.
        with self.assertLogs() as message:
            field = workbench_fields.LinkField()
            csv_record = collections.OrderedDict()
            csv_record['id'] = "link_002"
            csv_record['field_foo'] = "http://bar.com%%Bar website|http://biz.com%%Biz website"
            node = field.create(self.config, self.field_definitions, existing_node, csv_record, "field_foo")
            expected_node = {
                'type': [
                    {'target_id': 'islandora_object', 'target_type': 'node_type'}
                ],
                'title': [
                    {'value': "Test node"}
                ],
                'status': [
                    {'value': 1}
                ],
                'field_foo': [
                    {'uri': 'http://bar.com', 'title': 'Bar website'}
                ]
            }
            self.assertDictEqual(node, expected_node)
            self.assertRegex(str(message.output), r'for record link_002 would exceed maximum number of allowed values \(1\)')

        # Create a node with a link field of cardinality unlimited, no subdelimiters.
        self.field_definitions = {
            'field_foo': {
                'cardinality': -1,
            }
        }

        field = workbench_fields.LinkField()
        csv_record = collections.OrderedDict()
        csv_record['id'] = "link_003"
        csv_record['field_foo'] = "http://geo003.net%%Geo 3 Blog"
        node = field.create(self.config, self.field_definitions, existing_node, csv_record, "field_foo")
        expected_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {'uri': 'http://geo003.net', 'title': 'Geo 3 Blog'}
            ]
        }
        self.assertDictEqual(node, expected_node)

        # Create a node with a link field of cardinality unlimited, with subdelimiters.
        self.field_definitions = {
            'field_foo': {
                'cardinality': -1,
            }
        }

        field = workbench_fields.LinkField()
        csv_record = collections.OrderedDict()
        csv_record['id'] = "link_004"
        csv_record['field_foo'] = "http://link4-1.net%%Link 004-1 website|http://link4-1.net%%Link 004-1 website|http://link4-2.net%%Link 004-2 website"
        node = field.create(self.config, self.field_definitions, existing_node, csv_record, "field_foo")
        expected_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {'uri': 'http://link4-1.net', 'title': 'Link 004-1 website'},
                {'uri': 'http://link4-2.net', 'title': 'Link 004-2 website'}
            ]
        }
        self.assertDictEqual(node, expected_node)

        # Create a node with a link field of cardinality limited, no subdelimiters.
        self.field_definitions = {
            'field_foo': {
                'cardinality': 2,
            }
        }

        field = workbench_fields.LinkField()
        csv_record = collections.OrderedDict()
        csv_record['id'] = "link_005"
        csv_record['field_foo'] = "http://link5.net%%Link 005 website"
        node = field.create(self.config, self.field_definitions, existing_node, csv_record, "field_foo")
        expected_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {'uri': 'http://link5.net', 'title': 'Link 005 website'}
            ]
        }
        self.assertDictEqual(node, expected_node)

        # Create a node with a link field of cardinality limited, with subdelimiters.
        self.field_definitions = {
            'field_foo': {
                'cardinality': 2,
            }
        }

        with self.assertLogs() as message:
            field = workbench_fields.LinkField()
            csv_record = collections.OrderedDict()
            csv_record['id'] = "link_006"
            csv_record['field_foo'] = "http://link6-1.net%%Link 006-1 website|http://link6-2.net%%Link 006-2 website|http://link6-3.net%%Link 006-3 website"
            node = field.create(self.config, self.field_definitions, existing_node, csv_record, "field_foo")
            expected_node = {
                'type': [
                    {'target_id': 'islandora_object', 'target_type': 'node_type'}
                ],
                'title': [
                    {'value': "Test node"}
                ],
                'status': [
                    {'value': 1}
                ],
                'field_foo': [
                    {'uri': 'http://link6-1.net', 'title': 'Link 006-1 website'},
                    {'uri': 'http://link6-2.net', 'title': 'Link 006-2 website'}
                ]
            }
            self.assertDictEqual(node, expected_node)
            self.assertRegex(str(message.output), r'for record link_006 would exceed maximum number of allowed values \(2\)')

    def test_link_field_update_replace_cardinality_1_no_subdelims(self):
        existing_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': {
                "uri": "http://update1original.net", "title": "Update 1 original's website"
            }
        }

        self.field_definitions = {
            'field_foo': {
                'cardinality': 1,
            }
        }

        self.config['update_mode'] = 'replace'

        field = workbench_fields.LinkField()
        csv_record = collections.OrderedDict()
        csv_record['node_id'] = 100
        csv_record['field_foo'] = "http://update1replacement.net%%Update 1 replacement's website"
        node = field.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", existing_node["field_foo"])
        expected_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {'uri': 'http://update1replacement.net', 'title': "Update 1 replacement's website"}
            ]
        }
        self.assertDictEqual(node, expected_node)

    def test_link_field_update_replace_cardinality_1_with_subdelims(self):
        existing_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': {
                "uri": "http://update2original.net", "title": "Update 2 original's website"
            }
        }

        self.field_definitions = {
            'field_foo': {
                'cardinality': 1,
            }
        }

        self.config['update_mode'] = 'replace'

        with self.assertLogs() as message:
            field = workbench_fields.LinkField()
            csv_record = collections.OrderedDict()
            csv_record['node_id'] = 101
            csv_record['field_foo'] = "http://update2replacement.net%%Update 2 replacement's website|http://update2-1replacement.net%%Update 2-1 replacement's website"
            node = field.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", existing_node["field_foo"])
            expected_node = {
                'type': [
                    {'target_id': 'islandora_object', 'target_type': 'node_type'}
                ],
                'title': [
                    {'value': "Test node"}
                ],
                'status': [
                    {'value': 1}
                ],
                'field_foo': [
                    {'uri': 'http://update2replacement.net', 'title': "Update 2 replacement's website"}
                ]
            }
            self.assertDictEqual(node, expected_node)
            self.assertRegex(str(message.output), r'for record 101 would exceed maximum number of allowed values \(1\)')

    def test_link_field_update_replace_cardinality_unlimited_no_subdelims(self):
        existing_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': {
                "uri": "http://updatenode102original.net", "title": "Update node 102 original's website"
            }
        }

        self.field_definitions = {
            'field_foo': {
                'cardinality': -1,
            }
        }

        self.config['update_mode'] = 'replace'

        field = workbench_fields.LinkField()
        csv_record = collections.OrderedDict()
        csv_record['node_id'] = 102
        csv_record['field_foo'] = "http://updatenode102replace.net%%Update to node 102 replacement's website"
        node = field.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", existing_node["field_foo"])
        expected_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {'uri': 'http://updatenode102replace.net', 'title': "Update to node 102 replacement's website"}
            ]
        }
        self.assertDictEqual(node, expected_node)

    def test_link_field_update_replace_cardinality_unlimited_with_subdelims(self):
        existing_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': {
                "uri": "http://updatenode103original.net", "title": "Update node 103 original's website"
            }
        }

        self.field_definitions = {
            'field_foo': {
                'cardinality': -1,
            }
        }

        self.config['update_mode'] = 'replace'

        field = workbench_fields.LinkField()
        csv_record = collections.OrderedDict()
        csv_record['node_id'] = 103
        csv_record['field_foo'] = "http://updatenode103replace1.net%%103 replacement 1|http://updatenode103replacement2.net%%103 replacement 2|http://updatenode103replacement2.net%%103 replacement 2"
        node = field.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", existing_node["field_foo"])
        expected_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {'uri': 'http://updatenode103replace1.net', 'title': "103 replacement 1"},
                {'uri': 'http://updatenode103replacement2.net', 'title': "103 replacement 2"}
            ]
        }
        self.assertDictEqual(node, expected_node)

    def test_link_field_update_append_cardinality_unlimited_no_subdelims(self):
        existing_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {"uri": "http://node104o.net", "title": "Node 104 o"}
            ]
        }

        self.field_definitions = {
            'field_foo': {
                'cardinality': -1,
            }
        }

        self.config['update_mode'] = 'append'

        field = workbench_fields.LinkField()
        csv_record = collections.OrderedDict()
        csv_record['node_id'] = 104
        csv_record['field_foo'] = "http://node104a.net%%Node 104 a"
        node = field.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", existing_node["field_foo"])
        expected_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {'uri': 'http://node104o.net', 'title': "Node 104 o"},
                {'uri': 'http://node104a.net', 'title': "Node 104 a"}
            ]
        }
        self.assertDictEqual(node, expected_node)

    def test_link_field_update_append_cardinality_unlimited_with_subdelims(self):
        existing_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {"uri": "http://node105original.net", "title": "Node 105 original"}
            ]
        }

        self.field_definitions = {
            'field_foo': {
                'cardinality': -1,
            }
        }

        self.config['update_mode'] = 'append'

        field = workbench_fields.LinkField()
        csv_record = collections.OrderedDict()
        csv_record['node_id'] = 105
        csv_record['field_foo'] = "http://node105-1.net%%Node 105-1|http://node105-2.net%%Node 105-2|http://node105-2.net%%Node 105-2"
        node = field.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", existing_node["field_foo"])
        expected_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {'uri': 'http://node105original.net', 'title': "Node 105 original"},
                {'uri': 'http://node105-1.net', 'title': "Node 105-1"},
                {'uri': 'http://node105-2.net', 'title': "Node 105-2"}
            ]
        }
        self.assertDictEqual(node, expected_node)

    def test_link_field_update_replace_cardinality_limited_no_subdelims(self):
        existing_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {"uri": "http://106o-1.net", "title": "Node 106 1 original"},
                {"uri": "http://106o-2.net", "title": "Node 106 2 original"}
            ]
        }

        self.field_definitions = {
            'field_foo': {
                'cardinality': 2,
            }
        }

        self.config['update_mode'] = 'replace'

        field = workbench_fields.LinkField()
        csv_record = collections.OrderedDict()
        csv_record['node_id'] = 106
        csv_record['field_foo'] = "http://node06r.net%%Node 106 replacement"
        node = field.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", existing_node["field_foo"])
        expected_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {'uri': 'http://node06r.net', 'title': "Node 106 replacement"}
            ]
        }
        self.assertDictEqual(node, expected_node)

    def test_link_field_update_append_cardinality_limited_no_subdelims(self):
        existing_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {"uri": "http://107o-1.net", "title": "Node 107 1 original"},
                {"uri": "http://107o-2.net", "title": "Node 107 2 original"}
            ]
        }

        self.field_definitions = {
            'field_foo': {
                'cardinality': 2,
            }
        }

        self.config['update_mode'] = 'append'

        field = workbench_fields.LinkField()
        csv_record = collections.OrderedDict()
        csv_record['node_id'] = 107
        csv_record['field_foo'] = "http://node07a.net%%Node 107 appended"
        node = field.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", existing_node["field_foo"])
        expected_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {"uri": "http://107o-1.net", "title": "Node 107 1 original"},
                {"uri": "http://107o-2.net", "title": "Node 107 2 original"}
            ]
        }
        self.assertDictEqual(node, expected_node)

    def test_link_field_update_append_cardinality_limited_with_subdelims(self):
        existing_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {"uri": "http://108o-1.net", "title": "Node 108 1 original"},
                {"uri": "http://108o-2.net", "title": "Node 108 2 original"}
            ]
        }

        self.field_definitions = {
            'field_foo': {
                'cardinality': 2,
            }
        }

        self.config['update_mode'] = 'append'

        field = workbench_fields.LinkField()
        csv_record = collections.OrderedDict()
        csv_record['node_id'] = 108
        csv_record['field_foo'] = "http://08a-1.net%%Node 108 1 appended|http://108a-2.net%%Node 108 2 appended|http://108a-2.net%%Node 108 2 appended"
        node_field_values = []
        node = field.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", existing_node["field_foo"])
        expected_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {"uri": "http://108o-1.net", "title": "Node 108 1 original"},
                {"uri": "http://108o-2.net", "title": "Node 108 2 original"}
            ]
        }
        self.assertDictEqual(node, expected_node)

        # Violate cardinality.
        self.field_definitions = {
            'field_foo': {
                'cardinality': 3,
            }
        }

        self.config['update_mode'] = 'append'

        field = workbench_fields.LinkField()
        csv_record = collections.OrderedDict()
        csv_record['node_id'] = 109
        csv_record['field_foo'] = "http://09a-1.net%%Node 109 1 appended|http://109a-2.net%%Node 109 2 appended"
        node_field_values = [{"uri": "http://109o-1.net", "title": "Node 109 1 original"}, {"uri": "http://109o-2.net", "title": "Node 109 2 original"}]
        node = field.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", node_field_values)
        expected_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {"uri": "http://109o-1.net", "title": "Node 109 1 original"},
                {"uri": "http://109o-2.net", "title": "Node 109 2 original"},
                {"uri": "http://09a-1.net", "title": "Node 109 1 appended"},
            ]
        }
        self.assertDictEqual(node, expected_node)

    def test_link_field_update_replace_cardinality_limited_with_subdelims(self):
        existing_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {"uri": "http://110o-1.net", "title": "Node 110 1 original"},
                {"uri": "http://110o-2.net", "title": "Node 110 2 original"}
            ]
        }

        self.field_definitions = {
            'field_foo': {
                'cardinality': 2,
            }
        }

        self.config['update_mode'] = 'replace'

        field = workbench_fields.LinkField()
        csv_record = collections.OrderedDict()
        csv_record['node_id'] = 110
        csv_record['field_foo'] = "http://110r-1.net%%Node 110 1 replaced|http://110r-2.net%%Node 110 2 replaced|http://110r-2.net%%Node 110 2 replaced"
        node_field_values = []
        node = field.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", existing_node["field_foo"])
        expected_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {"uri": "http://110r-1.net", "title": "Node 110 1 replaced"},
                {"uri": "http://110r-2.net", "title": "Node 110 2 replaced"}
            ]
        }
        self.assertDictEqual(node, expected_node)

        # Violate cardinality.
        self.field_definitions = {
            'field_foo': {
                'cardinality': 3,
            }
        }

        field = workbench_fields.LinkField()
        csv_record = collections.OrderedDict()
        csv_record['node_id'] = 111
        csv_record['field_foo'] = "http://111r-1.net%%Node 111 1 replaced|http://111r-2.net%%Node 111 2 replaced|http://111r-2.net%%Node 111 2 replaced"
        node_field_values = [{"uri": "http://111o-1.net", "title": "Node 111 1 original"}, {"uri": "http://111o-2.net", "title": "Node 111 2 original"}]
        node = field.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", node_field_values)
        expected_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {"uri": "http://111r-1.net", "title": "Node 111 1 replaced"},
                {"uri": "http://111r-2.net", "title": "Node 111 2 replaced"}
            ]
        }
        self.assertDictEqual(node, expected_node)

    def test_link_field_update_delete(self):
        existing_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {"uri": "http://110o-1.net", "title": "Node 110 1 original"},
                {"uri": "http://110o-2.net", "title": "Node 110 2 original"}
            ]
        }

        self.field_definitions = {
            'field_foo': {
                'cardinality': 3,
            }
        }

        self.config['update_mode'] = 'delete'

        field = workbench_fields.LinkField()
        csv_record = collections.OrderedDict()
        csv_record['node_id'] = 112
        csv_record['field_foo'] = "http://112r-1.net%%Node 112 1 replaced|http://112r-2.net%%Node 112 2 replaced"
        node_field_values = [{"uri": "http://112o-1.net", "title": "Node 112 1 original"}, {"uri": "http://112o-2.net", "title": "Node 112 2 original"}]
        node = field.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", node_field_values)
        expected_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': []
        }
        self.assertDictEqual(node, expected_node)

    def test_link_field_dudupe_values(self):
        # Split values from CSV.
        input = ["http://example.net%%Example", "http://foo.net%%Foo", "http://example.net%%Example", "http://example.net%%Example"]
        field = workbench_fields.LinkField()
        output = field.dedupe_values(input)
        expected = ["http://example.net%%Example", "http://foo.net%%Foo"]
        self.assertEqual(output, expected)

        # Dictionaries.
        input = [
            {"uri": "http://example.net", "title": "Example"},
            {"uri": "http://foo.net", "title": "Foo"},
            {"uri": "http://example.net", "title": "Example"}
        ]
        field = workbench_fields.LinkField()
        output = field.dedupe_values(input)
        expected = [
            {"uri": "http://example.net", "title": "Example"},
            {"uri": "http://foo.net", "title": "Foo"}
        ]
        self.assertEqual(output, expected)


class TestEntityRefererenceField(unittest.TestCase):

    def setUp(self):
        self.maxDiff = None
        self.config = {
            'subdelimiter': '|',
            'id_field': 'id'
        }

    def test_create_with_entity_reference_field(self):
        existing_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ]
        }

        # Create a node with an entity_reference field of cardinality 1, no subdelimiters,
        # for both taxonomy term and node references.
        self.field_definitions = {
            'field_foo': {
                'cardinality': 1,
                'target_type': 'taxonomy_term'
            }
        }

        field = workbench_fields.EntityReferenceField()
        csv_record = collections.OrderedDict()
        csv_record['id'] = "term_entity_reference_001"
        csv_record['field_foo'] = "10"
        node = field.create(self.config, self.field_definitions, existing_node, csv_record, "field_foo")
        expected_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {'target_id': '10', 'target_type': 'taxonomy_term'}
            ]
        }
        self.assertDictEqual(node, expected_node)

        self.field_definitions = {
            'field_foo': {
                'cardinality': 1,
                'target_type': 'node'
            }
        }

        field = workbench_fields.EntityReferenceField()
        csv_record = collections.OrderedDict()
        csv_record['id'] = "node_entity_reference_001"
        csv_record['field_foo'] = "10"
        node = field.create(self.config, self.field_definitions, existing_node, csv_record, "field_foo")
        expected_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {'target_id': '10', 'target_type': 'node_type'}
            ]
        }
        self.assertDictEqual(node, expected_node)

        # Create a node with an entity_reference field of cardinality 1, with subdelimiters
        # for both taxonomy term and node references.
        self.field_definitions = {
            'field_foo': {
                'cardinality': 1,
                'target_type': 'taxonomy_term'
            }
        }

        with self.assertLogs() as message:
            field = workbench_fields.EntityReferenceField()
            csv_record = collections.OrderedDict()
            csv_record['id'] = "term_entity_reference_002"
            csv_record['field_foo'] = "101|102"
            node = field.create(self.config, self.field_definitions, existing_node, csv_record, "field_foo")
            expected_node = {
                'type': [
                    {'target_id': 'islandora_object', 'target_type': 'node_type'}
                ],
                'title': [
                    {'value': "Test node"}
                ],
                'status': [
                    {'value': 1}
                ],
                'field_foo': [
                    {'target_id': '101', 'target_type': 'taxonomy_term'}
                ]
            }
            self.assertDictEqual(node, expected_node)
            self.assertRegex(str(message.output), r'for record term_entity_reference_002 would exceed maximum number of allowed values \(1\)')

        self.field_definitions = {
            'field_foo': {
                'cardinality': 1,
                'target_type': 'node'
            }
        }

        with self.assertLogs() as message:
            field = workbench_fields.EntityReferenceField()
            csv_record = collections.OrderedDict()
            csv_record['id'] = "node_entity_reference_002"
            csv_record['field_foo'] = "100|101"
            node = field.create(self.config, self.field_definitions, existing_node, csv_record, "field_foo")
            expected_node = {
                'type': [
                    {'target_id': 'islandora_object', 'target_type': 'node_type'}
                ],
                'title': [
                    {'value': "Test node"}
                ],
                'status': [
                    {'value': 1}
                ],
                'field_foo': [
                    {'target_id': '100', 'target_type': 'node_type'}
                ]
            }
            self.assertDictEqual(node, expected_node)
            self.assertRegex(str(message.output), r'for record node_entity_reference_002 would exceed maximum number of allowed values \(1\)')

        # Create a node with an entity_reference field of cardinality unlimited, no subdelimiters,
        # for both taxonomy term and node references.
        self.field_definitions = {
            'field_foo': {
                'cardinality': -1,
                'target_type': 'taxonomy_term'
            }
        }

        field = workbench_fields.EntityReferenceField()
        csv_record = collections.OrderedDict()
        csv_record['id'] = "term_entity_reference_003"
        csv_record['field_foo'] = "1010"
        node = field.create(self.config, self.field_definitions, existing_node, csv_record, "field_foo")
        expected_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {'target_id': '1010', 'target_type': 'taxonomy_term'}
            ]
        }
        self.assertDictEqual(node, expected_node)

        self.field_definitions = {
            'field_foo': {
                'cardinality': -1,
                'target_type': 'node'
            }
        }

        field = workbench_fields.EntityReferenceField()
        csv_record = collections.OrderedDict()
        csv_record['id'] = "node_entity_reference_003"
        csv_record['field_foo'] = "10001"
        node = field.create(self.config, self.field_definitions, existing_node, csv_record, "field_foo")
        expected_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {'target_id': '10001', 'target_type': 'node_type'}
            ]
        }
        self.assertDictEqual(node, expected_node)

        # Create a node with an entity_reference field of cardinality unlimited, with subdelimiters,
        # for both taxonomy term and node references.
        self.field_definitions = {
            'field_foo': {
                'cardinality': -1,
                'target_type': 'taxonomy_term'
            }
        }

        field = workbench_fields.EntityReferenceField()
        csv_record = collections.OrderedDict()
        csv_record['id'] = "term_entity_reference_004"
        csv_record['field_foo'] = "1010|1011|1011"
        node = field.create(self.config, self.field_definitions, existing_node, csv_record, "field_foo")
        expected_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {'target_id': '1010', 'target_type': 'taxonomy_term'},
                {'target_id': '1011', 'target_type': 'taxonomy_term'}
            ]
        }
        self.assertDictEqual(node, expected_node)

        self.field_definitions = {
            'field_foo': {
                'cardinality': -1,
                'target_type': 'node'
            }
        }

        field = workbench_fields.EntityReferenceField()
        csv_record = collections.OrderedDict()
        csv_record['id'] = "node_entity_reference_004"
        csv_record['field_foo'] = "10001|10002"
        node = field.create(self.config, self.field_definitions, existing_node, csv_record, "field_foo")
        expected_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {'target_id': '10001', 'target_type': 'node_type'},
                {'target_id': '10002', 'target_type': 'node_type'}
            ]
        }
        self.assertDictEqual(node, expected_node)

        # Create a node with an entity_reference field of cardinality limited, no subdelimiters,
        # for both taxonomy term and node references.
        self.field_definitions = {
            'field_foo': {
                'cardinality': 2,
                'target_type': 'taxonomy_term'
            }
        }

        field = workbench_fields.EntityReferenceField()
        csv_record = collections.OrderedDict()
        csv_record['id'] = "term_entity_reference_005"
        csv_record['field_foo'] = "101010"
        node = field.create(self.config, self.field_definitions, existing_node, csv_record, "field_foo")
        expected_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {'target_id': '101010', 'target_type': 'taxonomy_term'}
            ]
        }
        self.assertDictEqual(node, expected_node)

        self.field_definitions = {
            'field_foo': {
                'cardinality': 1,
                'target_type': 'node'
            }
        }

        field = workbench_fields.EntityReferenceField()
        csv_record = collections.OrderedDict()
        csv_record['id'] = "node_entity_reference_005"
        csv_record['field_foo'] = "1010101"
        node = field.create(self.config, self.field_definitions, existing_node, csv_record, "field_foo")
        expected_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {'target_id': '1010101', 'target_type': 'node_type'}
            ]
        }
        self.assertDictEqual(node, expected_node)

        # Create a node with an entity_reference field of cardinality limited, with subdelimiters,
        # for both taxonomy term and node references.
        self.field_definitions = {
            'field_foo': {
                'cardinality': 2,
                'target_type': 'taxonomy_term'
            }
        }

        with self.assertLogs() as message:
            field = workbench_fields.EntityReferenceField()
            csv_record = collections.OrderedDict()
            csv_record['id'] = "term_entity_reference_006"
            csv_record['field_foo'] = "101|102|103|102"
            node = field.create(self.config, self.field_definitions, existing_node, csv_record, "field_foo")
            expected_node = {
                'type': [
                    {'target_id': 'islandora_object', 'target_type': 'node_type'}
                ],
                'title': [
                    {'value': "Test node"}
                ],
                'status': [
                    {'value': 1}
                ],
                'field_foo': [
                    {'target_id': '101', 'target_type': 'taxonomy_term'},
                    {'target_id': '102', 'target_type': 'taxonomy_term'}
                ]
            }
            self.assertDictEqual(node, expected_node)
            self.assertRegex(str(message.output), r'for record term_entity_reference_006 would exceed maximum number of allowed values \(2\)')

        self.field_definitions = {
            'field_foo': {
                'cardinality': 2,
                'target_type': 'node'
            }
        }

        with self.assertLogs() as message:
            field = workbench_fields.EntityReferenceField()
            csv_record = collections.OrderedDict()
            csv_record['id'] = "node_entity_reference_006"
            csv_record['field_foo'] = "200|201|202"
            node = field.create(self.config, self.field_definitions, existing_node, csv_record, "field_foo")
            expected_node = {
                'type': [
                    {'target_id': 'islandora_object', 'target_type': 'node_type'}
                ],
                'title': [
                    {'value': "Test node"}
                ],
                'status': [
                    {'value': 1}
                ],
                'field_foo': [
                    {'target_id': '200', 'target_type': 'node_type'},
                    {'target_id': '201', 'target_type': 'node_type'}
                ]
            }
            self.assertDictEqual(node, expected_node)
            self.assertRegex(str(message.output), r'for record node_entity_reference_006 would exceed maximum number of allowed values \(2\)')

    def test_entity_reference_field_update_replace_cardinality_1_no_subdelims(self):
        existing_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {'target_id': '1', 'target_type': 'taxonomy_term'}
            ]
        }

        self.field_definitions = {
            'field_foo': {
                'cardinality': 1,
                'target_type': 'taxonomy_term'
            }
        }

        self.config['update_mode'] = 'replace'

        field = workbench_fields.EntityReferenceField()
        csv_record = collections.OrderedDict()
        csv_record['node_id'] = 100
        csv_record['field_foo'] = '5'
        node = field.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", existing_node["field_foo"])
        expected_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {'target_id': '5', 'target_type': 'taxonomy_term'}
            ]
        }
        self.assertDictEqual(node, expected_node)

        self.field_definitions = {
            'field_foo': {
                'cardinality': 1,
                'target_type': 'node'
            }
        }

        self.config['update_mode'] = 'replace'

        field = workbench_fields.EntityReferenceField()
        csv_record = collections.OrderedDict()
        csv_record['node_id'] = 101
        csv_record['field_foo'] = '20'
        node_field_values = [{'target_id': '10', 'target_type': 'node'}]
        node = field.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", node_field_values)
        expected_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {'target_id': '20', 'target_type': 'node_type'}
            ]
        }
        self.assertDictEqual(node, expected_node)

    def test_entity_reference_field_update_replace_cardinality_1_with_subdelims(self):
        existing_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {'target_id': '1', 'target_type': 'taxonomy_term'}
            ]
        }

        self.field_definitions = {
            'field_foo': {
                'cardinality': 1,
                'target_type': 'taxonomy_term'
            }
        }

        self.config['update_mode'] = 'replace'

        with self.assertLogs() as message:
            field = workbench_fields.EntityReferenceField()
            csv_record = collections.OrderedDict()
            csv_record['node_id'] = 102
            csv_record['field_foo'] = '10|15'
            node = field.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", existing_node["field_foo"])
            expected_node = {
                'type': [
                    {'target_id': 'islandora_object', 'target_type': 'node_type'}
                ],
                'title': [
                    {'value': "Test node"}
                ],
                'status': [
                    {'value': 1}
                ],
                'field_foo': [
                    {'target_id': '10', 'target_type': 'taxonomy_term'}
                ]
            }
            self.assertDictEqual(node, expected_node)
            self.assertRegex(str(message.output), r'for record 102 would exceed maximum number of allowed values \(1\)')

        # Node reference.
        self.field_definitions = {
            'field_foo': {
                'cardinality': 1,
                'target_type': 'node'
            }
        }

        with self.assertLogs() as message:
            field = workbench_fields.EntityReferenceField()
            csv_record = collections.OrderedDict()
            csv_record['node_id'] = 103
            csv_record['field_foo'] = '20|25'
            node_field_values = [{'target_id': '1', 'target_type': 'node'}]
            node = field.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", node_field_values)
            expected_node = {
                'type': [
                    {'target_id': 'islandora_object', 'target_type': 'node_type'}
                ],
                'title': [
                    {'value': "Test node"}
                ],
                'status': [
                    {'value': 1}
                ],
                'field_foo': [
                    {'target_id': '20', 'target_type': 'node_type'}
                ]
            }
            self.assertDictEqual(node, expected_node)
            self.assertRegex(str(message.output), r'for record 103 would exceed maximum number of allowed values \(1\)')

    def test_entity_reference_field_update_replace_cardinality_unlimited_no_subdelims(self):
        existing_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {'target_id': '40', 'target_type': 'taxonomy_term'}
            ]
        }

        self.field_definitions = {
            'field_foo': {
                'cardinality': -1,
                'target_type': 'taxonomy_term'
            }
        }

        self.config['update_mode'] = 'replace'

        field = workbench_fields.EntityReferenceField()
        csv_record = collections.OrderedDict()
        csv_record['node_id'] = 104
        csv_record['field_foo'] = '30'
        node = field.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", existing_node["field_foo"])
        expected_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {'target_id': '30', 'target_type': 'taxonomy_term'}
            ]
        }
        self.assertDictEqual(node, expected_node)

        # Node reference.
        self.field_definitions = {
            'field_foo': {
                'cardinality': -1,
                'target_type': 'node'
            }
        }

        self.config['update_mode'] = 'replace'

        field = workbench_fields.EntityReferenceField()
        csv_record = collections.OrderedDict()
        csv_record['node_id'] = 105
        csv_record['field_foo'] = '40'
        node_field_values = [{'target_id': '50', 'target_type': 'node'}]
        node = field.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", node_field_values)
        expected_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {'target_id': '40', 'target_type': 'node_type'}
            ]
        }
        self.assertDictEqual(node, expected_node)

    def test_entity_reference_field_update_replace_cardinality_unlimited_with_subdelims(self):
        existing_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {'target_id': '50', 'target_type': 'taxonomy_term'}
            ]
        }

        self.field_definitions = {
            'field_foo': {
                'cardinality': -1,
                'target_type': 'taxonomy_term'
            }
        }

        self.config['update_mode'] = 'replace'

        field = workbench_fields.EntityReferenceField()
        csv_record = collections.OrderedDict()
        csv_record['node_id'] = 106
        csv_record['field_foo'] = '51|52|51'
        node = field.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", existing_node["field_foo"])
        expected_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {'target_id': '51', 'target_type': 'taxonomy_term'},
                {'target_id': '52', 'target_type': 'taxonomy_term'}
            ]
        }
        self.assertDictEqual(node, expected_node)

        # Node reference.
        self.field_definitions = {
            'field_foo': {
                'cardinality': -1,
                'target_type': 'node'
            }
        }

        self.config['update_mode'] = 'replace'

        field = workbench_fields.EntityReferenceField()
        csv_record = collections.OrderedDict()
        csv_record['node_id'] = 107
        csv_record['field_foo'] = '61|62'
        node_field_values = [{'target_id': '60', 'target_type': 'node'}]
        node = field.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", node_field_values)
        expected_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {'target_id': '61', 'target_type': 'node_type'},
                {'target_id': '62', 'target_type': 'node_type'}
            ]
        }
        self.assertDictEqual(node, expected_node)

    def test_entity_reference_field_update_append_cardinality_unlimited_no_subdelims(self):
        existing_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {'target_id': '70', 'target_type': 'taxonomy_term'}
            ]
        }

        self.field_definitions = {
            'field_foo': {
                'cardinality': -1,
                'target_type': 'taxonomy_term'
            }
        }

        self.config['update_mode'] = 'append'

        field = workbench_fields.EntityReferenceField()
        csv_record = collections.OrderedDict()
        csv_record['node_id'] = 108
        csv_record['field_foo'] = '71'
        node = field.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", existing_node["field_foo"])
        expected_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {'target_id': '70', 'target_type': 'taxonomy_term'},
                {'target_id': '71', 'target_type': 'taxonomy_term'}
            ]
        }
        self.assertDictEqual(node, expected_node)

        # Node reference.
        self.field_definitions = {
            'field_foo': {
                'cardinality': -1,
                'target_type': 'node'
            }
        }

        self.config['update_mode'] = 'append'

        field = workbench_fields.EntityReferenceField()
        csv_record = collections.OrderedDict()
        csv_record['node_id'] = 109
        csv_record['field_foo'] = '81'
        node_field_values = [{'target_id': '80', 'target_type': 'node_type'}]
        node = field.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", node_field_values)
        expected_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {'target_id': '80', 'target_type': 'node_type'},
                {'target_id': '81', 'target_type': 'node_type'}
            ]
        }
        self.assertDictEqual(node, expected_node)

    def test_entity_reference_field_update_append_cardinality_unlimited_with_subdelims(self):
        existing_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {'target_id': '70', 'target_type': 'taxonomy_term'}
            ]
        }

        self.field_definitions = {
            'field_foo': {
                'cardinality': -1,
                'target_type': 'taxonomy_term'
            }
        }

        self.config['update_mode'] = 'append'

        field = workbench_fields.EntityReferenceField()
        csv_record = collections.OrderedDict()
        csv_record['node_id'] = 110
        csv_record['field_foo'] = '72|73|73'
        node = field.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", existing_node["field_foo"])
        expected_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {'target_id': '70', 'target_type': 'taxonomy_term'},
                {'target_id': '72', 'target_type': 'taxonomy_term'},
                {'target_id': '73', 'target_type': 'taxonomy_term'}
            ]
        }
        self.assertDictEqual(node, expected_node)

        # Node reference.
        existing_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {'target_id': '71', 'target_type': 'node_type'}
            ]
        }

        self.field_definitions = {
            'field_foo': {
                'cardinality': -1,
                'target_type': 'node'
            }
        }

        self.config['update_mode'] = 'append'

        field = workbench_fields.EntityReferenceField()
        csv_record = collections.OrderedDict()
        csv_record['node_id'] = 111
        csv_record['field_foo'] = '74|75|71'
        node_field_values = [{'target_id': '71', 'target_type': 'node_type'}]
        node = field.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", existing_node["field_foo"])
        expected_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {'target_id': '71', 'target_type': 'node_type'},
                {'target_id': '74', 'target_type': 'node_type'},
                {'target_id': '75', 'target_type': 'node_type'}
            ]
        }
        self.assertDictEqual(node, expected_node)

    def test_entity_reference_field_update_replace_cardinality_limited_no_subdelims(self):
        existing_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {'target_id': '70', 'target_type': 'taxonomy_term'},
                {'target_id': '71', 'target_type': 'taxonomy_term'}
            ]
        }

        self.field_definitions = {
            'field_foo': {
                'cardinality': 2,
                'target_type': 'taxonomy_term'
            }
        }

        self.config['update_mode'] = 'replace'

        field = workbench_fields.EntityReferenceField()
        csv_record = collections.OrderedDict()
        csv_record['node_id'] = 112
        csv_record['field_foo'] = '112'
        node = field.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", existing_node["field_foo"])
        expected_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {'target_id': '112', 'target_type': 'taxonomy_term'}
            ]
        }
        self.assertDictEqual(node, expected_node)

    def test_entity_reference_field_update_append_cardinality_limited_no_subdelims(self):
        existing_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {'target_id': '1131', 'target_type': 'taxonomy_term'},
                {'target_id': '1132', 'target_type': 'taxonomy_term'}
            ]
        }

        self.field_definitions = {
            'field_foo': {
                'cardinality': 2,
                'target_type': 'taxonomy_term'
            }
        }

        self.config['update_mode'] = 'append'

        with self.assertLogs() as message:
            field = workbench_fields.EntityReferenceField()
            csv_record = collections.OrderedDict()
            csv_record['node_id'] = 113
            csv_record['field_foo'] = '1133'
            node = field.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", existing_node["field_foo"])
            expected_node = {
                'type': [
                    {'target_id': 'islandora_object', 'target_type': 'node_type'}
                ],
                'title': [
                    {'value': "Test node"}
                ],
                'status': [
                    {'value': 1}
                ],
                'field_foo': [
                    {'target_id': '1131', 'target_type': 'taxonomy_term'},
                    {'target_id': '1132', 'target_type': 'taxonomy_term'}
                ]
            }
            self.assertDictEqual(node, expected_node)
            self.assertRegex(str(message.output), r'for record 113 would exceed maximum number of allowed values \(2\)')

        # Do not violate cardinality.
        self.field_definitions = {
            'field_foo': {
                'cardinality': 3,
                'target_type': 'taxonomy_term'
            }
        }

        self.config['update_mode'] = 'append'

        field = workbench_fields.EntityReferenceField()
        csv_record = collections.OrderedDict()
        csv_record['node_id'] = 114
        csv_record['field_foo'] = '1133'
        node = field.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", existing_node["field_foo"])
        expected_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {'target_id': '1131', 'target_type': 'taxonomy_term'},
                {'target_id': '1132', 'target_type': 'taxonomy_term'},
                {'target_id': '1133', 'target_type': 'taxonomy_term'}
            ]
        }
        self.assertDictEqual(node, expected_node)

        # Node reference.
        existing_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {'target_id': '60', 'target_type': 'node_type'}
            ]
        }

        self.field_definitions = {
            'field_foo': {
                'cardinality': 2,
                'target_type': 'node'
            }
        }

        self.config['update_mode'] = 'append'

        with self.assertLogs() as message:
            field = workbench_fields.EntityReferenceField()
            csv_record = collections.OrderedDict()
            csv_record['node_id'] = 1141
            csv_record['field_foo'] = '101|102'
            node = field.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", existing_node["field_foo"])
            expected_node = {
                'type': [
                    {'target_id': 'islandora_object', 'target_type': 'node_type'}
                ],
                'title': [
                    {'value': "Test node"}
                ],
                'status': [
                    {'value': 1}
                ],
                'field_foo': [
                    {'target_id': '60', 'target_type': 'node_type'},
                    {'target_id': '101', 'target_type': 'node_type'}
                ]
            }
            self.assertDictEqual(node, expected_node)
            self.assertRegex(str(message.output), r'for record 1141 would exceed maximum number of allowed values \(2\)')

    def test_entity_reference_field_update_replace_cardinality_limited_with_subdelims(self):
        existing_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {'target_id': '1131', 'target_type': 'taxonomy_term'},
                {'target_id': '1132', 'target_type': 'taxonomy_term'}
            ]
        }

        self.field_definitions = {
            'field_foo': {
                'cardinality': 2,
                'target_type': 'taxonomy_term'
            }
        }

        self.config['update_mode'] = 'replace'

        field = workbench_fields.EntityReferenceField()
        csv_record = collections.OrderedDict()
        csv_record['node_id'] = 115
        csv_record['field_foo'] = '115|116|116'
        node = field.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", existing_node["field_foo"])
        expected_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {'target_id': '115', 'target_type': 'taxonomy_term'},
                {'target_id': '116', 'target_type': 'taxonomy_term'}
            ]
        }
        self.assertDictEqual(node, expected_node)

        # Violate cardinality
        with self.assertLogs() as message:
            self.field_definitions = {
                'field_foo': {
                    'cardinality': 2,
                    'target_type': 'taxonomy_term'
                }
            }

            self.config['update_mode'] = 'replace'

            field = workbench_fields.EntityReferenceField()
            csv_record = collections.OrderedDict()
            csv_record['node_id'] = 116
            csv_record['field_foo'] = '115|116|117|116'
            node_field_values = [{'target_id': '70', 'target_type': 'taxonomy_term'}, {'target_id': '71', 'target_type': 'taxonomy_term'}]
            node = field.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", node_field_values)
            expected_node = {
                'type': [
                    {'target_id': 'islandora_object', 'target_type': 'node_type'}
                ],
                'title': [
                    {'value': "Test node"}
                ],
                'status': [
                    {'value': 1}
                ],
                'field_foo': [
                    {'target_id': '115', 'target_type': 'taxonomy_term'},
                    {'target_id': '116', 'target_type': 'taxonomy_term'}
                ]
            }
            self.assertDictEqual(node, expected_node)
            self.assertRegex(str(message.output), r'for record 116 would exceed maximum number of allowed values \(2\)')

        # Node reference.
        existing_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {'target_id': '60', 'target_type': 'node_type'}
            ]
        }

        with self.assertLogs() as message:
            self.field_definitions = {
                'field_foo': {
                    'cardinality': 3,
                    'target_type': 'node'
                }
            }

            self.config['update_mode'] = 'replace'

            field = workbench_fields.EntityReferenceField()
            csv_record = collections.OrderedDict()
            csv_record['node_id'] = 1161
            csv_record['field_foo'] = '101|102|103|104'
            node = field.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", existing_node["field_foo"])
            expected_node = {
                'type': [
                    {'target_id': 'islandora_object', 'target_type': 'node_type'}
                ],
                'title': [
                    {'value': "Test node"}
                ],
                'status': [
                    {'value': 1}
                ],
                'field_foo': [
                    {'target_id': '101', 'target_type': 'node_type'},
                    {'target_id': '102', 'target_type': 'node_type'},
                    {'target_id': '103', 'target_type': 'node_type'}
                ]
            }
            self.assertDictEqual(node, expected_node)
            self.assertRegex(str(message.output), r'for record 1161 would exceed maximum number of allowed values \(3\)')

    def test_entity_reference_field_update_append_cardinality_limited_with_subdelims(self):
        existing_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {'target_id': '1161', 'target_type': 'taxonomy_term'},
                {'target_id': '1162', 'target_type': 'taxonomy_term'}
            ]
        }

        self.field_definitions = {
            'field_foo': {
                'cardinality': 2,
                'target_type': 'taxonomy_term'
            }
        }

        self.config['update_mode'] = 'append'

        with self.assertLogs() as message:
            field = workbench_fields.EntityReferenceField()
            csv_record = collections.OrderedDict()
            csv_record['node_id'] = 116
            csv_record['field_foo'] = '1163|1164|1163'
            node = field.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", existing_node["field_foo"])
            expected_node = {
                'type': [
                    {'target_id': 'islandora_object', 'target_type': 'node_type'}
                ],
                'title': [
                    {'value': "Test node"}
                ],
                'status': [
                    {'value': 1}
                ],
                'field_foo': [
                    {'target_id': '1161', 'target_type': 'taxonomy_term'},
                    {'target_id': '1162', 'target_type': 'taxonomy_term'}
                ]
            }
            self.assertDictEqual(node, expected_node)
            self.assertRegex(str(message.output), r'for record 116 would exceed maximum number of allowed values \(2\)')

        # Do not violate cardinality.
        self.field_definitions = {
            'field_foo': {
                'cardinality': 4,
                'target_type': 'taxonomy_term'
            }
        }

        self.config['update_mode'] = 'append'

        field = workbench_fields.EntityReferenceField()
        csv_record = collections.OrderedDict()
        csv_record['node_id'] = 117
        csv_record['field_foo'] = '117|118|118'
        node_field_values = [{'target_id': '1131', 'target_type': 'taxonomy_term'}, {'target_id': '1132', 'target_type': 'taxonomy_term'}]
        node = field.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", node_field_values)
        expected_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {'target_id': '1131', 'target_type': 'taxonomy_term'},
                {'target_id': '1132', 'target_type': 'taxonomy_term'},
                {'target_id': '117', 'target_type': 'taxonomy_term'},
                {'target_id': '118', 'target_type': 'taxonomy_term'}
            ]
        }
        self.assertDictEqual(node, expected_node)

        # Node reference.
        existing_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {'target_id': '60', 'target_type': 'node_type'}
            ]
        }

        self.field_definitions = {
            'field_foo': {
                'cardinality': 3,
                'target_type': 'node'
            }
        }

        self.config['update_mode'] = 'append'

        field = workbench_fields.EntityReferenceField()
        csv_record = collections.OrderedDict()
        csv_record['node_id'] = 1162
        csv_record['field_foo'] = '102|103|103'
        node = field.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", existing_node["field_foo"])
        expected_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {'target_id': '60', 'target_type': 'node_type'},
                {'target_id': '102', 'target_type': 'node_type'},
                {'target_id': '103', 'target_type': 'node_type'}
            ]
        }
        self.assertDictEqual(node, expected_node)

    def test_entity_reference_field_update_delete(self):
        existing_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {'target_id': '1001', 'target_type': 'taxonomy_term'},
                {'target_id': '1002', 'target_type': 'taxonomy_term'}
            ]
        }

        self.field_definitions = {
            'field_foo': {
                'cardinality': 3,
            }
        }

        self.config['update_mode'] = 'delete'

        field = workbench_fields.EntityReferenceField()
        csv_record = collections.OrderedDict()
        csv_record['node_id'] = 130
        csv_record['field_foo'] = ''
        self.config['update_mode'] = 'delete'
        node = field.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", existing_node["field_foo"])
        expected_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': []
        }
        self.assertDictEqual(node, expected_node)

    def test_entity_reference_field_dudupe_values(self):
        # Split values from CSV.
        input = ['cats:Tuxedo', 'cats:Misbehaving', 'dogs:German Shepherd', 'cats:Tuxedo']
        field = workbench_fields.LinkField()
        output = field.dedupe_values(input)
        expected = ['cats:Tuxedo', 'cats:Misbehaving', 'dogs:German Shepherd']
        self.assertEqual(output, expected)

        # Dictionaries.
        input = [
            {'target_id': '600', 'target_type': 'node_type'},
            {'target_id': '1020', 'target_type': 'node_type'},
            {'target_id': '1030', 'target_type': 'node_type'},
            {'target_id': '1020', 'target_type': 'node_type'},
            {'target_id': '1030', 'target_type': 'node_type'}
        ]
        field = workbench_fields.LinkField()
        output = field.dedupe_values(input)
        expected = [
            {'target_id': '600', 'target_type': 'node_type'},
            {'target_id': '1020', 'target_type': 'node_type'},
            {'target_id': '1030', 'target_type': 'node_type'}
        ]
        self.assertEqual(output, expected)


class TestTypedRelationField(unittest.TestCase):

    def setUp(self):
        self.maxDiff = None
        self.config = {
            'subdelimiter': '|',
            'id_field': 'id'
        }

        self.existing_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ]
        }

    def test_create_with_typed_relation_field(self):

        # Create a node with a typed_relation field of cardinality 1, no subdelimiters.
        field_definitions = {
            'field_foo': {
                'cardinality': 1,
                'target_type': 'taxonomy_term'
            }
        }

        field = workbench_fields.TypedRelationField()
        csv_record = collections.OrderedDict()
        csv_record['id'] = "typed_relation_001"
        csv_record['field_foo'] = "relators:pht:1"
        node = field.create(self.config, field_definitions, self.existing_node, csv_record, "field_foo")
        expected_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {'rel_type': 'relators:pht', 'target_id': '1', 'target_type': 'taxonomy_term'}
            ]
        }
        self.assertDictEqual(node, expected_node)

        # Create a node with a typed_relation field of cardinality 1, with subdelimiters.
        with self.assertLogs() as message:
            field = workbench_fields.TypedRelationField()
            csv_record = collections.OrderedDict()
            csv_record['id'] = "typed_relation_002"
            csv_record['field_foo'] = "relators:art:2|relators:art:22"
            node = field.create(self.config, field_definitions, self.existing_node, csv_record, "field_foo")
            expected_node = {
                'type': [
                    {'target_id': 'islandora_object', 'target_type': 'node_type'}
                ],
                'title': [
                    {'value': "Test node"}
                ],
                'status': [
                    {'value': 1}
                ],
                'field_foo': [
                    {'rel_type': 'relators:art', 'target_id': '2', 'target_type': 'taxonomy_term'}
                ]
            }
            self.assertDictEqual(node, expected_node)
            self.assertRegex(str(message.output), r'for record typed_relation_002 would exceed maximum number of allowed values \(1\)')

        # Create a node with a typed_relation field of cardinality unlimited, no subdelimiters.
        field_definitions = {
            'field_foo': {
                'cardinality': -1,
                'target_type': 'taxonomy_term'
            }
        }

        field = workbench_fields.TypedRelationField()
        csv_record = collections.OrderedDict()
        csv_record['id'] = "typed_relation_003"
        csv_record['field_foo'] = "relators:pht:3"
        node = field.create(self.config, field_definitions, self.existing_node, csv_record, "field_foo")
        expected_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {'rel_type': 'relators:pht', 'target_id': '3', 'target_type': 'taxonomy_term'}
            ]
        }
        self.assertDictEqual(node, expected_node)

        # Create a node with a typed_relation field of cardinality unlimited, with subdelimiters.
        field_definitions = {
            'field_foo': {
                'cardinality': -1,
                'target_type': 'taxonomy_term'
            }
        }

        field = workbench_fields.TypedRelationField()
        csv_record = collections.OrderedDict()
        csv_record['id'] = "typed_relation_004"
        csv_record['field_foo'] = "relators:pht:1|relators:pht:2|relators:pht:3"
        node = field.create(self.config, field_definitions, self.existing_node, csv_record, "field_foo")
        expected_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {'rel_type': 'relators:pht', 'target_id': '1', 'target_type': 'taxonomy_term'},
                {'rel_type': 'relators:pht', 'target_id': '2', 'target_type': 'taxonomy_term'},
                {'rel_type': 'relators:pht', 'target_id': '3', 'target_type': 'taxonomy_term'}
            ]
        }
        self.assertDictEqual(node, expected_node)

        # Create a node with a typed_relation field of cardinality limited, no subdelimiters.
        field_definitions = {
            'field_foo': {
                'cardinality': 2,
                'target_type': 'taxonomy_term'
            }
        }

        field = workbench_fields.TypedRelationField()
        csv_record = collections.OrderedDict()
        csv_record['id'] = "typed_relation_005"
        csv_record['field_foo'] = "relators:art:51"
        node = field.create(self.config, field_definitions, self.existing_node, csv_record, "field_foo")
        expected_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {'rel_type': 'relators:art', 'target_id': '51', 'target_type': 'taxonomy_term'}
            ]
        }
        self.assertDictEqual(node, expected_node)

        # Create a node with a typed_relation field of cardinality limited, with subdelimiters.
        field_definitions = {
            'field_foo': {
                'cardinality': 3,
                'target_type': 'taxonomy_term'
            }
        }

        with self.assertLogs() as message:
            field = workbench_fields.TypedRelationField()
            csv_record = collections.OrderedDict()
            csv_record['id'] = "typed_relation_006"
            csv_record['field_foo'] = "relators:art:26|relators:art:36|relators:art:46|relators:art:56"
            node = field.create(self.config, field_definitions, self.existing_node, csv_record, "field_foo")
            expected_node = {
                'type': [
                    {'target_id': 'islandora_object', 'target_type': 'node_type'}
                ],
                'title': [
                    {'value': "Test node"}
                ],
                'status': [
                    {'value': 1}
                ],
                'field_foo': [
                    {'rel_type': 'relators:art', 'target_id': '26', 'target_type': 'taxonomy_term'},
                    {'rel_type': 'relators:art', 'target_id': '36', 'target_type': 'taxonomy_term'},
                    {'rel_type': 'relators:art', 'target_id': '46', 'target_type': 'taxonomy_term'}
                ]
            }
            self.assertDictEqual(node, expected_node)
            self.assertRegex(str(message.output), r'for record typed_relation_006 would exceed maximum number of allowed values \(3\)')

    def test_typed_relation_field_update_replace_cardinality_1_no_subdelims(self):
        existing_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {'rel_type': 'relators:art', 'target_id': '777', 'target_type': 'taxonomy_term'}
            ]
        }

        self.field_definitions = {
            'field_foo': {
                'cardinality': 1,
                'target_type': 'taxonomy_term'
            }
        }

        self.config['update_mode'] = 'replace'

        field = workbench_fields.TypedRelationField()
        csv_record = collections.OrderedDict()
        csv_record['node_id'] = 'typed_relation_007'
        csv_record['field_foo'] = 'relators:art:701'
        node = field.update(self.config, self.field_definitions, self.existing_node, csv_record, "field_foo", existing_node["field_foo"])
        expected_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {'rel_type': 'relators:art', 'target_id': '701', 'target_type': 'taxonomy_term'}
            ]
        }
        self.assertDictEqual(node, expected_node)

    def test_typed_relation_field_update_replace_cardinality_1_with_subdelims(self):
        existing_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {'rel_type': 'relators:art', 'target_id': '778', 'target_type': 'taxonomy_term'}
            ]
        }

        self.field_definitions = {
            'field_foo': {
                'cardinality': 1,
                'target_type': 'taxonomy_term'
            }
        }

        self.config['update_mode'] = 'replace'

        with self.assertLogs() as message:
            field = workbench_fields.TypedRelationField()
            csv_record = collections.OrderedDict()
            csv_record['node_id'] = 'typed_relation_008'
            csv_record['field_foo'] = 'relators:xxx:801|relators:cpy:802'
            node = field.update(self.config, self.field_definitions, self.existing_node, csv_record, "field_foo", existing_node["field_foo"])
            expected_node = {
                'type': [
                    {'target_id': 'islandora_object', 'target_type': 'node_type'}
                ],
                'title': [
                    {'value': "Test node"}
                ],
                'status': [
                    {'value': 1}
                ],
                'field_foo': [
                    {'rel_type': 'relators:xxx', 'target_id': '801', 'target_type': 'taxonomy_term'}
                ]
            }
            self.assertDictEqual(node, expected_node)
            self.assertRegex(str(message.output), r'for record typed_relation_008 would exceed maximum number of allowed values \(1\)')

    def test_typed_relation_field_update_replace_cardinality_unlimited_no_subdelims(self):
        existing_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {'rel_type': 'relators:art', 'target_id': '779', 'target_type': 'taxonomy_term'}
            ]
        }

        self.field_definitions = {
            'field_foo': {
                'cardinality': -1,
                'target_type': 'taxonomy_term'
            }
        }
        self.config['update_mode'] = 'replace'

        field = workbench_fields.TypedRelationField()
        csv_record = collections.OrderedDict()
        csv_record['node_id'] = 'typed_relation_009'
        csv_record['field_foo'] = 'relators:aaa:901'
        node = field.update(self.config, self.field_definitions, self.existing_node, csv_record, "field_foo", existing_node["field_foo"])
        expected_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {'rel_type': 'relators:aaa', 'target_id': '901', 'target_type': 'taxonomy_term'}
            ]
        }
        self.assertDictEqual(node, expected_node)

    def test_typed_relation_field_update_replace_cardinality_unlimited_with_subdelims(self):
        existing_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {'rel_type': 'relators:art', 'target_id': '902', 'target_type': 'taxonomy_term'}
            ]
        }

        self.field_definitions = {
            'field_foo': {
                'cardinality': -1,
                'target_type': 'taxonomy_term'
            }
        }

        self.config['update_mode'] = 'replace'

        field = workbench_fields.TypedRelationField()
        csv_record = collections.OrderedDict()
        csv_record['node_id'] = 'typed_relation_010'
        csv_record['field_foo'] = 'relators:aaa:902|relators:bbb:903|relators:ccc:904'
        node = field.update(self.config, self.field_definitions, self.existing_node, csv_record, "field_foo", existing_node["field_foo"])
        expected_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {'rel_type': 'relators:aaa', 'target_id': '902', 'target_type': 'taxonomy_term'},
                {'rel_type': 'relators:bbb', 'target_id': '903', 'target_type': 'taxonomy_term'},
                {'rel_type': 'relators:ccc', 'target_id': '904', 'target_type': 'taxonomy_term'}
            ]
        }
        self.assertDictEqual(node, expected_node)

    def test_typed_relation_field_update_append_cardinality_unlimited_no_subdelims(self):
        existing_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {'rel_type': 'relators:art', 'target_id': '10', 'target_type': 'taxonomy_term'}
            ]
        }

        self.field_definitions = {
            'field_foo': {
                'cardinality': -1,
                'target_type': 'taxonomy_term'
            }
        }

        self.config['update_mode'] = 'append'

        field = workbench_fields.TypedRelationField()
        csv_record = collections.OrderedDict()
        csv_record['node_id'] = 'typed_relation_011'
        csv_record['field_foo'] = 'relators:aaa:11'
        node = field.update(self.config, self.field_definitions, self.existing_node, csv_record, "field_foo", existing_node["field_foo"])
        expected_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {'rel_type': 'relators:art', 'target_id': '10', 'target_type': 'taxonomy_term'},
                {'rel_type': 'relators:aaa', 'target_id': '11', 'target_type': 'taxonomy_term'}
            ]
        }
        self.assertDictEqual(node, expected_node)

    def test_typed_relation_field_update_append_cardinality_unlimited_no_subdelims(self):
        existing_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {'rel_type': 'relators:art', 'target_id': '10', 'target_type': 'taxonomy_term'}
            ]
        }

        self.field_definitions = {
            'field_foo': {
                'cardinality': -1,
                'target_type': 'taxonomy_term'
            }
        }

        self.config['update_mode'] = 'append'

        field = workbench_fields.TypedRelationField()
        csv_record = collections.OrderedDict()
        csv_record['node_id'] = 'typed_relation_012'
        csv_record['field_foo'] = 'relators:bbb:12|relators:ccc:13|relators:ddd:14'
        node = field.update(self.config, self.field_definitions, self.existing_node, csv_record, "field_foo", existing_node["field_foo"])
        expected_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {'rel_type': 'relators:art', 'target_id': '10', 'target_type': 'taxonomy_term'},
                {'rel_type': 'relators:bbb', 'target_id': '12', 'target_type': 'taxonomy_term'},
                {'rel_type': 'relators:ccc', 'target_id': '13', 'target_type': 'taxonomy_term'},
                {'rel_type': 'relators:ddd', 'target_id': '14', 'target_type': 'taxonomy_term'}
            ]
        }
        self.assertDictEqual(node, expected_node)

    def test_typed_relation_field_update_replace_cardinality_limited_no_subdelims(self):
        existing_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {'rel_type': 'relators:art', 'target_id': '130', 'target_type': 'taxonomy_term'}
            ]
        }

        self.field_definitions = {
            'field_foo': {
                'cardinality': 2,
                'target_type': 'taxonomy_term'
            }
        }

        self.config['update_mode'] = 'replace'

        field = workbench_fields.TypedRelationField()
        csv_record = collections.OrderedDict()
        csv_record['node_id'] = 'typed_relation_013'
        csv_record['field_foo'] = 'relators:bbb:13'
        node = field.update(self.config, self.field_definitions, self.existing_node, csv_record, "field_foo", existing_node["field_foo"])
        expected_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {'rel_type': 'relators:bbb', 'target_id': '13', 'target_type': 'taxonomy_term'}
            ]
        }
        self.assertDictEqual(node, expected_node)

    def test_typed_relation_field_update_append_cardinality_limited_no_subdelims(self):
        existing_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {'rel_type': 'relators:yyy', 'target_id': '140', 'target_type': 'taxonomy_term'},
                {'rel_type': 'relators:zzz', 'target_id': '141', 'target_type': 'taxonomy_term'}
            ]
        }

        self.field_definitions = {
            'field_foo': {
                'cardinality': 2,
                'target_type': 'taxonomy_term'
            }
        }

        self.config['update_mode'] = 'append'

        with self.assertLogs() as message:
            field = workbench_fields.TypedRelationField()
            csv_record = collections.OrderedDict()
            csv_record['node_id'] = 'typed_relation_014'
            csv_record['field_foo'] = 'relators:sss:14'
            node = field.update(self.config, self.field_definitions, self.existing_node, csv_record, "field_foo", existing_node["field_foo"])
            expected_node = {
                'type': [
                    {'target_id': 'islandora_object', 'target_type': 'node_type'}
                ],
                'title': [
                    {'value': "Test node"}
                ],
                'status': [
                    {'value': 1}
                ],
                'field_foo': [
                    {'rel_type': 'relators:yyy', 'target_id': '140', 'target_type': 'taxonomy_term'},
                    {'rel_type': 'relators:zzz', 'target_id': '141', 'target_type': 'taxonomy_term'}
                ]
            }
            self.assertDictEqual(node, expected_node)
            self.assertRegex(str(message.output), r'for record typed_relation_014 would exceed maximum number of allowed values \(2\)')

    def test_typed_relation_field_update_replace_cardinality_limited_with_subdelims(self):
        existing_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {'rel_type': 'relators:yyy', 'target_id': '555', 'target_type': 'taxonomy_term'}
            ]
        }

        self.field_definitions = {
            'field_foo': {
                'cardinality': 2,
                'target_type': 'taxonomy_term'
            }
        }

        self.config['update_mode'] = 'replace'

        with self.assertLogs() as message:
            field = workbench_fields.TypedRelationField()
            csv_record = collections.OrderedDict()
            csv_record['node_id'] = 'typed_relation_015'
            csv_record['field_foo'] = 'relators:bbb:150|relators:ccc:152|relators:ccc:152|relators:ddd:153'
            node_field_values = [{'rel_type': 'relators:art', 'target_id': '555', 'target_type': 'taxonomy_term'}]
            node = field.update(self.config, self.field_definitions, self.existing_node, csv_record, "field_foo", existing_node["field_foo"])
            expected_node = {
                'type': [
                    {'target_id': 'islandora_object', 'target_type': 'node_type'}
                ],
                'title': [
                    {'value': "Test node"}
                ],
                'status': [
                    {'value': 1}
                ],
                'field_foo': [
                    {'rel_type': 'relators:bbb', 'target_id': '150', 'target_type': 'taxonomy_term'},
                    {'rel_type': 'relators:ccc', 'target_id': '152', 'target_type': 'taxonomy_term'}
                ]
            }
            self.assertDictEqual(node, expected_node)
            self.assertRegex(str(message.output), r'for record typed_relation_015 would exceed maximum number of allowed values \(2\)')

    def test_typed_relation_field_update_append_cardinality_limited_with_subdelims(self):
        existing_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {'rel_type': 'relators:jjj', 'target_id': '164', 'target_type': 'taxonomy_term'}
            ]
        }

        self.field_definitions = {
            'field_foo': {
                'cardinality': 3,
                'target_type': 'taxonomy_term'
            }
        }

        self.config['update_mode'] = 'append'

        with self.assertLogs() as message:
            field = workbench_fields.TypedRelationField()
            csv_record = collections.OrderedDict()
            csv_record['node_id'] = 'typed_relation_016'
            csv_record['field_foo'] = 'relators:rrr:160|relators:sss:161|relators:sss:161|relators:ttt:162'
            node = field.update(self.config, self.field_definitions, self.existing_node, csv_record, "field_foo", existing_node["field_foo"])
            expected_node = {
                'type': [
                    {'target_id': 'islandora_object', 'target_type': 'node_type'}
                ],
                'title': [
                    {'value': "Test node"}
                ],
                'status': [
                    {'value': 1}
                ],
                'field_foo': [
                    {'rel_type': 'relators:jjj', 'target_id': '164', 'target_type': 'taxonomy_term'},
                    {'rel_type': 'relators:rrr', 'target_id': '160', 'target_type': 'taxonomy_term'},
                    {'rel_type': 'relators:sss', 'target_id': '161', 'target_type': 'taxonomy_term'}
                ]
            }
            self.assertDictEqual(node, expected_node)
            self.assertRegex(str(message.output), r'for record typed_relation_016 would exceed maximum number of allowed values \(3\)')

    def test_typed_relation_field_update_delete(self):
        existing_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {'rel_type': 'relators:art', 'target_id': '301', 'target_type': 'taxonomy_term'},
                {'rel_type': 'relators:art', 'target_id': '302', 'target_type': 'taxonomy_term'}
            ]
        }

        self.field_definitions = {
            'field_foo': {
                'cardinality': 4,
                'target_type': 'taxonomy_term'
            }
        }

        self.config['update_mode'] = 'delete'

        field = workbench_fields.TypedRelationField()
        csv_record = collections.OrderedDict()
        csv_record['node_id'] = 300
        csv_record['field_foo'] = ''
        self.config['update_mode'] = 'delete'
        node = field.update(self.config, self.field_definitions, self.existing_node, csv_record, "field_foo", existing_node["field_foo"])
        expected_node = {
            'type': [
                {'target_id': 'islandora_object', 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': []
        }
        self.assertDictEqual(node, expected_node)

    def test_entity_reference_field_dudupe_values(self):
        # Split values from CSV.
        input = ['relators:art:person:Bar, Foo', 'relators:art:person:Bang, Biz', 'relators:art:person:Bang, Biz']
        field = workbench_fields.LinkField()
        output = field.dedupe_values(input)
        expected = ['relators:art:person:Bar, Foo', 'relators:art:person:Bang, Biz']
        self.assertEqual(output, expected)

        # Dictionaries.
        input = [
            {'rel_type': 'relators:bbb', 'target_id': '1501', 'target_type': 'taxonomy_term'},
            {'rel_type': 'relators:ccc', 'target_id': '1521', 'target_type': 'taxonomy_term'},
            {'rel_type': 'relators:bbb', 'target_id': '1501', 'target_type': 'taxonomy_term'},
            {'rel_type': 'relators:ccc', 'target_id': '1521', 'target_type': 'taxonomy_term'}
        ]
        field = workbench_fields.LinkField()
        output = field.dedupe_values(input)
        expected = [
            {'rel_type': 'relators:bbb', 'target_id': '1501', 'target_type': 'taxonomy_term'},
            {'rel_type': 'relators:ccc', 'target_id': '1521', 'target_type': 'taxonomy_term'}
        ]
        self.assertEqual(output, expected)


if __name__ == '__main__':
    unittest.main()
