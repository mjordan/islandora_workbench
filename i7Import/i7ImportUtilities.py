from functools import lru_cache

from ruamel.yaml import YAML
import mimetypes
import requests
import re
import logging
from lxml.etree import ElementTree
from lxml import objectify
import sys
import os
import urllib.parse
from rich.console import Console
from rich.table import Table


def _params_to_querystring(params: dict) -> str:
    """Convert a dictionary of parameters to a query string.
    Parameters:
    params: dict: The parameters to convert.
    -------
    Returns:
    str: The query string.
    """
    querystring = ""
    for key, value in params.items():
        if len(querystring) > 0:
            querystring += "&"
        if isinstance(value, list):
            temp = [f"{key}={urllib.parse.quote_plus(str(item))}" for item in value]
            querystring += "&".join(temp)
        else:
            querystring += f"{key}={urllib.parse.quote_plus(str(value))}"
    return querystring


@lru_cache(maxsize=100)
def get_extension_from_mimetype(mimetype):
    """Get the file extension from a MIME type.
    Parameters:
    mimetype: str: The MIME type to convert.
    -------
    Returns:
    str: The file extension for the MIME type.
    """
    # mimetypes.add_type() is not working, e.g. mimetypes.add_type('image/jpeg', '.jpg')
    # Maybe related to https://bugs.python.org/issue4963? In the meantime, provide our own
    # MIMETYPE to extension mapping for common types, then let mimetypes guess at others.
    custom_map = {
        "image/jpeg": ".jpg",
        "image/jp2": ".jp2",
        "image/png": ".png",
        "image/tiff": ".tiff",
    }
    if mimetype in custom_map:
        return custom_map[mimetype]
    else:
        return mimetypes.guess_extension(mimetype)


@lru_cache(maxsize=5)
def get_metadata_solr_request(location):
    """Open the metadata solr request file and return the contents.
    Parameters:
    location: str: The path to the metadata solr request file.
    -------
    Returns:
    str: The contents of the metadata solr request file.
    """
    with open(location, "r") as file:
        solr_metadata_request = file.read()
    return solr_metadata_request


