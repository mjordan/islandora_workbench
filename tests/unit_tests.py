"""unittest tests that do not require a live Drupal."""

import sys
import os
from ruamel.yaml import YAML
import collections
import tempfile
import unittest

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import workbench_utils


class TestCompareStings(unittest.TestCase):

    def test_strings_match(self):
        res = workbench_utils.compare_strings("foo", "foo  ")
        self.assertTrue(res)
        res = workbench_utils.compare_strings("foo", "Foo")
        self.assertTrue(res)
        res = workbench_utils.compare_strings("foo", "Foo#~^.")
        self.assertTrue(res)
        res = workbench_utils.compare_strings("foo bar baz", "foo   bar baz")
        self.assertTrue(res)
        res = workbench_utils.compare_strings(
            "Lastname,Firstname", "Lastname, Firstname"
        )
        self.assertTrue(res)
        res = workbench_utils.compare_strings(
            "لدولي العاشر ليونيكود--", "لدولي, العاشر []ليونيكود"
        )
        self.assertTrue(res)

    def test_strings_do_not_match(self):
        res = workbench_utils.compare_strings("foo", "foot")
        self.assertFalse(res)


class TestCsvRecordHasher(unittest.TestCase):

    def test_hasher(self):
        csv_record = collections.OrderedDict()
        csv_record["one"] = "eijco87we "
        csv_record["two"] = "jjjclsle300sloww"
        csv_record["three"] = "pppzzffr46wkkw"
        csv_record["four"] = "لدولي, العاشر []ليونيكود"
        csv_record["four"] = ""
        csv_record["six"] = 5

        md5hash = workbench_utils.get_csv_record_hash(csv_record)
        self.assertEqual(md5hash, "bda4013d3695a98cd56d4d2b6a66fb4c")


class TestSplitGeolocationString(unittest.TestCase):

    def test_split_geolocation_string_single(self):
        config = {"subdelimiter": "|"}
        res = workbench_utils.split_geolocation_string(config, "49.16667, -123.93333")
        self.assertDictEqual(res[0], {"lat": "49.16667", "lng": "-123.93333"})

    def test_split_geolocation_string_multiple(self):
        config = {"subdelimiter": "|"}
        res = workbench_utils.split_geolocation_string(
            config, "30.16667, -120.93333|50.1,-120.5"
        )
        self.assertDictEqual(res[0], {"lat": "30.16667", "lng": "-120.93333"})
        self.assertDictEqual(res[1], {"lat": "50.1", "lng": "-120.5"})

    def test_split_geolocation_string_multiple_at_sign(self):
        config = {"subdelimiter": "@"}
        res = workbench_utils.split_geolocation_string(
            config, "49.16667, -123.93333@50.1,-120.5"
        )
        self.assertDictEqual(res[0], {"lat": "49.16667", "lng": "-123.93333"})
        self.assertDictEqual(res[1], {"lat": "50.1", "lng": "-120.5"})

    def test_split_geolocation_string_with_leading_slash(self):
        config = {"subdelimiter": "@"}
        res = workbench_utils.split_geolocation_string(
            config, r"\+49.16667, -123.93333@\+50.1,-120.5"
        )
        self.assertDictEqual(res[0], {"lat": "+49.16667", "lng": "-123.93333"})
        self.assertDictEqual(res[1], {"lat": "+50.1", "lng": "-120.5"})

    def test_split_geolocation_string_empty(self):
        config = {"subdelimiter": "|"}
        res = workbench_utils.split_geolocation_string(config, " ")
        self.assertEqual(res, [])


class TestSplitLinkString(unittest.TestCase):

    def test_split_link_string_single(self):
        config = {"subdelimiter": "|"}
        res = workbench_utils.split_link_string(
            config, "http://www.foo.bar%%Foobar website"
        )
        self.assertDictEqual(
            res[0], {"uri": "http://www.foo.bar", "title": "Foobar website"}
        )

    def test_split_geolocation_string_multiple(self):
        config = {"subdelimiter": "|"}
        res = workbench_utils.split_link_string(
            config,
            "http://foobar.net%%Foobardotnet website|http://baz.com%%Baz website",
        )
        self.assertDictEqual(
            res[0], {"uri": "http://foobar.net", "title": "Foobardotnet website"}
        )
        self.assertDictEqual(res[1], {"uri": "http://baz.com", "title": "Baz website"})

    def test_split_link_string_no_title_single(self):
        config = {"subdelimiter": "|"}
        res = workbench_utils.split_link_string(config, "http://www.foo.bar")
        self.assertDictEqual(
            res[0], {"uri": "http://www.foo.bar", "title": "http://www.foo.bar"}
        )

    def test_split_geolocation_string_no_title_multiple(self):
        config = {"subdelimiter": "|"}
        res = workbench_utils.split_link_string(
            config, "http://foobar.net|http://baz.com%%Baz website"
        )
        self.assertDictEqual(
            res[0], {"uri": "http://foobar.net", "title": "http://foobar.net"}
        )
        self.assertDictEqual(res[1], {"uri": "http://baz.com", "title": "Baz website"})


class TestSplitAuthorityLinkString(unittest.TestCase):

    def test_split_link_string_single(self):
        config = {"subdelimiter": "|"}
        res = workbench_utils.split_authority_link_string(
            config, "foo%%http://www.foo.bar%%Foobar website"
        )
        self.assertDictEqual(
            res[0],
            {"source": "foo", "uri": "http://www.foo.bar", "title": "Foobar website"},
        )

    def test_split_geolocation_string_multiple(self):
        config = {"subdelimiter": "|"}
        res = workbench_utils.split_authority_link_string(
            config,
            "bar%%http://foobar.net%%Foobardotnet website|xxx%%http://baz.com%%Baz website",
        )
        self.assertDictEqual(
            res[0],
            {
                "source": "bar",
                "uri": "http://foobar.net",
                "title": "Foobardotnet website",
            },
        )
        self.assertDictEqual(
            res[1], {"source": "xxx", "uri": "http://baz.com", "title": "Baz website"}
        )

    def test_split_link_string_no_title_single(self):
        config = {"subdelimiter": "|"}
        res = workbench_utils.split_authority_link_string(
            config, "foo%%http://www.foo.bar"
        )
        self.assertDictEqual(
            res[0], {"source": "foo", "uri": "http://www.foo.bar", "title": ""}
        )

    def test_split_geolocation_string_no_title_multiple(self):
        config = {"subdelimiter": "|"}
        res = workbench_utils.split_authority_link_string(
            config, "zzz%%http://foobar.net|rrr%%http://baz.com%%Baz website"
        )
        self.assertDictEqual(
            res[0], {"source": "zzz", "uri": "http://foobar.net", "title": ""}
        )
        self.assertDictEqual(
            res[1], {"source": "rrr", "uri": "http://baz.com", "title": "Baz website"}
        )


