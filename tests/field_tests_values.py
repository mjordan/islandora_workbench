"""unittest tests for the 'remove_invalid_values' methods in Drupal REST JSON field handlers.
Do not require a live Drupal.

Incomplete. Tracking issue is https://github.com/mjordan/islandora_workbench/issues/424.
"""

import sys
import os
import unittest

from unittest import mock

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import workbench_fields


class TestSimpleField(unittest.TestCase):

    def test_simple_field_edtf_validate(self):
        config = dict()
        field_definitions = {"field_foo": {"field_type": "edtf"}}

        with self.assertLogs() as message:
            input = ["1900", "1xxx", "1901", "1902"]
            field = workbench_fields.SimpleField()
            output = field.remove_invalid_values(
                config, field_definitions, "field_foo", input
            )
            self.assertEqual(output, ["1900", "1901", "1902"])
            self.assertRegex(str(message.output), r"is not a valid EDTF field value.")


"""
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
"""


class TestAuthorityLinkField(unittest.TestCase):

    def test_authority_link_field_validate(self):
        config = dict()
        field_definitions = {
            "field_foo": {
                "field_type": "authority_link",
                "authority_sources": ["foo", "bar"],
            }
        }

        with self.assertLogs() as message:
            input = [
                "foo%%https://foo.com%%Foo authority record",
                "xxx%%https://xxx.com",
            ]
            field = workbench_fields.AuthorityLinkField()
            output = field.remove_invalid_values(
                config, field_definitions, "field_foo", input
            )
            self.assertEqual(output, ["foo%%https://foo.com%%Foo authority record"])
            self.assertRegex(
                str(message.output), r"xxx.*not a valid Authority Link field value"
            )


def mocked_request_ping_taxonomy_term(*args, **kwargs):
    """Don't actually do the ping, just assume they exist."""
    return True


class TestEntityReferenceField(unittest.TestCase):

    @mock.patch(
        "workbench_fields.ping_term", side_effect=mocked_request_ping_taxonomy_term
    )
    def test_entity_reference_field_validate_single(self, mocked_request):
        input = [
            {
                "target_id": 105,
                "target_type": "taxonomy_term",
                "target_uuid": "8dfca720-06ba-4e3b-96dd-9930fec91480",
                "url": "\/taxonomy\/term\/105",
            }
        ]
        field_definitions = {
            "field_subject": {
                "entity_type": "node",
                "field_type": "entity_reference",
                "target_type": "taxonomy_term",
            }
        }
        config = {
            "task": "create",
            "host": "http://example.host",
            "export_csv_term_mode": "tid",
            "subdelimiter": "|",
        }
        field = workbench_fields.EntityReferenceField()
        output = field.serialize(config, field_definitions, "field_subject", input)
        self.assertEqual("105", output)

    @mock.patch(
        "workbench_fields.ping_term", side_effect=mocked_request_ping_taxonomy_term
    )
    def test_entity_reference_field_validate_two(self, mocked_request):
        input = [
            {
                "target_id": 105,
                "target_type": "taxonomy_term",
                "target_uuid": "8dfca720-06ba-4e3b-96dd-9930fec91480",
                "url": "\/taxonomy\/term\/105",
            },
            {
                "target_id": 251,
                "target_type": "taxonomy_term",
                "target_uuid": "22cbdcf1-a895-4414-848c-47831af77663",
                "url": "\/taxonomy\/term\/251",
            },
        ]
        field_definitions = {
            "field_subject": {
                "entity_type": "node",
                "field_type": "entity_reference",
                "target_type": "taxonomy_term",
            }
        }
        config = {
            "task": "create",
            "host": "http://example.host",
            "export_csv_term_mode": "tid",
            "subdelimiter": "|",
        }
        field = workbench_fields.EntityReferenceField()
        output = field.serialize(config, field_definitions, "field_subject", input)
        self.assertEqual("105|251", output)

    @mock.patch(
        "workbench_fields.ping_term", side_effect=mocked_request_ping_taxonomy_term
    )
    def test_entity_reference_field_validate_not_exist(self, mocked_request):
        input = [
            {
                "target_id": 105,
                "target_type": "taxonomy_term",
                "target_uuid": "8dfca720-06ba-4e3b-96dd-9930fec91480",
                "url": "\/taxonomy\/term\/105",
            },
            {
                "target_id": 251,
                "target_type": "taxonomy_term",
                "target_uuid": "22cbdcf1-a895-4414-848c-47831af77663",
                "url": "\/taxonomy\/term\/251",
            },
            {"target_id": 120},
        ]
        field_definitions = {
            "field_subject": {
                "entity_type": "node",
                "field_type": "entity_reference",
                "target_type": "taxonomy_term",
            }
        }
        config = {
            "task": "create",
            "host": "http://example.host",
            "export_csv_term_mode": "tid",
            "subdelimiter": "|",
        }
        field = workbench_fields.EntityReferenceField()
        output = field.serialize(config, field_definitions, "field_subject", input)
        self.assertEqual("105|251", output)


if __name__ == "__main__":
    unittest.main()
