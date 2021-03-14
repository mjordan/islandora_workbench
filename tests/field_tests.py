"""unittest tests for Drupal field handlers.
"""

import sys
import os
import unittest
import collections
import io

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import workbench_fields


class TestSimpleField(unittest.TestCase):

    def setUp(self):
        self.config = {
            'subdelimiter': '|',
            'id_field': 'id',
            'update_mode': 'replace'
        }

    def test_create_with_simple_field(self):
        existing_node = {
            'type': [
                {'target_id': 'islandora_object',
                 'target_type': 'node_type'}
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
                {'target_id': 'islandora_object',
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
        with self.assertLogs() as message:
            field = workbench_fields.SimpleField()
            csv_record = collections.OrderedDict()
            csv_record['id'] = "simple_002"
            csv_record['field_foo'] = "Field foo value|Extraneous value"
            node = field.create(self.config, self.field_definitions, existing_node, csv_record, "field_foo")
            expected_node = {
                'type': [
                    {'target_id': 'islandora_object',
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
            self.assertRegex(str(message.output), 'simple_002 would exceed maximum number of allowed values.+1')

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
                {'target_id': 'islandora_object',
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
        field = workbench_fields.SimpleField()
        csv_record = collections.OrderedDict()
        csv_record['id'] = "simple_004"
        csv_record['field_foo'] = "First value|Second value"
        node = field.create(self.config, self.field_definitions, existing_node, csv_record, "field_foo")
        expected_node = {
            'type': [
                {'target_id': 'islandora_object',
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

        field = workbench_fields.SimpleField()
        csv_record = collections.OrderedDict()
        csv_record['id'] = "simple_005"
        csv_record['field_foo'] = "First value"
        node = field.create(self.config, self.field_definitions, existing_node, csv_record, "field_foo")
        expected_node = {
            'type': [
                {'target_id': 'islandora_object',
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
        with self.assertLogs() as message:
            field = workbench_fields.SimpleField()
            csv_record = collections.OrderedDict()
            csv_record['id'] = "simple_006"
            csv_record['field_foo'] = "First 006 value|Second 006 value|Third 006 value"
            self.node = field.create(self.config, self.field_definitions, existing_node, csv_record, "field_foo")
            expected_node = {
                'type': [
                    {'target_id': 'islandora_object',
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
            self.assertRegex(str(message.output), 'simple_006 would exceed maximum number of allowed values.+2')

    def test_update_with_simple_field(self):
        existing_node = {
            'type': [
                {'target_id': 'islandora_object',
                 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ]
        }
        # Update a node with a simple field of cardinality 1, no subdelimiters. Fields with cardinality of 1 are
        # always replaced with incoming values, they are never appended to. First, when the field already exists.
        self.field_definitions = {
            'field_foo': {
                'cardinality': 1,
            }
        }

        field = workbench_fields.SimpleField()
        csv_record = collections.OrderedDict()
        csv_record['field_foo'] = "Field foo new value"
        csv_record['node_id'] = 1
        node_field_values = [{'value': "Field foo original value"}]
        node = field.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", node_field_values)
        expected_node = {
            'type': [
                {'target_id': 'islandora_object',
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

        # Then when the field doesn't already exist.
        field = workbench_fields.SimpleField()
        csv_record = collections.OrderedDict()
        csv_record['field_foo'] = "Field foo new value"
        csv_record['node_id'] = 1
        node_field_values = [{'value': "Field foo original value"}]
        node = field.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", node_field_values)
        expected_node = {
            'type': [
                {'target_id': 'islandora_object',
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
        with self.assertLogs() as message:
            field = workbench_fields.SimpleField()
            csv_record = collections.OrderedDict()
            csv_record['field_foo'] = "Field foo new value|Second foo new value"
            csv_record['node_id'] = 2
            node_field_values = [{'value': "Field foo original value"}]
            node = field.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", node_field_values)
            expected_node = {
                'type': [
                    {'target_id': 'islandora_object',
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
            self.assertRegex(str(message.output), 'record 2 would exceed maximum number of allowed values.+1')

        # Update a node with a simple field of cardinality unlimited, no subdelimiters. update_mode is 'replace'.
        self.field_definitions = {
            'field_foo': {
                'cardinality': -1,
            }
        }

        field = workbench_fields.SimpleField()
        csv_record = collections.OrderedDict()
        csv_record['node_id'] = 3
        csv_record['field_foo'] = "New value"
        node_field_values = [{'value': "Field foo original value"}]
        self.config['update_mode'] = 'replace'
        node = field.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", node_field_values)
        expected_node = {
            'type': [
                {'target_id': 'islandora_object',
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

        field = workbench_fields.SimpleField()
        csv_record = collections.OrderedDict()
        csv_record['node_id'] = 4
        csv_record['field_foo'] = "New value 1|New value 2"
        node_field_values = [{'value': "Field foo original value"}]
        self.config['update_mode'] = 'replace'
        node = field.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", node_field_values)
        expected_node = {
            'type': [
                {'target_id': 'islandora_object',
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

        field = workbench_fields.SimpleField()
        csv_record = collections.OrderedDict()
        csv_record['node_id'] = 5
        csv_record['field_foo'] = "New value"
        node_field_values = [{'value': "Field foo original value"}]
        self.config['update_mode'] = 'append'
        node = field.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", node_field_values)
        expected_node = {
            'type': [
                {'target_id': 'islandora_object',
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

        field = workbench_fields.SimpleField()
        csv_record = collections.OrderedDict()
        csv_record['node_id'] = 6
        csv_record['field_foo'] = "New value 1|New value 2"
        node_field_values = [{'value': "Field foo original value"}]
        self.config['update_mode'] = 'append'
        node = field.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", node_field_values)
        expected_node = {
            'type': [
                {'target_id': 'islandora_object',
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

        field = workbench_fields.SimpleField()
        csv_record = collections.OrderedDict()
        csv_record['node_id'] = 7
        csv_record['field_foo'] = "New value"
        node_field_values = [{'value': "Field foo original value"}]
        self.config['update_mode'] = 'replace'
        node = field.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", node_field_values)
        expected_node = {
            'type': [
                {'target_id': 'islandora_object',
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

        field = workbench_fields.SimpleField()
        csv_record = collections.OrderedDict()
        csv_record['node_id'] = 8
        csv_record['field_foo'] = "New value"
        node_field_values = [{'value': "Field foo original value"}]
        self.config['update_mode'] = 'append'
        node = field.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", node_field_values)
        expected_node = {
            'type': [
                {'target_id': 'islandora_object',
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
        with self.assertLogs() as message:
            field = workbench_fields.SimpleField()
            csv_record = collections.OrderedDict()
            csv_record['node_id'] = 9
            csv_record['field_foo'] = "First node 9 value|Second node 9 value|Third node 9 value"
            node_field_values = [{'value': "Field foo original value"}]
            self.config['update_mode'] = 'replace'
            node = field.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", node_field_values)
            expected_node = {
                'type': [
                    {'target_id': 'islandora_object',
                     'target_type': 'node_type'}
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
            self.assertRegex(str(message.output), 'record 9 would exceed maximum number of allowed values.+2')

        # Update a node with a simple field of cardinality limited, with subdelimiters. update_mode is 'append'.
        self.field_definitions = {
            'field_foo': {
                'cardinality': 3,
            }
        }

        with self.assertLogs() as message:
            field = workbench_fields.SimpleField()
            csv_record = collections.OrderedDict()
            csv_record['node_id'] = 10
            csv_record['field_foo'] = "First node 10 value|Second node 10 value|Third node 10 value"
            node_field_values = [{'value': "Field foo original value"}]
            self.config['update_mode'] = 'append'
            node = field.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", node_field_values)
            expected_node = {
                'type': [
                    {'target_id': 'islandora_object',
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
                    {'value': "First node 10 value"},
                    {'value': "Second node 10 value"}
                ]
            }
            self.assertDictEqual(node, expected_node)
            self.assertRegex(str(message.output), 'record 10 would exceed maximum number of allowed values.+3')

        # Update a node with update_mode of 'delete'.
        self.field_definitions = {
            'field_foo': {
                'cardinality': 3,
            }
        }

        field = workbench_fields.SimpleField()
        csv_record = collections.OrderedDict()
        csv_record['node_id'] = 11
        csv_record['field_foo'] = "First node 11 value|Second node 11 value"
        node_field_values = [{'value': "Field foo original value"}]
        self.config['update_mode'] = 'delete'
        node = field.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", node_field_values)
        expected_node = {
            'type': [
                {'target_id': 'islandora_object',
                 'target_type': 'node_type'}
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


class TestGeolocationField(unittest.TestCase):

    def setUp(self):
        self.maxDiff = None
        self.config = {
            'subdelimiter': '|',
            'id_field': 'id',
            'update_mode': 'replace'
        }

    def test_create_with_geolocation_field(self):
        existing_node = {
            'type': [
                {'target_id': 'islandora_object',
                 'target_type': 'node_type'}
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
                {'target_id': 'islandora_object',
                 'target_type': 'node_type'}
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
                    {'target_id': 'islandora_object',
                     'target_type': 'node_type'}
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
            self.assertRegex(str(message.output), 'for record geo_002 would exceed maximum number of allowed values.+1')

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
                {'target_id': 'islandora_object',
                 'target_type': 'node_type'}
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
        csv_record['field_foo'] = "59.16667,-123.93333|69.16667,-123.93333"
        node = field.create(self.config, self.field_definitions, existing_node, csv_record, "field_foo")
        expected_node = {
            'type': [
                {'target_id': 'islandora_object',
                 'target_type': 'node_type'}
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
                {'target_id': 'islandora_object',
                 'target_type': 'node_type'}
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
                'cardinality': 2,
            }
        }

        field = workbench_fields.GeolocationField()
        csv_record = collections.OrderedDict()
        csv_record['id'] = "geo_006"
        csv_record['field_foo'] = "51.16667,-123.93333|61.16667,-123.93333|63.16667,-123.93333"
        node = field.create(self.config, self.field_definitions, existing_node, csv_record, "field_foo")
        expected_node = {
            'type': [
                {'target_id': 'islandora_object',
                 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {'lat': '51.16667', 'lng': '-123.93333'},
                {'lat': '61.16667', 'lng': '-123.93333'}
            ]
        }
        self.assertDictEqual(node, expected_node)

    def test_update_with_geolocation_field(self):
        existing_node = {
            'type': [
                {'target_id': 'islandora_object',
                 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ]
        }

        # Update a node with a geolocation field of cardinality 1, no subdelimiters. Fields with cardinality of 1 are
        # always replaced with incoming values, they are never appended to.
        self.field_definitions = {
            'field_foo': {
                'cardinality': 1,
            }
        }

        geolocation = workbench_fields.GeolocationField()
        csv_record = collections.OrderedDict()
        csv_record['node_id'] = 100
        csv_record['field_foo'] = "50.16667,-123.93333"
        node_field_values = [{"lat": "49.16667", "lng": "-122.93333"}]
        node = geolocation.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", node_field_values)
        expected_node = {
            'type': [
                {'target_id': 'islandora_object',
                 'target_type': 'node_type'}
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

        # Update a node with a geolocation field of cardinality 1, with subdelimiters. Fields with cardinality of 1 are
        # always replaced with incoming values, they are never appended to.
        self.field_definitions = {
            'field_foo': {
                'cardinality': 1,
            }
        }

        with self.assertLogs() as message:
            geolocation = workbench_fields.GeolocationField()
            csv_record = collections.OrderedDict()
            csv_record['node_id'] = 101
            csv_record['field_foo'] = "50.16667,-123.93333|46.16667,-113.93333"
            node_field_values = [{"lat": "49.16667", "lng": "-122.93333"}]
            node = geolocation.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", node_field_values)
            expected_node = {
                'type': [
                    {'target_id': 'islandora_object',
                     'target_type': 'node_type'}
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
            self.assertRegex(str(message.output), 'for record 101 would exceed maximum number of allowed values.+1')

        # Update a node with a geolocation field of cardinality unlimited, no subdelimiters. update_mode is 'replace'.
        self.config['update_mode'] = 'replace'
        self.field_definitions = {
            'field_foo': {
                'cardinality': -1,
            }
        }

        geolocation = workbench_fields.GeolocationField()
        csv_record = collections.OrderedDict()
        csv_record['node_id'] = 102
        csv_record['field_foo'] = "55.26667,-113.93333"
        node_field_values = [{"lat": "49.16667", "lng": "-122.93333"}]
        node = geolocation.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", node_field_values)
        expected_node = {
            'type': [
                {'target_id': 'islandora_object',
                 'target_type': 'node_type'}
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

        # Update a node with a geolocation field of cardinality unlimited, with subdelimiters. update_mode is 'replace'.
        self.config['update_mode'] = 'replace'
        self.field_definitions = {
            'field_foo': {
                'cardinality': -1,
            }
        }

        geolocation = workbench_fields.GeolocationField()
        csv_record = collections.OrderedDict()
        csv_record['node_id'] = 103
        csv_record['field_foo'] = "55.26661,-113.93331|51.26667,-111.93333"
        node_field_values = [{"lat": "49.16667", "lng": "-122.93333"}]
        node103 = geolocation.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", node_field_values)
        expected_node = {
            'type': [
                {'target_id': 'islandora_object',
                 'target_type': 'node_type'}
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

        # Update a node with a geolocation field of cardinality unlimited, no subdelimiters. update_mode is 'append'.
        self.config['update_mode'] = 'append'
        self.field_definitions = {
            'field_foo': {
                'cardinality': -1,
            }
        }

        geolocation = workbench_fields.GeolocationField()
        csv_record = collections.OrderedDict()
        csv_record['node_id'] = 104
        csv_record['field_foo'] = "35.2,-99.9"
        node_field_values = [{"lat": "49.1", "lng": "-122.9"}]
        node104 = geolocation.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", node_field_values)
        expected_node = {
            'type': [
                {'target_id': 'islandora_object',
                 'target_type': 'node_type'}
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
        self.assertDictEqual(node104, expected_node)

        # Update a node with a geolocation field of cardinality unlimited, with subdelimiters. update_mode is 'append'.
        geolocation = workbench_fields.GeolocationField()
        csv_record = collections.OrderedDict()
        self.config['update_mode'] = 'append'
        csv_record['node_id'] = 105
        csv_record['field_foo'] = "56.2,-113.9|51.2,-100.9"
        node_field_values = [{'lat': "49.1", 'lng': "-122.9"}]
        node = geolocation.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", node_field_values)
        expected_node = {
            'type': [
                {'target_id': 'islandora_object',
                 'target_type': 'node_type'}
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

        # Update a node with a geolocation field of cardinality limited, no subdelimiters. update_mode is 'replace'.
        self.config['update_mode'] = 'replace'
        self.field_definitions = {
            'field_foo': {
                'cardinality': 2,
            }
        }

        geolocation = workbench_fields.GeolocationField()
        csv_record = collections.OrderedDict()
        csv_record['node_id'] = 106
        csv_record['field_foo'] = "53.26667,-133.93333"
        node_field_values = [{"lat": "43.16667", "lng": "-123.63"}]
        node = geolocation.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", node_field_values)
        expected_node = {
            'type': [
                {'target_id': 'islandora_object',
                 'target_type': 'node_type'}
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

        self.config['update_mode'] = 'replace'
        self.field_definitions = {
            'field_foo': {
                'cardinality': 2,
            }
        }

        geolocation = workbench_fields.GeolocationField()
        csv_record = collections.OrderedDict()
        csv_record['node_id'] = 106
        csv_record['field_foo'] = "53.26667,-133.93333|51.34,-111.1|51.51,-111.999"
        node_field_values = [{"lat": "43.16667", "lng": "-123.63"}]
        node = geolocation.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", node_field_values)
        expected_node = {
            'type': [
                {'target_id': 'islandora_object',
                 'target_type': 'node_type'}
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

        # Update a node with a geolocation field of cardinality limited, no subdelimiters. update_mode is 'append'.
        self.config['update_mode'] = 'append'
        self.field_definitions = {
            'field_foo': {
                'cardinality': 2,
            }
        }

        geolocation = workbench_fields.GeolocationField()
        csv_record = collections.OrderedDict()
        csv_record['node_id'] = 107
        csv_record['field_foo'] = "57.2,-133.7"
        node_field_values = [{"lat": "47.1", "lng": "-127.6"}]
        node = geolocation.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", node_field_values)
        expected_node = {
            'type': [
                {'target_id': 'islandora_object',
                 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {'lat': '47.1', 'lng': '-127.6'},
                {'lat': '57.2', 'lng': '-133.7'}
            ]
        }
        self.assertDictEqual(node, expected_node)

        self.config['update_mode'] = 'append'
        self.field_definitions = {
            'field_foo': {
                'cardinality': 3,
            }
        }

        geolocation = workbench_fields.GeolocationField()
        csv_record = collections.OrderedDict()
        csv_record['node_id'] = 107
        csv_record['field_foo'] = "57.2,-133.7"
        node_field_values = [{"lat": "47.1", "lng": "-127.6"}, {"lat": "47.11", "lng": "-127.61"}]
        node = geolocation.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", node_field_values)
        expected_node = {
            'type': [
                {'target_id': 'islandora_object',
                 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': [
                {'lat': '47.1', 'lng': '-127.6'},
                {'lat': '47.11', 'lng': '-127.61'},
                {'lat': '57.2', 'lng': '-133.7'}
            ]
        }
        self.assertDictEqual(node, expected_node)

        # Update a node with a geolocation field of cardinality limited, with subdelimiters. update_mode is 'replace'.
        self.config['update_mode'] = 'replace'
        self.field_definitions = {
            'field_foo': {
                'cardinality': 2,
            }
        }

        geolocation = workbench_fields.GeolocationField()
        csv_record = collections.OrderedDict()
        csv_record['node_id'] = 108
        csv_record['field_foo'] = "55.80,-113.80|55.82,-113.82|55.83,-113.83"
        node_field_values = [{"lat": "49.16667", "lng": "-122.93333"}]
        node103 = geolocation.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", node_field_values)
        expected_node = {
            'type': [
                {'target_id': 'islandora_object',
                 'target_type': 'node_type'}
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
        self.assertDictEqual(node103, expected_node)

        # Update a node with a geolocation field of cardinality limited, with subdelimiters. update_mode is 'append'.
        self.config['update_mode'] = 'append'
        self.field_definitions = {
            'field_foo': {
                'cardinality': 2,
            }
        }

        geolocation = workbench_fields.GeolocationField()
        csv_record = collections.OrderedDict()
        csv_record['node_id'] = 109
        csv_record['field_foo'] = "55.90,-113.90|55.92,-113.92|55.93,-113.93"
        node_field_values = [{"lat": "49.9", "lng": "-122.9"}]
        node103 = geolocation.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", node_field_values)
        expected_node = {
            'type': [
                {'target_id': 'islandora_object',
                 'target_type': 'node_type'}
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
        self.assertDictEqual(node103, expected_node)

        # Update a node with update_mode of 'delete'.
        self.config['update_mode'] = 'delete'
        self.field_definitions = {
            'field_foo': {
                'cardinality': 2,
            }
        }

        geolocation = workbench_fields.GeolocationField()
        csv_record = collections.OrderedDict()
        csv_record['node_id'] = 109
        csv_record['field_foo'] = "55.90,-113.90|55.92,-113.92|55.93,-113.93"
        node_field_values = [{"lat": "49.9", "lng": "-122.9"}]
        node103 = geolocation.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", node_field_values)
        expected_node = {
            'type': [
                {'target_id': 'islandora_object',
                 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ],
            'field_foo': []
        }
        self.assertDictEqual(node103, expected_node)


class TestLinkField(unittest.TestCase):

    def setUp(self):
        self.maxDiff = None

        self.config = {
            'subdelimiter': '|',
            'id_field': 'id',
            'update_mode': 'replace'
        }

    def test_create_with_link_field(self):
        existing_node = {
            'type': [
                {'target_id': 'islandora_object',
                 'target_type': 'node_type'}
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
                {'target_id': 'islandora_object',
                 'target_type': 'node_type'}
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
            csv_record['field_foo'] = "http://bar.com%%Bar webiste|http://biz.com%%Biz website"
            node = field.create(self.config, self.field_definitions, existing_node, csv_record, "field_foo")
            expected_node = {
                'type': [
                    {'target_id': 'islandora_object',
                     'target_type': 'node_type'}
                ],
                'title': [
                    {'value': "Test node"}
                ],
                'status': [
                    {'value': 1}
                ],
                'field_foo': [
                    {'uri': 'http://bar.com', 'title': 'Bar webiste'}
                ]
            }
            self.assertDictEqual(node, expected_node)
            self.assertRegex(str(message.output), 'for record link_002 would exceed maximum number of allowed values.+1')

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
                {'target_id': 'islandora_object',
                 'target_type': 'node_type'}
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
        csv_record['field_foo'] = "http://link4-1.net%%Link 004-1 website|http://link4-2.net%%Link 004-2 website"
        node = field.create(self.config, self.field_definitions, existing_node, csv_record, "field_foo")
        expected_node = {
            'type': [
                {'target_id': 'islandora_object',
                 'target_type': 'node_type'}
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
                {'target_id': 'islandora_object',
                 'target_type': 'node_type'}
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

        field = workbench_fields.LinkField()
        csv_record = collections.OrderedDict()
        csv_record['id'] = "link_006"
        csv_record['field_foo'] = "http://link6-1.net%%Link 006-1 website|http://link6-2.net%%Link 006-2 website|http://link6-3.net%%Link 006-3 website"
        node = field.create(self.config, self.field_definitions, existing_node, csv_record, "field_foo")
        expected_node = {
            'type': [
                {'target_id': 'islandora_object',
                 'target_type': 'node_type'}
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

    def test_update_with_link_field(self):
        existing_node = {
            'type': [
                {'target_id': 'islandora_object',
                 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ]
        }

        # Update a node with a link field of cardinality 1, no subdelimiters. Fields with cardinality of 1 are
        # always replaced with incoming values, they are never appended to.
        self.field_definitions = {
            'field_foo': {
                'cardinality': 1,
            }
        }

        field = workbench_fields.LinkField()
        csv_record = collections.OrderedDict()
        csv_record['node_id'] = 100
        csv_record['field_foo'] = "http://update1replacement.net%%Update 1 replacement's website"
        node_field_values = [{"uri": "http://update1original.net", "title": "Update 1 original's website"}]
        node = field.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", node_field_values)
        expected_node = {
            'type': [
                {'target_id': 'islandora_object',
                 'target_type': 'node_type'}
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

        # Update a node with a link field of cardinality 1, with subdelimiters. Fields with cardinality of 1 are
        # always replaced with incoming values, they are never appended to.
        self.field_definitions = {
            'field_foo': {
                'cardinality': 1,
            }
        }

        with self.assertLogs() as message:
            field = workbench_fields.LinkField()
            csv_record = collections.OrderedDict()
            csv_record['node_id'] = 101
            csv_record['field_foo'] = "http://update2replacement.net%%Update 2 replacement's website|http://update2-1replacement.net%%Update 2-1 replacement's website"
            node_field_values = [{"uri": "http://update2original.net", "title": "Update 2 original's website"}]
            node = field.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", node_field_values)
            expected_node = {
                'type': [
                    {'target_id': 'islandora_object',
                     'target_type': 'node_type'}
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
            self.assertRegex(str(message.output), 'for record 101 would exceed maximum number of allowed values.+1')

        # Update a node with a link field of cardinality unlimited, no subdelimiters. update_mode is 'replace'.
        self.config['update_mode'] = 'replace'
        self.field_definitions = {
            'field_foo': {
                'cardinality': -1,
            }
        }

        field = workbench_fields.LinkField()
        csv_record = collections.OrderedDict()
        csv_record['node_id'] = 102
        csv_record['field_foo'] = "http://updatenode102replace.net%%Update to node 102 replacement's website"
        node_field_values = [{"uri": "http://updatenode102original.net", "title": "Update node 102 original's website"}]
        node = field.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", node_field_values)
        expected_node = {
            'type': [
                {'target_id': 'islandora_object',
                 'target_type': 'node_type'}
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

        # Update a node with a link field of cardinality unlimited, with subdelimiters. update_mode is 'replace'.
        self.config['update_mode'] = 'replace'
        self.field_definitions = {
            'field_foo': {
                'cardinality': -1,
            }
        }

        field = workbench_fields.LinkField()
        csv_record = collections.OrderedDict()
        csv_record['node_id'] = 103
        csv_record['field_foo'] = "http://updatenode103replace1.net%%103 replacement 1|http://updatenode103replacement2.net%%103 replacement 2"
        node_field_values = [{"uri": "http://updatenode103original.net", "title": "Update node 103 original's website"}]
        node = field.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", node_field_values)
        expected_node = {
            'type': [
                {'target_id': 'islandora_object',
                 'target_type': 'node_type'}
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

        # Update a node with a link field of cardinality unlimited, no subdelimiters. update_mode is 'append'.
        self.config['update_mode'] = 'replace'
        self.field_definitions = {
            'field_foo': {
                'cardinality': -1,
            }
        }
        config = {
            'subdelimiter': '|',
            'id_field': 'id',
            'update_mode': 'append'
        }

        field = workbench_fields.LinkField()
        csv_record = collections.OrderedDict()
        csv_record['node_id'] = 104
        csv_record['field_foo'] = "http://node104a.net%%Node 104 a"
        node_field_values = [{"uri": "http://node104o.net", "title": "Node 104 o"}]
        node = field.update(config, self.field_definitions, existing_node, csv_record, "field_foo", node_field_values)
        expected_node = {
            'type': [
                {'target_id': 'islandora_object',
                 'target_type': 'node_type'}
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

        # Update a node with a link field of cardinality unlimited, with subdelimiters. update_mode is 'append'.
        self.config['update_mode'] = 'replace'
        self.field_definitions = {
            'field_foo': {
                'cardinality': -1,
            }
        }
        config = {
            'subdelimiter': '|',
            'id_field': 'id',
            'update_mode': 'append'
        }

        field = workbench_fields.LinkField()
        csv_record = collections.OrderedDict()
        csv_record['node_id'] = 105
        csv_record['field_foo'] = "http://node105-1.net%%Node 105-1|http://node105-2.net%%Node 105-2"
        node_field_values = [{"uri": "http://node105original.net", "title": "Node 105 original"}]
        node = field.update(config, self.field_definitions, existing_node, csv_record, "field_foo", node_field_values)
        expected_node = {
            'type': [
                {'target_id': 'islandora_object',
                 'target_type': 'node_type'}
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

        # Update a node with a link field of cardinality limited, no subdelimiters. update_mode is 'replace'.
        self.config['update_mode'] = 'replace'
        self.field_definitions = {
            'field_foo': {
                'cardinality': 2,
            }
        }

        field = workbench_fields.LinkField()
        csv_record = collections.OrderedDict()
        csv_record['node_id'] = 106
        csv_record['field_foo'] = "http://node06r.net%%Node 106 replacement"
        node_field_values = [{"uri": "http://106o-1.net", "title": "Node 106 1 original"}, {"uri": "http://106o-2.net", "title": "Node 106 2 original"}]
        node = field.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", node_field_values)
        expected_node = {
            'type': [
                {'target_id': 'islandora_object',
                 'target_type': 'node_type'}
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

        # Update a node with a link field of cardinality limited, no subdelimiters. update_mode is 'append'.
        self.config['update_mode'] = 'append'
        self.field_definitions = {
            'field_foo': {
                'cardinality': 2,
            }
        }

        field = workbench_fields.LinkField()
        csv_record = collections.OrderedDict()
        csv_record['node_id'] = 107
        csv_record['field_foo'] = "http://node07a.net%%Node 107 appended"
        node_field_values = [{"uri": "http://107o-1.net", "title": "Node 107 1 original"}, {"uri": "http://107o-2.net", "title": "Node 107 2 original"}]
        node = field.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", node_field_values)
        expected_node = {
            'type': [
                {'target_id': 'islandora_object',
                 'target_type': 'node_type'}
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

        # Update a node with a link field of cardinality limited, with subdelimiters. update_mode is 'append'.
        self.config['update_mode'] = 'append'
        self.field_definitions = {
            'field_foo': {
                'cardinality': 2,
            }
        }

        field = workbench_fields.LinkField()
        csv_record = collections.OrderedDict()
        csv_record['node_id'] = 108
        csv_record['field_foo'] = "http://08a-1.net%%Node 108 1 appended|http://108a-2.net%%Node 108 2 appended"
        node_field_values = [{"uri": "http://108o-1.net", "title": "Node 108 1 original"}, {"uri": "http://108o-2.net", "title": "Node 108 2 original"}]
        node = field.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", node_field_values)
        expected_node = {
            'type': [
                {'target_id': 'islandora_object',
                 'target_type': 'node_type'}
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

        self.field_definitions = {
            'field_foo': {
                'cardinality': 3,
            }
        }

        field = workbench_fields.LinkField()
        csv_record = collections.OrderedDict()
        csv_record['node_id'] = 109
        csv_record['field_foo'] = "http://09a-1.net%%Node 109 1 appended|http://109a-2.net%%Node 109 2 appended"
        node_field_values = [{"uri": "http://109o-1.net", "title": "Node 109 1 original"}, {"uri": "http://109o-2.net", "title": "Node 109 2 original"}]
        node = field.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", node_field_values)
        expected_node = {
            'type': [
                {'target_id': 'islandora_object',
                 'target_type': 'node_type'}
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

        # Update a node with a link field of cardinality limited, with subdelimiters. update_mode is 'replace'.
        self.config['update_mode'] = 'replace'
        self.field_definitions = {
            'field_foo': {
                'cardinality': 2,
            }
        }

        field = workbench_fields.LinkField()
        csv_record = collections.OrderedDict()
        csv_record['node_id'] = 110
        csv_record['field_foo'] = "http://110r-1.net%%Node 110 1 replaced|http://110r-2.net%%Node 110 2 replaced"
        node_field_values = [{"uri": "http://110o-1.net", "title": "Node 110 1 original"}, {"uri": "http://110o-2.net", "title": "Node 110 2 original"}]
        node = field.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", node_field_values)
        expected_node = {
            'type': [
                {'target_id': 'islandora_object',
                 'target_type': 'node_type'}
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

        self.field_definitions = {
            'field_foo': {
                'cardinality': 3,
            }
        }

        field = workbench_fields.LinkField()
        csv_record = collections.OrderedDict()
        csv_record['node_id'] = 111
        csv_record['field_foo'] = "http://111r-1.net%%Node 111 1 replaced|http://111r-2.net%%Node 111 2 replaced"
        node_field_values = [{"uri": "http://111o-1.net", "title": "Node 111 1 original"}, {"uri": "http://111o-2.net", "title": "Node 111 2 original"}]
        node = field.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", node_field_values)
        expected_node = {
            'type': [
                {'target_id': 'islandora_object',
                 'target_type': 'node_type'}
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

        # Update a node with update_mode of 'delete'.
        self.config['update_mode'] = 'delete'
        self.field_definitions = {
            'field_foo': {
                'cardinality': 3,
            }
        }

        field = workbench_fields.LinkField()
        csv_record = collections.OrderedDict()
        csv_record['node_id'] = 112
        csv_record['field_foo'] = "http://112r-1.net%%Node 112 1 replaced|http://112r-2.net%%Node 112 2 replaced"
        node_field_values = [{"uri": "http://112o-1.net", "title": "Node 112 1 original"}, {"uri": "http://112o-2.net", "title": "Node 112 2 original"}]
        node = field.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", node_field_values)
        expected_node = {
            'type': [
                {'target_id': 'islandora_object',
                 'target_type': 'node_type'}
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


class TestTypedRelationField(unittest.TestCase):

    def setUp(self):
        pass

    def test_create_with_typed_relation_field(self):
        # Create a node with a typed_relation field of cardinality 1, no subdelimiters.
        # Create a node with a typed_relation field of cardinality 1, with subdelimiters.
        # Create a node with a typed_relation field of cardinality unlimited, no subdelimiters.
        # Create a node with a typed_relation field of cardinality unlimited, with subdelimiters.
        # Create a node with a typed_relation field of cardinality limited, no subdelimiters.
        # Create a node with a typed_relation field of cardinality limited, with subdelimiters.
        pass

    def test_update_with_typed_relation_field(self):
        # Update a node with a typed_relation field of cardinality 1, no subdelimiters. Fields with cardinality of 1 are
        # always replaced with incoming values, they are never appended to.
        # Update a node with a typed_relation field of cardinality 1, with subdelimiters. Fields with cardinality of 1 are
        # always replaced with incoming values, they are never appended to.
        # Update a node with a typed_relation field of cardinality unlimited, no subdelimiters. update_mode is 'replace'.
        # Update a node with a typed_relation field of cardinality unlimited, with subdelimiters. update_mode is 'replace'.
        # Update a node with a typed_relation field of cardinality unlimited, no subdelimiters. update_mode is 'append'.
        # Update a node with a typed_relation field of cardinality unlimited, with subdelimiters. update_mode is 'append'.
        # Update a node with a typed_relation field of cardinality limited, no subdelimiters. update_mode is 'replace'.
        # Update a node with a typed_relation field of cardinality limited, no subdelimiters. update_mode is 'append'.
        # Update a node with a typed_relation field of cardinality limited, with subdelimiters. update_mode is 'replace'.
        # Update a node with a typed_relation field of cardinality limited, with subdelimiters. update_mode is 'append'.
        # Update a node with update_mode of 'delete'.
        pass


class TestEntityRefererenceField(unittest.TestCase):

    def setUp(self):
        self.maxDiff = None

        self.config = {
            'subdelimiter': '|',
            'id_field': 'id',
            'update_mode': 'replace'
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
            self.assertRegex(str(message.output), 'for record term_entity_reference_002 would exceed maximum number of allowed values.+1')

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
            self.assertRegex(str(message.output), 'for record node_entity_reference_002 would exceed maximum number of allowed values.+1')

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
        csv_record['field_foo'] = "1010|1011"
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
            csv_record['field_foo'] = "101|102|103"
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
            self.assertRegex(str(message.output), 'for record term_entity_reference_006 would exceed maximum number of allowed values.+2')

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
            csv_record['field_foo'] = "200|201"
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
            self.assertRegex(str(message.output), 'for record node_entity_reference_006 would exceed maximum number of allowed values.+2')

    def test_update_with_entity_reference_field(self):
        existing_node = {
            'type': [
                {'target_id': 'islandora_object',
                 'target_type': 'node_type'}
            ],
            'title': [
                {'value': "Test node"}
            ],
            'status': [
                {'value': 1}
            ]
        }

        # Update a node with an entity_reference field of cardinality 1, no subdelimiters. Fields with cardinality of 1 are
        # always replaced with incoming values, they are never appended to. Update both taxonomy term and node references.
        self.field_definitions = {
            'field_foo': {
                'cardinality': 1,
                'target_type': 'taxonomy_term'
            }
        }

        field = workbench_fields.EntityReferenceField()
        csv_record = collections.OrderedDict()
        csv_record['node_id'] = 100
        csv_record['field_foo'] = '5'
        node_field_values = [{'target_id': '1', 'target_type': 'taxonomy_term'}]
        node = field.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", node_field_values)
        expected_node = {
            'type': [
                {'target_id': 'islandora_object',
                 'target_type': 'node_type'}
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

        field = workbench_fields.EntityReferenceField()
        csv_record = collections.OrderedDict()
        csv_record['node_id'] = 101
        csv_record['field_foo'] = '20'
        node_field_values = [{'target_id': '10', 'target_type': 'node'}]
        node = field.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", node_field_values)
        expected_node = {
            'type': [
                {'target_id': 'islandora_object',
                 'target_type': 'node_type'}
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

        # Update a node with an entity_reference field of cardinality 1, with subdelimiters. Fields with cardinality of 1 are
        # always replaced with incoming values, they are never appended to. Update both taxonomy term and node references.
        self.field_definitions = {
            'field_foo': {
                'cardinality': 1,
                'target_type': 'taxonomy_term'
            }
        }

        with self.assertLogs() as message:
            field = workbench_fields.EntityReferenceField()
            csv_record = collections.OrderedDict()
            csv_record['node_id'] = 102
            csv_record['field_foo'] = '10|15'
            node_field_values = [{'target_id': '1', 'target_type': 'taxonomy_term'}]
            node = field.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", node_field_values)
            expected_node = {
                'type': [
                    {'target_id': 'islandora_object',
                     'target_type': 'node_type'}
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
            self.assertRegex(str(message.output), 'for record 102 would exceed maximum number of allowed values.+1')

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
                    {'target_id': 'islandora_object',
                     'target_type': 'node_type'}
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
            self.assertRegex(str(message.output), 'for record 103 would exceed maximum number of allowed values.+1')

        # Update a node with an entity_reference field of cardinality unlimited, no subdelimiters. update_mode is 'replace',
        # for both taxonomy term and node references.
        self.config['update_mode'] = 'replace'
        self.field_definitions = {
            'field_foo': {
                'cardinality': -1,
                'target_type': 'taxonomy_term'
            }
        }

        field = workbench_fields.EntityReferenceField()
        csv_record = collections.OrderedDict()
        csv_record['node_id'] = 104
        csv_record['field_foo'] = '30'
        node_field_values = [{'target_id': '40', 'target_type': 'taxonomy_term'}]
        node = field.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", node_field_values)
        expected_node = {
            'type': [
                {'target_id': 'islandora_object',
                 'target_type': 'node_type'}
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

        self.config['update_mode'] = 'replace'
        self.field_definitions = {
            'field_foo': {
                'cardinality': -1,
                'target_type': 'node_type'
            }
        }

        self.field_definitions = {
            'field_foo': {
                'cardinality': -1,
                'target_type': 'node'
            }
        }

        field = workbench_fields.EntityReferenceField()
        csv_record = collections.OrderedDict()
        csv_record['node_id'] = 105
        csv_record['field_foo'] = '40'
        node_field_values = [{'target_id': '50', 'target_type': 'node'}]
        node = field.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", node_field_values)
        expected_node = {
            'type': [
                {'target_id': 'islandora_object',
                 'target_type': 'node_type'}
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

        # Update a node with an entity_reference field of cardinality unlimited, with subdelimiters. update_mode is 'replace',
        # for both taxonomy term and node references.
        self.config['update_mode'] = 'replace'
        self.field_definitions = {
            'field_foo': {
                'cardinality': -1,
                'target_type': 'taxonomy_term'
            }
        }

        field = workbench_fields.EntityReferenceField()
        csv_record = collections.OrderedDict()
        csv_record['node_id'] = 106
        csv_record['field_foo'] = '51|52'
        node_field_values = [{'target_id': '50', 'target_type': 'taxonomy_term'}]
        node = field.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", node_field_values)
        expected_node = {
            'type': [
                {'target_id': 'islandora_object',
                 'target_type': 'node_type'}
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

        self.config['update_mode'] = 'replace'
        self.field_definitions = {
            'field_foo': {
                'cardinality': -1,
                'target_type': 'node'
            }
        }

        field = workbench_fields.EntityReferenceField()
        csv_record = collections.OrderedDict()
        csv_record['node_id'] = 107
        csv_record['field_foo'] = '61|62'
        node_field_values = [{'target_id': '60', 'target_type': 'node'}]
        node = field.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", node_field_values)
        expected_node = {
            'type': [
                {'target_id': 'islandora_object',
                 'target_type': 'node_type'}
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

        # Update a node with an entity_reference field of cardinality unlimited, no subdelimiters. update_mode is 'append',
        # for both taxonomy term and node references.
        self.config['update_mode'] = 'append'
        self.field_definitions = {
            'field_foo': {
                'cardinality': -1,
                'target_type': 'taxonomy_term'
            }
        }

        field = workbench_fields.EntityReferenceField()
        csv_record = collections.OrderedDict()
        csv_record['node_id'] = 108
        csv_record['field_foo'] = '71'
        node_field_values = [{'target_id': '70', 'target_type': 'taxonomy_term'}]
        node = field.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", node_field_values)
        expected_node = {
            'type': [
                {'target_id': 'islandora_object',
                 'target_type': 'node_type'}
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

        self.config['update_mode'] = 'append'
        self.field_definitions = {
            'field_foo': {
                'cardinality': -1,
                'target_type': 'node'
            }
        }

        field = workbench_fields.EntityReferenceField()
        csv_record = collections.OrderedDict()
        csv_record['node_id'] = 109
        csv_record['field_foo'] = '81'
        node_field_values = [{'target_id': '80', 'target_type': 'node_type'}]
        node = field.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", node_field_values)
        expected_node = {
            'type': [
                {'target_id': 'islandora_object',
                 'target_type': 'node_type'}
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

        # Update a node with an entity_reference field of cardinality unlimited, with subdelimiters. update_mode is 'append',
        # for both taxonomy term and node references.
        self.config['update_mode'] = 'append'
        self.field_definitions = {
            'field_foo': {
                'cardinality': -1,
                'target_type': 'taxonomy_term'
            }
        }

        field = workbench_fields.EntityReferenceField()
        csv_record = collections.OrderedDict()
        csv_record['node_id'] = 110
        csv_record['field_foo'] = '72|73'
        node_field_values = [{'target_id': '70', 'target_type': 'taxonomy_term'}]
        node = field.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", node_field_values)
        expected_node = {
            'type': [
                {'target_id': 'islandora_object',
                 'target_type': 'node_type'}
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

        self.config['update_mode'] = 'append'
        self.field_definitions = {
            'field_foo': {
                'cardinality': -1,
                'target_type': 'node'
            }
        }

        field = workbench_fields.EntityReferenceField()
        csv_record = collections.OrderedDict()
        csv_record['node_id'] = 111
        csv_record['field_foo'] = '74|75'
        node_field_values = [{'target_id': '71', 'target_type': 'node_type'}]
        node = field.update(self.config, self.field_definitions, existing_node, csv_record, "field_foo", node_field_values)
        expected_node = {
            'type': [
                {'target_id': 'islandora_object',
                 'target_type': 'node_type'}
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

        # Update a node with an entity_reference field of cardinality limited, no subdelimiters. update_mode is 'replace',
        # for both taxonomy term and node references.
        # Update a node with an entity_reference field of cardinality limited, no subdelimiters. update_mode is 'append',
        # for both taxonomy term and node references.
        # Update a node with an entity_reference field of cardinality limited, with subdelimiters. update_mode is 'replace',
        # for both taxonomy term and node references.
        # Update a node with an entity_reference field of cardinality limited, with subdelimiters. update_mode is 'append',
        # for both taxonomy term and node references.
        # Update a node with update_mode of 'delete', for both taxonomy term and node references.
        pass


if __name__ == '__main__':
    unittest.main()