class TestSplitTypedRelationString(unittest.TestCase):

    def test_split_typed_relation_string_single(self):
        config = {"subdelimiter": "|"}
        res = workbench_utils.split_typed_relation_string(
            config, "relators:pht:5", "foo"
        )
        self.assertDictEqual(
            res[0],
            {"target_id": int(5), "rel_type": "relators:pht", "target_type": "foo"},
        )

    def test_split_typed_relation_alpha_numeric_string_single(self):
        config = {"subdelimiter": "|"}
        res = workbench_utils.split_typed_relation_string(
            config, "aat:300024987:5", "foo"
        )
        self.assertDictEqual(
            res[0],
            {"target_id": int(5), "rel_type": "aat:300024987", "target_type": "foo"},
        )

    def test_split_typed_relation_uri_single(self):
        config = {"subdelimiter": "|"}
        res = workbench_utils.split_typed_relation_string(
            config, "relators:art:https://foo.bar/baz", "foo"
        )
        self.assertDictEqual(
            res[0],
            {
                "target_id": "https://foo.bar/baz",
                "rel_type": "relators:art",
                "target_type": "foo",
            },
        )

    def test_split_typed_relation_uri_multiple(self):
        config = {"subdelimiter": "|"}
        res = workbench_utils.split_typed_relation_string(
            config,
            "relators:pht:https://example.com/example1|relators:con:https://example5.com/example6",
            "bar",
        )
        self.assertDictEqual(
            res[0],
            {
                "target_id": "https://example.com/example1",
                "rel_type": "relators:pht",
                "target_type": "bar",
            },
        )
        self.assertDictEqual(
            res[1],
            {
                "target_id": "https://example5.com/example6",
                "rel_type": "relators:con",
                "target_type": "bar",
            },
        )

    def test_split_typed_relation_string_single_with_delimter_in_value(self):
        config = {"subdelimiter": "|"}
        res = workbench_utils.split_typed_relation_string(
            config, "relators:pbl:London: Bar Press", "foopub"
        )
        self.assertDictEqual(
            res[0],
            {
                "target_id": "London: Bar Press",
                "rel_type": "relators:pbl",
                "target_type": "foopub",
            },
        )

    def test_split_typed_relation_string_multiple(self):
        config = {"subdelimiter": "|"}
        res = workbench_utils.split_typed_relation_string(
            config, "relators:pht:5|relators:con:10", "bar"
        )
        self.assertDictEqual(
            res[0],
            {"target_id": int(5), "rel_type": "relators:pht", "target_type": "bar"},
        )
        self.assertDictEqual(
            res[1],
            {"target_id": int(10), "rel_type": "relators:con", "target_type": "bar"},
        )

    def test_split_typed_relation_string_multiple_at_sign(self):
        config = {"subdelimiter": "@"}
        res = workbench_utils.split_typed_relation_string(
            config, "relators:pht:5@relators:con:10", "baz"
        )
        self.assertDictEqual(
            res[0],
            {"target_id": int(5), "rel_type": "relators:pht", "target_type": "baz"},
        )
        self.assertDictEqual(
            res[1],
            {"target_id": int(10), "rel_type": "relators:con", "target_type": "baz"},
        )


class TestMediaTrackString(unittest.TestCase):

    def test_split_media_track_string_single(self):
        config = {"subdelimiter": "|"}
        res = workbench_utils.split_media_track_string(
            config, "Transcript:subtitles:en:/path/to/file"
        )
        self.assertDictEqual(
            res[0],
            {
                "label": "Transcript",
                "kind": "subtitles",
                "srclang": "en",
                "file_path": "/path/to/file",
            },
        )

    def test_split_media_track_string_single_windows(self):
        config = {"subdelimiter": "|"}
        res = workbench_utils.split_media_track_string(
            config, "Foo:subtitles:en:c:/path/to/file"
        )
        self.assertDictEqual(
            res[0],
            {
                "label": "Foo",
                "kind": "subtitles",
                "srclang": "en",
                "file_path": "c:/path/to/file",
            },
        )

    def test_split_media_track_multiple(self):
        config = {"subdelimiter": "|"}
        res = workbench_utils.split_media_track_string(
            config,
            "Bar:subtitles:en:c:/path/to/file.vtt|Baz:subtitles:fr:/path/to/file2.vtt",
        )
        self.assertDictEqual(
            res[0],
            {
                "label": "Bar",
                "kind": "subtitles",
                "srclang": "en",
                "file_path": "c:/path/to/file.vtt",
            },
        )
        self.assertDictEqual(
            res[1],
            {
                "label": "Baz",
                "kind": "subtitles",
                "srclang": "fr",
                "file_path": "/path/to/file2.vtt",
            },
        )


class TestValidateMediaTrackString(unittest.TestCase):

    def test_validate_media_track_values(self):
        res = workbench_utils.validate_media_track_value(
            "Transcript:subtitles:en:c:/path/to/file.vtt"
        )
        self.assertTrue(res)

        res = workbench_utils.validate_media_track_value(
            "Transcript:captions:de:c:/path/to/file.vtt"
        )
        self.assertTrue(res)

        res = workbench_utils.validate_media_track_value(
            "Transcript:subtitles:fr:c:/path/to/file.VTT"
        )
        self.assertTrue(res)

        res = workbench_utils.validate_media_track_value(
            "Transcript:subtitles:ff:c:/path/to/file.VTT"
        )
        self.assertFalse(res)

        res = workbench_utils.validate_media_track_value(
            "Transcript:subtitles:en:c:/path/to/file.ccc"
        )
        self.assertFalse(res)

        res = workbench_utils.validate_media_track_value(
            ":subtitles:en:c:/path/to/file.VTT"
        )
        self.assertFalse(res)

        res = workbench_utils.validate_media_track_value(
            "Transcript:subtitle:en:c:/path/to/file.vtt"
        )
        self.assertFalse(res)


class TestValidateLanguageCode(unittest.TestCase):

    def test_validate_code_in_list(self):
        res = workbench_utils.validate_language_code("es")
        self.assertTrue(res)

    def test_validate_code_not_in_list(self):
        res = workbench_utils.validate_language_code("foo")
        self.assertFalse(res)


class TestValidateLatlongValue(unittest.TestCase):

    def test_validate_good_latlong_values(self):
        values = [
            "+90.0, -127.554334",
            "90.0, -127.554334",
            "-90,-180",
            "+50.25,-117.8",
            "+48.43333,-123.36667",
        ]
        for value in values:
            res = workbench_utils.validate_latlong_value(value)
            self.assertTrue(res)

    def test_validate_bad_latlong_values(self):
        values = ["+90.1 -100.111", "045, 180", "+5025,-117.8", "-123.36667"]
        for value in values:
            res = workbench_utils.validate_latlong_value(value)
            self.assertFalse(res)