class i7ImportUtilities:
    """i7ImportUtilities is a class that provides utility functions for importing metadata from Islandora 7."""

    _logger = None
    _config = None
    config_location = None

    def __init__(self, config_location):
        """Initialize the i7ImportUtilities class.
        Parameters:
        config_location: str: The path to the configuration file.
        """
        self.config_location = config_location
        self._config = self._get_config()
        self.validate()

    default_config = {
        "solr_base_url": "http://localhost:8080/solr",
        "islandora_base_url": "http://localhost:8000",
        "csv_output_path": "islandora7_metadata.csv",
        "obj_directory": "/tmp/objs",
        "failure_report": "failure_report.txt",
        "log_file_path": "islandora_content.log",
        "fetch_files": False,
        "get_file_url": True,
        "namespace": "*",
        "standard_fields": [
            "PID",
            "RELS_EXT_hasModel_uri_s",
            "RELS_EXT_isMemberOfCollection_uri_ms",
            "RELS_EXT_isMemberOf_uri_ms",
            "RELS_EXT_isConstituentOf_uri_ms",
            "RELS_EXT_isPageOf_uri_ms",
        ],
        "field_pattern": "mods_.*(_s|_ms)$",
        "field_pattern_do_not_want": "(marcrelator|isSequenceNumberOf)",
        "id_field": "PID",
        "id_start_number": 1,
        "datastreams": ["OBJ", "PDF"],
        "debug": False,
        "deep_debug": False,
        "collection": False,
        "collections": False,
        "collection_field": "RELS_EXT_isMemberOfCollection_uri_s",
        "content_model": False,
        "solr_filters": False,
        "start": 0,
        "rows": 100000,
        "secure_ssl_only": True,
        "pids_to_use": False,
        "pids_to_skip": [],
        "paginate": False,
        "metadata_fields": {},
    }

    @property
    def config(self):
        """Return the configuration dictionary."""
        return self._config

    def _get_config(self):
        config = self.default_config
        with open(self.config_location, "r") as stream:
            try:
                loaded = YAML(typ="safe").load(stream)
            except OSError:
                print("Failed to load configuration file")
        for key, value in loaded.items():
            config[key] = value
        if "get_file_url" in loaded.keys() and "fetch_files" not in loaded.keys():
            config["fetch_files"] = False
        if config["deep_debug"]:
            config["debug"] = True
        return config

    @property
    def logger(self):
        if self._logger is None:
            self._configure_logger()
        return self._logger

    def _configure_logger(self):
        self._logger = logging.getLogger("i7ImportUtilities")
        self._logger.setLevel(logging.DEBUG if self.config["debug"] else logging.INFO)
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        formatter.datefmt = "%d-%b-%y %H:%M:%S"
        handler = logging.FileHandler(self.config["log_file_path"], mode="a")
        handler.setLevel(logging.DEBUG if self.config["debug"] else logging.INFO)
        handler.setFormatter(formatter)
        self._logger.propagate = False
        self._logger.addHandler(handler)

    @lru_cache(maxsize=10)
    def _get_i7_metadata_data(self, metadata_pid: str, ds_id: str) -> ElementTree:
        """Get the metadata for a given datastream ID as an ElementTree object.
        Parameters:
            metadata_pid: str: The PID of the metadata object.
            ds_id: str: The datastream ID to retrieve.
        -------
        Returns:
            ET: An ElementTree object containing the metadata.
        """
        metadata_url = f"{self.config['islandora_base_url']}/islandora/object/{metadata_pid}/datastream/{ds_id}/download"
        try:
            download_response = requests.get(
                verify=self.config["secure_ssl_only"],
                url=metadata_url,
                allow_redirects=True,
            )
            if download_response.ok:
                download_xml = download_response.content.decode()
                if self.config["deep_debug"]:
                    print(download_xml)
                root = objectify.fromstring(download_xml)
                return root
            return None

        except requests.exceptions.RequestException as e:
            self.logger.error(e)
            raise SystemExit(e)

    def get_metadata_value(
        self, pid: str, ds_id: str, xpath: str, first_only: bool = True
    ):
        """Get a specific metadata element from the i7 metadata.
        Parameters:
            pid: str: The PID of the metadata object.
            ds_id: str: The datastream ID to retrieve.
            xpath: str: The XPath to the specific element to retrieve.
            first_only: bool: If True, return only the first matching element.
        -------
        Returns:
            str: The text content of the element or multiple elements (with | delimiter), or None if not found.
        """
        root = self._get_i7_metadata_data(pid, ds_id)
        if root is not None:
            if first_only:
                element = root.find(xpath)
            else:
                element = root.findall(xpath)
            if element is not None and len(element) > 0:
                if self.config["deep_debug"]:
                    self.logger.debug(
                        f"Found element for PID {pid} with xpath {xpath}: {element.text}"
                    )
                if first_only:
                    return element.text
                else:
                    return "|".join([el.text for el in element if el.text is not None])
            else:
                self.logger.warning(
                    f"Element not found for PID {pid} with xpath {xpath}"
                )
        return None

    def parse_rels_ext(self, pid):
        root = self._get_i7_metadata_data(pid, "RELS-EXT")
        rel_ext = {}
        if root is not None:
            description = root.find(
                ".//{http://www.w3.org/1999/02/22-rdf-syntax-ns#}Description"
            )
            for x in description:
                tag = x.tag[x.tag.find("}") + 1 :]
                text = x.text
                if x.attrib.items():
                    text = next(iter(x.attrib.items()))[1]
                    text = text[text.find("/") + 1 :]
                rel_ext[tag] = text
        return rel_ext

    @lru_cache(maxsize=1)
    def get_solr_field_list(self):
        # This query gets all fields in the index. Does not need to be user-configurable.
        fields_solr_url = (
            f"{self.config['solr_base_url']}/admin/luke?wt=json&schema=show"
        )
        try:
            field_list_response = requests.get(
                verify=self.config["secure_ssl_only"],
                url=fields_solr_url,
                allow_redirects=True,
            )
            raw_data = field_list_response.json()
            raw_field_list = raw_data["fields"]
            field_list = raw_field_list.keys()
        except requests.exceptions.RequestException as e:
            self.logger.error(e)
            raise SystemExit(e)

        # Filter the field list based on if the field matches the field_pattern (if set) and
        # does not match the field_pattern_do_not_want.
        filtered_field_list = [
            keep
            for keep in field_list
            if (
                self.config["field_pattern"] is None
                or self.config["field_pattern"] == ""
                or re.search(self.config["field_pattern"], keep)
            )
            and not re.search(self.config["field_pattern_do_not_want"], keep)
        ]

        # Add required fieldnames.
        self.config["standard_fields"].reverse()
        for standard_field in self.config["standard_fields"]:
            if standard_field not in filtered_field_list:
                filtered_field_list.insert(0, standard_field)
        return filtered_field_list

    def get_default_metadata_solr_request(self):
        filtered_field_list = self.get_solr_field_list()
        fields_param = ",".join(filtered_field_list)

        params = {
            "q": f"PID:{self.config['namespace']}*",
            "wt": "json",
            "start": self.config["start"],
            "rows": self.config["rows"],
            "fl": fields_param,
            "fq": [],
        }

        if self.config["collection"]:
            collection = self.config["collection"]
            params["fq"].append(f'{self.config["collection_field"]}:"{collection}"')
        if self.config["content_model"]:
            model = self.config["content_model"]
            params["fq"].append(f'RELS_EXT_hasModel_uri_s:"{model}"')
        if self.config["solr_filters"]:
            for key, value in self.config["solr_filters"].items():
                params["fq"].append(f'{key}:"{value}"')
        if self.config["collections"]:
            collections = self.config["collections"]
            fedora_collections = [
                f'{self.config["collection_field"]}:"{collection}"'
                for collection in collections
            ]
            fq_string = " or ".join(fedora_collections)
            params["fq"].append(fq_string)
        if self.config["pids_to_use"]:
            pids_to_use = [f'PID:"{pid}"' for pid in self.config["pids_to_use"]]
            fq_string = " or ".join(pids_to_use)
            params["fq"].append(fq_string)

        # Get the populated CSV from Solr, with the object namespace and field list filters applied.
        querystring = _params_to_querystring(params)
        self.logger.debug(f"Default Solr Querystring: {querystring}")
        return f"{self.config['solr_base_url']}/select?" + querystring

    # Validates config.
    def validate(self):
        error_messages = []
        if self.config["get_file_url"] and self.config["fetch_files"]:
            message = f"'get_file_url' and 'fetch_files' cannot both be selected."
            error_messages.append(message)
        if error_messages:
            self.logger.error("Error: " + "\n".join(error_messages))
            sys.exit("Error: " + "\n".join(error_messages))

    # Gets file from i7 installation
    def get_i7_asset(self, pid, datastream):
        try:
            obj_url = f"{self.config['islandora_base_url']}/islandora/object/{pid}/datastream/{datastream}/download"
            self.logger.debug(f"Attempting to download {obj_url}")
            if self.config["get_file_url"]:
                obj_download_response = requests.head(
                    verify=self.config["secure_ssl_only"],
                    url=obj_url,
                    allow_redirects=True,
                )
            else:
                obj_download_response = requests.get(
                    verify=self.config["secure_ssl_only"],
                    url=obj_url,
                    allow_redirects=True,
                )
            if obj_download_response.status_code == 200:
                # Get MIMETYPE from 'Content-Type' header
                obj_mimetype = obj_download_response.headers["content-type"]
                obj_extension = get_extension_from_mimetype(obj_mimetype)
                if self.config["fetch_files"] and obj_extension:
                    obj_filename = pid.replace(":", "_")
                    obj_basename = obj_filename + obj_extension
                    # Save to file with name based on PID and extension based on MIMETYPE
                    obj_file_path = os.path.join(
                        self.config["obj_directory"], obj_basename
                    )
                    open(obj_file_path, "wb+").write(obj_download_response.content)
                    return obj_basename

                elif self.config["get_file_url"] and obj_extension:
                    return obj_url
            elif obj_download_response.status_code == 404:
                self.logger.warning(f"{obj_url} not found.")
            else:
                message = f"Bad response from server for item {pid} : {obj_download_response.status_code}"
                self.logger.error(message)
            return None

        except requests.exceptions.RequestException as e:
            self.logger.error(e)
            return None

    # Convenience function for debugging - Prints config to console screen.
    def print_config(self):
        table = Table(title="i7 Import Script Configuration")
        table.add_column("Parameter", justify="left")
        table.add_column("Value", justify="left")
        for key, value in self.config.items():
            if str(type(value)) == "<class 'ruamel.yaml.comments.CommentedMap'>":
                new_value = ""
                for k, v in value.items():
                    new_value += f"{k}: {v}\n"
                value = new_value
            table.add_row(key, str(value))
        console = Console()
        console.print(table)
