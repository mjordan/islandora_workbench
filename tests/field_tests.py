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
            node_field_values = [{"lat" : "49.16667", "lng": "-122.93333"}]
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
        self.field_definitions = {
            'field_foo': {
                'cardinality': -1,
            }
        }

        geolocation = workbench_fields.GeolocationField()
        csv_record = collections.OrderedDict()
        self.config['update_mode'] = 'replace'
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
        self.field_definitions = {
            'field_foo': {
                'cardinality': -1,
            }
        }

        geolocation = workbench_fields.GeolocationField()
        csv_record = collections.OrderedDict()
        self.config['update_mode'] = 'replace'
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
        '''
        self.field_definitions = {
            'field_foo': {
                'cardinality': -1,
            }
        }

        geolocation = workbench_fields.GeolocationField()
        csv_record = collections.OrderedDict()
        self.config['update_mode'] = 'append'
        csv_record['node_id'] = 104
        csv_record['field_foo'] = "35.2,-99.9"
        node_field_values = [{"lat": "49.1" , "lng": "-122.9"}]
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
        '''

        # Update a node with a geolocation field of cardinality unlimited, with subdelimiters. update_mode is 'append'.
        '''
        geolocation = workbench_fields.GeolocationField()
        csv_record = collections.OrderedDict()
        self.config['update_mode'] = 'append'
        csv_record['node_id'] = 105
        csv_record['field_foo'] = "56.2,-113.9|51.2,-100.9"
        node_field_values = [{"49.1,-122.9"}]
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
                {'lat': '55.2', 'lng': '-113.9'},
                {'lat': '51.2', 'lng': '-100.9'}
            ]
        }
        self.assertDictEqual(node, expected_node)
        '''

        # Update a node with a geolocation field of cardinality limited, no subdelimiters. update_mode is 'replace'.
        # Update a node with a geolocation field of cardinality limited, no subdelimiters. update_mode is 'append'.
        # Update a node with a geolocation field of cardinality limited, with subdelimiters. update_mode is 'replace'.
        # Update a node with a geolocation field of cardinality limited, with subdelimiters. update_mode is 'append'.
        # Update a node with update_mode of 'delete'.
        pass


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
        pass

    def test_create_with_entity_referernce_field(self):
        # Create a node with an entity_reference field of cardinality 1, no subdelimiters.
        # Create a node with an entity_reference field of cardinality 1, with subdelimiters.
        # Create a node with an entity_reference field of cardinality unlimited, no subdelimiters.
        # Create a node with an entity_reference field of cardinality unlimited, with subdelimiters.
        # Create a node with an entity_reference field of cardinality limited, no subdelimiters.
        # Create a node with an entity_reference field of cardinality limited, with subdelimiters.
        pass

    def test_update_with_entity_referernce_field(self):
        # Update a node with an entity_reference field of cardinality 1, no subdelimiters. Fields with cardinality of 1 are
        # always replaced with incoming values, they are never appended to.
        # Update a node with an entity_reference field of cardinality 1, with subdelimiters. Fields with cardinality of 1 are
        # always replaced with incoming values, they are never appended to.
        # Update a node with an entity_reference field of cardinality unlimited, no subdelimiters. update_mode is 'replace'.
        # Update a node with an entity_reference field of cardinality unlimited, with subdelimiters. update_mode is 'replace'.
        # Update a node with an entity_reference field of cardinality unlimited, no subdelimiters. update_mode is 'append'.
        # Update a node with an entity_reference field of cardinality unlimited, with subdelimiters. update_mode is 'append'.
        # Update a node with an entity_reference field of cardinality limited, no subdelimiters. update_mode is 'replace'.
        # Update a node with an entity_reference field of cardinality limited, no subdelimiters. update_mode is 'append'.
        # Update a node with an entity_reference field of cardinality limited, with subdelimiters. update_mode is 'replace'.
        # Update a node with an entity_reference field of cardinality limited, with subdelimiters. update_mode is 'append'.
        # Update a node with update_mode of 'delete'.
        pass


if __name__ == '__main__':
    unittest.main()