class TestValidateLinkValue(unittest.TestCase):

    def test_validate_good_link_values(self):
        values = ["http://foo.com", "https://foo1.com%%Foo Hardware"]
        for value in values:
            res = workbench_utils.validate_link_value(value)
            self.assertTrue(res)

    def test_validate_bad_link_values(self):
        values = [
            "foo.com",
            "http:/foo.com",
            "file://server/folder/data.xml",
            "mailto:someone@example.com",
        ]
        for value in values:
            res = workbench_utils.validate_link_value(value)
            self.assertFalse(res)


class TestValidateAuthorityLinkValue(unittest.TestCase):

    def test_validate_good_authority_link_values(self):
        values = [
            "viaf%%http://viaf.org/viaf/10646807%%VIAF Record",
            "cash%%http://cash.org%%foo",
        ]
        for value in values:
            res = workbench_utils.validate_authority_link_value(value, ["cash", "viaf"])
            self.assertTrue(res)

    def test_validate_bad_authority_link_values(self):
        values = ["viaf%%htt://viaf.org/viaf/10646807%%VIAF Record"]
        for value in values:
            res = workbench_utils.validate_authority_link_value(value, ["cash", "viaf"])
            self.assertFalse(res)

        values = ["xcash%%http://cash.org%%foo"]
        for value in values:
            res = workbench_utils.validate_authority_link_value(value, ["cash", "viaf"])
            self.assertFalse(res)


class TestValidateNodeCreatedDateValue(unittest.TestCase):

    def test_validate_good_date_string_values(self):
        values = ["2020-11-15T23:49:22+00:00"]
        for value in values:
            res = workbench_utils.validate_node_created_date_string(value)
            self.assertTrue(res)

    def test_validate_bad_date_string_values(self):
        values = ["2020-11-15:23:49:22+00:00", "2020-11-15T:23:49:22", "2020-11-15"]
        for value in values:
            res = workbench_utils.validate_node_created_date_string(value)
            self.assertFalse(res)


class TestValidEdtfDate(unittest.TestCase):

    def test_validate_good_edtf_values(self):
        good_values = [
            "190X",
            "1900-XX",
            "1900",
            "2020-10",
            "2021-10-12",
            "2001-21",
            "2001-22",
            "2001-23",
            "2001-24",
            "2001-31",
            "193X/196X",
            "195X-01~",
            "198X?",
            "19XX?",
            "2XXX?",
            "198X~",
            "19XX~",
            "2XXX~",
            "198X%",
            "19XX%",
            "2XXX%",
            "XXXX?",
            "XXXX~",
            "XXXX%",
        ]
        for good_value in good_values:
            res = workbench_utils.validate_edtf_date(good_value)
            self.assertTrue(res, good_value)

    def test_validate_bad_edtf_values(self):
        bad_values = [
            "1900-05-45",
            "1900-13-01",
            "1900-02-31",
            "1900-00-31",
            "1900-00",
            "19000",
            "7/5/51",
            "19X?",
            "2XX%",
        ]
        for bad_value in bad_values:
            res = workbench_utils.validate_edtf_date(bad_value)
            self.assertFalse(res, bad_value)


class TestSetMediaType(unittest.TestCase):

    def setUp(self):
        yaml = YAML()
        dir_path = os.path.dirname(os.path.realpath(__file__))

        # Media types are mapped from extensions.
        types_config_file_path = os.path.join(
            dir_path, "assets", "set_media_type_test", "multi_types_config.yml"
        )
        with open(types_config_file_path, "r") as f:
            multi_types_config_file_contents = f.read()
        self.multi_types_config_yaml = yaml.load(multi_types_config_file_contents)

        # Media type is set for all media.
        type_config_file_path = os.path.join(
            dir_path, "assets", "set_media_type_test", "single_type_config.yml"
        )
        with open(type_config_file_path, "r") as f:
            single_type_config_file_contents = f.read()
        self.single_type_config_yaml = yaml.load(single_type_config_file_contents)

    def test_multi_types_set_media_type(self):
        fake_csv_record = collections.OrderedDict()
        fake_csv_record["file"] = "/tmp/foo.txt"
        res = workbench_utils.set_media_type(
            self.multi_types_config_yaml, "/tmp/foo.txt", "file", fake_csv_record
        )
        self.assertEqual(res, "sometextmedia")

        fake_csv_record = collections.OrderedDict()
        fake_csv_record["file"] = "/tmp/foo.tif"
        res = workbench_utils.set_media_type(
            self.multi_types_config_yaml, "/tmp/foo.tif", "file", fake_csv_record
        )
        self.assertEqual(res, "file")

        fake_csv_record = collections.OrderedDict()
        fake_csv_record["file"] = "/tmp/foo.tif"
        res = workbench_utils.set_media_type(
            self.multi_types_config_yaml, "/tmp/foocaps.TIF", "file", fake_csv_record
        )
        self.assertEqual(res, "file")

        fake_csv_record = collections.OrderedDict()
        fake_csv_record["file"] = "/tmp/foo.mp4"
        res = workbench_utils.set_media_type(
            self.multi_types_config_yaml, "/tmp/foo.mp4", "file", fake_csv_record
        )
        self.assertEqual(res, "video")

        fake_csv_record = collections.OrderedDict()
        fake_csv_record["file"] = "/tmp/foo.mp4"
        res = workbench_utils.set_media_type(
            self.multi_types_config_yaml, "/tmp/foocaps.MP4", "file", fake_csv_record
        )
        self.assertEqual(res, "video")

        fake_csv_record = collections.OrderedDict()
        fake_csv_record["file"] = "/tmp/foo.png"
        res = workbench_utils.set_media_type(
            self.multi_types_config_yaml, "/tmp/foo.png", "file", fake_csv_record
        )
        self.assertEqual(res, "image")

        fake_csv_record = collections.OrderedDict()
        fake_csv_record["file"] = "/tmp/foo.pptx"
        res = workbench_utils.set_media_type(
            self.multi_types_config_yaml, "/tmp/foo.pptx", "file", fake_csv_record
        )
        self.assertEqual(res, "document")

        fake_csv_record = collections.OrderedDict()
        fake_csv_record["file"] = "/tmp/foo.pptx"
        res = workbench_utils.set_media_type(
            self.multi_types_config_yaml, "/tmp/foo.Pptx", "file", fake_csv_record
        )
        self.assertEqual(res, "document")

        fake_csv_record = collections.OrderedDict()
        fake_csv_record["file"] = "/tmp/foo.xxx"
        res = workbench_utils.set_media_type(
            self.multi_types_config_yaml, "/tmp/foo.xxx", "file", fake_csv_record
        )
        self.assertEqual(res, "file")

        fake_csv_record = collections.OrderedDict()
        fake_csv_record["file"] = "/tmp/foo.wp"
        res = workbench_utils.set_media_type(
            self.multi_types_config_yaml, "/tmp/foo.wp", "file", fake_csv_record
        )
        self.assertEqual(res, "document")

        fake_csv_record = collections.OrderedDict()
        fake_csv_record["file"] = "/tmp/foo.ogg"
        res = workbench_utils.set_media_type(
            self.multi_types_config_yaml, "/tmp/foo.ogg", "file", fake_csv_record
        )
        self.assertEqual(res, "video")

        fake_csv_record = collections.OrderedDict()
        fake_csv_record["file"] = "/tmp/xxx.foo"
        res = workbench_utils.set_media_type(
            self.multi_types_config_yaml, "/tmp/xxx.foo", "file", fake_csv_record
        )
        self.assertEqual(res, "foomedia")

        fake_csv_record = collections.OrderedDict()
        fake_csv_record["file"] = "https://youtu.be/xxxx"
        res = workbench_utils.set_media_type(
            self.multi_types_config_yaml,
            "https://youtu.be/xxxx",
            "file",
            fake_csv_record,
        )
        self.assertEqual(res, "remote_video")

        fake_csv_record = collections.OrderedDict()
        fake_csv_record["file"] = "https://vimeo.com/xxxx"
        res = workbench_utils.set_media_type(
            self.multi_types_config_yaml,
            "https://vimeo.com/xxxx",
            "file",
            fake_csv_record,
        )
        self.assertEqual(res, "remote_video")

    def test_single_type_set_media_type(self):
        fake_csv_record = collections.OrderedDict()
        fake_csv_record["file"] = "/tmp/foo.xxx"
        res = workbench_utils.set_media_type(
            self.single_type_config_yaml, "/tmp/foo.xxx", "file", fake_csv_record
        )
        self.assertEqual(res, "barmediatype")


class TestGetCsvFromExcel(unittest.TestCase):
    """Note: this tests the extraction of CSV data from Excel only,
    not using an Excel file as an input CSV file. That is tested
    in TestCommentedCsvs in islandora_tests.py.
    """

    def setUp(self):
        self.config = {
            "input_dir": "tests/assets/excel_test",
            "temp_dir": "tests/assets/excel_test",
            "input_csv": "test_excel_file.xlsx",
            "excel_worksheet": "Sheet1",
            "excel_csv_filename": "excel_csv.csv",
            "id_field": "id",
        }

        self.csv_file_path = os.path.join(
            self.config["input_dir"], self.config["excel_csv_filename"]
        )

    def test_get_csv_from_excel(self):
        workbench_utils.get_csv_from_excel(self.config)
        csv_data_fh = open(self.csv_file_path, "r")
        csv_data = csv_data_fh.readlines()
        csv_data_fh.close()

        self.assertEqual(len(csv_data), 5)

        fourth_row = csv_data[4]
        fourth_row_parts = fourth_row.split(",")
        self.assertEqual(fourth_row_parts[1], "Title 4")

    def tearDown(self):
        os.remove(self.csv_file_path)


class TestSqliteManager(unittest.TestCase):
    def setUp(self):
        self.config = {
            "temp_dir": tempfile.gettempdir(),
            "sqlite_db_filename": "workbench_unit_tests.db",
        }

        self.db_file_path = os.path.join(
            self.config["temp_dir"], self.config["sqlite_db_filename"]
        )

        workbench_utils.sqlite_manager(
            self.config, db_file_path=self.db_file_path, operation="create_database"
        )
        workbench_utils.sqlite_manager(
            self.config,
            db_file_path=self.db_file_path,
            operation="create_table",
            table_name="names",
            query="CREATE TABLE names (name TEXT, location TEXT)",
        )

    def test_crud_operations(self):
        workbench_utils.sqlite_manager(
            self.config,
            operation="insert",
            db_file_path=self.db_file_path,
            query="INSERT INTO names VALUES (?, ?)",
            values=("Mark", "Burnaby"),
        )
        workbench_utils.sqlite_manager(
            self.config,
            operation="insert",
            db_file_path=self.db_file_path,
            query="INSERT INTO names VALUES (?, ?)",
            values=("Mix", "Catland"),
        )
        res = workbench_utils.sqlite_manager(
            self.config,
            operation="select",
            db_file_path=self.db_file_path,
            query="select * from names",
        )
        self.assertEqual(res[0]["name"], "Mark")
        self.assertEqual(res[1]["location"], "Catland")

        workbench_utils.sqlite_manager(
            self.config,
            operation="update",
            db_file_path=self.db_file_path,
            query="UPDATE names set location = ? where name = ?",
            values=("Blank stare", "Mix"),
        )
        res = workbench_utils.sqlite_manager(
            self.config,
            operation="select",
            db_file_path=self.db_file_path,
            query="select * from names",
        )
        self.assertEqual(res[1]["location"], "Blank stare")

        workbench_utils.sqlite_manager(
            self.config,
            operation="delete",
            db_file_path=self.db_file_path,
            query="delete from names where name = ?",
            values=("Mix",),
        )
        res = workbench_utils.sqlite_manager(
            self.config,
            operation="select",
            db_file_path=self.db_file_path,
            query="select * from names",
        )
        self.assertEqual(len(res), 1)

    def tearDown(self):
        os.remove(self.db_file_path)


class TestDrupalCoreVersionNumbers(unittest.TestCase):
    def test_version_numbers(self):
        minimum_core_version = tuple([8, 6])
        lower_versions = ["8.3.0", "8.5.0-alpha1", "8.5.0", "8.5.6"]
        for version in lower_versions:
            version_number = workbench_utils.convert_semver_to_number(version)
            res = version_number < minimum_core_version
            self.assertTrue(
                res, "Version number " + str(version_number) + " is greater than 8.6."
            )

        version_number = workbench_utils.convert_semver_to_number("8.6")
        self.assertTrue(version_number == minimum_core_version, "Not sure what failed.")

        higher_versions = [
            "8.6.1",
            "8.6.4",
            "8.9.14",
            "8.10.0-dev",
            "9.0",
            "9.1",
            "9.0.0-dev",
            "9.1.0-rc3",
            "9.0.2",
        ]
        for version in higher_versions:
            version_number = workbench_utils.convert_semver_to_number(version)
            res = version_number >= minimum_core_version
            self.assertTrue(
                res, "Version number " + str(version_number) + " is less than 8.6."
            )


class TestIntegrationModuleVersionNumbers(unittest.TestCase):
    def test_version_numbers(self):
        minimum_version = tuple([1, 0])
        lower_versions = ["0.9", "0.8", "0.8.0-dev"]
        for version in lower_versions:
            version_number = workbench_utils.convert_semver_to_number(version)
            res = version_number < minimum_version
            self.assertTrue(
                res, "Version number " + str(version_number) + " is greater than 1.0."
            )

        higher_versions = ["1.0.0", "1.0.1", "1.2", "1.0.1-dev", "10.0"]
        for version in higher_versions:
            version_number = workbench_utils.convert_semver_to_number(version)
            res = version_number >= minimum_version
            self.assertTrue(
                res, "Version number " + str(version_number) + " is less than 1.0."
            )


class TestDedupedFilePaths(unittest.TestCase):
    def test_deduped_file_paths(self):
        paths = [
            ["/home/foo/bar.txt", "/home/foo/bar_1.txt"],
            ["/home/foo/bar_1.txt", "/home/foo/bar_2.txt"],
            ["/tmp/dir/dog_05.zip", "/tmp/dir/dog_6.zip"],
        ]
        for path_pair in paths:
            deduped_path = workbench_utils.get_deduped_file_path(path_pair[0])
            self.assertEqual(deduped_path, path_pair[1])


class TestValueIsNumeric(unittest.TestCase):
    def test_value_is_numeric(self):
        values = ["200", "0", 999]
        for value in values:
            res = workbench_utils.value_is_numeric(value)
            self.assertTrue(res, "Value " + str(value) + " is not numeric.")

        values = ["200.23", "0.5", 999.999]
        for value in values:
            res = workbench_utils.value_is_numeric(value, allow_decimals=True)
            self.assertTrue(res, "Value " + str(value) + " is not numeric.")

    def test_value_is_not_numeric(self):
        values = ["n200", False, "999-1000"]
        for value in values:
            res = workbench_utils.value_is_numeric(value)
            self.assertFalse(res, "Value " + str(value) + " is numeric.")


class TestCleanCsvValues(unittest.TestCase):
    def test_clean_csv_values(self):
        config = {"subdelimiter": "|", "clean_csv_values_skip": []}

        csv_record = collections.OrderedDict()
        csv_record["one"] = " blsidlw  "
        csv_record["two"] = 'hheo "s7s9w9"'
        csv_record["three"] = "b‘bbbbb’"
        csv_record["four"] = "لدولي, العاشر []ليونيكود "
        newline = "\n"
        csv_record["five"] = f"{newline}new lines{newline}"
        csv_record["six"] = "a  b c    d  e"

        clean_csv_record = collections.OrderedDict()
        clean_csv_record["one"] = "blsidlw"
        clean_csv_record["two"] = 'hheo "s7s9w9"'
        clean_csv_record["three"] = "b'bbbbb'"
        clean_csv_record["four"] = "لدولي, العاشر []ليونيكود"
        clean_csv_record["five"] = "new lines"
        clean_csv_record["six"] = "a b c d e"

        csv_record = workbench_utils.clean_csv_values(config, csv_record)
        self.assertEqual(clean_csv_record, csv_record)

    def test_clean_csv_values_skip_smart_quotes(self):
        config = {"subdelimiter": "|", "clean_csv_values_skip": ["smart_quotes"]}

        csv_record = collections.OrderedDict()
        csv_record["smq1"] = "b‘bbxbbb’"

        clean_csv_record = collections.OrderedDict()
        clean_csv_record["smq1"] = "b‘bbxbbb’"

        csv_record = workbench_utils.clean_csv_values(config, csv_record)
        self.assertEqual(clean_csv_record, csv_record)

    def test_clean_csv_values_skip_spaces(self):
        config = {
            "subdelimiter": "|",
            "clean_csv_values_skip": ["inside_spaces", "outside_spaces"],
        }

        csv_record = collections.OrderedDict()
        csv_record["one"] = " blsidlw  "
        csv_record["two"] = 'hheo "s7s9w9"'
        csv_record["three"] = "b‘bbbbb’"
        csv_record["four"] = "لدولي, العاشر []ليونيكود "
        newline = "\n"
        csv_record["five"] = f"{newline}new lines{newline}"
        csv_record["six"] = "a  b c    d  e"

        clean_csv_record = collections.OrderedDict()
        clean_csv_record["one"] = " blsidlw  "
        clean_csv_record["two"] = 'hheo "s7s9w9"'
        clean_csv_record["three"] = "b'bbbbb'"
        clean_csv_record["four"] = "لدولي, العاشر []ليونيكود "
        clean_csv_record["five"] = f"{newline}new lines{newline}"
        clean_csv_record["six"] = "a  b c    d  e"

        csv_record = workbench_utils.clean_csv_values(config, csv_record)
        self.assertEqual(clean_csv_record, csv_record)

    def test_clean_csv_values_subdelimiters(self):
        # Most common case, using the default subdelimiter.
        config = {"subdelimiter": "|", "clean_csv_values_skip": []}

        csv_record = collections.OrderedDict()
        csv_record["one"] = " |blsidlw  "
        csv_record["two"] = "something|"
        csv_record["three"] = "something||"

        clean_csv_record = collections.OrderedDict()
        clean_csv_record["one"] = "blsidlw"
        clean_csv_record["two"] = "something"
        clean_csv_record["three"] = "something"

        csv_record = workbench_utils.clean_csv_values(config, csv_record)
        self.assertEqual(clean_csv_record, csv_record)

        # Non-| dubdelimiter.
        config = {"subdelimiter": "%%", "clean_csv_values_skip": []}

        csv_record = collections.OrderedDict()
        csv_record["one"] = " %%blsidlw  "
        csv_record["two"] = "something%%"

        clean_csv_record = collections.OrderedDict()
        clean_csv_record["one"] = "blsidlw"
        clean_csv_record["two"] = "something"

        csv_record = workbench_utils.clean_csv_values(config, csv_record)
        self.assertEqual(clean_csv_record, csv_record)

        # Skipping the outside whitespace and subdelimiter.
        config = {
            "subdelimiter": "|",
            "clean_csv_values_skip": ["outside_spaces", "outside_subdelimiters"],
        }

        csv_record = collections.OrderedDict()
        csv_record["one"] = " |blsidlw"
        csv_record["two"] = "something|"
        csv_record["three"] = "something||"

        clean_csv_record = collections.OrderedDict()
        clean_csv_record["one"] = " |blsidlw"
        clean_csv_record["two"] = "something|"
        clean_csv_record["three"] = "something||"

        csv_record = workbench_utils.clean_csv_values(config, csv_record)
        self.assertEqual(clean_csv_record, csv_record)


class TestGetPageTitleFromTemplate(unittest.TestCase):
    def test_get_page_title_from_template(self):
        fixtures = [
            {
                "config": {"page_title_template": "$parent_title, page $weight"},
                "parent_title": "Test parent title",
                "weight": 2,
                "control": "Test parent title, page 2",
            },
            {
                "config": {"page_title_template": "$parent_title, part $weight"},
                "parent_title": "Test parent title",
                "weight": 10,
                "control": "Test parent title, part 10",
            },
            {
                "config": {"page_title_template": "section $weight"},
                "parent_title": "Foo",
                "weight": 9,
                "control": "section 9",
            },
        ]

        for fixture in fixtures:
            page_title = workbench_utils.get_page_title_from_template(
                fixture["config"], fixture["parent_title"], fixture["weight"]
            )
            self.assertEqual(fixture["control"], page_title)


class TestApplyCsvValueTemplates(unittest.TestCase):
    def test_fixed_string_templates(self):
        """Tests $csv_value and $filenamne templates. Dynamically generated template strings
        have their own test functions, below.
        """
        fixtures = [
            {
                "config": {
                    "subdelimiter": "|",
                    "csv_value_templates": [{"field_foo_1": "$csv_value, bar"}],
                    "allow_csv_value_templates_if_field_empty": [],
                    "csv_value_templates_rand_length": 5,
                },
                "row": {"title": "Title 1", "field_foo_1": "I am foo", "file": ""},
                "control": {
                    "title": "Title 1",
                    "field_foo_1": "I am foo, bar",
                    "file": "",
                },
            },
            {
                "config": {
                    "subdelimiter": "|",
                    "csv_value_templates": [{"field_foo_2": "pre-$csv_value-post"}],
                    "allow_csv_value_templates_if_field_empty": [],
                    "csv_value_templates_rand_length": 5,
                },
                "row": {
                    "title": "Title 1",
                    "field_foo_2": "I am foo",
                    "file": "foo.jpg",
                },
                "control": {
                    "title": "Title 1",
                    "field_foo_2": "pre-I am foo-post",
                    "file": "foo.jpg",
                },
            },
            {
                "config": {
                    "subdelimiter": "|",
                    "csv_value_templates": [{"field_foo_2": "pre-$file-post"}],
                    "allow_csv_value_templates_if_field_empty": [],
                    "csv_value_templates_rand_length": 5,
                },
                "row": {
                    "title": "Title 1",
                    "field_foo_2": "I am foo",
                    "file": "bar.tif",
                },
                "control": {
                    "title": "Title 1",
                    "field_foo_2": "pre-bar.tif-post",
                    "file": "bar.tif",
                },
            },
            {
                "config": {
                    "subdelimiter": "|",
                    "csv_value_templates": [{"field_foo_2": "$csv_value-$file"}],
                    "allow_csv_value_templates_if_field_empty": [],
                    "csv_value_templates_rand_length": 5,
                },
                "row": {
                    "title": "Title 1",
                    "field_foo_2": "I am a value",
                    "file": "a good movie.mov",
                },
                "control": {
                    "title": "Title 1",
                    "field_foo_2": "I am a value-a good movie.mov",
                    "file": "a good movie.mov",
                },
            },
            {
                "config": {
                    "subdelimiter": "|",
                    "csv_value_templates": [{"field_foo_2": "$csv_value-$file"}],
                    "allow_csv_value_templates_if_field_empty": [],
                    "csv_value_templates_rand_length": 5,
                },
                "row": {
                    "title": "Title 1",
                    "field_foo_1": "",
                    "field_foo_2": "I am a value",
                    "file": "a good movie.mov",
                },
                "control": {
                    "title": "Title 1",
                    "field_foo_1": "",
                    "field_foo_2": "I am a value-a good movie.mov",
                    "file": "a good movie.mov",
                },
            },
            {
                "config": {
                    "subdelimiter": "|",
                    "csv_value_templates": [
                        {
                            "field_foo_1": "$csv_value-$file",
                            "field_foo_2": "$csv_value-$file",
                        }
                    ],
                    "allow_csv_value_templates_if_field_empty": ["field_foo_1"],
                    "csv_value_templates_rand_length": 5,
                },
                "row": {
                    "title": "Title 1",
                    "field_foo_1": "",
                    "field_foo_2": "I am a value",
                    "file": "a good movie.mov",
                },
                "control": {
                    "title": "Title 1",
                    "field_foo_1": "-a good movie.mov",
                    "field_foo_2": "I am a value-a good movie.mov",
                    "file": "a good movie.mov",
                },
            },
            {
                "config": {
                    "subdelimiter": "|",
                    "csv_value_templates": [{"field_foo_2": "$csv_value-$file"}],
                    "allow_csv_value_templates_if_field_empty": [],
                    "csv_value_templates_rand_length": 5,
                },
                "row": {
                    "title": "Title 1",
                    "field_foo_2": "I am a value",
                    "file": "a good movie.mov",
                },
                "control": {
                    "title": "Title 1",
                    "field_foo_2": "I am a value-a good movie.mov",
                    "file": "a good movie.mov",
                },
            },
        ]

        for fixture in fixtures:
            output_row = workbench_utils.apply_csv_value_templates(
                fixture["config"], "csv_value_templates", fixture["row"]
            )
            self.assertEqual(fixture["control"], output_row)

    def test_fixed_string_templates_in_paged_content(self):
        """Tests $filename_without_extension and $weight templates."""
        fixtures = [
            {
                "config": {
                    "subdelimiter": "|",
                    "csv_value_templates_for_paged_content": [
                        {"field_foo_1": "$filename_without_extension, bar"}
                    ],
                    "allow_csv_value_templates_if_field_empty": [],
                    "csv_value_templates_rand_length": 5,
                },
                "row": {
                    "title": "Title 1",
                    "field_foo_1": "I am foo",
                    "file": "baz.jpg",
                    "field_weight": 1,
                },
                "control": {
                    "title": "Title 1",
                    "field_foo_1": "baz, bar",
                    "file": "baz.jpg",
                    "field_weight": 1,
                },
            },
            {
                "config": {
                    "subdelimiter": "|",
                    "csv_value_templates_for_paged_content": [
                        {"field_foo_2": "pre-$weight"}
                    ],
                    "allow_csv_value_templates_if_field_empty": [],
                    "csv_value_templates_rand_length": 5,
                },
                "row": {
                    "title": "Title 1",
                    "field_foo_2": "I am foo",
                    "file": "foo.jpg",
                    "field_weight": 2,
                },
                "control": {
                    "title": "Title 1",
                    "field_foo_2": "pre-2",
                    "file": "foo.jpg",
                    "field_weight": 2,
                },
            },
        ]

        for fixture in fixtures:
            output_row = workbench_utils.apply_csv_value_templates(
                fixture["config"],
                "csv_value_templates_for_paged_content",
                fixture["row"],
            )
            self.assertEqual(fixture["control"], output_row)

    def test_alphanumeric_string_template(self):
        fixtures = [
            {
                "config": {
                    "subdelimiter": "|",
                    "csv_value_templates": [
                        {"field_foo_2": "bar -- $random_alphanumeric_string"}
                    ],
                    "allow_csv_value_templates_if_field_empty": [],
                    "csv_value_templates_rand_length": 6,
                },
                "row": {
                    "title": "Title 1",
                    "field_foo_1": "I am foo",
                    "field_foo_2": "ha",
                    "file": "",
                },
            },
            {
                "config": {
                    "subdelimiter": "|",
                    "csv_value_templates": [
                        {"field_foo_2": "bar -- $random_alphanumeric_string"}
                    ],
                    "allow_csv_value_templates_if_field_empty": [],
                    "csv_value_templates_rand_length": 10,
                },
                "row": {
                    "title": "Title 1",
                    "field_foo_1": "I am foo",
                    "field_foo_2": "ha",
                    "file": "",
                },
            },
        ]

        for fixture in fixtures:
            rand_str_length = fixture["config"]["csv_value_templates_rand_length"]
            output_row = workbench_utils.apply_csv_value_templates(
                fixture["config"], "csv_value_templates", fixture["row"]
            )
            # Sorry for the inscrutible {{{}}} in the regex quantifier...
            self.assertRegex(
                fixture["row"]["field_foo_2"],
                f"bar -- [A-Za-z0-9]{{{rand_str_length}}}",
                "",
            )

    def test_numeric_string_template(self):
        fixtures = [
            {
                "config": {
                    "subdelimiter": "|",
                    "csv_value_templates": [
                        {"field_foo_2": "$random_number_string: xxx"}
                    ],
                    "allow_csv_value_templates_if_field_empty": [],
                    "csv_value_templates_rand_length": 5,
                },
                "row": {
                    "title": "Title 1",
                    "field_foo_1": "I am foo",
                    "field_foo_2": "ha",
                    "file": "",
                },
            },
            {
                "config": {
                    "subdelimiter": "|",
                    "csv_value_templates": [
                        {"field_foo_2": "$random_number_string: xxx"}
                    ],
                    "allow_csv_value_templates_if_field_empty": [],
                    "csv_value_templates_rand_length": 20,
                },
                "row": {
                    "title": "Title 1",
                    "field_foo_1": "I am foo",
                    "field_foo_2": "ha",
                    "file": "",
                },
            },
        ]

        for fixture in fixtures:
            rand_str_length = fixture["config"]["csv_value_templates_rand_length"]
            output_row = workbench_utils.apply_csv_value_templates(
                fixture["config"], "csv_value_templates", fixture["row"]
            )
            # Sorry about the inscrutible {{{rand_str_length}}} in the regex quantifier...
            self.assertRegex(
                fixture["row"]["field_foo_2"],
                f"[A-Za-z0-9]{{{rand_str_length}}}: xxx",
                "",
            )

    def test_uuid_template(self):
        fixtures = [
            {
                "config": {
                    "subdelimiter": "|",
                    "csv_value_templates": [{"field_foo_3": "yyy:$uuid_string"}],
                    "allow_csv_value_templates_if_field_empty": [],
                    "csv_value_templates_rand_length": 5,
                },
                "row": {
                    "title": "Title 1",
                    "field_foo_1": "I am foo",
                    "field_foo_3": "ha",
                    "file": "",
                },
            },
            {
                "config": {
                    "subdelimiter": "|",
                    "csv_value_templates": [{"field_foo_3": "ggg:$uuid_string"}],
                    "allow_csv_value_templates_if_field_empty": ["field_foo_3"],
                    "csv_value_templates_rand_length": 5,
                },
                "row": {
                    "title": "Title 1",
                    "field_foo_1": "I am foo",
                    "field_foo_3": "",
                    "file": "",
                },
            },
        ]

        for fixture in fixtures:
            output_row = workbench_utils.apply_csv_value_templates(
                fixture["config"], "csv_value_templates", fixture["row"]
            )
            self.assertRegex(
                fixture["row"]["field_foo_3"],
                "^.{3}:[a-f0-9]{8}-?[a-f0-9]{4}-?4[a-f0-9]{3}-?[89ab][a-f0-9]{3}-?[a-f0-9]{12}",
                "",
            )


class TestGetPreprocessedFilePath(unittest.TestCase):
    def test_get_preprocessed_file_path_with_extension(self):
        node_csv_record = collections.OrderedDict()
        node_csv_record["id"] = "id_0001"
        node_csv_record["file"] = (
            "https://example.com/somepathinfo/fullsize/test-filename.jpg"
        )
        node_csv_record["title"] = "Test Title"
        self.node_csv_record = node_csv_record

        self.config = {
            "task": "create",
            "id_field": "id",
            "oembed_providers": [],
            "temp_dir": tempfile.gettempdir(),
            "field_for_remote_filename": False,
        }

        path = workbench_utils.get_preprocessed_file_path(
            self.config, "file", self.node_csv_record
        )
        expected_path = os.path.join(
            self.config["temp_dir"], self.node_csv_record["id"], "test-filename.jpg"
        )
        self.assertEqual(path, expected_path)

    def test_get_preprocessed_file_path_use_node_title_for_remote_filename(self):
        node_csv_record = collections.OrderedDict()
        node_csv_record["id"] = "id_0001"
        node_csv_record["file"] = (
            "https://example.com/somepathinfo/fullsize/test-filename.jpg"
        )
        node_csv_record["title"] = "Test Title"
        self.node_csv_record = node_csv_record

        self.config = {
            "task": "create",
            "id_field": "id",
            "oembed_providers": [],
            "temp_dir": tempfile.gettempdir(),
            "field_for_remote_filename": False,
            "use_node_title_for_remote_filename": True,
        }

        path = workbench_utils.get_preprocessed_file_path(
            self.config, "file", self.node_csv_record
        )
        expected_path = os.path.join(
            self.config["temp_dir"], self.node_csv_record["id"], "Test_Title.jpg"
        )
        self.assertEqual(path, expected_path)

    def test_get_preprocessed_file_path_use_nid_in_remote_filename(self):
        node_csv_record = collections.OrderedDict()
        node_csv_record["id"] = "id_0001"
        node_csv_record["file"] = (
            "https://example.com/somepathinfo/fullsize/test-filename.jpg"
        )
        node_csv_record["title"] = "Test Title"
        self.node_csv_record = node_csv_record

        self.config = {
            "task": "create",
            "id_field": "id",
            "oembed_providers": [],
            "temp_dir": tempfile.gettempdir(),
            "field_for_remote_filename": False,
            "use_nid_in_remote_filename": True,
        }

        path = workbench_utils.get_preprocessed_file_path(
            self.config, "file", self.node_csv_record, node_id=456
        )
        expected_path = os.path.join(
            self.config["temp_dir"], self.node_csv_record["id"], "456.jpg"
        )
        self.assertEqual(path, expected_path)

    def test_get_preprocessed_file_path_field_for_remote_filename(self):
        node_csv_record = collections.OrderedDict()
        node_csv_record["id"] = "id_0001"
        node_csv_record["file"] = (
            "https://example.com/somepathinfo/fullsize/test-filename.jpg"
        )
        node_csv_record["title"] = "Test Title"
        node_csv_record["field_description"] = "A description used for testing."
        self.node_csv_record = node_csv_record

        self.config = {
            "task": "create",
            "id_field": "id",
            "oembed_providers": [],
            "temp_dir": tempfile.gettempdir(),
            "field_for_remote_filename": False,
            "field_for_remote_filename": "field_description",
        }

        path = workbench_utils.get_preprocessed_file_path(
            self.config, "file", self.node_csv_record, node_id=456
        )
        expected_path = os.path.join(
            self.config["temp_dir"],
            self.node_csv_record["id"],
            "A_description_used_for_testing.jpg",
        )
        self.assertEqual(path, expected_path)


class TestDeduplicateFieldValues(unittest.TestCase):
    def test_strings(self):
        fixtures = [
            {
                "input": ["one", "two", "two", "three"],
                "control": ["one", "two", "three"],
            },
            {
                "input": ["one", "two", "two", "three", "three"],
                "control": ["one", "two", "three"],
            },
        ]

        for fixture in fixtures:
            unique_values = workbench_utils.deduplicate_field_values(fixture["input"])
            self.assertEqual(fixture["control"], unique_values)

    def test_dictionaries(self):
        fixtures = [
            {
                "input": [{"foo": "bar"}, {"1": 2}, {"1": 2}, {"three": "four"}],
                "control": [{"foo": "bar"}, {"1": 2}, {"three": "four"}],
            },
            {
                "input": [
                    {"foo": "bar", "up": "down"},
                    {"1": 2},
                    {"three": "four"},
                    {"1": 2},
                ],
                "control": [{"foo": "bar", "up": "down"}, {"1": 2}, {"three": "four"}],
            },
            {
                "input": [
                    {"foo": {"up": "down"}},
                    {"1": 2},
                    {"three": "four"},
                    {"1": 2},
                ],
                "control": [{"foo": {"up": "down"}}, {"1": 2}, {"three": "four"}],
            },
            {
                "input": [
                    {
                        "target_type": "node",
                        "target_id": 1000,
                        "target_uuid": "a5f348bc-ee11-4055-bc9c-599b4da65819",
                        "url": "/node/1000",
                    },
                    {
                        "target_id": 1000,
                        "target_type": "node",
                        "url": "/node/1000",
                        "target_uuid": "a5f348bc-ee11-4055-bc9c-599b4da65819",
                    },
                ],
                "control": [
                    {
                        "target_id": 1000,
                        "target_type": "node",
                        "target_uuid": "a5f348bc-ee11-4055-bc9c-599b4da65819",
                        "url": "/node/1000",
                    }
                ],
            },
        ]

        for fixture in fixtures:
            unique_values = workbench_utils.deduplicate_field_values(fixture["input"])
            self.assertEqual(fixture["control"], unique_values)


class TestMimeTypeFunctions(unittest.TestCase):
    def test_mimeypes_from_extensions(self):
        config = dict({"input_dir": "."})
        fixtures = [
            {
                "file_path": "tests/assets/mime_type_test/test2.tXt",
                "mime_type": "text/plain",
            },
            {
                "file_path": "tests/assets/mime_type_test/test2.hocR",
                "mime_type": "text/vnd.hocr+html",
            },
            {
                "file_path": "tests/assets/mime_type_test/test.101910",
                "mime_type": None,
            },
            {
                "file_path": "tests/assets/mime_type_test/testtest",
                "mime_type": None,
            },
            {
                "file_path": "tests/assets/mime_type_test/test.jpg",
                "mime_type": "image/jpeg",
            },
            {
                "file_path": "tests/assets/mime_type_test/test.xml",
                "mime_type": "application/xml",
            },
        ]

        for fixture in fixtures:
            mimetype = workbench_utils.get_mimetype_from_extension(
                config, fixture["file_path"]
            )
            self.assertEqual(fixture["mime_type"], mimetype)

    def test_mimeypes_from_extensions_lazy(self):
        config = dict({"input_dir": "."})
        fixtures = [
            {
                "file_path": "tests/assets/mime_type_test/test.txt",
                "mime_type": "application/octet-stream",
            },
            {
                "file_path": "tests/assets/mime_type_test/test.hocr",
                "mime_type": "text/vnd.hocr+html",
            },
            {
                "file_path": "tests/assets/mime_type_test/test.101910",
                "mime_type": "application/octet-stream",
            },
        ]

        for fixture in fixtures:
            mimetype = workbench_utils.get_mimetype_from_extension(
                config, fixture["file_path"], lazy=True
            )
            self.assertEqual(fixture["mime_type"], mimetype)

    def test_mimeypes_from_extensions_with_configs(self):
        extensions_to_mimetypes = collections.OrderedDict()
        extensions_to_mimetypes["txt"] = "foo/bar"
        extensions_to_mimetypes[".xml"] = "foo/xml"
        config = {"input_dir": ".", "extensions_to_mimetypes": extensions_to_mimetypes}
        fixtures = [
            {
                "file_path": "tests/assets/mime_type_test/test.txt",
                "mime_type": "foo/bar",
            },
            {
                "file_path": "tests/assets/mime_type_test/test.101910",
                "mime_type": None,
            },
            {
                "file_path": "tests/assets/mime_type_test/test.hocr",
                "mime_type": "text/vnd.hocr+html",
            },
            {
                "file_path": "tests/assets/mime_type_test/test.xml",
                "mime_type": "foo/xml",
            },
        ]

        for fixture in fixtures:
            mimetype = workbench_utils.get_mimetype_from_extension(
                config, fixture["file_path"]
            )
            self.assertEqual(fixture["mime_type"], mimetype)


class TestFileIsUtf8(unittest.TestCase):
    def test_file_is_utf8(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        input_files_dir = os.path.join(current_dir, "assets", "file_is_utf8_test")
        with os.scandir(input_files_dir) as files_to_test:
            for file_to_test in files_to_test:
                if file_to_test.name.startswith("true_"):
                    is_utf8 = workbench_utils.file_is_utf8(
                        os.path.join(input_files_dir, file_to_test)
                    )
                    self.assertEqual(is_utf8, True)

    def test_file_is_not_utf8(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        input_files_dir = os.path.join(current_dir, "assets", "file_is_utf8_test")
        with os.scandir(input_files_dir) as files_to_test:
            for file_to_test in files_to_test:
                if file_to_test.name.startswith("false_"):
                    is_utf8 = workbench_utils.file_is_utf8(
                        os.path.join(input_files_dir, file_to_test)
                    )
                    self.assertEqual(is_utf8, False)


if __name__ == "__main__":
    unittest.main()
