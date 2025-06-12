"""Utility functions for Islandora Workbench."""

import os
import sys
import json
from json.decoder import JSONDecodeError
import csv
import openpyxl
import time
import string
import re
import copy
import logging
import random
import uuid
import datetime
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import subprocess
import hashlib
import mimetypes
import collections
import urllib.parse
from pathlib import Path
from ruamel.yaml import YAML, YAMLError
from unidecode import unidecode
from progress_bar import InitBar
import edtf_validate.valid_edtf
import shutil
import itertools
import http.client
import sqlite3
import zipfile
import requests_cache
from rich.traceback import install

install()

# Set some global variables.
yaml = YAML()

EXECUTION_START_TIME = datetime.datetime.now()
INTEGRATION_MODULE_MIN_VERSION = "1.0"
# Workaround for https://github.com/mjordan/islandora_workbench/issues/360.
http.client._MAXHEADERS = 10000
http_response_times = []
# Global lists of terms to reduce queries to Drupal.
checked_terms = list()
newly_created_terms = list()
# These are the Drupal field names on the standard types of media.
file_fields = [
    "field_media_file",
    "field_media_image",
    "field_media_document",
    "field_media_audio_file",
    "field_media_video_file",
]


def set_media_type(config, filepath, file_fieldname, csv_row):
    """Using either the 'media_type' or 'media_types_override' configuration
    setting, determine which media bundle type to use.

    Parameters
    ----------
    config : dict
        The configuration settings defined by workbench_config.get_config().
    filepath: string
        The value of the CSV 'file' column.
    file_fieldname: string
         The name of the CSV column containing the filename (usually 'file'). None if the file
         isn't in a CSV field (e.g., when config['paged_content_from_directories'] is True).
    csv_row : OrderedDict
         The CSV row for the current item.
    Returns
    -------
    string
        A string naming the configured media type, e.g. 'image'.
    """
    if "media_type" in config:
        return config["media_type"]
    if config["media_type_by_media_use"] and len(config["media_type_by_media_use"]) > 0:
        additional_files = get_additional_files_config(config)
        media_url = additional_files.get(file_fieldname)
        if file_fieldname in additional_files:
            for entry in config["media_type_by_media_use"]:
                for key, value in entry.items():
                    if key == media_url:
                        return value

    # Determine if the incomtimg filepath matches a registered eEmbed media type.
    oembed_media_type = get_oembed_url_media_type(config, filepath)
    if oembed_media_type is not None:
        return oembed_media_type

    if file_fieldname is not None and filepath.strip().startswith("http"):
        preprocessed_file_path = get_preprocessed_file_path(
            config, file_fieldname, csv_row
        )
        filename = preprocessed_file_path.split("/")[-1]
        extension = filename.split(".")[-1]
        extension_with_dot = "." + extension
    else:
        extension_with_dot = os.path.splitext(filepath)[-1]

    extension = extension_with_dot[1:]
    normalized_extension = extension.lower()
    media_type = "file"
    for types in config["media_types"]:
        for type, extensions in types.items():
            if normalized_extension in extensions:
                media_type = type
    if "media_types_override" in config:
        for override in config["media_types_override"]:
            for type, extensions in override.items():
                if normalized_extension in extensions:
                    media_type = type

    # If extension isn't in one of the lists, default to 'file' bundle.
    return media_type


def get_oembed_url_media_type(config, filepath):
    """Since oEmbed remote media (e.g. remove video) don't have extensions, which we
    use to detect the media type of local files, we use remote URL patterns to
    detect if the value of the 'file' columns is an oEmbed media.

    Parameters
    ----------
    config : dict
       The configuration settings defined by workbench_config.get_config().
    filepath: string
       The value of the CSV 'file' column.
    Returns
    -------
    mtype : str|None
       A string naming the detected media type, e.g. 'remote_video', or None
       if the filepath does not start with a configured provider URL.
    """
    for oembed_provider in config["oembed_providers"]:
        for mtype, provider_urls in oembed_provider.items():
            for provider_url in provider_urls:
                if filepath.startswith(provider_url):
                    return mtype

    return None


def get_oembed_media_types(config):
    """Get a list of the registered oEmbed media types from config.

    Parameters
    ----------
    config : dict
           The configuration settings defined by workbench_config.get_config().

    Returns
    -------
    media_types : list
        A list with the configured allowed oEmbed media type(s), e.g. ['remote_video'].
    """

    media_types = list()
    for omt in config["oembed_providers"]:
        keys = list(omt.keys())
        media_types.append(keys[0])
    return media_types


def set_model_from_extension(file_name, config):
    """Using configuration options, determine which Islandora Model value
    to assign to nodes created from files. Options are either a single model
    or a set of mappings from file extension to Islandora Model term ID.

    Parameters
    ----------
    file_name : str
        Filename that will be checked to determine Islandora Model value(s).
    config : dict
        The configuration settings defined by workbench_config.get_config().


    Returns
    -------
    None|str|dict
        None is returned if 'task' is not set to 'create_from_files'.

        str is returned if 'model' config value is set, a single model term ID is str returned.

        dict is returned if 'models' config value is set, a dict with a mapping of URIs or Islandora Model term ID(s)
        to file extension(s) is returned.
    """
    if config["task"] != "create_from_files":
        return None

    if "model" in config:
        return config["model"]

    extension_with_dot = os.path.splitext(file_name)[1]
    extension = extension_with_dot[1:]
    normalized_extension = extension.lower()
    for model_tids in config["models"]:
        for tid, extensions in model_tids.items():
            if str(tid).startswith("http"):
                tid = get_term_id_from_uri(config, tid)
            if normalized_extension in extensions:
                return tid
            # If the file's extension is not listed in the config,
            # We use the term ID that contains an empty extension.
            if "" in extensions:
                return tid


def issue_request(config, method, path, headers=None, json="", data="", query=None):
    """Issue the HTTP request to Drupal. Note: calls to non-Drupal URLs
    do not use this function.

    Parameters
    ----------
    config : dict
        The configuration settings defined by workbench_config.get_config().
    method : str
        The HTTP method to be issued for the request, e.g. POST or GET.
    path : str
        Path to the API endpoint that will be used for request.
    headers : dict, optional
        HTTP header information to be sent with request encoded as a dict.
    json : dict, optional
        Data to be sent with request body as JSON format, but encoded as a dict.
    data : str, optional
        Data to be sent in request body.
    query : dict, optional
        Request parameters sent as a dict.

    Returns
    -------
    requests.Response
    """
    with requests.Session() as session:
        retries = Retry(
            total=config["http_max_retries"],
            backoff_factor=config["http_backoff_factor"],
            status_forcelist=config["http_retry_on_status_codes"],
            allowed_methods=config["http_retry_allowed_methods"],
        )
        session.mount("http://", HTTPAdapter(max_retries=retries))
        session.mount("https://", HTTPAdapter(max_retries=retries))
        try:
            if config["secure_ssl_only"] is False:
                requests.packages.urllib3.disable_warnings()

            if not config["password"]:
                message = (
                    'Password for Drupal user not found. Please add the "password" option to your configuration '
                    + "file or provide the Drupal user's password in your ISLANDORA_WORKBENCH_PASSWORD environment variable."
                )
                logging.error(message)
                sys.exit("Error: " + message)

            if config["check"] is False:
                if (
                    "pause" in config
                    # and method in ["POST", "PUT", "PATCH", "DELETE"]
                    and value_is_numeric(config["pause"])
                ):
                    time.sleep(int(config["pause"]))

            if headers is None:
                headers = dict()

            if query is None:
                query = dict()

            headers.update({"User-Agent": config["user_agent"]})

            # The trailing / is stripped in config, but we do it here too, just in case.
            config["host"] = config["host"].rstrip("/")
            if config["host"] in path:
                url = path
            else:
                # Since we remove the trailing / from the hostname, we need to ensure
                # that there is a / separating the host from the path.
                if not path.startswith("/"):
                    path = "/" + path
                url = config["host"] + path

            if config["log_request_url"] is True:
                logging.info(method + " " + url)

            if method == "GET":
                if config["log_headers"] is True:
                    logging.info(headers)
                response = session.get(
                    url,
                    allow_redirects=config["allow_redirects"],
                    verify=config["secure_ssl_only"],
                    auth=(config["username"], config["password"]),
                    params=query,
                    headers=headers,
                )
            if method == "HEAD":
                if config["log_headers"] is True:
                    logging.info(headers)
                response = session.head(
                    url,
                    allow_redirects=config["allow_redirects"],
                    verify=config["secure_ssl_only"],
                    auth=(config["username"], config["password"]),
                    headers=headers,
                )
            if method == "POST":
                if config["log_headers"] is True:
                    logging.info(headers)
                if config["log_json"] is True:
                    logging.info(json)
                response = session.post(
                    url,
                    allow_redirects=config["allow_redirects"],
                    stream=True,
                    verify=config["secure_ssl_only"],
                    auth=(config["username"], config["password"]),
                    headers=headers,
                    json=json,
                    data=data,
                )
            if method == "PUT":
                if config["log_headers"] is True:
                    logging.info(headers)
                if config["log_json"] is True:
                    logging.info(json)
                response = session.put(
                    url,
                    allow_redirects=config["allow_redirects"],
                    stream=True,
                    verify=config["secure_ssl_only"],
                    auth=(config["username"], config["password"]),
                    headers=headers,
                    json=json,
                    data=data,
                )
            if method == "PATCH":
                if config["log_headers"] is True:
                    logging.info(headers)
                if config["log_json"] is True:
                    logging.info(json)
                response = session.patch(
                    url,
                    allow_redirects=config["allow_redirects"],
                    stream=True,
                    verify=config["secure_ssl_only"],
                    auth=(config["username"], config["password"]),
                    headers=headers,
                    json=json,
                    data=data,
                )
            if method == "DELETE":
                if config["log_headers"] is True:
                    logging.info(headers)
                response = session.delete(
                    url,
                    allow_redirects=config["allow_redirects"],
                    verify=config["secure_ssl_only"],
                    auth=(config["username"], config["password"]),
                    headers=headers,
                )

            if config["log_response_status_code"] is True:
                logging.info(response.status_code)

            if config["log_response_body"] is True:
                logging.info(response.text)

            response_time = response.elapsed.total_seconds()
            average_response_time = calculate_response_time_trend(config, response_time)

            log_response_time_value = copy.copy(config["log_response_time"])
            if "adaptive_pause" in config and value_is_numeric(
                config["adaptive_pause"]
            ):
                # Pause defined in config['adaptive_pause'] is included in the response time,
                # so we subtract it to get the "unpaused" response time.
                if average_response_time is not None and (
                    response_time - int(config["adaptive_pause"])
                ) > (average_response_time * int(config["adaptive_pause_threshold"])):
                    message = (
                        "HTTP requests paused for "
                        + str(config["adaptive_pause"])
                        + " seconds because request in next log entry "
                        + "exceeded adaptive threshold of "
                        + str(config["adaptive_pause_threshold"])
                        + "."
                    )
                    time.sleep(int(config["adaptive_pause"]))
                    logging.info(message)
                    # Enable response time logging if we surpass the adaptive pause threashold.
                    config["log_response_time"] = True

            if config["log_response_time"] is True:
                parsed_query_string = urllib.parse.urlparse(url).query
                if len(parsed_query_string):
                    url_for_logging = (
                        urllib.parse.urlparse(url).path + "?" + parsed_query_string
                    )
                else:
                    url_for_logging = urllib.parse.urlparse(url).path
                if "adaptive_pause" in config and value_is_numeric(
                    config["adaptive_pause"]
                ):
                    response_time = response_time - int(config["adaptive_pause"])
                response_time_trend_entry = {
                    "method": method,
                    "response": response.status_code,
                    "url": url_for_logging,
                    "response_time": response_time,
                    "average_response_time": average_response_time,
                }
                logging.info(response_time_trend_entry)
                # Set this config option back to what it was before we updated in above.
                config["log_response_time"] = log_response_time_value
            return response
        except requests.exceptions.Timeout as err_timeout:
            message = f'Workbench timed out while requesting "{url}".'
            logging.error(message)
            logging.error(err_timeout)
            sys.exit("Error: " + message)
        except requests.exceptions.ConnectionError as error_connection:
            message = f'Workbench could not connect to {config["host"]} while requesting "{url}".'
            logging.error(message)
            logging.error(error_connection)
            sys.exit("Error: " + message)
        except requests.exceptions.RequestException as request_error:
            message = f'Workbench encountered an exception while requesting "{url}".'
            logging.error(message)
            logging.error(request_error)
            sys.exit("Error: " + message)


def convert_semver_to_number(version_string):
    """Convert a Semantic Version number (e.g. Drupal's) string to a number. We only need the major
    and minor numbers (e.g. 9.2).

    Parameters
    ----------
    version_string: string
        The version string as retrieved from Drupal.
    Returns
    -------
    tuple
        A tuple containing the major and minor Drupal core version numbers as integers.
    """
    parts = version_string.split(".")
    parts = parts[:2]
    int_parts = [int(part) for part in parts]
    version_tuple = tuple(int_parts)
    return version_tuple


def get_drupal_core_version(config):
    """Get Drupal's version number.

    Parameters
    ----------
    config : dict
        The configuration settings defined by workbench_config.get_config().
    Returns
    -------
    string|False
        The Drupal core version number string (i.e., may contain -dev, etc.).
    """
    url = config["host"] + "/islandora_workbench_integration/core_version"
    response = issue_request(config, "GET", url)
    if response.status_code == 200:
        version_body = json.loads(response.text)
        return version_body["core_version"]
    else:
        logging.warning(
            "Attempt to get Drupal core version number returned a %s status code",
            response.status_code,
        )
        return False


def check_drupal_core_version(config):
    """Used during --check to verify if the minimum required Drupal version for workbench is being used.

    Parameters
    ----------
    config : dict
        The configuration settings defined by workbench_config.get_config().
    Returns
    -------
    None
    """
    drupal_core_version = get_drupal_core_version(config)
    if drupal_core_version is not False:
        core_version_number = convert_semver_to_number(drupal_core_version)
    else:
        message = "Workbench cannot determine Drupal's version number."
        logging.error(message)
        sys.exit("Error: " + message)
    if core_version_number < tuple([8, 6]):
        message = (
            "Warning: Media creation in your version of Drupal ("
            + drupal_core_version
            + ") is less reliable than in Drupal 8.6 or higher."
        )
        print(message)


def check_integration_module_version(config):
    """Verifies if the minimum required version of the workbench integration module is being used.

    Parameters
    ----------
    config : dict
        The configuration settings defined by workbench_config.get_config().
    Returns
    -------
    None
    """
    version = get_integration_module_version(config)

    if version is False:
        message = (
            "Workbench cannot determine the Islandora Workbench Integration module's version number. It must be version "
            + str(INTEGRATION_MODULE_MIN_VERSION)
            + " or higher."
        )
        logging.error(message)
        sys.exit("Error: " + message)
    else:
        version_number = convert_semver_to_number(version)
        minimum_version_number = convert_semver_to_number(
            INTEGRATION_MODULE_MIN_VERSION
        )
        if version_number < minimum_version_number:
            message = (
                "The Islandora Workbench Integration module installed on "
                + config["host"]
                + " must be"
                + " upgraded to version "
                + str(INTEGRATION_MODULE_MIN_VERSION)
                + "."
            )
            logging.error(message)
            sys.exit("Error: " + message)
        else:
            logging.info(
                "OK, Islandora Workbench Integration module installed on "
                + config["host"]
                + " is at version "
                + str(version)
                + "."
            )


def get_integration_module_version(config):
    """Get the Islandora Workbench Integration module's version number.

    Parameters
    ----------
    config : dict
        The configuration settings defined by workbench_config.get_config().
    Returns
    -------
    string|False
        The version number string (i.e., may contain -dev, etc.) from the
        Islandora Workbench Integration module.
    """
    url = config["host"] + "/islandora_workbench_integration/version"
    response = issue_request(config, "GET", url)
    if response.status_code == 200:
        version_body = json.loads(response.text)
        return version_body["integration_module_version"]
    else:
        logging.warning(
            "Attempt to get the Islandora Workbench Integration module's version number returned a %s status code",
            response.status_code,
        )
        return False


def ping_node(config, nid_to_ping, method="HEAD", return_json=False, warn=True):
    """Ping the node to see if it exists.

    Note that HEAD requests do not return a response body.

    Parameters
    ----------
    config : dict
        The configuration settings defined by workbench_config.get_config().
    nid_to_ping : string
        Node ID/URL/alias of the node to be pinged.
    method: string, optional
        Either 'HEAD' or 'GET'.
    return_json: boolean, optional
        If True, return the entire response body to the caller.
    warn: boolean, optional
       If True, write a log entry.

    Returns
    ------
     boolean|str
        True if method is HEAD and node was found, the response JSON response
        body if method was GET. False if request returns a non-allowed status code.
    """
    incoming_nid_to_ping = copy.copy(nid_to_ping)
    if nid_to_ping is False:
        if warn is True:
            logging.warning(
                "Can't perform node ping because the provided node ID was 'False'."
            )
        return False

    if value_is_numeric(nid_to_ping) is False:
        nid_to_ping = get_nid_from_url_alias(config, nid_to_ping)
    url_to_ping = config["host"] + "/node/" + str(nid_to_ping) + "?_format=json"
    response = issue_request(config, method.upper(), url_to_ping)
    allowed_status_codes = [200, 301, 302]
    if response.status_code in allowed_status_codes:
        if return_json is True:
            return response.text
        else:
            return True
    else:
        if warn is True:
            logging.warning(
                "(%s) ping on node %s (using node ID %s) returned a %s status code.",
                method.upper(),
                url_to_ping,
                incoming_nid_to_ping,
                response.status_code,
            )
        return False


def verify_node_exists_by_key(config, csv_row):
    """Query a View using a value from CSV (the "key") to see if the node exists.

    Parameters
    ----------
    config : dict
        The configuration settings defined by workbench_config.get_config().
    csv_row :
        A copy of the CSV row that represents the node we are interested in.

    Returns
    ------
     str|False
        The node ID if the node exists, False if the node doesn't exist, there are more than 1 node exists,
        or if there was a non-200 HTTP response.
    """
    endpoint_mapping = get_node_exists_verification_view_endpoint(config)
    if len(csv_row[endpoint_mapping[0]]) == 0:
        row_id = csv_row[config["id_field"]]
        logging.warning(
            f'Can\'t verify node exists for item in row "{row_id}" since it has no value in its "{endpoint_mapping[0]}" CSV column.'
        )
        return False

    csv_value = copy.copy(csv_row[endpoint_mapping[0]])
    if config["subdelimiter"] in csv_value:
        csv_value_for_url = csv_value.replace(config["subdelimiter"], "%20")
    else:
        csv_value_for_url = csv_value

    view_url = f'{config["host"]}/{endpoint_mapping[1].lstrip("/")}?{endpoint_mapping[0]}={csv_value_for_url}'
    headers = {"Content-Type": "application/json"}
    response = issue_request(config, "GET", view_url, headers)
    if response.status_code == 200:
        body = json.loads(response.text)
        if len(body) == 1:
            return body[0]["nid"]
        elif len(body) > 1:
            logging.warning(
                f'Query to View "{view_url}" found more than one node ({body}). CSV "{endpoint_mapping[0]}" value was {csv_row[endpoint_mapping[0]]}. Workbench skipped this CSV row.'
            )
        else:
            return False
    else:
        logging.warning(
            f"Query to View {view_url} encountered a problem: HTTP status code was {response.status_code}"
        )
        return False


def ping_url_alias(config, url_alias):
    """Ping the URL alias to see if it exists. Return the status code.

    Parameters
    ----------
    config : dict
        The configuration settings defined by workbench_config.get_config().
    url_alias : str
        The string with the URL alias being pinged.
    Returns
    -------
    int
        HTTP status code.
    """
    url = config["host"] + url_alias + "?_format=json"
    response = issue_request(config, "GET", url)
    return response.status_code


def ping_vocabulary(config, vocab_id):
    """Ping the node to see if it exists.

    Parameters
    ----------
    config : dict
        The configuration settings defined by workbench_config.get_config().
    vocab_id : str
        The string with the vocabulary ID being pinged.
    Returns
    -------
    boolean
        Returns Ture if HTTP status code returned is 200, if not False is returned.
    """
    url = (
        config["host"]
        + "/entity/taxonomy_vocabulary/"
        + vocab_id.strip()
        + "?_format=json"
    )
    response = issue_request(config, "GET", url)
    if response.status_code == 200:
        return True
    else:
        logging.warning(
            "Node ping (GET) on %s returned a %s status code.",
            url,
            response.status_code,
        )
        return False


def ping_term(config, term_id):
    """Ping the term to see if it exists.

    Parameters
    ----------
    config : dict
        The configuration settings defined by workbench_config.get_config().
    term_id : str
        The string with the term ID being pinged.
    Returns
    -------
    boolean
        Returns Ture if HTTP status code returned is 200, if not False is returned.
    """

    url = config["host"] + "/taxonomy/term/" + str(term_id).strip() + "?_format=json"
    response = issue_request(config, "GET", url)
    if response.status_code == 200:
        return True
    else:
        logging.warning(
            "Term ping (GET) on %s returned a %s status code.",
            url,
            response.status_code,
        )
        return False


def ping_islandora(config, print_message=True):
    """Connect to Islandora in prep for subsequent HTTP requests.

    Parameters
    ----------
    config : dict
        The configuration settings defined by workbench_config.get_config().
    print_message : boolean, optional
        If set to True, after ping successfully performed, a status message is printed for the user.
    Returns
    -------
    None
    """

    # First, test a known request that requires Administrator-level permissions.
    url = config["host"] + "/islandora_workbench_integration/version"
    try:
        host_response = issue_request(config, "GET", url)
    except requests.exceptions.Timeout as err_timeout:
        message = (
            "Workbench timed out trying to reach "
            + config["host"]
            + '. Please verify the "host" setting in your configuration '
            + "and check your network connection."
        )
        logging.error(message)
        logging.error(err_timeout)
        sys.exit("Error: " + message)
    except requests.exceptions.ConnectionError as error_connection:
        message = (
            "Workbench cannot connect to "
            + config["host"]
            + '. Please verify the "host" setting in your configuration '
            + "and check your network connection."
        )
        logging.error(message)
        logging.error(error_connection)
        sys.exit("Error: " + message)

    if host_response.status_code == 404:
        message = (
            "Workbench cannot detect whether the Islandora Workbench Integration module is "
            + "enabled on "
            + config["host"]
            + ". Please ensure it is enabled and that its version is "
            + str(INTEGRATION_MODULE_MIN_VERSION)
            + " or higher."
        )
        logging.error(message)
        sys.exit("Error: " + message)

    not_authorized = [401, 403]
    if host_response.status_code in not_authorized:
        message = (
            "Workbench can connect to "
            + config["host"]
            + ' but the user "'
            + config["username"]
            + '" does not have sufficient permissions to continue, or the credentials are invalid.'
        )
        logging.error(message)
        sys.exit("Error: " + message)

    if config["secure_ssl_only"] is True:
        message = "OK, connection to Drupal at " + config["host"] + " verified."
    else:
        message = (
            "OK, connection to Drupal at "
            + config["host"]
            + " verified. Ignoring SSL certificates."
        )
    if print_message is True:
        logging.info(message)
        print(message)


def ping_content_type(config):
    """Ping the content_type set in the configuration to see if it exists.
    Parameters
    ----------
    config : dict
        The configuration settings defined by workbench_config.get_config().
    Returns
    -------
    int
        The HTTP response code.
    """

    url = f"{config['host']}/entity/entity_form_display/node.{config['content_type']}.default?_format=json"
    return issue_request(config, "GET", url).status_code


def ping_view_endpoint(config, view_url):
    """Verifies that the View REST endpoint is accessible.

    Parameters
    ----------
    config : dict
        The configuration settings defined by workbench_config.get_config().
    view_url
        The View's REST export path.
    Returns
    -------
    int
        The HTTP response code.
    """
    return issue_request(config, "HEAD", view_url).status_code


def ping_entity_reference_view_endpoint(config, fieldname, handler_settings):
    """Verifies that the REST endpoint of the View is accessible. The path to this endpoint
    is defined in the configuration file's 'entity_reference_view_endpoints' option.

    Necessary for entity reference fields configured as "Views: Filter by an entity reference View".
    Unlike Views endpoints for taxonomy entity reference fields configured using the "default"
    entity reference method, the Islandora Workbench Integration module does not provide a generic
    Views REST endpoint that can be used to validate values in this type of field.

    Parameters
    ----------
    config : dict
        The configuration settings defined by workbench_config.get_config().
    fieldname : string
        The name of the Drupal field.
    handler_settings : dict
        The handler_settings values from the field's configuration.
        # handler_settings': {'view': {'view_name': 'mj_entity_reference_test', 'display_name': 'entity_reference_1', 'arguments': []}}
    Returns
    -------
    bool
        True if the REST endpoint is accessible, False if not.
    """
    endpoint_mappings = get_entity_reference_view_endpoints(config)
    if len(endpoint_mappings) == 0:
        logging.warning(
            "The 'entity_reference_view_endpoints' option in your configuration file does not contain any field-Views endpoint mappings."
        )
        return False
    if fieldname not in endpoint_mappings:
        logging.warning(
            'The field "'
            + fieldname
            + '" is not in your "entity_reference_view_endpoints" configuration option.'
        )
        return False

    # E.g., "http://localhost:8000/issue_452_test?name=xxx&_format=json"
    url = config["host"] + endpoint_mappings[fieldname] + "?name=xxx&_format=json"
    response = issue_request(config, "GET", url)
    if response.status_code == 200:
        return True
    else:
        logging.warning(
            "View REST export ping (GET) on %s returned a %s status code",
            url,
            response.status_code,
        )
        return False


def ping_media_bundle(config, bundle_name):
    """Ping the Media bundle/type to see if it exists. Return the status code,
    a 200 if it exists or a 404 if it doesn't exist or the Media Type REST resource
    is not enabled on the target Drupal.

    Parameters
    ----------
    config : dict
        The configuration settings defined by workbench_config.get_config().
    bundle_name : str
        Media bundle/type to be pinged.
    Returns
    -------
    int
        The HTTP response code.
    """
    url = config["host"] + "/entity/media_type/" + bundle_name + "?_format=json"
    response = issue_request(config, "GET", url)
    return response.status_code


def ping_media(config, mid, method="HEAD", return_json=False, warn=True):
    """Ping the media to see if it exists.

    Note that HEAD requests do not return a response body.

    Parameters
    ----------
    config : dict
        The configuration settings defined by workbench_config.get_config().
    mid :
        Media ID of the media to be pinged. Could be a numeric media ID or a full URL to the media.
    method: string, optional
        Either 'HEAD' or 'GET'.
    return_json: boolean, optional
    warn: boolean, optional

    Returns
    ------
     boolean|str
        True if method is HEAD and node was found, the response JSON response
        body if method was GET. False if request returns a non-allowed status code.
    """
    if value_is_numeric(mid) is False:
        mid = get_mid_from_media_url_alias(config, mid)

    if config["standalone_media_url"] is True:
        url = config["host"] + "/media/" + str(mid) + "?_format=json"
    else:
        url = config["host"] + "/media/" + str(mid) + "/edit?_format=json"

    response = issue_request(config, method.upper(), url)
    allowed_status_codes = [200, 301, 302]
    if response.status_code in allowed_status_codes:
        if return_json is True:
            return response.text
        else:
            return True
    else:
        if warn is True:
            logging.warning(
                "Media ping (%s) on %s returned a %s status code.",
                method.upper(),
                url,
                response.status_code,
            )
        return False


def extract_media_id(config: dict, media_csv_row: dict):
    """Extract the media entity's ID from the CSV row.

    Parameters
    ----------
    config : dict
        The global configuration object.
    media_csv_row : OrderedDict
        The CSV row containing the media entity's field names and values.

    Returns
    -------
    str|None
        The media entity's ID if it could be extracted from the CSV row and is valid, otherwise None.
    """
    if "media_id" not in media_csv_row:  # Media ID column is missing
        logging.error("Media ID column missing in CSV file.")
        return None

    if not media_csv_row["media_id"]:  # Media ID column is present but empty
        logging.error("Row with empty media_id column detected in CSV file.")
        return None

    # If media ID is not numeric, assume it is a media URL alias.
    if not value_is_numeric(media_csv_row["media_id"]):
        # Note that this function returns False if the media URL alias does not exist.
        media_id = get_mid_from_media_url_alias(config, media_csv_row["media_id"])
        # Media URL alias does not exist.
        if media_id is False:
            logging.error(
                "Media URL alias %s does not exist.", media_csv_row["media_id"]
            )
            return None
        else:
            return str(media_id)
    # If media ID is numeric, use it as is, if it is a valid media ID
    else:
        media_response_code = ping_media(config, media_csv_row["media_id"])
        if media_response_code is not True:
            logging.error("Media ID %s does not exist.", media_csv_row["media_id"])
            return None
        # If media ID exists, use it as is (since this is a string)
        else:
            return media_csv_row["media_id"]


def ping_remote_file(config, url):
    """Ping remote file, but logging, exiting, etc. happens in caller, except on requests error.
    Parameters
    ----------
    config : dict
        The configuration settings defined by workbench_config.get_config().
    url : str
        URL of remote file to be pinged.
    Returns
    -------
    int|None
    """
    headers = {"User-Agent": config["user_agent"]}

    sections = urllib.parse.urlparse(url)
    try:
        response = requests.head(
            url, allow_redirects=True, verify=config["secure_ssl_only"], headers=headers
        )
        return response.status_code
    except requests.exceptions.Timeout as err_timeout:
        message = (
            "Workbench timed out trying to reach "
            + sections.netloc
            + " while connecting to "
            + url
            + ". Please verify that URL and check your network connection."
        )
        logging.error(message)
        logging.error(err_timeout)
        sys.exit("Error: " + message)
    except requests.exceptions.ConnectionError as error_connection:
        message = (
            "Workbench cannot connect to "
            + sections.netloc
            + " while connecting to "
            + url
            + ". Please verify that URL and check your network connection."
        )
        logging.error(message)
        logging.error(error_connection)
        sys.exit("Error: " + message)


def get_nid_from_url_alias(config, url_alias_to_query):
    """Gets a node ID from a URL alias. This function also works on canonical
    URLs, e.g. https://localhost:8000/node/1648 and URL aliases without a hostname,
    e.g., /i_am_an_alias.

    Parameters
    ----------
    config : dict
        The configuration settings defined by workbench_config.get_config().
    url_alias_to_query : string
        The full URL alias (or canonical URL), including https://, etc.
    Returns
    -------
    int|boolean
        The node ID, or False if the URL cannot be found.
    """
    if url_alias_to_query is False:
        return False

    if url_alias_to_query.startswith("http") is True:
        # Drupal sometimes returns "http://" instead of "https://" in the "location"
        # response header. Check for that and replace it if necessary.
        if url_alias_to_query.startswith("http://") and config["host"].startswith(
            "https://"
        ):
            url_alias_to_query = re.sub(
                r"^http://", "https://", url_alias_to_query, flags=re.IGNORECASE
            )
        alias_query_url = f"{url_alias_to_query}?_format=json"
    else:
        alias_query_url = (
            f'{config["host"]}/{url_alias_to_query.lstrip("/")}?_format=json'
        )

    alias_query_response = issue_request(config, "GET", alias_query_url)
    if alias_query_response.status_code != 200:
        return False
    else:
        alias_query_node = json.loads(alias_query_response.text)
        return alias_query_node["nid"][0]["value"]


def get_mid_from_media_url_alias(config, url_alias):
    """Gets a media ID from a media URL alias. This function also works
    with canonical URLs, e.g. http://localhost:8000/media/1234.

    Parameters
    ----------
    config : dict
        The configuration settings defined by workbench_config.get_config().
    url_alias : string
        The full URL alias (or canonical URL), including http://, etc.
    Returns
    -------
    int|boolean
        The media ID, or False if the URL cannot be found.
    """
    # Drupal sometimes returns "http://" instead of "https://" in the "location"
    # response header. Check for that and replace it if necessary.
    if url_alias.startswith("http://") and config["host"].startswith("https://"):
        url_alias = re.sub(r"^http://", "https://", url_alias, flags=re.IGNORECASE)

    url = url_alias + "?_format=json"
    response = issue_request(config, "GET", url)
    if response.status_code != 200:
        return False
    else:
        media = json.loads(response.text)
        return media["mid"][0]["value"]


def get_nid_from_url_without_config(url):
    """Gets a node ID from a raw Drupal URL, with no accompanying config data. Useful
       within integration tests where the config is not directly accessible.

    Parameters
    ----------
    url : string
        The full URL alias (or canonical URL), including http://, etc.
    Returns
    -------
    int|boolean
        The node ID, or False if the URL cannot be found.
    """
    url = url + "?_format=json"
    response = requests.get(url, verify=False)
    if response.status_code != 200:
        return False
    else:
        media = json.loads(response.text)
        return media["nid"][0]["value"]


def get_node_title_from_nid(config, node_id):
    """Get node title from Drupal.

    Parameters
    ----------
    config : dict
        The configuration settings defined by workbench_config.get_config().
    node_id : string
        The node ID for the node title being fetched.
    Returns
    -------
    str|boolean
        The node title, or False if the URL does not return HTTP status 200.
    """
    node_url = config["host"] + "/node/" + node_id + "?_format=json"
    node_response = issue_request(config, "GET", node_url)
    if node_response.status_code == 200:
        node_dict = json.loads(node_response.text)
        return node_dict["title"][0]["value"]
    else:
        return False


def get_field_definitions(config, entity_type, bundle_type=None):
    """Get field definitions from Drupal.

    Parameters
    ----------
    config : dict
        The configuration settings defined by workbench_config.get_config().
    entity_type : string
        One of 'node', 'media', 'taxonomy_term', or 'paragraph'.
    bundle_type : string, optional
        None for nodes (the content type can optionally be gotten from config),
        the vocabulary name, or the media type (image', 'document', 'audio',
        'video', 'file', etc.).
    Returns
    -------
    dict
        A dictionary with field names as keys and values arrays containing
        field config data. Config data varies slightly by entity type.
    """
    ping_islandora(config, print_message=False)
    field_definitions = {}

    if entity_type == "node":
        bundle_type = config["content_type"]
        fields = get_entity_fields(config, entity_type, bundle_type)
        for fieldname in fields:
            field_definitions[fieldname] = {}
            raw_field_config = get_entity_field_config(
                config, fieldname, entity_type, bundle_type
            )
            field_config = json.loads(raw_field_config)

            field_definitions[fieldname]["entity_type"] = field_config["entity_type"]
            field_definitions[fieldname]["required"] = field_config["required"]
            field_definitions[fieldname]["label"] = field_config["label"]
            raw_vocabularies = [
                x
                for x in field_config["dependencies"]["config"]
                if re.match("^taxonomy.vocabulary.", x)
            ]
            if len(raw_vocabularies) > 0:
                vocabularies = [
                    x.replace("taxonomy.vocabulary.", "") for x in raw_vocabularies
                ]
                field_definitions[fieldname]["vocabularies"] = vocabularies
            # Reference 'handler' could be nothing, 'default:taxonomy_term' (or some other entity type), or 'views'.
            if "handler" in field_config["settings"]:
                field_definitions[fieldname]["handler"] = field_config["settings"][
                    "handler"
                ]
            else:
                field_definitions[fieldname]["handler"] = None
            if "handler_settings" in field_config["settings"]:
                field_definitions[fieldname]["handler_settings"] = field_config[
                    "settings"
                ]["handler_settings"]
            else:
                field_definitions[fieldname]["handler_settings"] = None

            raw_field_storage = get_entity_field_storage(config, fieldname, entity_type)
            field_storage = json.loads(raw_field_storage)
            field_definitions[fieldname]["field_type"] = field_storage["type"]
            field_definitions[fieldname]["cardinality"] = field_storage["cardinality"]
            if "max_length" in field_storage["settings"]:
                field_definitions[fieldname]["max_length"] = field_storage["settings"][
                    "max_length"
                ]
            else:
                field_definitions[fieldname]["max_length"] = None
            if "target_type" in field_storage["settings"]:
                field_definitions[fieldname]["target_type"] = field_storage["settings"][
                    "target_type"
                ]
            else:
                field_definitions[fieldname]["target_type"] = None
            if (
                field_storage["type"] == "typed_relation"
                and "rel_types" in field_config["settings"]
            ):
                field_definitions[fieldname]["typed_relations"] = field_config[
                    "settings"
                ]["rel_types"]
            if "authority_sources" in field_config["settings"]:
                field_definitions[fieldname]["authority_sources"] = list(
                    field_config["settings"]["authority_sources"].keys()
                )
            else:
                field_definitions[fieldname]["authority_sources"] = None
            if "allowed_values" in field_storage["settings"]:
                field_definitions[fieldname]["allowed_values"] = list(
                    field_storage["settings"]["allowed_values"].keys()
                )
            else:
                field_definitions[fieldname]["allowed_values"] = None
            if field_config["field_type"].startswith("text"):
                field_definitions[fieldname]["formatted_text"] = True
            else:
                field_definitions[fieldname]["formatted_text"] = False

        # title's configuration is not returned by Drupal so we construct it here. Note: if you add a new key to
        # 'field_definitions', also add it to title's entry here. Also add it for 'title' in the other entity types, below.
        field_definitions["title"] = {
            "entity_type": "node",
            "required": True,
            "label": "Title",
            "field_type": "string",
            "cardinality": 1,
            "max_length": config["max_node_title_length"],
            "target_type": None,
            "handler": None,
            "handler_settings": None,
        }

    if entity_type == "taxonomy_term":
        fields = get_entity_fields(config, "taxonomy_term", bundle_type)
        for fieldname in fields:
            field_definitions[fieldname] = {}
            raw_field_config = get_entity_field_config(
                config, fieldname, entity_type, bundle_type
            )
            field_config = json.loads(raw_field_config)
            field_definitions[fieldname]["entity_type"] = field_config["entity_type"]
            field_definitions[fieldname]["required"] = field_config["required"]
            field_definitions[fieldname]["label"] = field_config["label"]
            raw_vocabularies = [
                x
                for x in field_config["dependencies"]["config"]
                if re.match("^taxonomy.vocabulary.", x)
            ]
            if len(raw_vocabularies) > 0:
                vocabularies = [
                    x.replace("taxonomy.vocabulary.", "") for x in raw_vocabularies
                ]
                field_definitions[fieldname]["vocabularies"] = vocabularies
            # Reference 'handler' could be nothing, 'default:taxonomy_term' (or some other entity type), or 'views'.
            if "handler" in field_config["settings"]:
                field_definitions[fieldname]["handler"] = field_config["settings"][
                    "handler"
                ]
            else:
                field_definitions[fieldname]["handler"] = None
            if "handler_settings" in field_config["settings"]:
                field_definitions[fieldname]["handler_settings"] = field_config[
                    "settings"
                ]["handler_settings"]
            else:
                field_definitions[fieldname]["handler_settings"] = None

            raw_field_storage = get_entity_field_storage(config, fieldname, entity_type)
            field_storage = json.loads(raw_field_storage)
            field_definitions[fieldname]["field_type"] = field_storage["type"]
            field_definitions[fieldname]["cardinality"] = field_storage["cardinality"]
            if "max_length" in field_storage["settings"]:
                field_definitions[fieldname]["max_length"] = field_storage["settings"][
                    "max_length"
                ]
            else:
                field_definitions[fieldname]["max_length"] = None
            if "target_type" in field_storage["settings"]:
                field_definitions[fieldname]["target_type"] = field_storage["settings"][
                    "target_type"
                ]
            else:
                field_definitions[fieldname]["target_type"] = None
            if "authority_sources" in field_config["settings"]:
                field_definitions[fieldname]["authority_sources"] = list(
                    field_config["settings"]["authority_sources"].keys()
                )
            else:
                field_definitions[fieldname]["authority_sources"] = None
            if (
                field_storage["type"] == "typed_relation"
                and "rel_types" in field_config["settings"]
            ):
                field_definitions[fieldname]["typed_relations"] = field_config[
                    "settings"
                ]["rel_types"]
            if "allowed_values" in field_storage["settings"]:
                field_definitions[fieldname]["allowed_values"] = list(
                    field_storage["settings"]["allowed_values"].keys()
                )
            else:
                field_definitions[fieldname]["allowed_values"] = None
            if field_config["field_type"].startswith("text"):
                field_definitions[fieldname]["formatted_text"] = True
            else:
                field_definitions[fieldname]["formatted_text"] = False

        field_definitions["term_name"] = {
            "entity_type": "taxonomy_term",
            "required": True,
            "label": "Name",
            "field_type": "string",
            "cardinality": 1,
            "max_length": 255,
            "target_type": None,
            "handler": None,
            "handler_settings": None,
        }

    if entity_type == "media":
        fields = get_entity_fields(config, entity_type, bundle_type)
        for fieldname in fields:
            field_definitions[fieldname] = {}
            raw_field_config = get_entity_field_config(
                config, fieldname, entity_type, bundle_type
            )
            field_config = json.loads(raw_field_config)
            field_definitions[fieldname]["media_type"] = bundle_type
            field_definitions[fieldname]["field_type"] = field_config["field_type"]
            field_definitions[fieldname]["required"] = field_config["required"]
            field_definitions[fieldname]["label"] = field_config["label"]
            raw_vocabularies = [
                x
                for x in field_config["dependencies"]["config"]
                if re.match("^taxonomy.vocabulary.", x)
            ]
            if len(raw_vocabularies) > 0:
                vocabularies = [
                    x.replace("taxonomy.vocabulary.", "") for x in raw_vocabularies
                ]
                field_definitions[fieldname]["vocabularies"] = vocabularies
            # Reference 'handler' could be nothing, 'default:taxonomy_term' (or some other entity type), or 'views'.
            if "handler" in field_config["settings"]:
                field_definitions[fieldname]["handler"] = field_config["settings"][
                    "handler"
                ]
            else:
                field_definitions[fieldname]["handler"] = None
            if "handler_settings" in field_config["settings"]:
                field_definitions[fieldname]["handler_settings"] = field_config[
                    "settings"
                ]["handler_settings"]
            else:
                field_definitions[fieldname]["handler_settings"] = None
            if "file_extensions" in field_config["settings"]:
                field_definitions[fieldname]["file_extensions"] = field_config[
                    "settings"
                ]["file_extensions"]

            raw_field_storage = get_entity_field_storage(config, fieldname, entity_type)
            field_storage = json.loads(raw_field_storage)
            field_definitions[fieldname]["field_type"] = field_storage["type"]
            field_definitions[fieldname]["cardinality"] = field_storage["cardinality"]
            if "max_length" in field_storage["settings"]:
                field_definitions[fieldname]["max_length"] = field_storage["settings"][
                    "max_length"
                ]
            else:
                field_definitions[fieldname]["max_length"] = None
            if "target_type" in field_storage["settings"]:
                field_definitions[fieldname]["target_type"] = field_storage["settings"][
                    "target_type"
                ]
            else:
                field_definitions[fieldname]["target_type"] = None
            if (
                field_storage["type"] == "typed_relation"
                and "rel_types" in field_config["settings"]
            ):
                field_definitions[fieldname]["typed_relations"] = field_config[
                    "settings"
                ]["rel_types"]
            if "authority_sources" in field_config["settings"]:
                field_definitions[fieldname]["authority_sources"] = list(
                    field_config["settings"]["authority_sources"].keys()
                )
            else:
                field_definitions[fieldname]["authority_sources"] = None
            if "allowed_values" in field_storage["settings"]:
                field_definitions[fieldname]["allowed_values"] = list(
                    field_storage["settings"]["allowed_values"].keys()
                )
            else:
                field_definitions[fieldname]["allowed_values"] = None
            if field_config["field_type"].startswith("text"):
                field_definitions[fieldname]["formatted_text"] = True
            else:
                field_definitions[fieldname]["formatted_text"] = False

        field_definitions["name"] = {
            "entity_type": "media",
            "required": True,
            "label": "Name",
            "field_type": "string",
            "cardinality": 1,
            "max_length": 255,
            "target_type": None,
            "handler": None,
            "handler_settings": None,
        }

    if entity_type == "paragraph":
        fields = get_entity_fields(config, entity_type, bundle_type)
        for fieldname in fields:
            # NOTE, WIP on #292. Code below copied from 'node' section above, may need modification.
            field_definitions[fieldname] = {}
            raw_field_config = get_entity_field_config(
                config, fieldname, entity_type, bundle_type
            )
            field_config = json.loads(raw_field_config)

            field_definitions[fieldname]["entity_type"] = field_config["entity_type"]
            field_definitions[fieldname]["required"] = field_config["required"]
            field_definitions[fieldname]["label"] = field_config["label"]
            raw_vocabularies = [
                x
                for x in field_config["dependencies"]["config"]
                if re.match("^taxonomy.vocabulary.", x)
            ]
            if len(raw_vocabularies) > 0:
                vocabularies = [
                    x.replace("taxonomy.vocabulary.", "") for x in raw_vocabularies
                ]
                field_definitions[fieldname]["vocabularies"] = vocabularies
            # Reference 'handler' could be nothing, 'default:taxonomy_term' (or some other entity type), or 'views'.
            if "handler" in field_config["settings"]:
                field_definitions[fieldname]["handler"] = field_config["settings"][
                    "handler"
                ]
            else:
                field_definitions[fieldname]["handler"] = None
            if "handler_settings" in field_config["settings"]:
                field_definitions[fieldname]["handler_settings"] = field_config[
                    "settings"
                ]["handler_settings"]
            else:
                field_definitions[fieldname]["handler_settings"] = None

            raw_field_storage = get_entity_field_storage(config, fieldname, entity_type)
            field_storage = json.loads(raw_field_storage)
            field_definitions[fieldname]["field_type"] = field_storage["type"]
            field_definitions[fieldname]["cardinality"] = field_storage["cardinality"]
            if "max_length" in field_storage["settings"]:
                field_definitions[fieldname]["max_length"] = field_storage["settings"][
                    "max_length"
                ]
            else:
                field_definitions[fieldname]["max_length"] = None
            if "target_type" in field_storage["settings"]:
                field_definitions[fieldname]["target_type"] = field_storage["settings"][
                    "target_type"
                ]
            else:
                field_definitions[fieldname]["target_type"] = None
            if (
                field_storage["type"] == "typed_relation"
                and "rel_types" in field_config["settings"]
            ):
                field_definitions[fieldname]["typed_relations"] = field_config[
                    "settings"
                ]["rel_types"]
            if "authority_sources" in field_config["settings"]:
                field_definitions[fieldname]["authority_sources"] = list(
                    field_config["settings"]["authority_sources"].keys()
                )
            else:
                field_definitions[fieldname]["authority_sources"] = None
            if "allowed_values" in field_storage["settings"]:
                field_definitions[fieldname]["allowed_values"] = list(
                    field_storage["settings"]["allowed_values"].keys()
                )
            else:
                field_definitions[fieldname]["allowed_values"] = None
            if field_config["field_type"].startswith("text"):
                field_definitions[fieldname]["formatted_text"] = True
            else:
                field_definitions[fieldname]["formatted_text"] = False

    return field_definitions


def get_entity_fields(config, entity_type, bundle_type):
    """Get all the fields configured on a bundle.

    Parameters
    ----------
    config : dict
        The configuration settings defined by workbench_config.get_config().

    entity_type : string
        Values could be 'node', 'media', 'taxonomy_term', or 'paragraph'.
    bundle_type : string

    Returns
    -------
    list
        A list with field names, e.g. ['field_name1', 'field_name2'].

    """
    if ping_content_type(config) == 404:
        message = f"Content type '{config['content_type']}' does not exist on {config['host']}."
        logging.error(message)
        sys.exit("Error: " + message)
    fields_endpoint = (
        config["host"]
        + "/entity/entity_form_display/"
        + entity_type
        + "."
        + bundle_type
        + ".default?_format=json"
    )
    bundle_type_response = issue_request(config, "GET", fields_endpoint)
    # If a vocabulary has no custom fields (like the default "Tags" vocab), this query will
    # return a 404 response. So, we need to use an alternative way to check if the vocabulary
    # really doesn't exist.
    if bundle_type_response.status_code == 404 and entity_type == "taxonomy_term":
        fallback_fields_endpoint = (
            "/entity/taxonomy_vocabulary/" + bundle_type + "?_format=json"
        )
        fallback_bundle_type_response = issue_request(
            config, "GET", fallback_fields_endpoint
        )
        # If this request confirms the vocabulary exists, its OK to make some assumptions
        # about what fields it has.
        if fallback_bundle_type_response.status_code == 200:
            return []

    fields = []
    if bundle_type_response.status_code == 200:
        node_config_raw = json.loads(bundle_type_response.text)
        fieldname_prefix = "field.field." + entity_type + "." + bundle_type + "."
        fieldnames = [
            field_dependency.replace(fieldname_prefix, "")
            for field_dependency in node_config_raw["dependencies"]["config"]
        ]
        for fieldname in node_config_raw["dependencies"]["config"]:
            fieldname_prefix = "field.field." + entity_type + "." + bundle_type + "."
            if re.match(fieldname_prefix, fieldname):
                fieldname = fieldname.replace(fieldname_prefix, "")
                fields.append(fieldname)
    else:
        message = "Workbench cannot retrieve field definitions from Drupal."
        if config["task"] == "create_terms" or config["task"] == "update_terms":
            message_detail = f" Check that the vocabulary name identified in your vocab_id config setting is spelled correctly."
        if config["task"] == "create" or config["task"] == "create_from_files":
            message_detail = f" Check that the content type named in your content_type config setting is spelled correctly."
        logging.error(
            message
            + message_detail
            + " HTTP response code was "
            + str(bundle_type_response.status_code)
            + "."
        )
        sys.exit("Error: " + message + " See the log for more information.")

    return fields


def get_required_bundle_fields(config, entity_type, bundle_type):
    """Gets a list of required fields for the given bundle type.

    Parameters
    ----------
    config : dict
        The configuration settings defined by workbench_config.get_config().
    entity_type : string
        One of 'node', 'media', or 'taxonomy_term'.
    bundle_type : string
        The (node) content type, the vocabulary name, or the media type ('image',
        'document', 'audio', 'video', 'file', etc.).

    Returns
    -------
    list
        A list of Drupal field names that are configured as required for this bundle, e.g
        ['required_field1_name', 'required_field2_name'].
    """
    field_definitions = get_field_definitions(config, entity_type, bundle_type)
    required_drupal_fields = list()
    for drupal_fieldname in field_definitions:
        if (
            "entity_type" in field_definitions[drupal_fieldname]
            and field_definitions[drupal_fieldname]["entity_type"] == entity_type
        ):
            if (
                "required" in field_definitions[drupal_fieldname]
                and field_definitions[drupal_fieldname]["required"] is True
            ):
                required_drupal_fields.append(drupal_fieldname)
    return required_drupal_fields


def get_entity_field_config(config, fieldname, entity_type, bundle_type):
    """Get a specific fields's configuration.

    Example query for taxo terms: /entity/field_config/taxonomy_term.islandora_media_use.field_external_uri?_format=json
    """
    field_config_endpoint = (
        config["host"]
        + "/entity/field_config/"
        + entity_type
        + "."
        + bundle_type
        + "."
        + fieldname
        + "?_format=json"
    )
    field_config_response = issue_request(config, "GET", field_config_endpoint)
    if field_config_response.status_code == 200:
        return field_config_response.text
    else:
        message = "Workbench cannot retrieve field definitions from Drupal. Please confirm that the Field, Field Storage, and Entity Form Display REST resources are enabled."
        logging.error(message)
        sys.exit("Error: " + message)


def get_entity_field_storage(config, fieldname, entity_type):
    """Get a specific fields's storage configuration.

    Example query for taxo terms: /entity/field_storage_config/taxonomy_term.field_external_uri?_format=json
    """
    field_storage_endpoint = (
        config["host"]
        + "/entity/field_storage_config/"
        + entity_type
        + "."
        + fieldname
        + "?_format=json"
    )
    field_storage_response = issue_request(config, "GET", field_storage_endpoint)
    if field_storage_response.status_code == 200:
        return field_storage_response.text
    else:
        message = "Workbench cannot retrieve field definitions from Drupal. Please confirm that the Field, Field Storage, and Entity Form Display REST resources are enabled."
        logging.error(message)
        sys.exit("Error: " + message)


def get_fieldname_map(config, entity_type, bundle_type, keys, die=True):
    """Get a mapping of field machine names to labels, or labels to machine names.

    Note: does not account for multilingual configurations.

     Parameters
     ----------
     config : dict
         The configuration settings defined by workbench_config.get_config().
     entity_type : string
         One of 'node', 'media', 'taxonomy_term', or 'paragraph'.
     bundle_type : string
         The node content type, the vocabulary name, or the media type
         (image', 'document', 'audio', 'video', 'file', etc.).
     keys: string
         One of 'labels' or 'names'. 'labels' returns a dictionary where the field labels are
         the keys, 'names' returns a dictionary where the field machine names are the keys.
     die: bool
         Whether or not to exit if there is a problem generating the map.
     Returns
     -------
     dict|bool
         A dictionary with either field labels or machine names as the keys.
         Returns False if the field labels are not unique.
    """
    # We delete the cached map in check_input() and in Workbench's create(), update(), and
    # create_terms() functions so the cache is always fresh.
    fieldname_map_cache_path = os.path.join(
        config["temp_dir"], f"{entity_type}-{bundle_type}-{keys}.fieldname_map"
    )
    if os.path.exists(fieldname_map_cache_path):
        cache_file = open(fieldname_map_cache_path, "r")
        cache = cache_file.read()
        cache_file.close()
        return json.loads(cache)

    field_defs = get_field_definitions(config, entity_type, bundle_type)
    map = dict()
    labels = []
    for field, properties in field_defs.items():
        labels.append(properties["label"])
        if keys == "labels":
            map[properties["label"]] = field

        if keys == "names":
            map[field] = properties["label"]

    if keys == "labels":
        duplicate_labels = [
            label for label, count in collections.Counter(labels).items() if count > 1
        ]
        if len(duplicate_labels) > 0:
            if die is True:
                message = (
                    f"Duplicate field labels exist ({', '. join(duplicate_labels)}). To continue, remove the \"csv_headers\" setting "
                    + "from your configuration file and change your CSV headers from field labels to field machine names."
                )
                logging.error(message)
                sys.exit("Error: " + message)
            else:
                return False

    cache_file = open(fieldname_map_cache_path, "w")
    cache_file.write(json.dumps(map))
    cache_file.close()

    return map


def replace_field_labels_with_names(config, csv_headers):
    """Replace field labels in a list of CSV column headers with their machine name equivalents.

    Note: we can't use this feature for add_media or update_media tasks since the fieldnames
    vary by media type, and each row in the CSV can have a different media type.

     Parameters
     ----------
     config : dict
         The configuration settings defined by workbench_config.get_config().
     csv_headers: list
         A list containing the CSV headers.
     Returns
     -------
     list
         The list of CSV headers with any labels replaced with field names.
    """
    if config["task"] == "create_terms" or config["task"] == "update_terms":
        field_map = get_fieldname_map(
            config, "taxonomy_term", config["vocab_id"], "labels"
        )
    else:
        field_map = get_fieldname_map(config, "node", config["content_type"], "labels")

    for header_index in range(len(csv_headers)):
        if csv_headers[header_index] in field_map:
            csv_headers[header_index] = field_map.get(csv_headers[header_index])

    return csv_headers


def check_input(config, args):
    """Validate the config file and input data.

    Parameters
    ----------
    config : dict
        The configuration settings defined by workbench_config.get_config().
    args: ArgumentParser
        Command-line arguments from argparse.parse_args().
    Returns
    -------
    None
        Exits if an error is encountered.
    """
    logging.info(
        'Starting configuration check for "%s" task using config file %s.',
        config["task"],
        args.config,
    )

    if "check_lock_file_path" in config:
        if os.path.exists(config["check_lock_file_path"]):
            os.remove(config["check_lock_file_path"])

    ping_islandora(config, print_message=False)
    check_integration_module_version(config)

    rows_with_missing_files = list()

    # @todo #606: break out node entity and reserved field, media entity and reserved field, and term entity and reserved fields?
    node_base_fields = [
        "title",
        "status",
        "promote",
        "sticky",
        "uid",
        "created",
        "published",
    ]
    # Any new reserved columns introduced into the CSV need to be removed here. 'langcode' is a standard Drupal field
    # but it doesn't show up in any field configs.
    reserved_fields = [
        "file",
        "directory",
        "media_use_tid",
        "checksum",
        "node_id",
        "url_alias",
        "image_alt_text",
        "parent_id",
        "langcode",
        "revision_log",
    ]
    entity_fields = get_entity_fields(config, "node", config["content_type"])
    if config["id_field"] not in entity_fields:
        reserved_fields.append(config["id_field"])

    # Check the config file.
    tasks = [
        "create",
        "update",
        "delete",
        "add_media",
        "update_media",
        "delete_media",
        "delete_media_by_node",
        "create_from_files",
        "create_terms",
        "export_csv",
        "get_data_from_view",
        "get_media_report_from_view",
        "update_terms",
        "create_redirects",
        "add_alt_text",
        "update_alt_text",
    ]
    joiner = ", "
    if config["task"] not in tasks:
        message = (
            '"task" in your configuration file must be one of "create", "update", "delete", "add_alt_text", "update_alt_text", '
            + '"add_media", "update_media", "delete_media", "delete_media_by_node", "create_from_files", "create_terms", "export_csv", "get_data_from_view", "update_terms", or "create_redirects".'
        )
        logging.error(message)
        sys.exit("Error: " + message)

    config_keys = list(config.keys())
    config_keys.remove("check")

    if config["task"] in ["create", "create_from_files"]:
        if config["csv_id_to_node_id_map_dir"] == config["temp_dir"]:
            message = f'You should set your "csv_id_to_node_id_map_dir" config setting to a location other than your system\'s temporary directory.'
            print("Warning: " + message)
            logging.warning(message)
        if (
            config["recovery_mode_starting_from_node_id"] is not False
            and value_is_numeric(config["recovery_mode_starting_from_node_id"]) is True
        ):
            message = f'"recovery_mode" option in effect. Items that have already been ingested with node IDs starting at {config["recovery_mode_starting_from_node_id"]} will be skipped.'
            print(message)
            logging.info(message)

        # Check to see if there are any "host" column values in the CSV ID to node ID map that
        # aren't empty or the current config["host"] value.
        check_for_parent_csv_data = get_csv_data(config)
        check_for_parent_csv_headers = check_for_parent_csv_data.fieldnames
        # This is the set of conditions where the map is queried to get parent node IDs. AFAIK it's
        # complete but if others come up, they should be added here.
        if (
            len(config["csv_id_to_node_id_map_allowed_hosts"]) > 0
            or (os.environ.get("ISLANDORA_WORKBENCH_SECONDARY_TASKS") is not None)
            or (
                "parent_id" in check_for_parent_csv_headers
                and config["query_csv_id_to_node_id_map_for_parents"] is True
            )
            or (
                config["recovery_mode_starting_from_node_id"] is not False
                and value_is_numeric(config["recovery_mode_starting_from_node_id"])
                is True
            )
        ):
            csv_to_node_id_map_path = config["csv_id_to_node_id_map_path"]
            current_host = config["host"]

            check_for_host_column_result = sqlite_manager(
                config,
                operation="select",
                db_file_path=csv_to_node_id_map_path,
                query="select * from pragma_table_info(?)",
                values=("csv_id_to_node_id_map",),
            )
            if check_for_host_column_result[-1][1] == "host":
                num_unique_hosts_result = sqlite_manager(
                    config,
                    operation="select",
                    db_file_path=csv_to_node_id_map_path,
                    query="select distinct host from csv_id_to_node_id_map",
                )

                unique_host_values = list()
                for unique_host in num_unique_hosts_result:
                    if unique_host[0] is None or unique_host[0] == "":
                        unique_host_values.append("")
                    else:
                        unique_host_values.append(unique_host[0])

                if "" in unique_host_values:
                    unique_host_values.remove("")
                if current_host in unique_host_values:
                    unique_host_values.remove(current_host)
                list_of_hosts = ", ".join(unique_host_values).strip()
                if len(unique_host_values) > 0:
                    multiple_hosts_in_map_log_message = (
                        'There are values for the "host" column in the CSV ID to node ID map '
                        + f'at "{csv_to_node_id_map_path}" other than "" (empty) and your currently configured host ("{current_host}"). '
                        + f"Those extra hosts are {list_of_hosts}. Please see https://mjordan.github.io/islandora_workbench_docs/csv_id_to_node_id_map/"
                        + " for advice on what to do."
                    )
                    logging.warning(multiple_hosts_in_map_log_message)
                    multiple_hosts_in_map_console_message = (
                        'There are values for the "host" column in the CSV ID to node ID map '
                        + f'at "{csv_to_node_id_map_path}" other than your current "host" configuration setting. Please see your workbench log for more information.'
                    )
                    print("Warning: " + multiple_hosts_in_map_console_message)
                else:
                    logging.info(
                        'No unexpected values in the CSV ID to node ID map\'s "host" column.'
                    )

    # Check for presence of required config keys, which varies by task.
    if config["task"] == "create":
        if config["nodes_only"] is True:
            message = '"nodes_only" option in effect. Media files will not be checked/validated.'
            print(message)
            logging.info(message)
        create_required_options = ["task", "host", "username", "password"]
        for create_required_option in create_required_options:
            if create_required_option not in config_keys:
                message = (
                    "Please check your config file for required values: "
                    + joiner.join(create_required_options)
                    + "."
                )
                logging.error(message)
                sys.exit("Error: " + message)
    if config["task"] == "update":
        update_required_options = ["task", "host", "username", "password"]
        for update_required_option in update_required_options:
            if update_required_option not in config_keys:
                message = (
                    "Please check your config file for required values: "
                    + joiner.join(update_required_options)
                    + "."
                )
                logging.error(message)
                sys.exit("Error: " + message)
        update_mode_options = ["replace", "append", "delete"]
        if config["update_mode"] not in update_mode_options:
            message = (
                'Your "update_mode" config option must be one of the following: '
                + joiner.join(update_mode_options)
                + "."
            )
            logging.error(message)
            sys.exit("Error: " + message)
    if config["task"] == "delete":
        delete_required_options = ["task", "host", "username", "password"]
        for delete_required_option in delete_required_options:
            if delete_required_option not in config_keys:
                message = (
                    "Please check your config file for required values: "
                    + joiner.join(delete_required_options)
                    + "."
                )
                logging.error(message)
                sys.exit("Error: " + message)
    if config["task"] == "add_media":
        add_media_required_options = [
            "task",
            "host",
            "username",
            "password",
            "media_type",
        ]
        for add_media_required_option in add_media_required_options:
            if add_media_required_option not in config_keys:
                message = (
                    "Please check your config file for required values: "
                    + joiner.join(add_media_required_options)
                    + "."
                )
                logging.error(message)
                sys.exit("Error: " + message)
    if config["task"] == "update_media":
        update_media_required_options = [
            "task",
            "host",
            "username",
            "password",
            "input_csv",
            "media_type",
        ]
        for update_media_required_option in update_media_required_options:
            if update_media_required_option not in config_keys:
                message = (
                    "Please check your config file for required values: "
                    + joiner.join(update_media_required_options)
                    + "."
                )
                logging.error(message)
                sys.exit("Error: " + message)
        update_mode_options = ["replace", "append", "delete"]
        if config["update_mode"] not in update_mode_options:
            message = (
                'Your "update_mode" config option must be one of the following: '
                + joiner.join(update_mode_options)
                + "."
            )
            logging.error(message)
            sys.exit("Error: " + message)
    if config["task"] == "delete_media":
        delete_media_required_options = ["task", "host", "username", "password"]
        for delete_media_required_option in delete_media_required_options:
            if delete_media_required_option not in config_keys:
                message = (
                    "Please check your config file for required values: "
                    + joiner.join(delete_media_required_options)
                    + "."
                )
                logging.error(message)
                sys.exit("Error: " + message)
    if config["task"] == "delete_media_by_node":
        delete_media_by_node_required_options = ["task", "host", "username", "password"]
        for (
            delete_media_by_node_required_option
        ) in delete_media_by_node_required_options:
            if delete_media_by_node_required_option not in config_keys:
                message = (
                    "Please check your config file for required values: "
                    + joiner.join(delete_media_by_node_required_options)
                    + "."
                )
                logging.error(message)
                sys.exit("Error: " + message)
    if config["task"] == "export_csv":
        export_csv_required_options = ["task", "host", "username", "password"]
        for export_csv_required_option in export_csv_required_options:
            if export_csv_required_option not in config_keys:
                message = (
                    "Please check your config file for required values: "
                    + joiner.join(export_csv_required_options)
                    + "."
                )
                logging.error(message)
                sys.exit("Error: " + message)
        if config["export_csv_term_mode"] == "name":
            message = 'The "export_csv_term_mode" configuration option is set to "name", which will slow down the export.'
            print(message)
    if config["task"] == "create_terms":
        create_terms_required_options = [
            "task",
            "host",
            "username",
            "password",
            "vocab_id",
        ]
        for create_terms_required_option in create_terms_required_options:
            if create_terms_required_option not in config_keys:
                message = (
                    "Please check your config file for required values: "
                    + joiner.join(create_terms_required_options)
                    + "."
                )
                logging.error(message)
                sys.exit("Error: " + message)
    if (
        config["task"] == "get_data_from_view"
        or config["task"] == "get_media_report_from_view"
    ):
        get_data_from_view_required_options = [
            "task",
            "host",
            "username",
            "password",
            "view_path",
        ]
        for get_data_from_view_required_option in get_data_from_view_required_options:
            if get_data_from_view_required_option not in config_keys:
                message = (
                    "Please check your config file for required values: "
                    + joiner.join(get_data_from_view_required_options)
                    + "."
                )
                logging.error(message)
                sys.exit("Error: " + message)
    if config["task"] == "update_terms":
        update_terms_required_options = [
            "task",
            "host",
            "username",
            "password",
            "vocab_id",
        ]
        for update_terms_required_option in update_terms_required_options:
            if update_terms_required_option not in config_keys:
                message = (
                    "Please check your config file for required values: "
                    + joiner.join(update_terms_required_options)
                    + "."
                )
                logging.error(message)
                sys.exit("Error: " + message)

    message = "OK, configuration file has all required values (did not check for optional values)."
    print(message)
    logging.info(message)

    # Check that the rollback configuration file and CSV file directories exist and are writable.
    if config["task"] in ["create", "create_from_files"]:
        check_rollback_file_path_directories(config)

    create_temp_dir(config)

    # Perform checks on get_data_from_view tasks. Since this task doesn't use input_dir, input_csv, etc.,
    # we exit immediately after doing these checks.
    if (
        config["task"] == "get_data_from_view"
        or config["task"] == "get_media_report_from_view"
    ):
        # First, ping the View.
        view_parameters = (
            "&".join(config["view_parameters"]) if "view_parameters" in config else ""
        )
        view_url = (
            config["host"]
            + "/"
            + config["view_path"].lstrip("/")
            + "?page=0&"
            + view_parameters
        )

        view_path_status_code = ping_view_endpoint(config, view_url)
        view_url_for_message = config["host"] + "/" + config["view_path"].lstrip("/")
        if view_path_status_code != 200:
            message = f"Cannot access View at {view_url_for_message}."
            logging.error(message)
            sys.exit("Error: " + message)
        else:
            message = f'View REST export at "{view_url_for_message}" is accessible.'
            logging.info(message)
            print("OK, " + message)

        if config["export_file_directory"] is not None:
            if not os.path.exists(config["export_file_directory"]):
                try:
                    os.mkdir(config["export_file_directory"])
                    os.rmdir(config["export_file_directory"])
                except Exception as e:
                    message = (
                        'Path in configuration option "export_file_directory" ("'
                        + config["export_file_directory"]
                        + '") is not writable.'
                    )
                    logging.error(message + " " + str(e))
                    sys.exit("Error: " + message + " See log for more detail.")

        if config["export_file_media_use_term_id"] is False:
            message = f'Unknown value for configuration setting "export_file_media_use_term_id": {config["export_file_media_use_term_id"]}.'
            logging.error(message)
            sys.exit("Error: " + message)

        # Check to make sure the output path for the CSV file is writable.
        if config["export_csv_file_path"] is not None:
            csv_file_path = config["export_csv_file_path"]
        else:
            csv_file_path = os.path.join(
                config["input_dir"],
                os.path.basename(args.config).split(".")[0]
                + ".csv_file_with_data_from_view",
            )
        csv_file_path_file = open(csv_file_path, "a")
        if csv_file_path_file.writable() is False:
            message = f'Path to CSV file "{csv_file_path}" is not writable.'
            logging.error(message)
            csv_file_path_file.close()
            sys.exit("Error: " + message)
        else:
            message = f"CSV output file location at {csv_file_path} is writable."
            logging.info(message)
            print("OK, " + message)
            csv_file_path_file.close()

        if os.path.exists(csv_file_path):
            os.remove(csv_file_path)

        # If nothing has failed by now, exit with a positive, upbeat message.
        print("Configuration and input data appear to be valid.")
        if config["perform_soft_checks"] is True:
            print(
                'Warning: "perform_soft_checks" is enabled so you need to review your log for errors despite the "OK" reports above.'
            )
        logging.info(
            'Configuration checked for "%s" task using config file "%s", no problems found.',
            config["task"],
            args.config,
        )
        sys.exit()

    validate_input_dir(config)

    check_csv_file_exists(config, "node_fields")

    # Check column headers in CSV file. Does not apply to add_media or update_media tasks (handled just below).
    csv_data = get_csv_data(config)
    if config["csv_headers"] == "labels" and config["task"] in [
        "create",
        "update",
        "create_terms",
        "update_terms",
    ]:
        if config["task"] == "create_terms" or config["task"] == "update_terms":
            fieldname_map_cache_path = os.path.join(
                config["temp_dir"],
                f"taxonomy_term-{config['vocab_id']}-labels.fieldname_map",
            )
        else:
            fieldname_map_cache_path = os.path.join(
                config["temp_dir"],
                f"node-{config['content_type']}-labels.fieldname_map",
            )
        if os.path.exists(fieldname_map_cache_path):
            os.remove(fieldname_map_cache_path)
        csv_column_headers = replace_field_labels_with_names(
            config, csv_data.fieldnames
        )
    else:
        csv_column_headers = csv_data.fieldnames

    if config["task"] in ["add_media", "update_media"]:
        field_definitions = get_field_definitions(config, "media", config["media_type"])
        base_media_fields = ["status", "uid", "langcode"]
        drupal_fieldnames = []
        for drupal_fieldname in field_definitions:
            drupal_fieldnames.append(drupal_fieldname)

        for csv_column_header in csv_column_headers:
            if (
                csv_column_header not in drupal_fieldnames
                and csv_column_header != "media_id"
                and csv_column_header != "file"
                and csv_column_header != "node_id"
                and csv_column_header not in base_media_fields
                and csv_column_header not in get_additional_files_config(config).keys()
            ):
                logging.error(
                    'CSV column header "%s" does not match any Drupal field names in the "%s" media type',
                    csv_column_header,
                    config["media_type"],
                )
                sys.exit(
                    'Error: CSV column header "'
                    + csv_column_header
                    + '" does not match any Drupal field names in the "'
                    + config["media_type"]
                    + '" media type.'
                )
        message = "OK, CSV column headers match Drupal field names."
        print(message)
        logging.info(message)

    # Check whether each row contains the same number of columns as there are headers.
    row_count = 0
    for row_count, row in enumerate(csv_data, start=1):
        extra_headers = False
        field_count = 0
        for field in row:
            # 'stringtopopulateextrafields' is added by get_csv_data() if there are extra headers.
            if row[field] == "stringtopopulateextrafields":
                extra_headers = True
            else:
                field_count += 1
        if extra_headers is True:
            message = (
                "Row "
                + str(row_count)
                + " (ID "
                + row[config["id_field"]]
                + ") of the CSV file has fewer columns "
                + "than there are headers ("
                + str(len(csv_column_headers))
                + ")."
            )
            logging.error(message)
            sys.exit("Error: " + message)
        # Note: this message is also generated in get_csv_data() since CSV Writer thows an exception if the row has form fields than headers.
        if len(csv_column_headers) < field_count:
            message = (
                "Row "
                + str(row_count)
                + " (ID "
                + row[config["id_field"]]
                + ") of the CSV file has more columns ("
                + str(field_count)
                + ") than there are headers ("
                + str(len(csv_column_headers))
                + ")."
            )
            logging.error(message)
            sys.exit("Error: " + message)
    if row_count == 0:
        message = "Input CSV file " + config["input_csv"] + " has 0 rows."
        logging.error(message)
        sys.exit("Error: " + message)
    else:
        message = (
            "OK, all "
            + str(row_count)
            + " rows in the CSV file have the same number of columns as there are headers ("
            + str(len(csv_column_headers))
            + ")."
        )
        print(message)
        logging.info(message)

    # Check existence of input data zip archives.
    if len(config["input_data_zip_archives"]) > 0:
        for input_data_zip_archive_location in config["input_data_zip_archives"]:
            if input_data_zip_archive_location.lower().startswith("http"):
                remote_zip_archive_ping_response_code = ping_remote_file(
                    config, input_data_zip_archive_location
                )
                if remote_zip_archive_ping_response_code != 200:
                    message = f'Remote input data zip archive "{input_data_zip_archive_location}" not found, ping returned a {remote_zip_archive_ping_response_code} response.'
                    print("Warning: " + message)
                    logging.warning(message)
            else:
                if os.path.exists(input_data_zip_archive_location):
                    message = f'Local input data zip archive "{input_data_zip_archive_location}" found.'
                    print("Ok, " + message)
                    logging.info(message)
                else:
                    message = f'Local input data zip archive "{input_data_zip_archive_location}" not found.'
                    print("Warning: " + message)
                    logging.warning(message)

    # Task-specific CSV checks.
    langcode_was_present = False
    if config["task"] == "create":
        field_definitions = get_field_definitions(config, "node")
        if config["id_field"] not in csv_column_headers:
            message = 'For "create" tasks, your CSV file must have a column containing a unique identifier.'
            logging.error(message)
            sys.exit("Error: " + message)
        if (
            config["nodes_only"] is False
            and "file" not in csv_column_headers
            and config["paged_content_from_directories"] is False
        ):
            message = 'For "create" tasks, your CSV file must contain a "file" column.'
            logging.error(message)
            sys.exit("Error: " + message)
        if "title" not in csv_column_headers:
            message = 'For "create" tasks, your CSV file must contain a "title" column.'
            logging.error(message)
            sys.exit("Error: " + message)
        if "output_csv" in config.keys():
            if os.path.exists(config["output_csv"]):
                message = (
                    "Output CSV already exists at "
                    + config["output_csv"]
                    + ", records will be appended to it."
                )
                print(message)
                logging.info(message)
        if "url_alias" in csv_column_headers:
            validate_url_aliases_csv_data = get_csv_data(config)
            validate_url_aliases(config, validate_url_aliases_csv_data)

        # We populate the ISLANDORA_WORKBENCH_PRIMARY_TASK_EXECUTION_START_TIME environment variable here so secondary
        # tasks can access it during in validate_parent_ids_in_csv_id_to_node_id_map().
        workbench_execution_start_time = "{:%Y-%m-%d %H:%M:%S}".format(
            datetime.datetime.now()
        )
        # Assumes that only primary tasks have something in their 'secondary_tasks' config setting.
        if config["secondary_tasks"] is not None:
            os.environ["ISLANDORA_WORKBENCH_PRIMARY_TASK_EXECUTION_START_TIME"] = (
                workbench_execution_start_time
            )
        if "parent_id" in csv_column_headers:
            validate_parent_ids_precede_children_csv_data = get_csv_data(config)
            validate_parent_ids_precede_children(
                config, validate_parent_ids_precede_children_csv_data
            )
            prepare_csv_id_to_node_id_map(config)
            if config["query_csv_id_to_node_id_map_for_parents"] is True:
                validate_parent_ids_in_csv_id_to_node_id_map_csv_data = get_csv_data(
                    config
                )
                validate_parent_ids_in_csv_id_to_node_id_map(
                    config, validate_parent_ids_in_csv_id_to_node_id_map_csv_data
                )
            else:
                message = f"Only node IDs for parents created during this session will be used (not using the CSV ID to node ID map)."
                print(message)
                logging.warning(message)

        # Specific to creating aggregated content such as collections, compound objects and paged content. Currently, if 'parent_id' is present
        # in the CSV file 'field_member_of' is mandatory.
        if "parent_id" in csv_column_headers:
            if "field_weight" not in csv_column_headers:
                message = 'If you are ingesting compound objects, a "field_weight" column is required in your input CSV file.'
                logging.info(message)
            if "field_member_of" not in csv_column_headers:
                message = 'If your CSV file contains a "parent_id" column, it must also contain a "field_member_of" column (with empty values in child rows).'
                logging.error(message)
                sys.exit("Error: " + message)
        drupal_fieldnames = []
        for drupal_fieldname in field_definitions:
            drupal_fieldnames.append(drupal_fieldname)

        if len(drupal_fieldnames) == 0:
            message = "Workbench cannot retrieve field definitions from Drupal. Please confirm that the Field, Field Storage, and Entity Form Display REST resources are enabled."
            logging.error(message)
            sys.exit("Error: " + message)

        if config["list_missing_drupal_fields"] is True:
            missing_drupal_fields = []
            for csv_column_header in csv_column_headers:
                if (
                    csv_column_header not in drupal_fieldnames
                    and csv_column_header not in node_base_fields
                ):
                    if (
                        csv_column_header not in reserved_fields
                        and csv_column_header
                        not in get_additional_files_config(config).keys()
                    ):
                        if csv_column_header != config["id_field"]:
                            missing_drupal_fields.append(csv_column_header)
            if len(missing_drupal_fields) > 0:
                missing_drupal_fields_message = ", ".join(missing_drupal_fields)
                logging.error(
                    "The following header(s) require a matching Drupal field name: %s.",
                    missing_drupal_fields_message,
                )
                sys.exit(
                    "Error: The following header(s) require a matching Drupal field name: "
                    + missing_drupal_fields_message
                    + "."
                )

        # We .remove() CSV column headers for this check because they are not Drupal field names (including 'langcode').
        for reserved_field in reserved_fields:
            if reserved_field in csv_column_headers:
                csv_column_headers.remove(reserved_field)

        # langcode is a standard Drupal field but it doesn't show up in any field configs.
        if "langcode" in csv_column_headers:
            csv_column_headers.remove("langcode")
            # Set this so we can validate langcode below.
            langcode_was_present = True

        # We .remove() CSV column headers that use the 'media:video:field_foo' media track convention.
        media_track_headers = list()
        for column_header in csv_column_headers:
            if column_header.startswith("media:"):
                media_track_header_parts = column_header.split(":")
                if (
                    media_track_header_parts[1]
                    in config["media_track_file_fields"].keys()
                    and media_track_header_parts[2]
                    == config["media_track_file_fields"][media_track_header_parts[1]]
                ):
                    media_track_headers.append(column_header)
        for media_track_header in media_track_headers:
            if media_track_header in csv_column_headers:
                csv_column_headers.remove(media_track_header)

        # We also validate the structure of the media track column headers.
        for media_track_header in media_track_headers:
            media_track_header_parts = media_track_header.split(":")
            if (
                media_track_header_parts[0] != "media"
                and len(media_track_header_parts) != 3
            ):
                message = (
                    f'"{media_track_header}" is not a valide media track CSV header.'
                )
                logging.error(message)
                sys.exit("Error: " + message)

        # Check the configuration that is necessary for verifying nodes already exist in the target Drupal.
        if "node_exists_verification_view_endpoint" in config:
            node_exists_config = get_node_exists_verification_view_endpoint(config)
            if node_exists_config is not False:
                if node_exists_config[0] not in csv_column_headers:
                    message = f'CSV column identified in "node_exists_verification_view_endpoint" is not in your CSV file.'
                    logging.error(message)
                    sys.exit("Error: " + message)
                view_url = f'{config["host"]}/{node_exists_config[1].lstrip("/")}'
                view_path_status_code = ping_view_endpoint(config, view_url)
                if view_path_status_code != 200:
                    message = f'Cannot access View REST export configured in "node_exists_verification_view_endpoint" ({view_url}).'
                    logging.error(message)
                    sys.exit("Error: " + message)
                else:
                    message = f'View REST export configured in "node_exists_verification_view_endpoint" ({view_url}) is accessible. Values in the "{node_exists_config[0]}" CSV column will be used to check whether nodes already exist.'
                    logging.info(message)
                    print("OK, " + message)

        # Check for the View that is necessary for entity reference fields configured
        # as "Views: Filter by an entity reference View" (issue 452).
        for csv_column_header in csv_column_headers:
            if (
                csv_column_header in field_definitions
                and field_definitions[csv_column_header]["handler"] == "views"
            ):
                if (
                    config["require_entity_reference_views"] is True
                    and "entity_reference_view_endpoints" not in config
                ):
                    entity_reference_view_exists = ping_entity_reference_view_endpoint(
                        config,
                        csv_column_header,
                        field_definitions[csv_column_header]["handler_settings"],
                    )
                    if entity_reference_view_exists is False:
                        console_message = (
                            'Workbench cannot access the View "'
                            + field_definitions[csv_column_header]["handler_settings"][
                                "view"
                            ]["view_name"]
                            + '" required to validate values for field "'
                            + csv_column_header
                            + '". See log for more detail.'
                        )
                        log_message = (
                            'Workbench cannot access the path defined by the REST Export display "'
                            + field_definitions[csv_column_header]["handler_settings"][
                                "view"
                            ]["display_name"]
                            + '" in the View "'
                            + field_definitions[csv_column_header]["handler_settings"][
                                "view"
                            ]["view_name"]
                            + '" required to validate values for field "'
                            + csv_column_header
                            + '". Please check your Drupal Views configuration.'
                            + ' See the "Entity Reference Views fields" section of '
                            + "https://mjordan.github.io/islandora_workbench_docs/fields/#entity-reference-views-fields for more info."
                        )
                        logging.error(log_message)
                        sys.exit("Error: " + console_message)
                else:
                    message = f'Workbench will not validate values in your CSV file\'s "{csv_column_header}" column because your "require_entity_reference_views" configuration setting is "false".'
                    print("Warning: " + message)
                    logging.warning(
                        message
                        + ' See the "Entity Reference Views fields" section of '
                        + "https://mjordan.github.io/islandora_workbench_docs/fields/#entity-reference-views-fields for more info."
                    )

            if len(get_additional_files_config(config)) > 0:
                if (
                    csv_column_header not in drupal_fieldnames
                    and csv_column_header not in node_base_fields
                    and csv_column_header
                    not in get_additional_files_config(config).keys()
                ):
                    if csv_column_header in config["ignore_csv_columns"]:
                        continue
                    additional_files_entries = get_additional_files_config(config)
                    if csv_column_header in additional_files_entries.keys():
                        continue
                    logging.error(
                        'CSV column header %s does not match any Drupal, reserved, or "additional_files" field names.',
                        csv_column_header,
                    )
                    sys.exit(
                        'Error: CSV column header "'
                        + csv_column_header
                        + '" does not match any Drupal, reserved, or "additional_files" field names.'
                    )
            else:
                if (
                    csv_column_header not in drupal_fieldnames
                    and csv_column_header not in node_base_fields
                    and csv_column_header
                ):
                    if csv_column_header in config["ignore_csv_columns"]:
                        continue
                    logging.error(
                        "CSV column header %s does not match any Drupal or reserved field names.",
                        csv_column_header,
                    )
                    sys.exit(
                        'Error: CSV column header "'
                        + csv_column_header
                        + '" does not match any Drupal or reserved field names.'
                    )
        message = "OK, CSV column headers match Drupal field names."
        print(message)
        logging.info(message)

        if (
            "field_viewer_override_extensions" in config
            or "field_viewer_override_models" in config
        ):
            preprocessed_input_csv_file_path = get_preprocessed_input_csv_file_path(
                config
            )
            message = f'You should review "{preprocessed_input_csv_file_path}" to ensure that values in the "field_viewer_override" column have been correctly assigned based on your configuration settings.'
            print("Warning: " + message)
            logging.warning(message)

    # Check that Drupal fields that are required are in the 'create' task CSV file.
    if config["task"] == "create":
        required_drupal_fields_node = get_required_bundle_fields(
            config, "node", config["content_type"]
        )
        for required_drupal_field in required_drupal_fields_node:
            if required_drupal_field not in csv_column_headers:
                logging.error(
                    "Required Drupal field %s is not present in the CSV file.",
                    required_drupal_field,
                )
                sys.exit(
                    'Error: Field "'
                    + required_drupal_field
                    + '" required for content type "'
                    + config["content_type"]
                    + '" is not present in the CSV file.'
                )
        message = "OK, required Drupal fields are present in the CSV file."
        print(message)
        logging.info(message)

        validate_required_fields_have_values_csv_data = get_csv_data(config)
        # @todo: add the 'rows_with_missing_files' method of accumulating invalid values (issue 268).
        validate_required_fields_have_values(
            config,
            required_drupal_fields_node,
            validate_required_fields_have_values_csv_data,
        )

        # Validate dates in 'created' field, if present.
        # @todo: add the 'rows_with_missing_files' method of accumulating invalid values (issue 268).
        if "created" in csv_column_headers:
            validate_node_created_csv_data = get_csv_data(config)
            validate_node_created_date(config, validate_node_created_csv_data)
        # Validate user IDs in 'uid' field, if present.
        # @todo: add the 'rows_with_missing_files' method of accumulating invalid values (issue 268).
        if "uid" in csv_column_headers:
            validate_node_uid_csv_data = get_csv_data(config)
            validate_node_uid(config, validate_node_uid_csv_data)

    if config["task"] == "update":
        if "node_id" not in csv_column_headers:
            message = (
                'For "update" tasks, your CSV file must contain a "node_id" column.'
            )
            logging.error(message)
            sys.exit("Error: " + message)
        if "url_alias" in csv_column_headers:
            # @todo: add the 'rows_with_missing_files' method of accumulating invalid values (issue 268).
            validate_url_aliases_csv_data = get_csv_data(config)
            validate_url_aliases(config, validate_url_aliases_csv_data)
        field_definitions = get_field_definitions(config, "node")
        drupal_fieldnames = []
        for drupal_fieldname in field_definitions:
            drupal_fieldnames.append(drupal_fieldname)
        if "title" in csv_column_headers:
            csv_column_headers.remove("title")
        if "url_alias" in csv_column_headers:
            csv_column_headers.remove("url_alias")
        if "image_alt_text" in csv_column_headers:
            csv_column_headers.remove("image_alt_text")
        if "media_use_tid" in csv_column_headers:
            csv_column_headers.remove("media_use_tid")
        if "revision_log" in csv_column_headers:
            csv_column_headers.remove("revision_log")
        if "file" in csv_column_headers:
            message = 'Error: CSV column header "file" is not allowed in update tasks.'
            logging.error(message)
            sys.exit(message)
        if "node_id" in csv_column_headers:
            csv_column_headers.remove("node_id")

        # langcode is a standard Drupal field but it doesn't show up in any field configs.
        if "langcode" in csv_column_headers:
            csv_column_headers.remove("langcode")
            # Set this so we can validate langcode below.
            langcode_was_present = True

        for csv_column_header in csv_column_headers:
            if (
                csv_column_header not in drupal_fieldnames
                and csv_column_header not in node_base_fields
            ):
                if csv_column_header in config["ignore_csv_columns"]:
                    continue
                logging.error(
                    "CSV column header %s does not match any Drupal field names in the %s content type.",
                    csv_column_header,
                    config["content_type"],
                )
                sys.exit(
                    'Error: CSV column header "'
                    + csv_column_header
                    + '" does not match any Drupal field names in the '
                    + config["content_type"]
                    + " content type."
                )
        message = "OK, CSV column headers match Drupal field names."
        print(message)
        logging.info(message)

    # If the task is update media, check if all media_id values are valid.
    if config["task"] == "update_media":
        csv_data = get_csv_data(config)
        row_number = 1
        for row in csv_data:
            media_id = extract_media_id(config, row)
            if media_id is None:
                message = (
                    "Error: Invalid media ID in row "
                    + str(row_number)
                    + " of the CSV file."
                )
                logging.error(message)
                sys.exit(message)
            row_number += 1

    if (
        config["task"] == "add_media"
        or config["task"] == "create"
        and config["nodes_only"] is False
    ):
        # @todo: add the 'rows_with_missing_files' method of accumulating invalid values (issue 268).
        validate_media_use_tid(config)
        # @todo: add the 'rows_with_missing_files' method of accumulating invalid values (issue 268).
        validate_media_use_tid_values_csv_data = get_csv_data(config)
        # @todo: add the 'rows_with_missing_files' method of accumulating invalid values (issue 268).
        validate_media_use_tids_in_csv(config, validate_media_use_tid_values_csv_data)

        if config["fixity_algorithm"] is not None:
            allowed_algorithms = ["md5", "sha1", "sha256"]
            if config["fixity_algorithm"] not in allowed_algorithms:
                message = (
                    "Configured fixity algorithm '"
                    + config["fixity_algorithm"]
                    + "' must be one of 'md5', 'sha1', or 'sha256'."
                )
                logging.error(message)
                sys.exit("Error: " + message)

        if (
            config["validate_fixity_during_check"] is True
            and config["fixity_algorithm"] is not None
        ):
            print("Performing local checksum validation. This might take some time.")
            if "file" in csv_column_headers and "checksum" in csv_column_headers:
                # @todo: add the 'rows_with_missing_files' method of accumulating invalid values (issue 268).
                validate_checksums_csv_data = get_csv_data(config)
                if config["task"] == "add_media":
                    row_id = "node_id"
                else:
                    row_id = config["id_field"]
                checksum_validation_all_ok = True
                for checksum_validation_row_count, checksum_validation_row in enumerate(
                    validate_checksums_csv_data, start=1
                ):
                    file_path = checksum_validation_row["file"]
                    hash_from_local = get_file_hash_from_local(
                        config, file_path, config["fixity_algorithm"]
                    )
                    if "checksum" in checksum_validation_row:
                        if (
                            hash_from_local
                            == checksum_validation_row["checksum"].strip()
                        ):
                            logging.info(
                                'Local %s checksum and value in the CSV "checksum" field for file "%s" (%s) match.',
                                config["fixity_algorithm"],
                                file_path,
                                hash_from_local,
                            )
                        else:
                            checksum_validation_all_ok = False
                            logging.warning(
                                'Local %s checksum and value in the CSV "checksum" field for file "%s" (named in CSV row "%s") do not match (local: %s, CSV: %s).',
                                config["fixity_algorithm"],
                                file_path,
                                checksum_validation_row[row_id],
                                hash_from_local,
                                checksum_validation_row["checksum"],
                            )

                if checksum_validation_all_ok is True:
                    checksum_validation_message = (
                        "OK, checksum validation during complete. All checks pass."
                    )
                    logging.info(checksum_validation_message)
                    print(checksum_validation_message + " See the log for more detail.")
                else:
                    checksum_validation_message = "Not all checksum validation passed."
                    logging.warning(checksum_validation_message)
                    print(
                        "Warning: "
                        + checksum_validation_message
                        + " See the log for more detail."
                    )

    if config["task"] == "create_terms":
        # Check that all required fields are present in the CSV.
        field_definitions = get_field_definitions(
            config, "taxonomy_term", config["vocab_id"]
        )

        # Check here that all required fields are present in the CSV.
        required_fields = get_required_bundle_fields(
            config, "taxonomy_term", config["vocab_id"]
        )
        required_fields.insert(0, "term_name")
        required_fields_check_csv_data = get_csv_data(config)
        missing_fields = []
        for required_field in required_fields:
            if required_field not in required_fields_check_csv_data.fieldnames:
                missing_fields.append(required_field)
        if len(missing_fields) > 0:
            message = (
                "Required columns missing from input CSV file: "
                + joiner.join(missing_fields)
                + "."
            )
            logging.error(message)
            sys.exit("Error: " + message)

        # Validate length of 'term_name'.
        # @todo: add the 'rows_with_missing_files' method of accumulating invalid values (issue 268).
        validate_term_name_csv_data = get_csv_data(config)
        for count, row in enumerate(validate_term_name_csv_data, start=1):
            if "term_name" in row and len(row["term_name"]) > 255:
                message = (
                    "The 'term_name' column in row for term '"
                    + row["term_name"]
                    + "' of your CSV file exceeds Drupal's maximum length of 255 characters."
                )
                logging.error(message)
                sys.exit("Error: " + message)

    if config["task"] == "update_terms":
        field_definitions = get_field_definitions(
            config, "taxonomy_term", config["vocab_id"]
        )
        term_base_fields = [
            "status",
            "langcode",
            "term_name",
            "parent",
            "weight",
            "description",
            "published",
        ]
        drupal_fieldnames = []
        for drupal_fieldname in field_definitions:
            drupal_fieldnames.append(drupal_fieldname)
        """
        if "term_name" in csv_column_headers:
            csv_column_headers.remove("term_name")
        if "parent" in csv_column_headers:
            csv_column_headers.remove("parent")
        if "weight" in csv_column_headers:
            csv_column_headers.remove("weight")
        if "description" in csv_column_headers:
            csv_column_headers.remove("description")
        if "term_id" in csv_column_headers:
            csv_column_headers.remove("term_id")
        """

        for csv_column_header in csv_column_headers:
            if (
                csv_column_header not in drupal_fieldnames
                and csv_column_header != "term_id"
                and csv_column_header not in term_base_fields
            ):
                message = f'CSV column header "{csv_column_header}" does not match any Drupal field names in the {config["vocab_id"]} vocabulary.'
                logging.error(message)
                sys.exit("Error: " + message)
        message = "OK, CSV column headers match Drupal field names."
        print(message)
        logging.info(message)

        # Validate length of 'term_name'.
        # @todo: add the 'rows_with_missing_files' method of accumulating invalid values (issue 268).
        validate_term_name_csv_data = get_csv_data(config)
        for count, row in enumerate(validate_term_name_csv_data, start=1):
            if "term_name" in row and len(row["term_name"]) > 255:
                message = (
                    "The 'term_name' column in row for term '"
                    + row["term_name"]
                    + "' of your CSV file exceeds Drupal's maximum length of 255 characters."
                )
                logging.error(message)
                sys.exit("Error: " + message)

    if config["task"] in ["add_alt_text", "update_alt_text"]:
        _alt_text_required_options = ["task", "host", "username", "password"]
        for _alt_text_required_options in _alt_text_required_options:
            if _alt_text_required_options not in config_keys:
                message = (
                    "Please check your config file for required values: "
                    + joiner.join(delete_media_required_options)
                    + "."
                )
                logging.error(message)
                sys.exit("Error: " + message)
        update_mode_options = ["replace", "append", "delete"]
        if config["update_mode"] not in update_mode_options:
            message = (
                'Your "update_mode" config option must be one of the following: '
                + joiner.join(update_mode_options)
                + "."
            )
            logging.error(message)
            sys.exit("Error: " + message)

        validate_alt_text_csv_data = get_csv_data(config)
        row_counter = 0
        for count, row in enumerate(validate_alt_text_csv_data, start=1):
            row_counter += 1
            if len(row["node_id"]) > 0:
                node_id = row["node_id"]
                parent_node_exists = ping_node(config, row["node_id"], warn=False)
                if parent_node_exists is False:
                    message = f'Node identified in "node_id" ({node_id}) in row "{row_counter}" of your input CSV cannot be found or accessed.'
                    logging.error(message)
                    sys.exit(
                        "Error: " + message + " See Workbench log for more information."
                    )
            else:
                message = f"Row {row_counter} in your input CSV file is empty."
                logging.error(message)
                sys.exit(
                    "Error: " + message + " See Workbench log for more information."
                )

            if len(row["image_alt_text"]) > config["max_image_alt_text_length"]:
                image_alt_text = row["image_alt_text"]
                max_alt_text_length = config["max_image_alt_text_length"]
                node_id = row["node_id"]
                message = f"Alt text in input CSV row with node ID {node_id} is longer than the maximum configured alt text length ({max_alt_text_length})"
                logging.warning(
                    message
                    + f" (length is {len(image_alt_text)} characters). This row will be skipped."
                )
                print("Warning: " + message + ". See log for more information.")

    if config["task"] == "create":
        validate_alt_text_csv_data = get_csv_data(config)
        row_counter = 0
        for count, row in enumerate(validate_alt_text_csv_data, start=1):
            row_counter += 1
            if "image_alt_text" in row:
                if len(row["image_alt_text"]) > config["max_image_alt_text_length"]:
                    image_alt_text = row["image_alt_text"]
                    max_alt_text_length = config["max_image_alt_text_length"]
                    node_id = row[config["id_field"]]
                    message = f"Alt text in input CSV row with node ID {node_id} is longer than the maximum configured alt text length ({max_alt_text_length})"
                    logging.warning(
                        message
                        + f" (length is {len(image_alt_text)} characters). Adding the alt text in this row will be skipped."
                    )
                    print("Warning: " + message + ". See log for more information.")

    if config["task"] == "create_terms" or config["task"] == "update_terms":
        # Check that all required fields are present in the CSV.
        field_definitions = get_field_definitions(
            config, "taxonomy_term", config["vocab_id"]
        )
        validate_geolocation_values_csv_data = get_csv_data(config)
        # @todo: add the 'rows_with_missing_files' method of accumulating invalid values (issue 268).
        validate_geolocation_fields(
            config, field_definitions, validate_geolocation_values_csv_data
        )

        validate_link_values_csv_data = get_csv_data(config)
        # @todo: add the 'rows_with_missing_files' method of accumulating invalid values (issue 268).
        validate_link_fields(config, field_definitions, validate_link_values_csv_data)

        validate_authority_link_values_csv_data = get_csv_data(config)
        # @todo: add the 'rows_with_missing_files' method of accumulating invalid values (issue 268).
        validate_authority_link_fields(
            config, field_definitions, validate_authority_link_values_csv_data
        )

        validate_edtf_values_csv_data = get_csv_data(config)
        # @todo: add the 'rows_with_missing_files' method of accumulating invalid values (issue 268).
        validate_edtf_fields(config, field_definitions, validate_edtf_values_csv_data)

        validate_csv_field_cardinality_csv_data = get_csv_data(config)
        # @todo: add the 'rows_with_missing_files' method of accumulating invalid values (issue 268).
        validate_csv_field_cardinality(
            config, field_definitions, validate_csv_field_cardinality_csv_data
        )

        validate_csv_field_length_csv_data = get_csv_data(config)
        # @todo: add the 'rows_with_missing_files' method of accumulating invalid values (issue 268).
        validate_csv_field_length(
            config, field_definitions, validate_csv_field_length_csv_data
        )

        validate_taxonomy_field_csv_data = get_csv_data(config)
        # @todo: add the 'rows_with_missing_files' method of accumulating invalid values (issue 268).
        warn_user_about_taxo_terms = validate_taxonomy_field_values(
            config, field_definitions, validate_taxonomy_field_csv_data
        )
        if warn_user_about_taxo_terms is True:
            print(
                "Warning: Issues detected with validating taxonomy field values in the CSV file. See the log for more detail."
            )

        validate_typed_relation_csv_data = get_csv_data(config)
        # @todo: add the 'rows_with_missing_files' method of accumulating invalid values (issue 268).
        warn_user_about_typed_relation_terms = validate_typed_relation_field_values(
            config, field_definitions, validate_typed_relation_csv_data
        )
        if warn_user_about_typed_relation_terms is True:
            print(
                "Warning: Issues detected with validating typed relation field values in the CSV file. See the log for more detail."
            )

    if config["task"] == "update" or config["task"] == "create":
        field_definitions = get_field_definitions(config, "node")
        validate_geolocation_values_csv_data = get_csv_data(config)
        # @todo: add the 'rows_with_missing_files' method of accumulating invalid values (issue 268).
        validate_geolocation_fields(
            config, field_definitions, validate_geolocation_values_csv_data
        )

        validate_link_values_csv_data = get_csv_data(config)
        # @todo: add the 'rows_with_missing_files' method of accumulating invalid values (issue 268).
        validate_link_fields(config, field_definitions, validate_link_values_csv_data)

        validate_authority_link_values_csv_data = get_csv_data(config)
        # @todo: add the 'rows_with_missing_files' method of accumulating invalid values (issue 268).
        validate_authority_link_fields(
            config, field_definitions, validate_authority_link_values_csv_data
        )

        validate_edtf_values_csv_data = get_csv_data(config)
        # @todo: add the 'rows_with_missing_files' method of accumulating invalid values (issue 268).
        validate_edtf_fields(config, field_definitions, validate_edtf_values_csv_data)

        validate_csv_field_cardinality_csv_data = get_csv_data(config)
        # @todo: add the 'rows_with_missing_files' method of accumulating invalid values (issue 268).
        validate_csv_field_cardinality(
            config, field_definitions, validate_csv_field_cardinality_csv_data
        )

        validate_csv_field_length_csv_data = get_csv_data(config)
        # @todo: add the 'rows_with_missing_files' method of accumulating invalid values (issue 268).
        validate_csv_field_length(
            config, field_definitions, validate_csv_field_length_csv_data
        )

        validate_text_list_fields_data = get_csv_data(config)
        # @todo: add the 'rows_with_missing_files' method of accumulating invalid values (issue 268).
        validate_text_list_fields(
            config, field_definitions, validate_text_list_fields_data
        )

        validate_taxonomy_field_csv_data = get_csv_data(config)
        # @todo: add the 'rows_with_missing_files' method of accumulating invalid values (issue 268).
        warn_user_about_taxo_terms = validate_taxonomy_field_values(
            config, field_definitions, validate_taxonomy_field_csv_data
        )
        if warn_user_about_taxo_terms is True:
            print(
                "Warning: Issues detected with validating taxonomy field values in the CSV file. See the log for more detail."
            )

        validate_typed_relation_csv_data = get_csv_data(config)
        # @todo: add the 'rows_with_missing_files' method of accumulating invalid values (issue 268).
        warn_user_about_typed_relation_terms = validate_typed_relation_field_values(
            config, field_definitions, validate_typed_relation_csv_data
        )
        if warn_user_about_typed_relation_terms is True:
            print(
                "Warning: Issues detected with validating typed relation field values in the CSV file. See the log for more detail."
            )

        validate_numeric_fields_data = get_csv_data(config)
        # @todo: add the 'rows_with_missing_files' method of accumulating invalid values (issue 268).
        validate_numeric_fields(config, field_definitions, validate_numeric_fields_data)

        validate_media_track_csv_data = get_csv_data(config)
        # @todo: add the 'rows_with_missing_files' method of accumulating invalid values (issue 268).
        validate_media_track_fields(config, validate_media_track_csv_data)

        # Validate existence of nodes specified in 'field_member_of'. This could be generalized out to validate node IDs in other fields.
        # See https://github.com/mjordan/islandora_workbench/issues/90.
        # @todo: add the 'rows_with_missing_files' method of accumulating invalid values (issue 268).
        if config["validate_parent_node_exists"] is True:
            validate_field_member_of_csv_data = get_csv_data(config)
            for count, row in enumerate(validate_field_member_of_csv_data, start=1):
                if "field_member_of" in csv_column_headers:
                    parent_nids = row["field_member_of"].split(config["subdelimiter"])
                    for parent_nid in parent_nids:
                        if len(parent_nid) > 0:
                            parent_node_exists = ping_node(
                                config, parent_nid, warn=False
                            )
                            if parent_node_exists is False:
                                message = (
                                    "The 'field_member_of' field in row with ID '"
                                    + row[config["id_field"]]
                                    + "' of your CSV file contains a node ID ("
                                    + parent_nid
                                    + ") that "
                                    + "doesn't exist or is not accessible. See the workbench log for more information."
                                )
                                message = f'Node identified in "field_member_of" ({parent_nid}) in row with ID "{row[config["id_field"]]}" cannot be found or accessed.'
                                logging.error(message)
                                sys.exit(
                                    "Error: "
                                    + message
                                    + " See Workbench log for more information."
                                )
        else:
            message = (
                '"validate_parent_node_exists" is set to false. Node IDs in "field_member_of" that do not exist or are not accessible '
                + 'will result in 422 errors in "create" and "update" tasks.'
            )
            logging.warning(message)

        # Check the configuration that is necessary for enabling use of term names in Entity Reference Views fields.
        if "entity_reference_view_endpoints" in config:
            entity_reference_view_endpoints = get_entity_reference_view_endpoints(
                config
            )
            for (
                entity_reference_view_field_name,
                entity_reference_view_endpoint,
            ) in entity_reference_view_endpoints.items():
                if entity_reference_view_field_name not in csv_column_headers:
                    message = f'CSV column {entity_reference_view_field_name} identified in "entity_reference_view_endpoints" is not in your CSV file.'
                    logging.error(message)
                    sys.exit("Error: " + message)
                view_url = (
                    f'{config["host"]}/{entity_reference_view_endpoint.lstrip("/")}'
                )
                view_path_status_code = ping_view_endpoint(config, view_url)
                if view_path_status_code != 200:
                    message = f'Cannot access View REST export configured in "entity_reference_view_endpoints" ({view_url}).'
                    logging.error(message)
                    sys.exit("Error: " + message)
                else:
                    message = f'View REST export configured in "entity_reference_view_endpoints" ({view_url}) is accessible.'
                    logging.info(message)
                    print("OK, " + message)

        # Validate 'langcode' values if that field exists in the CSV.
        # @todo: add the 'rows_with_missing_files' method of accumulating invalid values (issue 268).
        if langcode_was_present:
            validate_langcode_csv_data = get_csv_data(config)
            for count, row in enumerate(validate_langcode_csv_data, start=1):
                langcode_valid = validate_language_code(row["langcode"])
                if not langcode_valid:
                    message = (
                        "Row with ID "
                        + row[config["id_field"]]
                        + " of your CSV file contains an invalid Drupal language code ("
                        + row["langcode"]
                        + ") in its 'langcode' column."
                    )
                    logging.error(message)
                    sys.exit("Error: " + message)

    if config["task"] == "delete":
        if "node_id" not in csv_column_headers:
            message = (
                'For "delete" tasks, your CSV file must contain a "node_id" column.'
            )
            logging.error(message)
            sys.exit("Error: " + message)
    if config["task"] == "add_media":
        if "node_id" not in csv_column_headers:
            message = (
                'For "add_media" tasks, your CSV file must contain a "node_id" column.'
            )
            logging.error(message)
            sys.exit("Error: " + message)
        if "file" not in csv_column_headers:
            message = (
                'For "add_media" tasks, your CSV file must contain a "file" column.'
            )
            logging.error(message)
            sys.exit("Error: " + message)
    if config["task"] == "update_media":
        if "media_id" not in csv_column_headers:
            message = 'For "update_media" tasks, your CSV file must contain a "media_id" column.'
            logging.error(message)
            sys.exit("Error: " + message)
    if config["task"] == "delete_media":
        if "media_id" not in csv_column_headers:
            message = 'For "delete_media" tasks, your CSV file must contain a "media_id" column.'
            logging.error(message)
            sys.exit("Error: " + message)
    if config["task"] == "delete_media_by_node":
        if "node_id" not in csv_column_headers:
            message = 'For "delete_media_by_node" tasks, your CSV file must contain a "node_id" column.'
            logging.error(message)
            sys.exit("Error: " + message)
    if config["task"] == "update_terms":
        if "term_id" not in csv_column_headers:
            message = 'For "update_terms" tasks, your CSV file must contain a "term_id" column.'
            logging.error(message)
            sys.exit("Error: " + message)
    if config["task"] == "create_redirects":
        if "redirect_source" not in csv_column_headers:
            message = 'For "create_redirects" tasks, your CSV file must contain a "redirect_source" column.'
            logging.error(message)
            sys.exit("Error: " + message)
        if "redirect_target" not in csv_column_headers:
            message = 'For "create_redirects" tasks, your CSV file must contain a "redirect_target" column.'
            logging.error(message)
            sys.exit("Error: " + message)
    if config["task"] in ["add_alt_text", "update_alt_text"]:
        if "node_id" not in csv_column_headers:
            t = config["task"]
            message = f'For "{t}" tasks, your CSV file must contain a "node_id" column.'
            logging.error(message)
            sys.exit("Error: " + message)
        if "image_alt_text" not in csv_column_headers:
            message = f'For "{t}" tasks, your CSV file must contain a "image_alt_text" column.'
            logging.error(message)
            sys.exit("Error: " + message)

    warnings_about_redirect_input_csv = False
    if config["task"] == "create_redirects":
        # Ping /entity/redirect and expect a 405 response.
        endpoint_ping_response = requests.head(
            config["host"].rstrip("/") + "/entity/redirect?_format=json",
            allow_redirects=True,
            verify=config["secure_ssl_only"],
            auth=(config["username"], config["password"]),
        )
        if endpoint_ping_response.status_code != 405:
            message = (
                'Cannot access "'
                + config["host"].rstrip("/")
                + "/entity/redirect"
                + '". Please confirm that the "Redirect" REST endpoint is configured properly.'
            )
            logging.error(message)
            sys.exit("Error: " + message)

        check_for_redirects_csv_data = get_csv_data(config)
        for count, row in enumerate(check_for_redirects_csv_data, start=1):
            if len(row["redirect_source"].strip()) == 0:
                message = f"Redirect source value in input CSV row {count} is empty. Redirect will not be created."
                logging.warning(message)
                warnings_about_redirect_input_csv = True
                continue

            if len(row["redirect_target"].strip()) == 0:
                message = f"Redirect target value in input CSV row {count} is empty. Redirect will not be created."
                logging.warning(message)
                warnings_about_redirect_input_csv = True
                continue

            if row["redirect_source"].lower().startswith("http"):
                message = (
                    'Redirect source values cannot contain a hostname, they must be a path only, without a hostname. Please correct "'
                    + row["redirect_source"]
                    + " (row "
                    + str(count)
                    + ")."
                )
                logging.warning(message)
                warnings_about_redirect_input_csv = True
                continue

            # Check to see if the redirect source value is already a redirect. We don't use issue_request()
            # since we don't want to override config["allow_redirects"] for this one request.
            is_redirect_url = config["host"].rstrip("/") + "/" + row["redirect_source"]
            is_redirect_response = requests.head(
                is_redirect_url,
                allow_redirects=False,
                verify=config["secure_ssl_only"],
                auth=(config["username"], config["password"]),
            )
            if str(is_redirect_response.status_code).startswith("30"):
                message = (
                    'Redirect source path "'
                    + row["redirect_source"].strip()
                    + '" (row '
                    + str(count)
                    + ') is already a redirect to "'
                    + is_redirect_response.headers["Location"]
                    + '" (HTTP response code is '
                    + str(is_redirect_response.status_code)
                    + ")."
                )
                logging.warning(message)
                warnings_about_redirect_input_csv = True
                continue

            # Log whether the source path exists. We don't use issue_request() since we
            # don't want to override config["allow_redirects"] for this one request.
            path_exists_url = config["host"].rstrip("/") + "/" + row["redirect_source"]
            path_exists_response = requests.head(
                path_exists_url,
                allow_redirects=False,
                verify=config["secure_ssl_only"],
                auth=(config["username"], config["password"]),
            )
            if path_exists_response.status_code == 404:
                message = (
                    'Redirect source path "'
                    + row["redirect_source"].strip()
                    + '" (row '
                    + str(count)
                    + ") does not exist (HTTP response code is "
                    + str(path_exists_response.status_code)
                    + ") so is available as a redirect."
                )
                logging.info(message)
                continue
            else:
                # We've already tested for 3xx responses, so assume that the path exists.
                message = (
                    'Redirect source path "'
                    + row["redirect_source"].strip()
                    + '" (row '
                    + str(count)
                    + ") already exists."
                )
                logging.warning(message)
                warnings_about_redirect_input_csv = True
                continue

        if warnings_about_redirect_input_csv is True:
            message = (
                "Input CSV contains at least one row that has generated a warning."
            )
            print("Warning: " + message + " See the log for details.")

    # Check for existence of files listed in the 'file' column.
    if (
        config["task"] == "create"
        or config["task"] == "add_media"
        or config["task"] == "update_media"
        and "file" in csv_column_headers
    ):
        if (
            config["nodes_only"] is False
            and config["paged_content_from_directories"] is False
        ):
            # Temporary fix for https://github.com/mjordan/islandora_workbench/issues/478.
            if config["task"] == "add_media":
                config["id_field"] = "node_id"
            if config["task"] == "update_media":
                config["id_field"] = "media_id"

            file_check_csv_data = get_csv_data(config)
            for count, file_check_row in enumerate(file_check_csv_data, start=1):
                file_check_row["file"] = file_check_row["file"].strip()
                # Check for and log empty 'file' values.
                if len(file_check_row["file"]) == 0:
                    message = (
                        "CSV row with ID "
                        + file_check_row[config["id_field"]]
                        + ' contains an empty "file" value.'
                    )
                    logging.warning(message)

                # Check for files that cannot be found.
                if (
                    not file_check_row["file"].startswith("http")
                    and len(file_check_row["file"].strip()) > 0
                ):
                    if os.path.isabs(file_check_row["file"]):
                        file_path = file_check_row["file"]
                    else:
                        file_path = os.path.join(
                            config["input_dir"], file_check_row["file"]
                        )
                    if not os.path.exists(file_path) or not os.path.isfile(file_path):
                        message = (
                            'File "'
                            + file_path
                            + '" identified in CSV "file" column for row with ID "'
                            + file_check_row[config["id_field"]]
                            + '" not found.'
                        )
                        if config["allow_missing_files"] is False:
                            logging.error(message)
                            if config["perform_soft_checks"] is False:
                                sys.exit("Error: " + message)
                            else:
                                if (
                                    file_check_row[config["id_field"]]
                                    not in rows_with_missing_files
                                    and len(file_check_row["file"].strip()) > 0
                                ):
                                    rows_with_missing_files.append(
                                        file_check_row[config["id_field"]]
                                    )
                        else:
                            logging.error(message)
                            if (
                                file_check_row[config["id_field"]]
                                not in rows_with_missing_files
                                and len(file_check_row["file"].strip()) > 0
                            ):
                                rows_with_missing_files.append(
                                    file_check_row[config["id_field"]]
                                )
                # Remote files.
                else:
                    if len(file_check_row["file"].strip()) > 0:
                        http_response_code = ping_remote_file(
                            config, file_check_row["file"]
                        )
                        if (
                            http_response_code != 200
                            or ping_remote_file(config, file_check_row["file"]) is False
                        ):
                            message = (
                                'Remote file "'
                                + file_check_row["file"]
                                + '" identified in CSV "file" column for row with ID "'
                                + file_check_row[config["id_field"]]
                                + '" not found or not accessible (HTTP response code '
                                + str(http_response_code)
                                + ")."
                            )
                            if config["allow_missing_files"] is False:
                                logging.error(message)
                                if config["perform_soft_checks"] is False:
                                    sys.exit("Error: " + message)
                                else:
                                    if (
                                        file_check_row[config["id_field"]]
                                        not in rows_with_missing_files
                                        and len(file_check_row["file"].strip()) > 0
                                    ):
                                        rows_with_missing_files.append(
                                            file_check_row[config["id_field"]]
                                        )
                            else:
                                logging.error(message)
                                if (
                                    file_check_row[config["id_field"]]
                                    not in rows_with_missing_files
                                    and len(file_check_row["file"].strip()) > 0
                                ):
                                    rows_with_missing_files.append(
                                        file_check_row[config["id_field"]]
                                    )

            # @todo for issue 268: All accumulator variables like 'rows_with_missing_files' should be checked at end of
            # check_input() (to work with perform_soft_checks: True) in addition to at place of check (to work wit perform_soft_checks: False).
            if len(rows_with_missing_files) > 0:
                if config["allow_missing_files"] is True:
                    message = '"allow_missing_files" configuration setting is set to "true", and CSV "file" column values containing missing files were detected.'
                    print("Warning: " + message + " See the log for more information.")
                    logging.warning(message + " Details are logged above.")
            else:
                message = 'OK, files named in the CSV "file" column are all present.'
                print(message)
                logging.info(message)

            # Verify that all media bundles/types exist.
            if config["nodes_only"] is False:
                media_type_check_csv_data = get_csv_data(config)
                for count, file_check_row in enumerate(
                    media_type_check_csv_data, start=1
                ):
                    filename_fields_to_check = ["file"]
                    for filename_field in filename_fields_to_check:
                        if len(file_check_row[filename_field]) != 0:
                            media_type = set_media_type(
                                config,
                                file_check_row[filename_field],
                                filename_field,
                                file_check_row,
                            )
                            media_bundle_response_code = ping_media_bundle(
                                config, media_type
                            )
                            if media_bundle_response_code == 404:
                                message = (
                                    'File "'
                                    + file_check_row[filename_field]
                                    + '" identified in CSV row '
                                    + file_check_row[config["id_field"]]
                                    + " will create a media of type ("
                                    + media_type
                                    + "), but that media type is not configured in the destination Drupal."
                                    + " Please make sure your media type configuration matches your Drupal configuration."
                                )
                                logging.error(message)
                                sys.exit("Error: " + message)

                            # Check that each file's extension is allowed for the current media type. 'file' is the only
                            # CSV field to check here. Files added using the 'additional_files' setting are checked below.
                            if file_check_row["file"].startswith("http"):
                                # First check to see if the file has an extension.
                                extension = os.path.splitext(file_check_row["file"])[1]
                                if len(extension) > 0:
                                    extension = extension.lstrip(".").lower()
                                else:
                                    extension = get_remote_file_extension(
                                        config, file_check_row["file"]
                                    )
                                    extension = extension.lstrip(".")
                            else:
                                extension = os.path.splitext(file_check_row["file"])[1]
                                extension = extension.lstrip(".").lower()
                            media_type_file_field = config["media_type_file_fields"][
                                media_type
                            ]
                            registered_extensions = get_registered_media_extensions(
                                config, media_type, media_type_file_field
                            )
                            if (
                                isinstance(extension, str)
                                and isinstance(registered_extensions, dict)
                                and extension
                                not in registered_extensions[media_type_file_field]
                            ):
                                message = (
                                    'File "'
                                    + file_check_row[filename_field]
                                    + '" in CSV row "'
                                    + file_check_row[config["id_field"]]
                                    + '" has an extension ('
                                    + str(extension)
                                    + ') that is not allowed in the "'
                                    + media_type_file_field
                                    + '" field of the "'
                                    + media_type
                                    + '" media type.'
                                )
                                logging.error(message)
                                if config["perform_soft_checks"] is False:
                                    sys.exit("Error: " + message)

    # Check existence of fields identified in 'additional_files' config setting.
    if (
        (config["task"] == "create" or config["task"] == "add_media")
        and config["nodes_only"] is False
        and config["paged_content_from_directories"] is False
    ):
        if "additional_files" in config and len(config["additional_files"]) > 0:
            additional_files_entries = get_additional_files_config(config)
            additional_files_check_csv_data = get_csv_data(config)
            additional_files_fields = additional_files_entries.keys()
            additional_files_fields_csv_headers = (
                additional_files_check_csv_data.fieldnames
            )
            if config["nodes_only"] is False:
                for additional_file_field in additional_files_fields:
                    if additional_file_field not in additional_files_fields_csv_headers:
                        message = (
                            'CSV column "'
                            + additional_file_field
                            + '" registered in the "additional_files" configuration setting is missing from your CSV file.'
                        )
                        logging.error(message)
                        sys.exit("Error: " + message)

            # Verify media use tids. @todo: add the 'rows_with_missing_files' method of accumulating invalid values (issue 268).
            if config["nodes_only"] is False:
                for (
                    additional_files_media_use_field,
                    additional_files_media_use_tid,
                ) in additional_files_entries.items():
                    validate_media_use_tid_in_additional_files_setting(
                        config,
                        additional_files_media_use_tid,
                        additional_files_media_use_field,
                    )

            # Check existence of files named in columns identified as 'additional_files' columns.
            missing_additional_files = False
            for count, file_check_row in enumerate(
                additional_files_check_csv_data, start=1
            ):
                for additional_file_field in additional_files_fields:
                    file_check_row[additional_file_field] = file_check_row[
                        additional_file_field
                    ].strip()
                    if len(file_check_row[additional_file_field]) == 0:
                        message = (
                            "CSV row with ID "
                            + file_check_row[config["id_field"]]
                            + ' contains an empty value in its "'
                            + additional_file_field
                            + '" column.'
                        )
                        logging.warning(message)

                    if file_check_row[additional_file_field].startswith("http"):
                        http_response_code = ping_remote_file(
                            config, file_check_row[additional_file_field]
                        )
                        if (
                            http_response_code != 200
                            or ping_remote_file(
                                config, file_check_row[additional_file_field]
                            )
                            is False
                        ):
                            missing_additional_files = True
                            message = (
                                'Additional file "'
                                + file_check_row[additional_file_field]
                                + '" in CSV column "'
                                + additional_file_field
                                + '" in row with ID '
                                + file_check_row[config["id_field"]]
                                + " not found or not accessible (HTTP response code "
                                + str(http_response_code)
                                + ")."
                            )
                            if config["allow_missing_files"] is False:
                                logging.error(message)
                                if config["perform_soft_checks"] is False:
                                    sys.exit("Error: " + message)
                            else:
                                logging.error(message)
                                continue
                    else:
                        if len(file_check_row[additional_file_field]) > 0:
                            if (
                                check_file_exists(
                                    config, file_check_row[additional_file_field]
                                )
                                is False
                            ):
                                missing_additional_files = True
                                message = (
                                    'Additional file "'
                                    + file_check_row[additional_file_field]
                                    + '" in CSV column "'
                                    + additional_file_field
                                    + '" in row with ID '
                                    + file_check_row[config["id_field"]]
                                    + " not found."
                                )
                                if config["allow_missing_files"] is False:
                                    logging.error(message)
                                    if config["perform_soft_checks"] is False:
                                        sys.exit("Error: " + message)
                                else:
                                    logging.error(message)
                                    continue

            if missing_additional_files is True:
                if config["allow_missing_files"] is True:
                    message = '"allow_missing_files" configuration setting is set to "true", and "additional_files" CSV columns containing missing files were detected.'
                    print("Warning: " + message + " See the log for more information.")
                    logging.warning(message + " Details are logged above.")
                else:
                    if config["perform_soft_checks"] is False:
                        sys.exit(message)
            else:
                message = (
                    'OK, files named in "additional_files" CSV columns are all present.'
                )
                print(message)
                logging.info(message)

        # @todo: add the 'rows_with_missing_files' method of accumulating invalid values (issue 268).
        if (
            "additional_files" in config
            and len(config["additional_files"]) > 0
            and config["nodes_only"] is False
        ):
            additional_files_check_extensions_csv_data = get_csv_data(config)
            # Check media types for files registered in 'additional_files'.
            for count, file_check_row in enumerate(
                additional_files_check_extensions_csv_data, start=1
            ):
                for additional_file_field in additional_files_fields:
                    if len(file_check_row[additional_file_field].strip()) > 0:
                        media_type = set_media_type(
                            config,
                            file_check_row[additional_file_field],
                            additional_file_field,
                            file_check_row,
                        )
                        media_bundle_response_code = ping_media_bundle(
                            config, media_type
                        )
                        if media_bundle_response_code == 404:
                            message = (
                                'File "'
                                + file_check_row[additional_file_field]
                                + '" identified in CSV row '
                                + file_check_row[config["id_field"]]
                                + " will create a media of type ("
                                + media_type
                                + "), but that media type is not configured in the destination Drupal."
                                + " Please make sure your media type configuration matches your Drupal configuration."
                            )
                            logging.error(message)
                            sys.exit("Error: " + message)

                        # Check that each file's extension is allowed for the current media type.
                        additional_filenames = file_check_row[
                            additional_file_field
                        ].split(config["subdelimiter"])
                        media_type_file_field = config["media_type_file_fields"][
                            media_type
                        ]
                        for additional_filename in additional_filenames:
                            if check_file_exists(config, additional_filename):
                                if additional_filename.startswith("http"):
                                    # First check to see if the file has an extension.
                                    extension = os.path.splitext(additional_filename)[1]
                                    if len(extension) > 0:
                                        extension = extension.lstrip(".")
                                        extension = extension.lstrip(".")
                                    else:
                                        extension = get_remote_file_extension(
                                            config, additional_filename
                                        )
                                        extension = extension.lstrip(".")
                                else:
                                    extension = os.path.splitext(additional_filename)
                                    extension = extension[1].lstrip(".").lower()

                                registered_extensions = get_registered_media_extensions(
                                    config, media_type, media_type_file_field
                                )
                                if (
                                    extension
                                    not in registered_extensions[media_type_file_field]
                                ):
                                    message = (
                                        'File "'
                                        + additional_filename
                                        + '" in the "'
                                        + additional_file_field
                                        + '" field of row "'
                                        + file_check_row[config["id_field"]]
                                        + '" has an extension ('
                                        + str(extension)
                                        + ') that is not allowed in the "'
                                        + media_type_file_field
                                        + '" field of the "'
                                        + media_type
                                        + '" media type.'
                                    )
                                    logging.error(message)
                                    sys.exit("Error: " + message)

    # @todo Add warning to accommodate #639
    if config["task"] == "create" and config["paged_content_from_directories"] is True:
        if "paged_content_page_model_tid" not in config:
            message = 'If you are creating paged content, you must include "paged_content_page_model_tid" in your configuration.'
            logging.error(
                'Configuration requires "paged_content_page_model_tid" setting when creating paged content.'
            )
            sys.exit("Error: " + message)

        if "paged_content_additional_page_media" in config:
            disable_action_message = (
                'Including the "paged_content_additional_page_media" setting in your configuration will create '
                + "media that are normally generated by Islandora microservices. You should disable any actions your Drupal Contexts "
                + '"Derivatives" configuration so that Islandora does not also generate duplicate media.'
            )
            logging.warning(disable_action_message)
            print("Warning: " + disable_action_message)

            if (
                "paged_content_image_file_extension" not in config
                or "paged_content_additional_page_media" not in config
            ):
                message = (
                    'If your configuration contains the "paged_content_additional_page_media" setting, it must also include both '
                    + 'the "paged_content_image_file_extension" and "paged_content_additional_page_media" settings.'
                )
                logging.error(message)
                sys.exit("Error: " + message)

        paged_content_sequence_indicator_warnings = False
        paged_content_from_directories_csv_data = get_csv_data(config)
        for count, file_check_row in enumerate(
            paged_content_from_directories_csv_data, start=1
        ):
            dir_path = os.path.join(
                config["input_dir"],
                file_check_row[config["page_files_source_dir_field"]],
            )
            if not os.path.exists(dir_path) or os.path.isfile(dir_path):
                message = (
                    "Page directory "
                    + dir_path
                    + ' for CSV record with ID "'
                    + file_check_row[config["id_field"]]
                    + '"" not found.'
                )
                logging.error(message)
                sys.exit("Error: " + message)
            page_files = os.listdir(dir_path)
            if len(page_files) == 0:
                message = "Page directory " + dir_path + " is empty."
                print("Warning: " + message)
                logging.warning(message)

            for page_file_name in page_files:
                # Only want files, not directories.
                if os.path.isdir(os.path.join(dir_path, page_file_name)):
                    continue

                if page_file_name.strip().lower() not in [
                    fn.strip().lower() for fn in config["paged_content_ignore_files"]
                ]:
                    if config["paged_content_sequence_separator"] not in page_file_name:
                        message = (
                            "Page file "
                            + os.path.join(dir_path, page_file_name)
                            + " does not contain a sequence separator ("
                            + config["paged_content_sequence_separator"]
                            + ")."
                        )
                        logging.warning(message)
                        paged_content_sequence_indicator_warnings = True

                page_sequence_indicator = get_sequence_indicator_from_filename(
                    config, page_file_name
                )
                if validate_weight_value(page_sequence_indicator) is False:
                    logging.warning(
                        f'Sequence indicator in page filename "{os.path.join(dir_path, page_file_name)}" is not a valid "field_weight" value.'
                    )
                    paged_content_sequence_indicator_warnings = True

            # Check additional page media files (e.g. OCR andhOCR files) for utf8 encoding.
            additional_page_media_no_utf8_warnings = list()
            if config["paged_content_from_directories"] is True:
                if "paged_content_additional_page_media" in config:
                    for extension_mapping in config[
                        "paged_content_additional_page_media"
                    ]:
                        for (
                            additional_page_media_use_term,
                            additional_page_media_extension,
                        ) in extension_mapping.items():
                            for page_file_name in page_files:
                                page_file_base_path, page_file_extension = (
                                    os.path.splitext(page_file_name)
                                )
                                if (
                                    page_file_extension.lstrip(".")
                                    == additional_page_media_extension
                                ):
                                    additional_page_media_file_path = os.path.join(
                                        dir_path,
                                        page_file_base_path
                                        + "."
                                        + additional_page_media_extension.strip(),
                                    )
                                    if check_file_exists(
                                        config, additional_page_media_file_path
                                    ):
                                        if (
                                            file_is_utf8(
                                                additional_page_media_file_path
                                            )
                                            is False
                                        ):
                                            message = (
                                                'Additional page/child media file "'
                                                + additional_page_media_file_path
                                                + '" in directory for row ID "'
                                                + row[config["id_field"]]
                                                + '" is not encoded as UTF-8 so will not be ingested.'
                                            )
                                            if (
                                                additional_page_media_file_path
                                                not in additional_page_media_no_utf8_warnings
                                            ):
                                                logging.warning(message)
                                                additional_page_media_no_utf8_warnings.append(
                                                    additional_page_media_file_path
                                                )

        print("OK, page directories are all present.")
        if paged_content_sequence_indicator_warnings is True:
            print(
                "Warning: Check your Workbench log for entries about sequence indicator/field_weight values for page/child files."
            )
        if len(additional_page_media_no_utf8_warnings) > 0:
            print(
                "Warning: Check your Workbench log for entries about UTF-8 encoding of additional page/child files."
            )

    # Check for bootstrap scripts, if any are configured.
    bootsrap_scripts_present = False
    if "bootstrap" in config and len(config["bootstrap"]) > 0:
        bootsrap_scripts_present = True
        for bootstrap_script in config["bootstrap"]:
            if not os.path.exists(bootstrap_script):
                message = "Bootstrap script " + bootstrap_script + " not found."
                logging.error(message)
                sys.exit("Error: " + message)
            if os.access(bootstrap_script, os.X_OK) is False:
                message = "Bootstrap script " + bootstrap_script + " is not executable."
                logging.error(message)
                sys.exit("Error: " + message)
        if bootsrap_scripts_present is True:
            message = "OK, registered bootstrap scripts found and executable."
            logging.info(message)
            print(message)

    # Check for shutdown scripts, if any are configured.
    shutdown_scripts_present = False
    if "shutdown" in config and len(config["shutdown"]) > 0:
        shutdown_scripts_present = True
        for shutdown_script in config["shutdown"]:
            if not os.path.exists(shutdown_script):
                message = "shutdown script " + shutdown_script + " not found."
                logging.error(message)
                sys.exit("Error: " + message)
            if os.access(shutdown_script, os.X_OK) is False:
                message = "Shutdown script " + shutdown_script + " is not executable."
                logging.error(message)
                sys.exit("Error: " + message)
        if shutdown_scripts_present is True:
            message = "OK, registered shutdown scripts found and executable."
            logging.info(message)
            print(message)

    # Check for preprocessor scripts, if any are configured.
    preprocessor_scripts_present = False
    if "preprocessors" in config and len(config["preprocessors"]) > 0:
        preprocessor_scripts_present = True
        # for preprocessor_script in config['preprocessors']:
        for field, script_path in config["preprocessors"].items():
            if not os.path.exists(script_path):
                message = f'Preprocessor script "{script_path}" for field "{field}" not found.'
                logging.error(message)
                sys.exit("Error: " + message)
            if os.access(script_path, os.X_OK) is False:
                message = f'Preprocessor script "{script_path}" for field "{field}" is not executable.'
                logging.error(message)
                sys.exit("Error: " + message)
        if preprocessor_scripts_present is True:
            message = f"OK, registered preprocessor scripts found and executable."
            logging.info(message)
            print(message)

    # Check for the existence and executableness of post-action scripts, if any are configured.
    if (
        config["task"] == "create"
        or config["task"] == "update"
        or config["task"] == "add_media"
    ):
        post_action_scripts_configs = [
            "node_post_create",
            "node_post_update",
            "media_post_create",
        ]
        for post_action_script_config in post_action_scripts_configs:
            post_action_scripts_present = False
            if (
                post_action_script_config in config
                and len(config[post_action_script_config]) > 0
            ):
                post_action_scripts_present = True
                for post_action_script in config[post_action_script_config]:
                    if not os.path.exists(post_action_script):
                        message = (
                            "Post-action script " + post_action_script + " not found."
                        )
                        logging.error(message)
                        sys.exit("Error: " + message)
                    if os.access(post_action_script, os.X_OK) is False:
                        message = (
                            "Post-action script "
                            + post_action_script
                            + " is not executable."
                        )
                        logging.error(message)
                        sys.exit("Error: " + message)
            if post_action_scripts_present is True:
                message = "OK, registered post-action scripts found and executable."
                logging.info(message)
                print(message)

    if config["task"] == "export_csv":
        if "node_id" not in csv_column_headers:
            message = (
                'For "export_csv" tasks, your CSV file must contain a "node_id" column.'
            )
            logging.error(message)
            sys.exit("Error: " + message)

        export_csv_term_mode_options = ["tid", "name"]
        if config["export_csv_term_mode"] not in export_csv_term_mode_options:
            message = 'Configuration option "export_csv_term_mode_options" must be either "tid" or "name".'
            logging.error(message)
            sys.exit("Error: " + message)

        if config["export_file_directory"] is not None:
            if not os.path.exists(config["export_csv_file_path"]):
                try:
                    os.mkdir(config["export_file_directory"])
                    os.rmdir(config["export_file_directory"])
                except Exception as e:
                    message = (
                        'Path in configuration option "export_file_directory" ("'
                        + config["export_file_directory"]
                        + '") is not writable.'
                    )
                    logging.error(message + " " + str(e))
                    sys.exit("Error: " + message + " See log for more detail.")

        if config["export_file_media_use_term_id"] is False:
            message = f'Unknown value for configuration setting "export_file_media_use_term_id": {config["export_file_media_use_term_id"]}.'
            logging.error(message)
            sys.exit("Error: " + message)

    if (
        len(rows_with_missing_files) > 0
        and config["allow_missing_files"] is False
        and config["perform_soft_checks"] is False
    ):
        logging.error(
            'Missing or empty CSV "file" column values detected. See log entries above.'
        )
        sys.exit(
            'Error: Missing or empty CSV "file" column values detected. See the log for more information.'
        )

    if len(rows_with_missing_files) > 0 and config["perform_soft_checks"] is True:
        message = '"perform_soft_checks" configuration setting is set to "true" and some values in the "file" column were not found.'
        logging.warning(message + " See log entries above.")
        print("Warning: " + message + " See the log for more information.")

    if (
        "additional_files" in config
        and len(config["additional_files"]) > 0
        and config["nodes_only"] is False
    ):
        if missing_additional_files is True:
            if config["allow_missing_files"] is False:
                message = '"allow_missing_files" configuration setting is set to "false", and some files in fields configured as "additional_file" fields cannot be found.'
                logging.error(message + " See log entries above.")
                print(message + " See the log for more information.")
                if config["perform_soft_checks"] is True:
                    message = 'The "perform_soft_checks" configuration setting is set to "true", so Workbench did not exit after finding the first missing file.'
                    logging.warning(message)
                    print(message + " See the log for more information.")
                else:
                    sys.exit("Error: " + message)
        else:
            message = 'OK, files in fields configured as "additional_file" fields are all present.'
            logging.info(message)
            print(message)

    # If nothing has failed by now, exit with a positive, upbeat message.
    print("Configuration and input data appear to be valid.")
    logging.info(
        'Configuration checked for "%s" task using config file "%s", no problems found.',
        config["task"],
        args.config,
    )

    if "check_lock_file_path" in config:
        with open(config["check_lock_file_path"], "a") as check_lock_file:
            config_file_md5 = get_file_hash_from_local(
                config, config["config_file_path"], "md5"
            )
            check_lock_file.write(
                f'Check against {config["config_file_path"]} (md5 hash {config_file_md5}) OK'
            )
            logging.info(
                f"Writing --check lock file \"{config['check_lock_file_path']}\"."
            )

    if args.contactsheet is True:
        if os.path.isabs(config["contact_sheet_output_dir"]):
            contact_sheet_path = os.path.join(
                config["contact_sheet_output_dir"], "contact_sheet.htm"
            )
        else:
            contact_sheet_path = os.path.join(
                os.getcwd(), config["contact_sheet_output_dir"], "contact_sheet.htm"
            )
        generate_contact_sheet_from_csv(config)
        message = f"Contact sheet is at {contact_sheet_path}."
        print(message)
        logging.info(message)

    if config["secondary_tasks"] is None:
        sys.exit(0)
    else:
        for secondary_config_file in json.loads(
            os.environ["ISLANDORA_WORKBENCH_SECONDARY_TASKS"]
        ):
            print("")
            print(
                'Running --check using secondary configuration file "'
                + secondary_config_file
                + '"'
            )
            if os.name == "nt":
                # Assumes python.exe is in the user's PATH.
                cmd = [
                    "python",
                    "./workbench",
                    "--config",
                    secondary_config_file,
                    "--check",
                ]
            else:
                cmd = ["./workbench", "--config", secondary_config_file, "--check"]
            output = subprocess.run(cmd)

        sys.exit(0)


def check_rollback_file_path_directories(config):
    rollback_config_file_path = get_rollback_config_filepath(config)
    rollback_config_file_path_head, rollback_config_file_path_tail = os.path.split(
        rollback_config_file_path
    )
    if not os.access(rollback_config_file_path_head, os.W_OK):
        message = f'Directory "{rollback_config_file_path_head}" in the rollback configuration file path does not exist or is not writable.'
        logging.error(message)
        sys.exit("Error: " + message)

    if config["check"] is True:
        logging.info(
            f"Rollback configuration file will be written to {rollback_config_file_path}."
        )

    rollback_csv_file_path = get_rollback_csv_filepath(config)
    rollback_csv_file_path_head, rollback_csv_file_path_tail = os.path.split(
        rollback_csv_file_path
    )
    if not os.access(rollback_csv_file_path_head, os.W_OK):
        message = f'Directory "{rollback_csv_file_path_head}" in the rollback CSV file path does not exist or is not writable.'
        logging.error(message)
        sys.exit("Error: " + message)

    if config["check"] is True:
        logging.info(f"Rollback CSV file will be written to {rollback_csv_file_path}.")


def get_registered_media_extensions(config, media_bundle, field_name_filter=None):
    """For the given media bundle, gets a list of file extensions registered in Drupal's
    "Allowed file extensions" configuration for each field that has this setting.
    """
    """Parameters
        ----------
        config : dict
            The configuration settings defined by workbench_config.get_config().
        bundle_type : string
            The (node) content type, the vocabulary name, or the media type (image',
            'document', 'audio', 'video', 'file', etc.).
        field_name_filter: string
            If not None, filter the return value to just that field; if the field is
            not a key in the return dict, return False.
        Returns
        -------
        dict
            A dictionary with one key per media bundle field name that has registered exensions.
            Each key has as its value a list of file extensions, without leading periods,
            registered for those fields in Drupal. All extensions are lower case.
    """
    registered_extensions = dict()
    media_field_definitions = get_field_definitions(config, "media", media_bundle)
    for field_name, field_def in media_field_definitions.items():
        if "file_extensions" in field_def:
            registered_extensions[field_name] = re.split(
                r"\s+", field_def["file_extensions"]
            )
            for i in range(len(registered_extensions[field_name])):
                registered_extensions[field_name][i] = registered_extensions[
                    field_name
                ][i].lower()

    if field_name_filter is not None and field_name_filter in registered_extensions:
        return {field_name_filter: registered_extensions[field_name_filter]}
    elif (
        field_name_filter is not None and field_name_filter not in registered_extensions
    ):
        return False
    else:
        return registered_extensions


def check_input_for_create_from_files(config, args):
    """Validate the config file and input data if task is 'create_from_files'."""
    if config["task"] != "create_from_files":
        message = 'Your task must be "create_from_files".'
        logging.error(message)
        sys.exit("Error: " + message)

    logging.info(
        'Starting configuration check for "%s" task using config file %s.',
        config["task"],
        args.config,
    )

    ping_islandora(config, print_message=False)

    config_keys = list(config.keys())
    unwanted_in_create_from_files = [
        "check",
        "delimiter",
        "subdelimiter",
        "allow_missing_files",
        "paged_content_from_directories",
        "delete_media_with_nodes",
        "allow_adding_terms",
    ]
    for option in unwanted_in_create_from_files:
        if option in config_keys:
            config_keys.remove(option)
    joiner = ", "
    # Check for presence of required config keys.
    create_required_options = ["task", "host", "username", "password"]
    for create_required_option in create_required_options:
        if create_required_option not in config_keys:
            message = (
                "Please check your config file for required values: "
                + joiner.join(create_required_options)
                + "."
            )
            logging.error(message)
            sys.exit("Error: " + message)

    # Check existence of input directory.
    if os.path.exists(config["input_dir"]):
        message = 'OK, input directory "' + config["input_dir"] + '" found.'
        print(message)
        logging.info(message)
    else:
        message = 'Input directory "' + config["input_dir"] + '"" not found.'
        logging.error(message)
        sys.exit("Error: " + message)

    # Validate length of 'title'.
    files = os.listdir(config["input_dir"])
    for file_name in files:
        filename_without_extension = os.path.splitext(file_name)[0]
        if len(filename_without_extension) > int(config["max_node_title_length"]):
            message = (
                'The filename "'
                + filename_without_extension
                + "\" exceeds Drupal's maximum length of "
                + config["max_node_title_length"]
                + " characters and cannot be used for a node title."
            )
            logging.error(message)
            sys.exit("Error: " + message)

    # Check that either 'model' or 'models' are present in the config file.
    if "model" not in config and "models" not in config:
        message = 'You must include either the "model" or "models" option in your configuration.'
        logging.error(message)
        sys.exit("Error: " + message)

    # If nothing has failed by now, exit with a positive message.
    print("Configuration and input data appear to be valid.")
    logging.info(
        'Configuration checked for "%s" task using config file %s, no problems found.',
        config["task"],
        args.config,
    )
    sys.exit(0)


def log_field_cardinality_violation(field_name, record_id, cardinality):
    """Writes an entry to the log during create/update tasks if any field values
    are sliced off. Workbench does this if the number of values in a field
    exceeds the field's cardinality. record_id could be a value from the
    configured id_field or a node ID.
    """
    logging.warning(
        "Adding all values in CSV field %s for record %s would exceed maximum number of allowed values (%s). Skipping adding extra values.",
        field_name,
        record_id,
        cardinality,
    )


def validate_language_code(langcode):
    # Drupal's language codes.
    codes = [
        "af",
        "am",
        "ar",
        "ast",
        "az",
        "be",
        "bg",
        "bn",
        "bo",
        "bs",
        "ca",
        "cs",
        "cy",
        "da",
        "de",
        "dz",
        "el",
        "en",
        "en-x-simple",
        "eo",
        "es",
        "et",
        "eu",
        "fa",
        "fi",
        "fil",
        "fo",
        "fr",
        "fy",
        "ga",
        "gd",
        "gl",
        "gsw-berne",
        "gu",
        "he",
        "hi",
        "hr",
        "ht",
        "hu",
        "hy",
        "id",
        "is",
        "it",
        "ja",
        "jv",
        "ka",
        "kk",
        "km",
        "kn",
        "ko",
        "ku",
        "ky",
        "lo",
        "lt",
        "lv",
        "mg",
        "mk",
        "ml",
        "mn",
        "mr",
        "ms",
        "my",
        "ne",
        "nl",
        "nb",
        "nn",
        "oc",
        "pa",
        "pl",
        "pt-pt",
        "pt-br",
        "ro",
        "ru",
        "sco",
        "se",
        "si",
        "sk",
        "sl",
        "sq",
        "sr",
        "sv",
        "sw",
        "ta",
        "ta-lk",
        "te",
        "th",
        "tr",
        "tyv",
        "ug",
        "uk",
        "ur",
        "vi",
        "xx-lolspeak",
        "zh-hans",
        "zh-hant",
    ]
    if langcode in codes:
        return True
    else:
        return False


def clean_csv_values(config, row):
    """Performs basic string cleanup on CSV values. Applies to entier value,
    not each subdivided value.
    """
    """Parameters
        ----------
        config : dict
            The configuration settings defined by workbench_config.get_config().
        row : OrderedDict
            A CSV row.
        Returns
        -------
        preprocessed_csv_reader
            The CSV DictReader object.
    """
    for field in row:
        if "smart_quotes" not in config["clean_csv_values_skip"]:
            # Replace smart/curly quotes with straight ones.
            row[field] = str(row[field]).replace("“", '"').replace("”", '"')
            row[field] = str(row[field]).replace("‘", "'").replace("’", "'")

        if "inside_spaces" not in config["clean_csv_values_skip"]:
            # Remove multiple spaces within string.
            row[field] = re.sub(" +", " ", str(row[field]))

        # Any outside .strip()s should come after 'outside_spaces', so they are removed first.
        # Assumes that spaces/newlines are the most likely extraneous leading and trailing
        # characters in CSV values.
        if "outside_spaces" not in config["clean_csv_values_skip"]:
            # Strip leading and trailing whitespace, including newlines.
            row[field] = str(row[field]).strip()

        if "outside_subdelimiters" not in config["clean_csv_values_skip"]:
            # Strip leading and trailing subdelimters.
            row[field] = str(row[field]).strip(config["subdelimiter"])

    return row


def truncate_csv_value(field_name, record_id, field_config, value):
    """Drupal will not accept text field values that have a length that
    exceeds the configured maximum length for that field. 'value'
    here is a field subvalue.
    """
    if isinstance(value, str) and "max_length" in field_config:
        max_length = field_config["max_length"]
        if max_length is not None and len(value) > int(max_length):
            original_value = value
            value = value[:max_length]
            logging.warning(
                'CSV field value "%s" in field "%s" (record ID %s) truncated at %s characters as required by the field\'s configuration.',
                original_value,
                field_name,
                record_id,
                max_length,
            )
    return value


def deduplicate_field_values(values):
    """Removes duplicate entries from 'values' while retaining
    the order of the unique members.
    """
    """Parameters
        ----------
        values : list
            List containing value(s) to dedupe. Members could be strings
            from CSV or dictionairies.
        Returns
        -------
        list
            A list of unique field values.
    """
    deduped_list = []
    for member in values:
        if member not in deduped_list:
            deduped_list.append(member)

    return deduped_list


def get_node_field_values(config, nid):
    """Get a node's field data so we can use it during PATCH updates, which replace a field's values."""
    if value_is_numeric(nid) is False:
        nid = get_nid_from_url_alias(config, nid)
    node_url = config["host"] + "/node/" + str(nid) + "?_format=json"
    response = issue_request(config, "GET", node_url)
    node_fields = json.loads(response.text)
    return node_fields


def get_media_field_values(config, media_id):
    """Get a media's field data so we can use it during PATCH updates, which replace a field's values."""
    if config["standalone_media_url"] is True:
        media_url = config["host"] + "/media/" + media_id + "?_format=json"
    else:
        media_url = config["host"] + "/media/" + media_id + "/edit?_format=json"

    get_media_response = issue_request(config, "GET", media_url)
    media_fields = json.loads(get_media_response.text)
    return media_fields


def get_target_ids(node_field_values):
    """Get the target IDs of all entities in a field."""
    target_ids = []
    for target in node_field_values:
        target_ids.append(target["target_id"])
    return target_ids


def get_additional_files_config(config):
    """Converts values in 'additional_files' config setting to a simple
    dictionary for easy access.
    """
    additional_files_entries = dict()
    if "additional_files" in config and len(config["additional_files"]) > 0:
        for additional_files_entry in config["additional_files"]:
            for (
                additional_file_field,
                additional_file_media_use_tid,
            ) in additional_files_entry.items():
                additional_files_entries[additional_file_field] = (
                    additional_file_media_use_tid
                )
    return additional_files_entries


def split_typed_relation_string(config, typed_relation_string, target_type):
    """Fields of type 'typed_relation' are represented in the CSV file
    using a structured string, specifically namespace:property:id,
    e.g., 'relators:pht:5'. 'id' is either a term ID or a node ID. This
    function takes one of those strings (optionally with a multivalue
    subdelimiter) and returns a list of dictionaries in the form they
    take in existing node values. ID values can also be term names (strings)
    and term URIs (also strings, but in the form 'http....').

    Also, these values can (but don't need to) have an optional namespace
    in the term ID segment, which is the vocabulary ID string. These
    typed relation strings look like 'relators:pht:person:Jordan, Mark'.
    However, since we split the typed relation strings only on the first
    two :, the entire third segment is considered, for the purposes of
    splitting the value, to be the term.
    """
    typed_relation_string = typed_relation_string.strip()

    return_list = []
    if len(typed_relation_string) == 0:
        return return_list

    temp_list = typed_relation_string.split(config["subdelimiter"])
    for item in temp_list:
        item_list = item.split(":", 2)
        if value_is_numeric(item_list[2]):
            target_id = int(item_list[2])
        else:
            target_id = item_list[2]
        item_dict = {
            "target_id": target_id,
            "rel_type": item_list[0] + ":" + item_list[1],
            "target_type": target_type,
        }
        return_list.append(item_dict)

    return return_list


def split_geolocation_string(config, geolocation_string):
    """Fields of type 'geolocation' are represented in the CSV file using a
    structured string, specifically lat,lng, e.g. "49.16667, -123.93333"
    or "+49.16667, -123.93333". This function takes one of those strings
    (optionally with a multivalue subdelimiter) and returns a list of
    dictionaries with 'lat' and 'lng' keys required by the 'geolocation'
    field type.
    """
    geolocation_string = geolocation_string.strip()

    return_list = []
    if len(geolocation_string) == 0:
        return return_list

    temp_list = geolocation_string.split(config["subdelimiter"])
    for item in temp_list:
        item_list = item.split(",")
        # Remove any leading \ which might be in value if it comes from a spreadsheet.
        item_dict = {
            "lat": item_list[0].lstrip("\\").strip(),
            "lng": item_list[1].lstrip("\\").strip(),
        }
        return_list.append(item_dict)

    return return_list


def split_link_string(config, link_string):
    """Fields of type 'link' are represented in the CSV file using a structured string,
    specifically uri%%title, e.g. "https://www.lib.sfu.ca%%SFU Library Website".
    This function takes one of those strings (optionally with a multivalue subdelimiter)
    and returns a list of dictionaries with 'uri' and 'title' keys required by the
    'link' field type.
    """
    link_string = link_string.strip()

    return_list = []
    if len(link_string) == 0:
        return return_list

    temp_list = link_string.split(config["subdelimiter"])
    for item in temp_list:
        if "%%" in item:
            item_list = item.split("%%", 1)
            item_dict = {"uri": item_list[0].strip(), "title": item_list[1].strip()}
            return_list.append(item_dict)
        else:
            # If there is no %% and title, use the URL as the title.
            item_dict = {"uri": item.strip(), "title": item.strip()}
            return_list.append(item_dict)

    return return_list


def split_authority_link_string(config, authority_link_string):
    """Fields of type 'authority_link' are represented in the CSV file using a structured string,
    specifically source%%uri%%title, e.g. "viaf%%http://viaf.org/viaf/153525475%%Rush (Musical group)".
    This function takes one of those strings (optionally with a multivalue subdelimiter)
    and returns a list of dictionaries with 'source', 'uri' and 'title' keys required by the
    'authority_link' field type.
    """
    authority_link_string = authority_link_string.strip()

    return_list = []
    if len(authority_link_string) == 0:
        return return_list

    temp_list = authority_link_string.split(config["subdelimiter"])
    for item in temp_list:
        if item.count("%%") == 2:
            item_list = item.split("%%", 2)
            item_dict = {
                "source": item_list[0].strip(),
                "uri": item_list[1].strip(),
                "title": item_list[2].strip(),
            }
            return_list.append(item_dict)
        if item.count("%%") == 1:
            # There is no title.
            item_list = item.split("%%", 1)
            item_dict = {
                "source": item_list[0].strip(),
                "uri": item_list[1].strip(),
                "title": "",
            }
            return_list.append(item_dict)

    return return_list


def split_media_track_string(config, media_track_string):
    """Fields of type 'media_track' are represented in the CSV file using a structured string,
    specifically 'label:kind:srclang:path_to_vtt_file', e.g. "en:subtitles:en:path/to/the/vtt/file.vtt".
    This function takes one of those strings (optionally with a multivalue subdelimiter) and returns
    a list of dictionaries with 'label', 'kind', 'srclang', 'file_path' keys required by the
    'media_track' field type.
    """
    media_track_string = media_track_string.strip()

    return_list = []
    if len(media_track_string) == 0:
        return return_list

    temp_list = media_track_string.split(config["subdelimiter"])
    for item in temp_list:
        track_parts_list = item.split(":", 3)
        item_dict = {
            "label": track_parts_list[0],
            "kind": track_parts_list[1],
            "srclang": track_parts_list[2],
            "file_path": track_parts_list[3],
        }
        return_list.append(item_dict)

    return return_list


def validate_media_use_tid_in_additional_files_setting(
    config, media_use_tid_value, additional_field_name
):
    """Validate whether the term ID registered in the "additional_files" config setting
    is in the Islandora Media Use vocabulary.
    """
    media_use_tids = []
    if config["subdelimiter"] in str(media_use_tid_value):
        media_use_tids = str(media_use_tid_value).split(config["subdelimiter"])
    else:
        media_use_tids.append(media_use_tid_value)

    for media_use_tid in media_use_tids:
        if not value_is_numeric(media_use_tid) and media_use_tid.strip().startswith(
            "http"
        ):
            media_use_tid = get_term_id_from_uri(config, media_use_tid.strip())
        if not value_is_numeric(media_use_tid) and not media_use_tid.strip().startswith(
            "http"
        ):
            media_use_tid = find_term_in_vocab(
                config, "islandora_media_use", media_use_tid.strip()
            )

        term_endpoint = (
            config["host"]
            + "/taxonomy/term/"
            + str(media_use_tid).strip()
            + "?_format=json"
        )
        headers = {"Content-Type": "application/json"}
        response = issue_request(config, "GET", term_endpoint, headers)
        if response.status_code == 404:
            message = (
                'Term ID "'
                + str(media_use_tid)
                + '" registered in the "additional_files" config option '
                + 'for field "'
                + additional_field_name
                + "\" is not a term ID (term doesn't exist)."
            )
            logging.error(message)
            sys.exit("Error: " + message)
        if response.status_code == 200:
            response_body = json.loads(response.text)
            if "vid" in response_body:
                if response_body["vid"][0]["target_id"] != "islandora_media_use":
                    message = (
                        'Term ID "'
                        + str(media_use_tid)
                        + '" registered in the "additional_files" config option '
                        + 'for field "'
                        + additional_field_name
                        + '" is not in the Islandora Media Use vocabulary.'
                    )
                    logging.error(message)
                    sys.exit("Error: " + message)
            if "field_external_uri" in response_body:
                if (
                    len(response_body["field_external_uri"]) > 0
                    and response_body["field_external_uri"][0]["uri"]
                    != "http://pcdm.org/use#OriginalFile"
                ):
                    message = (
                        'Warning: Term ID "'
                        + str(media_use_tid)
                        + '" registered in the "additional_files" config option '
                        + 'for CSV field "'
                        + additional_field_name
                        + '" will assign an Islandora Media Use term that might '
                        + "conflict with derivative media. You should temporarily disable the Context or Action that generates those derivatives."
                    )
                else:
                    # There is no field_external_uri so we can't identify the term. Provide a generic message.
                    message = (
                        'Warning: Terms registered in the "additional_files" config option '
                        + 'for CSV field "'
                        + additional_field_name
                        + '" may assign an Islandora Media Use term that will '
                        + "conflict with derivative media. You should temporarily disable the Context or Action that generates those derivatives."
                    )
                    print(message)
                    logging.warning(message)


def validate_media_use_tid(config, media_use_tid_value_from_csv=None, csv_row_id=None):
    """Validate whether the term ID, term name, or terms URI provided in the
    config value for media_use_tid is in the Islandora Media Use vocabulary.
    """
    if media_use_tid_value_from_csv is not None and csv_row_id is not None:
        if len(str(media_use_tid_value_from_csv)) > 0:
            media_use_tid_value = media_use_tid_value_from_csv
            message_wording = ' in the CSV "media_use_tid" column '
    else:
        media_use_tid_value = config["media_use_tid"]
        message_wording = ' in configuration option "media_use_tid" '

    media_use_terms = str(media_use_tid_value).split(config["subdelimiter"])
    for media_use_term in media_use_terms:
        if value_is_numeric(
            media_use_term
        ) is not True and media_use_term.strip().startswith("http"):
            media_use_tid = get_term_id_from_uri(config, media_use_term.strip())
            if csv_row_id is None:
                if media_use_tid is False:
                    message = (
                        'URI "'
                        + media_use_term
                        + '" provided '
                        + message_wording
                        + " does not match any taxonomy terms."
                    )
                    logging.error(message)
                    sys.exit("Error: " + message)
                if (
                    media_use_tid is not False
                    and media_use_term.strip() != "http://pcdm.org/use#OriginalFile"
                ):
                    message = (
                        'Warning: URI "'
                        + media_use_term
                        + '" provided'
                        + message_wording
                        + "will assign an Islandora Media Use term that might conflict with derivative media. "
                        + "You should temporarily disable the Context or Action that generates those derivatives."
                    )
                    print(message)
                    logging.warning(message)
            else:
                if media_use_tid is False:
                    message = (
                        'URI "'
                        + media_use_term
                        + '" provided in "media_use_tid" field in CSV row '
                        + str(csv_row_id)
                        + " does not match any taxonomy terms."
                    )
                    logging.error(message)
                    sys.exit("Error: " + message)
                if (
                    media_use_tid is not False
                    and media_use_term.strip() != "http://pcdm.org/use#OriginalFile"
                ):
                    message = (
                        'Warning: URI "'
                        + media_use_term
                        + '" provided in "media_use_tid" field in CSV row '
                        + str(csv_row_id)
                        + "will assign an Islandora Media Use term that might conflict with "
                        + "derivative media. You should temporarily disable the Context or Action that generates those derivatives."
                    )
                    logging.warning(message)

        elif (
            value_is_numeric(media_use_term) is not True
            and media_use_term.strip().startswith("http") is not True
        ):
            media_use_tid = find_term_in_vocab(
                config, "islandora_media_use", media_use_term.strip()
            )
            if csv_row_id is None:
                if media_use_tid is False:
                    message = (
                        'Warning: Term name "'
                        + media_use_term.strip()
                        + '" provided in configuration option "media_use_tid" does not match any taxonomy terms.'
                    )
                    logging.warning(message)
                    sys.exit("Error: " + message)
            else:
                if media_use_tid is False:
                    message = (
                        'Warning: Term name "'
                        + media_use_term.strip()
                        + '" provided in "media_use_tid" field in CSV row '
                        + str(csv_row_id)
                        + " does not match any taxonomy terms."
                    )
                    logging.warning(message)
                    sys.exit("Error: " + message)
        else:
            # Confirm the tid exists and is in the islandora_media_use vocabulary
            term_endpoint = (
                config["host"]
                + "/taxonomy/term/"
                + str(media_use_term.strip())
                + "?_format=json"
            )
            headers = {"Content-Type": "application/json"}
            response = issue_request(config, "GET", term_endpoint, headers)
            if response.status_code == 404:
                if csv_row_id is None:
                    message = (
                        'Term ID "'
                        + str(media_use_term)
                        + '" used in the "media_use_tid" configuration option is not a term ID (term doesn\'t exist).'
                    )
                    logging.error(message)
                    sys.exit("Error: " + message)
                else:
                    message = (
                        'Term ID "'
                        + str(media_use_term)
                        + '" used in the "media_use_tid" field in CSV row '
                        + str(csv_row_id)
                        + " is not a term ID (term doesn't exist)."
                    )
                    logging.error(message)
                    sys.exit("Error: " + message)
            if response.status_code == 200:
                response_body = json.loads(response.text)
                if csv_row_id is None:
                    if "vid" in response_body:
                        if (
                            response_body["vid"][0]["target_id"]
                            != "islandora_media_use"
                        ):
                            message = (
                                'Term ID "'
                                + str(media_use_term)
                                + '" provided in configuration option "media_use_tid" is not in the Islandora Media Use vocabulary.'
                            )
                            logging.error(message)
                            sys.exit("Error: " + message)
                    if "field_external_uri" in response_body:
                        if (
                            response_body["field_external_uri"][0]["uri"]
                            != "http://pcdm.org/use#OriginalFile"
                        ):
                            message = (
                                'Warning: Term ID "'
                                + media_use_term
                                + '" provided in configuration option "media_use_tid" '
                                + "will assign an Islandora Media Use term that might conflict with derivative media. "
                                + " You should temporarily disable the Context or Action that generates those derivatives."
                            )
                            print(message)
                            logging.warning(message)
                else:
                    if "vid" in response_body:
                        if (
                            response_body["vid"][0]["target_id"]
                            != "islandora_media_use"
                        ):
                            message = (
                                'Term ID "'
                                + str(media_use_term)
                                + '" provided in the "media_use_tid" field in CSV row '
                                + str(csv_row_id)
                                + " is not in the Islandora Media Use vocabulary."
                            )
                            logging.error(message)
                            sys.exit("Error: " + message)
                    if "field_external_uri" in response_body:
                        if (
                            response_body["field_external_uri"][0]["uri"]
                            != "http://pcdm.org/use#OriginalFile"
                        ):
                            message = (
                                'Warning: Term ID "'
                                + media_use_term
                                + '" provided in "media_use_tid" field in CSV row '
                                + str(csv_row_id)
                                + " will assign an Islandora Media Use term that might conflict with "
                                + "derivative media. You should temporarily disable the Context or Action that generates those derivatives."
                            )
                            print(message)
                            logging.warning(message)


def validate_media_use_tids_in_csv(config, csv_data):
    """Validate 'media_use_tid' values in CSV if they exist."""
    if config["task"] == "add_media":
        csv_id_field = "node_id"
    else:
        csv_id_field = config["id_field"]

    for count, row in enumerate(csv_data, start=1):
        if "media_use_tid" in row:
            delimited_field_values = row["media_use_tid"].split(config["subdelimiter"])
            for field_value in delimited_field_values:
                if len(field_value.strip()) > 0:
                    validate_media_use_tid(config, field_value, row[csv_id_field])


def preprocess_field_data(subdelimiter, field_value, path_to_script):
    """Executes a field preprocessor script and returns its output and exit status code. The script
    is passed the field subdelimiter as defined in the config YAML and the field's value, and
    prints a modified vesion of the value (result) back to this function.
    """
    cmd = subprocess.Popen(
        [path_to_script, subdelimiter, field_value], stdout=subprocess.PIPE
    )
    result, stderrdata = cmd.communicate()

    return result, cmd.returncode


def execute_bootstrap_script(path_to_script, path_to_config_file):
    """Executes a bootstrap script and returns its output and exit status code."""
    cmd = subprocess.Popen(
        [path_to_script, path_to_config_file], stdout=subprocess.PIPE
    )
    result, stderrdata = cmd.communicate()

    return result, cmd.returncode


def execute_shutdown_script(path_to_script, path_to_config_file):
    """Executes a shutdown script and returns its output and exit status code."""
    cmd = subprocess.Popen(
        [path_to_script, path_to_config_file], stdout=subprocess.PIPE
    )
    result, stderrdata = cmd.communicate()

    return result, cmd.returncode


def execute_entity_post_task_script(
    path_to_script, path_to_config_file, http_response_code, entity_json=""
):
    """Executes a entity-level post-task script and returns its output and exit status code."""
    cmd = subprocess.Popen(
        [path_to_script, path_to_config_file, str(http_response_code), entity_json],
        stdout=subprocess.PIPE,
    )
    result, stderrdata = cmd.communicate()

    return result, cmd.returncode


# def upload_local_file(config, filename, media_type):
#     """Uploads a file to Drupal.
#     """
#     file_path = os.path.join(config['input_dir'], filename)
#     if media_type in config['media_type_file_fields']:
#         media_file_field = config['media_type_file_fields'][media_type]
#     else:
#         logging.error('File not created for CSV row "%s": media type "%s" not recognized.', media_csv_row[config['media_id']], media_type)
#         return False

#     # Requests/urllib3 requires filenames used in Content-Disposition headers to be encoded as latin-1.
#     # Since it is impossible to reliably convert to latin-1 without knowing the source encoding of the filename
#     # (which may or may not have originated on the machine running Workbench, so sys.stdout.encoding isn't reliable),
#     # the best we can do for now is to use unidecode to replace non-ASCII characters in filenames with their ASCII
#     # equivalents (at least the unidecode() equivalents). Also, while Requests requires filenames to be encoded
#     # in latin-1, Drupal passes filenames through its validateUtf8() function. So ASCII is a low common denominator
#     # of both requirements.
#     ascii_only = string_is_ascii(filename)
#     if ascii_only is False:
#         original_filename = copy.copy(filename)
#         filename = unidecode(filename)
#         logging.warning("Filename '" + original_filename + "' contains non-ASCII characters, normalized to '" + filename + "'.")

#     file_endpoint_path = '/file/upload/media/' + media_type + '/' + media_file_field + '?_format=json'
#     file_headers = {
#         'Content-Type': 'application/octet-stream',
#         'Content-Disposition': 'file; filename="' + filename + '"'
#     }

#     binary_data = open(file_path, 'rb')

#     try:
#         file_response = issue_request(config, 'POST', file_endpoint_path, file_headers, '', binary_data)
#         if file_response.status_code == 201:
#             file_json = json.loads(file_response.text)
#             file_id = file_json['fid'][0]['value']
#             return file_id
#         else:
#             logging.error('File not created for "' + file_path + '", POST request to "%s" returned an HTTP status code of "%s" and a response body of %s.',
#                         file_endpoint_path, file_response.status_code, file_response.content)
#             return False
#     except requests.exceptions.RequestException as e:
#         logging.error(e)
#         return False

#     # TODO: Handle checksums, temporary files, etc. as in create_file


def create_file(config, filename, file_fieldname, node_csv_row, node_id):
    """Creates a file in Drupal, which is then referenced by the accompanying media.
    Parameters
    ----------
     config : dict
         The configuration settings defined by workbench_config.get_config().
     filename : string
         The full path to the file (either from the 'file' CSV column or downloaded from somewhere).
     file_fieldname: string
         The name of the CSV column containing the filename. None if the file isn't
         in a CSV field (e.g., when config['paged_content_from_directories'] is True).
     node_csv_row: OrderedDict
         E.g., OrderedDict([('file', 'IMG_5083.JPG'), ('id', '05'), ('title', 'Alcatraz Island').
     node_id: string
         The nid of the parent media's parent node.
     Returns
     -------
     int|bool|None
         The file ID (int) of the successfully created file; False if there is insufficient
         information to create the file or file creation failed, or None if config['nodes_only'].
    """
    if config["nodes_only"] is True:
        return None

    if config["task"] == "add_media" or config["task"] == "create":
        if (
            file_fieldname is not None
            and len(node_csv_row[file_fieldname].strip()) == 0
        ):
            return None

    is_remote = False
    filename = filename.strip()

    if filename.startswith("http"):
        remote_file_http_response_code = ping_remote_file(config, filename)
        if remote_file_http_response_code != 200:
            return False

        file_path = download_remote_file(
            config, filename, file_fieldname, node_csv_row, node_id
        )
        if file_path is False:
            return False
        filename = file_path.split("/")[-1]
        is_remote = True
    elif os.path.isabs(filename):
        # Validate that the file exists
        if check_file_exists(config, filename) is False:
            logging.error(
                'File not created for CSV row "%s": file "%s" does not exist.',
                node_csv_row[config["id_field"]],
                filename,
            )
            return False
        file_path = filename
    elif filename.startswith(config["file_systems"]):
        details = issue_request(
            config,
            "POST",
            "/api/server-file",
            {"Content-Type": "application/json"},
            {"path": filename, "retval": "fid"},
        )
        if details.ok:
            data = details.json()
            return int(data["fid"])

        else:
            logging.error(
                f"File creation for row {node_csv_row[config['id_field']]} returned code:{details.status_code} with message{details.text}"
            )
            return False

    else:
        if check_file_exists(config, filename) is False:
            logging.error(
                'File not created for CSV row "%s": file "%s" does not exist.',
                node_csv_row[config["id_field"]],
                filename,
            )
            return False
        file_path = os.path.join(config["input_dir"], filename)

    media_type = set_media_type(config, file_path, file_fieldname, node_csv_row)

    if media_type in config["media_type_file_fields"]:
        media_file_field = config["media_type_file_fields"][media_type]
    else:
        logging.error(
            'File not created for CSV row "%s": media type "%s" not recognized.',
            node_csv_row[config["id_field"]],
            media_type,
        )
        return False

    # Requests/urllib3 requires filenames used in Content-Disposition headers to be encoded as latin-1.
    # Since it is impossible to reliably convert to latin-1 without knowing the source encoding of the filename
    # (which may or may not have originated on the machine running Workbench, so sys.stdout.encoding isn't reliable),
    # the best we can do for now is to use unidecode to replace non-ASCII characters in filenames with their ASCII
    # equivalents (at least the unidecode() equivalents). Also, while Requests requires filenames to be encoded
    # in latin-1, Drupal passes filenames through its validateUtf8() function. So ASCII is a low common denominator
    # of both requirements.
    ascii_only = string_is_ascii(filename)
    if ascii_only is False:
        original_filename = copy.copy(filename)
        filename = unidecode(filename)
        logging.warning(
            "Filename '"
            + original_filename
            + "' contains non-ASCII characters, normalized to '"
            + filename
            + "'."
        )

    file_endpoint_path = (
        "/file/upload/media/" + media_type + "/" + media_file_field + "?_format=json"
    )
    file_headers = {
        "Content-Type": "application/octet-stream",
        "Content-Disposition": 'file; filename="' + filename + '"',
    }

    binary_data = open(file_path, "rb")

    try:
        file_response = issue_request(
            config, "POST", file_endpoint_path, file_headers, "", binary_data
        )
        if file_response.status_code == 201:
            file_json = json.loads(file_response.text)
            file_id = file_json["fid"][0]["value"]
            # For now, we can only validate checksums for files named in the 'file' CSV column.
            # See https://github.com/mjordan/islandora_workbench/issues/307.
            if config["fixity_algorithm"] is not None and file_fieldname == "file":
                file_uuid = file_json["uuid"][0]["value"]
                hash_from_drupal = get_file_hash_from_drupal(
                    config, file_uuid, config["fixity_algorithm"]
                )
                hash_from_local = get_file_hash_from_local(
                    config, file_path, config["fixity_algorithm"]
                )
                if hash_from_drupal == hash_from_local:
                    logging.info(
                        'Local and Drupal %s checksums for file "%s" (%s) match.',
                        config["fixity_algorithm"],
                        file_path,
                        hash_from_local,
                    )
                else:
                    print(
                        "Warning: local and Drupal checksums for '"
                        + file_path
                        + "' do not match. See the log for more detail."
                    )
                    logging.warning(
                        'Local and Drupal %s checksums for file "%s" (named in CSV row "%s") do not match (local: %s, Drupal: %s).',
                        config["fixity_algorithm"],
                        file_path,
                        node_csv_row[config["id_field"]],
                        hash_from_local,
                        hash_from_drupal,
                    )
                if "checksum" in node_csv_row:
                    if hash_from_local == node_csv_row["checksum"].strip():
                        logging.info(
                            'Local %s checksum and value in the CSV "checksum" field for file "%s" (%s) match.',
                            config["fixity_algorithm"],
                            file_path,
                            hash_from_local,
                        )
                    else:
                        print(
                            "Warning: local checksum and value in CSV for '"
                            + file_path
                            + "' do not match. See the log for more detail."
                        )
                        logging.warning(
                            'Local %s checksum and value in the CSV "checksum" field for file "%s" (named in CSV row "%s") do not match (local: %s, CSV: %s).',
                            config["fixity_algorithm"],
                            file_path,
                            node_csv_row[config["id_field"]],
                            hash_from_local,
                            node_csv_row["checksum"],
                        )
            if is_remote and config["delete_tmp_upload"] is True:
                containing_folder = os.path.join(
                    config["temp_dir"],
                    re.sub("[^A-Za-z0-9]+", "_", node_csv_row[config["id_field"]]),
                )
                try:
                    # E.g., on Windows, "[WinError 32] The process cannot access the file because it is being used by another process"
                    shutil.rmtree(containing_folder)
                except PermissionError as e:
                    logging.error(e)

            return file_id
        else:
            logging.error(
                'File not created for "'
                + file_path
                + '", POST request to "%s" returned an HTTP status code of "%s" and a response body of %s.',
                file_endpoint_path,
                file_response.status_code,
                file_response.content,
            )
            return False
    except requests.exceptions.RequestException as e:
        logging.error(e)
        return False


def create_media(
    config, filename, file_fieldname, node_id, csv_row, media_use_tid=None
):
    """Creates a media in Drupal.

    Parameters
    ----------
     config : dict
         The configuration settings defined by workbench_config.get_config().
     filename : string
         The value of the CSV 'file' field for the current node.
     file_fieldname: string
         The name of the CSV column containing the filename. None if the file isn't
         in a CSV field (e.g., when config['paged_content_from_directories'] is True).
     node_id: string
         The ID of the node to attach the media to. This is False if file creation failed.
     csv_row: OrderedDict
         E.g., OrderedDict([('file', 'IMG_5083.JPG'), ('id', '05'), ('title', 'Alcatraz Island').
         Could be either a CSV row describing nodes (e.g. during 'create' tasks) or describing
         media (e.g. during 'add_media' tasks).
     media_use_tid : int|str
         A valid term ID (or a subdelimited list of IDs) from the Islandora Media Use vocabulary.
     Returns
     -------
     int|False
          The HTTP status code from the attempt to create the media, False if
          it doesn't have sufficient information to create the media, or None
          if config['nodes_only'] is True.
    """
    if config["nodes_only"] is True:
        return None

    if len(filename.strip()) == 0:
        if file_fieldname is None:
            message = (
                'Media not created because field "'
                + file_fieldname
                + '" in CSV row with ID "'
                + csv_row[config["id_field"]]
                + '" is empty.'
            )
            logging.error(message)
            return False

    if check_file_exists(config, filename) is False:
        if file_fieldname is None:
            message = (
                'Media not created because file "' + filename + '" could not be found.'
            )
        else:
            message = (
                'Media not created because file "'
                + filename
                + '" identified in field "'
                + file_fieldname
                + '" in CSV row with ID "'
                + csv_row[config["id_field"]]
                + '" could not be found.'
            )
        logging.error(message)
        return False

    # Importing the workbench_fields module at the top of this module with the
    # rest of the imports causes a circular import exception, so we do it here.
    import workbench_fields

    if value_is_numeric(node_id) is False:
        node_id = get_nid_from_url_alias(config, node_id)

    # media_type_for_oembed_check = set_media_type(config, filename, file_fieldname, node_csv_row)
    media_type = set_media_type(config, filename, file_fieldname, csv_row)

    if media_type in get_oembed_media_types(config):
        # file_result must be an integer.
        file_result = -1
    else:
        file_result = create_file(config, filename, file_fieldname, csv_row, node_id)

    if filename.startswith("http"):
        if file_result > 0:
            filename = get_preprocessed_file_path(
                config, file_fieldname, csv_row, node_id, False
            )

    if isinstance(file_result, int):
        if "media_use_tid" in csv_row and len(csv_row["media_use_tid"]) > 0:
            media_use_tid_value = csv_row["media_use_tid"]
        else:
            media_use_tid_value = config["media_use_tid"]

        if media_use_tid is not None:
            media_use_tid_value = media_use_tid

        media_use_tids = []
        media_use_terms = str(media_use_tid_value).split(config["subdelimiter"])
        for media_use_term in media_use_terms:
            if value_is_numeric(media_use_term):
                media_use_tids.append(media_use_term)
            if not value_is_numeric(
                media_use_term
            ) and media_use_term.strip().startswith("http"):
                media_use_tids.append(get_term_id_from_uri(config, media_use_term))
            if not value_is_numeric(
                media_use_term
            ) and not media_use_term.strip().startswith("http"):
                media_use_tids.append(
                    find_term_in_vocab(
                        config, "islandora_media_use", media_use_term.strip()
                    )
                )

        media_bundle_response_code = ping_media_bundle(config, media_type)
        if media_bundle_response_code == 404:
            message = (
                'File "'
                + filename
                + '" identified in CSV row '
                + file_fieldname
                + " will create a media of type ("
                + media_type
                + "), but that media type is not configured in the destination Drupal."
            )
            logging.error(message)
            return False

        media_field = config["media_type_file_fields"][media_type]
        if media_type in get_oembed_media_types(config):
            if "title" in csv_row:
                # WIP on #572: 'title' applies to node CSVs, for media, it should be 'name'.
                media_name = csv_row["title"]
            else:
                media_name = get_node_title_from_nid(config, node_id)
                if not media_name:
                    message = 'Cannot access node " + node_id + ", so cannot get its title for use in media title. Using oEmbed URL instead.'
                    logging.warning(message)
                    media_name = os.path.basename(filename)
        else:
            media_name = os.path.basename(filename)

        if config["use_node_title_for_media_title"]:
            if "title" in csv_row:
                # WIP on #572: 'title' applies to node CSVs, for media, it should be 'name'.
                media_name = csv_row["title"]
            else:
                media_name = get_node_title_from_nid(config, node_id)
                if not media_name:
                    message = 'Cannot access node " + node_id + ", so cannot get its title for use in media title. Using filename instead.'
                    logging.warning(message)
                    media_name = os.path.basename(filename)
        elif config["use_nid_in_media_title"]:
            media_name = f"{node_id}-Original File"
        elif config["field_for_media_title"]:
            if len(csv_row[config["field_for_media_title"]]) > 0:
                media_name = csv_row[config["field_for_media_title"]][:255]
        else:
            media_name = os.path.basename(filename)

        # Create a media from an oEmbed URL.
        if media_type in get_oembed_media_types(config):
            media_json = {
                "bundle": [
                    {
                        "target_id": media_type,
                        "target_type": "media_type",
                    }
                ],
                "name": [{"value": media_name}],
                media_field: [{"value": filename}],
                "field_media_of": [{"target_id": int(node_id), "target_type": "node"}],
                "field_media_use": [
                    {"target_id": media_use_tids[0], "target_type": "taxonomy_term"}
                ],
            }
        # Create a media from a local or remote file.
        else:
            media_json = {
                "bundle": [
                    {
                        "target_id": media_type,
                        "target_type": "media_type",
                    }
                ],
                "name": [{"value": media_name}],
                media_field: [{"target_id": file_result, "target_type": "file"}],
                "field_media_of": [{"target_id": int(node_id), "target_type": "node"}],
                "field_media_use": [
                    {"target_id": media_use_tids[0], "target_type": "taxonomy_term"}
                ],
            }

            # Use the 'paged_content_additional_page_media' config setting to determine
            # if any hOCR files are being added, since we need to explicitly define hOCR
            # media's MIME type as "text/vnd.hocr+html".
            file_is_hocr = False
            if "paged_content_additional_page_media" in config:
                file_mimetype = get_mimetype_from_extension(config, filename)
                for uri_to_extension_mapping in config[
                    "paged_content_additional_page_media"
                ]:
                    if (
                        "https://discoverygarden.ca/use#hocr"
                        in uri_to_extension_mapping
                    ):
                        file_is_hocr = True

            if file_is_hocr is True:
                media_use_uri = get_term_uri(config, media_use_tids[0])
                if (
                    media_use_uri == "https://discoverygarden.ca/use#hocr"
                    and file_mimetype == "text/vnd.hocr+html"
                ):
                    media_json.update({"field_mime_type": [{"value": file_mimetype}]})

        if "published" in csv_row and len(csv_row["published"]) > 0:
            media_json["status"] = {"value": csv_row["published"]}

        # Populate some media type-specific fields on the media. @todo: We need a generalized way of
        # determining which media fields are required, e.g. checking the media type configuration.
        if media_field == "field_media_image":
            if "image_alt_text" in csv_row and len(csv_row["image_alt_text"]) > 0:
                alt_text = clean_image_alt_text(csv_row["image_alt_text"])
                media_json[media_field][0]["alt"] = alt_text
            else:
                alt_text = clean_image_alt_text(media_name)
                media_json[media_field][0]["alt"] = alt_text

        # extracted_text media must have their field_edited_text field populated for full text indexing.
        # Text must be encoded as utf-8.
        if media_type == "extracted_text":
            if check_file_exists(config, filename):
                media_json["field_edited_text"] = list()
                if filename.startswith(config["file_systems"]):
                    details = issue_request(
                        config,
                        "POST",
                        "/api/server-file",
                        {"Content-Type": "application/json"},
                        {"path": filename, "retval": "contents"},
                    )
                    if details.ok:
                        data = details.json()
                        media_json["field_edited_text"].append(data["contents"])
                    else:
                        logging.error(
                            f"Could not extract text from {filename}.  Process returned code:{details.status_code} with message{details.text}"
                        )

                elif os.path.isabs(filename) is False:
                    filename = os.path.join(config["input_dir"], filename)
                    try:
                        extracted_text_file = open(filename, "r", -1, "utf-8-sig")
                        media_json["field_edited_text"].append(
                            {"value": extracted_text_file.read()}
                        )
                    except Exception as e:
                        logging.error(
                            f'Extracted text file "{filename}" caused a problem that prevented it from being ingested ({e}).'
                        )
            else:
                logging.error("Extracted text file %s not found.", filename)
            if check_file_exists(config, filename):
                media_json["field_edited_text"] = list()

                if os.path.isabs(filename) is False:
                    filename = os.path.join(config["input_dir"], filename)
                try:
                    extracted_text_file = open(filename, "r", -1, "utf-8-sig")
                    media_json["field_edited_text"].append(
                        {"value": extracted_text_file.read()}
                    )
                except Exception as e:
                    logging.error(
                        f'Extracted text file "{filename}" caused a problem that prevented it from being ingested ({e}).'
                    )
            else:
                logging.error("Extracted text file %s not found.", filename)

        # WIP on #572: if this is an `add_media` task, add fields in CSV to media_json, being careful to
        # not stomp on existing fields. Block below is copied from create() and needs to be modified to
        # suit creation of custom fields in add_media tasks.
        """
        if config['task'] == 'add_media':
            field_definitions = get_field_definitions(config, 'media')

            # Add custom (non-required) CSV fields.
            entity_fields = get_entity_fields(config, 'node', config['content_type'])
            # Only add config['id_field'] to required_fields if it is not a node field.
            required_fields = ['file', 'title']
            if config['id_field'] not in entity_fields:
                required_fields.append(config['id_field'])
            custom_fields = list(set(csv_column_headers) - set(required_fields))
            additional_files_entries = get_additional_files_config(config)
            for custom_field in custom_fields:
                # Skip processing field if empty.
                if len(row[custom_field].strip()) == 0:
                    continue

                if len(additional_files_entries) > 0:
                    if custom_field in additional_files_entries.keys():
                        continue

                # This field can exist in the CSV to create parent/child
                # relationships and is not a Drupal field.
                if custom_field == 'parent_id':
                    continue

                # 'langcode' is a core Drupal field, but is not considered a "base field".
                if custom_field == 'langcode':
                    continue

                # 'image_alt_text' is a reserved CSV field.
                if custom_field == 'image_alt_text':
                    continue

                # 'url_alias' is a reserved CSV field.
                if custom_field == 'url_alias':
                    continue

                # 'media_use_tid' is a reserved CSV field.
                if custom_field == 'media_use_tid':
                    continue

                # 'checksum' is a reserved CSV field.
                if custom_field == 'checksum':
                    continue

                # We skip CSV columns whose headers use the 'media:video:field_foo' media track convention.
                if custom_field.startswith('media:'):
                    continue

                # Assemble Drupal field structures from CSV data. If new field types are added to
                # workbench_fields.py, they need to be registered in the following if/elif/else block.

                # Entity reference fields (taxonomy_term and node).
                if field_definitions[custom_field]['field_type'] == 'entity_reference':
                    entity_reference_field = workbench_fields.EntityReferenceField()
                    node = entity_reference_field.create(config, field_definitions, node, row, custom_field)

                # Typed relation fields.
                elif field_definitions[custom_field]['field_type'] == 'typed_relation':
                    typed_relation_field = workbench_fields.TypedRelationField()
                    node = typed_relation_field.create(config, field_definitions, node, row, custom_field)

                # Geolocation fields.
                elif field_definitions[custom_field]['field_type'] == 'geolocation':
                    geolocation_field = workbench_fields.GeolocationField()
                    node = geolocation_field.create(config, field_definitions, node, row, custom_field)

                # Link fields.
                elif field_definitions[custom_field]['field_type'] == 'link':
                    link_field = workbench_fields.LinkField()
                    node = link_field.create(config, field_definitions, node, row, custom_field)

                # Authority Link fields.
                elif field_definitions[custom_field]['field_type'] == 'authority_link':
                    link_field = workbench_fields.AuthorityLinkField()
                    node = link_field.create(config, field_definitions, node, row, custom_field)

                # For non-entity reference and non-typed relation fields (text, integer, boolean etc.).
                else:
                    simple_field = workbench_fields.SimpleField()
                    node = simple_field.create(config, field_definitions, node, row, custom_field)
        """

        # Create media_track files here, since they should exist before we create the parent media.
        # @todo WIP on #572: if there are track file fields in the add_media CSV, create them here, as below for track file field in node CSV.
        media_types_with_track_files = config["media_track_file_fields"].keys()
        valid_media_track_fields = list()
        if media_type in media_types_with_track_files:
            # Check for fields in node_csv_row that have names like 'media:video:field_track' and validate their contents.
            # Note: Does not validate the fields' configuration (--check does that).
            node_csv_field_names = list(csv_row.keys())
            if len(node_csv_field_names):
                media_track_fields = [
                    x
                    for x in node_csv_field_names
                    if x.startswith("media:" + media_type)
                ]
                # Should be just one field per media type.
                if (
                    len(media_track_fields)
                    and media_type in config["media_track_file_fields"]
                ):
                    for media_track_field in media_track_fields:
                        if (
                            validate_media_track_value(csv_row[media_track_field])
                            is True
                        ):
                            valid_media_track_fields.append(media_track_field)

            # Create the media track file(s) for each entry in valid_potential_media_track_fields (there could be multiple track entries).
            if len(valid_media_track_fields):
                media_track_field_data = []
                # Should be just one field per media type.
                fully_qualified_media_track_field_name = valid_media_track_fields[0]
                media_track_entries = split_media_track_string(
                    config, csv_row[fully_qualified_media_track_field_name]
                )
                for media_track_entry in media_track_entries:
                    media_track_field_name_parts = (
                        fully_qualified_media_track_field_name.split(":")
                    )
                    try:
                        create_track_file_result = create_file(
                            config,
                            media_track_entry["file_path"],
                            fully_qualified_media_track_field_name,
                            csv_row,
                            node_id,
                        )
                    except Exception as e:
                        media_track_entry_file_path = media_track_entry["file_path"]
                        logging.error(
                            f'Media track file "{media_track_entry_file_path}" caused a problem that prevented it from being ingested ({e}).'
                        )
                        continue

                    if create_track_file_result is not False and isinstance(
                        create_track_file_result, int
                    ):
                        # /entity/file/xxx?_format=json will return JSON containing the file's 'uri'.
                        track_file_info_response = issue_request(
                            config,
                            "GET",
                            f"/entity/file/{create_track_file_result}?_format=json",
                        )
                        track_file_info = json.loads(track_file_info_response.text)
                        track_file_url = track_file_info["uri"][0]["url"]
                        logging.info(
                            f"Media track file {config['host'].rstrip('/')}{track_file_url} created from {media_track_entry['file_path']}."
                        )
                        track_file_data = {
                            "target_id": track_file_info["fid"][0]["value"],
                            "kind": media_track_entry["kind"],
                            "label": media_track_entry["label"],
                            "srclang": media_track_entry["srclang"],
                            "default": False,
                            "url": track_file_url,
                        }
                        media_track_field_data.append(track_file_data)
                    else:
                        # If there are any failures, proceed with creating the parent media.
                        logging.error(
                            f"Media track using {media_track_entry['file_path']} not created; create_file returned {create_track_file_result}."
                        )

                    # Set the "default" attribute of the first media track.
                    if media_track_field_data:
                        media_track_field_data[0]["default"] = True
                        media_json[media_track_field_name_parts[2]] = (
                            media_track_field_data
                        )

        media_endpoint_path = (
            "/entity/media?_format=json"
            if config["standalone_media_url"]
            else "/entity/media"
        )
        media_headers = {"Content-Type": "application/json"}
        try:
            media_response = issue_request(
                config, "POST", media_endpoint_path, media_headers, media_json
            )
            if media_response.status_code != 201:
                logging.error(
                    'Media not created, POST request to "%s" returned an HTTP status code of "%s" and a response body of %s.',
                    media_endpoint_path,
                    media_response.status_code,
                    media_response.content,
                )
                logging.error(
                    'JSON request body used in previous POST to "%s" was %s.',
                    media_endpoint_path,
                    media_json,
                )

            if len(media_use_tids) > 1:
                media_response_body = json.loads(media_response.text)
                if "mid" in media_response_body:
                    media_id = media_response_body["mid"][0]["value"]
                    patch_media_use_terms(config, media_id, media_type, media_use_tids)
                else:
                    logging.error(
                        "Could not PATCH additional media use terms to media created from '%s' because media ID is not available.",
                        filename,
                    )

            # Execute media-specific post-create scripts, if any are configured.
            if "media_post_create" in config and len(config["media_post_create"]) > 0:
                for command in config["media_post_create"]:
                    post_task_output, post_task_return_code = (
                        execute_entity_post_task_script(
                            command,
                            config["config_file_path"],
                            media_response.status_code,
                            media_response.text,
                        )
                    )
                    if post_task_return_code == 0:
                        logging.info(
                            "Post media create script "
                            + command
                            + " executed successfully."
                        )
                    else:
                        logging.error(
                            "Post media create script " + command + " failed."
                        )

            return media_response.status_code
        except requests.exceptions.RequestException as e:
            logging.error(e)
            return False

    if file_result is False:
        return file_result

    if file_result is None:
        return file_result


def patch_media_fields(config, media_id, media_type, node_csv_row):
    """Patch the media entity with base fields from the parent node."""
    media_json = {"bundle": [{"target_id": media_type}]}

    for field_name, field_value in node_csv_row.items():
        if field_name == "created" and len(field_value) > 0:
            media_json["created"] = [{"value": field_value}]
        if field_name == "uid" and len(field_value) > 0:
            media_json["uid"] = [{"target_id": field_value}]

    if len(media_json) > 1:
        if config["standalone_media_url"] is True:
            endpoint = config["host"] + "/media/" + str(media_id) + "?_format=json"
        else:
            endpoint = config["host"] + "/media/" + str(media_id) + "/edit?_format=json"
        headers = {"Content-Type": "application/json"}
        response = issue_request(config, "PATCH", endpoint, headers, media_json)
        if response.status_code == 200:
            logging.info("Media %s fields updated to match parent node's.", endpoint)
        else:
            logging.warning(
                "Media %s fields not updated to match parent node's.", endpoint
            )


def patch_media_use_terms(config, media_id, media_type, media_use_tids):
    """Patch the media entity's field_media_use."""
    media_json = {"bundle": [{"target_id": media_type}]}

    media_use_tids_json = []
    for media_use_tid in media_use_tids:
        media_use_tids_json.append(
            {"target_id": media_use_tid, "target_type": "taxonomy_term"}
        )

    media_json["field_media_use"] = media_use_tids_json
    if config["standalone_media_url"] is True:
        endpoint = config["host"] + "/media/" + str(media_id) + "?_format=json"
    else:
        endpoint = config["host"] + "/media/" + str(media_id) + "/edit?_format=json"
    headers = {"Content-Type": "application/json"}
    response = issue_request(config, "PATCH", endpoint, headers, media_json)
    if response.status_code == 200:
        logging.info("Media %s Islandora Media Use terms updated.", endpoint)
    else:
        logging.warning("Media %s Islandora Media Use terms not updated.", endpoint)


def clean_image_alt_text(input_string):
    """Strip out HTML markup to guard against CSRF in alt text."""
    cleaned_string = re.sub("<[^<]+?>", "", input_string)
    return cleaned_string


def patch_image_alt_text(config, media_id, csv_row):
    """Patch the alt text value for an image media. Use the parent node's title
    unless the CSV record contains an image_alt_text field with something in it.
    """
    if config["standalone_media_url"] is True:
        get_media_endpoint = (
            config["host"] + "/media/" + str(media_id) + "?_format=json"
        )
    else:
        get_media_endpoint = (
            config["host"] + "/media/" + str(media_id) + "/edit?_format=json"
        )
    get_media_headers = {"Content-Type": "application/json"}
    get_media_response = issue_request(
        config, "GET", get_media_endpoint, get_media_headers
    )
    if get_media_response.status_code == 200:
        get_media_response_body = json.loads(get_media_response.text)
        field_media_image_target_id = get_media_response_body["field_media_image"][0][
            "target_id"
        ]
    else:
        logging.error(
            f"Media {get_media_endpoint} returned an HTTP status code of {get_media_response.status_code}."
        )
        return False

    for field_name, field_value in csv_row.items():
        if field_name == "title":
            alt_text = clean_image_alt_text(field_value)
        # "image_alt_text" can be in "create", "add_alt_text", or "update_alt_text" input CSV.
        if field_name == "image_alt_text":
            alt_text = clean_image_alt_text(field_value)

    max_image_alt_text_length = config["max_image_alt_text_length"]
    if len(alt_text) > max_image_alt_text_length:
        logging.warning(
            f'Alt text "{alt_text}" is longer than the configured maximum length ({max_image_alt_text_length}), skipping adding it to image.'
        )
        return False

    media_json = {
        "bundle": [{"target_id": "image"}],
        "field_media_image": [
            {"target_id": field_media_image_target_id, "alt": alt_text}
        ],
    }

    if config["standalone_media_url"] is True:
        patch_media_endpoint = (
            config["host"] + "/media/" + str(media_id) + "?_format=json"
        )
    else:
        patch_media_endpoint = (
            config["host"] + "/media/" + str(media_id) + "/edit?_format=json"
        )
    patch_media_headers = {"Content-Type": "application/json"}
    patch_media_response = issue_request(
        config, "PATCH", patch_media_endpoint, patch_media_headers, media_json
    )

    if patch_media_response.status_code != 200:
        logging.error("Alt text for image media %s not updated.", patch_media_endpoint)

    return patch_media_response.status_code


def remove_media_and_file(config, media_id):
    """Delete a media and the file associated with it."""
    # First get the media JSON.
    if config["standalone_media_url"] is True:
        get_media_url = config["host"] + "/media/" + str(media_id) + "?_format=json"
    else:
        get_media_url = (
            config["host"] + "/media/" + str(media_id) + "/edit?_format=json"
        )
    get_media_response = issue_request(config, "GET", get_media_url)
    get_media_response_body = json.loads(get_media_response.text)

    # See https://github.com/mjordan/islandora_workbench/issues/446 for background.
    if "message" in get_media_response_body and get_media_response_body[
        "message"
    ].startswith("No route found for"):
        message = f'Please visit {config["host"]}/admin/config/media/media-settings and uncheck the "Standalone media URL" option.'
        logging.error(message)
        sys.exit("Error: " + message)

    # See https://github.com/mjordan/islandora_workbench/issues/446 for background.
    if get_media_response.status_code == 403:
        message = (
            f'If the "Standalone media URL" option at {config["host"]}/admin/config/media/media-settings is unchecked, clear your Drupal cache and run Workbench again.'
            + ' If that doesn\'t work, try adding "standalone_media_url: true" to your configuration file.'
        )
        logging.error(message)
        sys.exit("Error: " + message)

    for file_field_name in file_fields:
        if file_field_name in get_media_response_body:
            try:
                file_id = get_media_response_body[file_field_name][0]["target_id"]
            except Exception as e:
                logging.error(
                    "Unable to get file ID for media %s (reason: %s); proceeding to delete media without file.",
                    media_id,
                    e,
                )
                file_id = None
            break

    # Delete the file first.
    if file_id is not None:
        file_endpoint = (
            config["host"] + "/entity/file/" + str(file_id) + "?_format=json"
        )
        file_response = issue_request(config, "DELETE", file_endpoint)
        if file_response.status_code == 204:
            logging.info("File %s (from media %s) deleted.", file_id, media_id)
        else:
            logging.error(
                "File %s (from media %s) not deleted (HTTP response code %s).",
                file_id,
                media_id,
                file_response.status_code,
            )

    # Delete any audio/video media_track files.
    media_bundle_name = get_media_response_body["bundle"][0]["target_id"]
    if media_bundle_name in config["media_track_file_fields"]:
        track_file_field = config["media_track_file_fields"][media_bundle_name]
        if (
            track_file_field in get_media_response_body
            and len(get_media_response_body[track_file_field]) > 0
        ):
            for track_file in get_media_response_body[track_file_field]:
                track_file_id = track_file["target_id"]
                track_file_endpoint = (
                    config["host"]
                    + "/entity/file/"
                    + str(track_file_id)
                    + "?_format=json"
                )
                track_file_response = issue_request(
                    config, "DELETE", track_file_endpoint
                )
                if track_file_response.status_code == 204:
                    logging.info(
                        "Media track file %s (from media %s) deleted.",
                        track_file_id,
                        media_id,
                    )
                else:
                    logging.error(
                        "Media track file %s (from media %s) not deleted (HTTP response code %s).",
                        track_file_id,
                        media_id,
                        track_file_response.status_code,
                    )

    # Then the media.
    if file_id is None or file_response.status_code == 204:
        if config["standalone_media_url"] is True:
            media_endpoint = (
                config["host"] + "/media/" + str(media_id) + "?_format=json"
            )
        else:
            media_endpoint = (
                config["host"] + "/media/" + str(media_id) + "/edit?_format=json"
            )
        media_response = issue_request(config, "DELETE", media_endpoint)
        if media_response.status_code == 204:
            logging.info("Media %s deleted.", media_id)
            return media_response.status_code
        else:
            logging.error(
                "Media %s not deleted (HTTP response code %s).",
                media_id,
                media_response.status_code,
            )
            return False

    return False


def get_preprocessed_input_csv_file_path(config):
    return (
        os.path.join(config["temp_dir"], os.path.basename(config["input_csv"]))
        + ".preprocessed"
    )


def get_csv_data(config, csv_file_target="node_fields", file_path=None):
    """Read the input CSV data and prepare it for use in all tasks that use an input CSV file.

    This function reads the source CSV file (or the CSV dump from Google Sheets or Excel),
    applies some prepocessing to each CSV record (specifically, it adds any CSV field
    templates that are registered in the config file, and it filters out any CSV
    records or lines in the CSV file that begine with a #), and finally, writes out
    a version of the CSV data to a file that appends .preprocessed to the input
    CSV file name. It is this .preprocessed file that is used in create, update, etc.
    tasks.
    """
    """Parameters
        ----------
        config : dict
            The configuration settings defined by workbench_config.get_config().
        csv_file_target: string
            Either 'node_fields' or 'taxonomy_fields'.
        file_path: string
            The path to the file to check (applies only to vocabulary CSVs).
        Returns
        -------
        preprocessed_csv_reader
            The CSV DictReader object.
    """
    if csv_file_target == "node_fields":
        file_path = config["input_csv"]

    if os.path.isabs(file_path):
        input_csv_path = file_path
    elif file_path.startswith("http") is True:
        input_csv_path = get_extracted_csv_file_path(config)
        if os.path.exists(input_csv_path):
            os.remove(input_csv_path)
        get_csv_from_google_sheet(config)
    elif file_path.endswith(".xlsx") is True:
        input_csv_path = get_extracted_csv_file_path(config)
        if os.path.exists(input_csv_path):
            os.remove(input_csv_path)
        get_csv_from_excel(config)
    else:
        input_csv_path = os.path.join(config["input_dir"], file_path)

    if not os.path.exists(input_csv_path):
        message = "CSV file " + input_csv_path + " not found."
        logging.error(message)
        sys.exit("Error: " + message)

    try:
        # 'utf-8-sig' encoding skips Microsoft BOM (0xef, 0xbb, 0xbf) at the start of files,
        # e.g. exported from Excel and has no effect when reading standard UTF-8 encoded files.
        csv_reader_file_handle = open(
            input_csv_path, "r", encoding="utf-8-sig", newline=""
        )
    except UnicodeDecodeError:
        message = (
            "Error: CSV file " + input_csv_path + " must be encoded in ASCII or UTF-8."
        )
        logging.error(message)
        sys.exit(message)

    preprocessed_csv_path = get_preprocessed_input_csv_file_path(config)

    csv_writer_file_handle = open(
        preprocessed_csv_path, "w+", newline="", encoding="utf-8"
    )
    # 'restval' is used to populate superfluous fields/labels.
    csv_reader = csv.DictReader(
        csv_reader_file_handle,
        delimiter=config["delimiter"],
        restval="stringtopopulateextrafields",
    )

    # Unfinished (e.g. still need to apply this to creating taxonomies) WIP on #559.
    if config["csv_headers"] == "labels" and config["task"] in [
        "create",
        "update",
        "create_terms",
        "update_terms",
    ]:
        """
        if config['task'] == 'create_terms' or config['task'] == 'update_terms':
            field_map = get_fieldname_map(config, 'taxonomy_term', config['vocab_id'], 'labels')
        else:
            field_map = get_fieldname_map(config, 'node', config['content_type'], 'labels')
        """
        csv_reader_fieldnames = replace_field_labels_with_names(
            config, csv_reader.fieldnames
        )
    else:
        csv_reader_fieldnames = csv_reader.fieldnames

    # Even though we check for the columrespective ID column n in the incoming CSV in check_input(),
    # we need to check it here as well since check_input() reads the CSV prior to those checks.
    id_columns = {
        "create": config["id_field"],
        "update": "node_id",
        "delete": "node_id",
        "add_media": "node_id",
        "delete_media": "media_id",
        "delete_media_by_node": "node_id",
        "update_media": "media_id",
        "create_terms": "term_name",
        "update_terms": "term_id",
        "export_csv": "node_id",
    }
    for task, id_column in id_columns.items():
        if (
            task == config["task"]
            and id_columns[config["task"]] not in csv_reader_fieldnames
        ):
            message = f'"{task}" tasks require a "{id_columns[task]}" CSV column. Please check your input CSV file and try again.'
            logging.error(message)
            sys.exit("Error: " + message)

    confirmed = []
    duplicates = []
    for item in csv_reader_fieldnames:
        if item not in confirmed:
            confirmed.append(item)
        else:
            duplicates.append(item)
    if len(duplicates) > 0:
        message = "Error: CSV has duplicate header names - " + ", ".join(duplicates)
        logging.error(message)
        sys.exit(message)
    csv_reader_fieldnames = [
        x for x in csv_reader_fieldnames if x not in config["ignore_csv_columns"]
    ]

    #  If configured to do so, add "field_viewer_override" to output CSV so we can autopopulate the field_viewer_override column.
    if config["task"] == "create" and (
        "field_viewer_override_extensions" in config
        or "field_viewer_override_models" in config
    ):
        if "field_viewer_override" not in csv_reader_fieldnames:
            csv_reader_fieldnames.append("field_viewer_override")

    # CSV field templates and CSV value templates currently apply only to node CSV files, not vocabulary CSV files.
    tasks = ["create", "update", "add_media"]
    if config["task"] in tasks and csv_file_target == "node_fields":
        # If the config file contains CSV field templates, append them to the CSV data.
        # Make a copy of the column headers so we can skip adding templates to the new CSV
        # if they're present in the source CSV. We don't want fields in the source CSV to be
        # stomped on by templates.
        csv_reader_fieldnames_orig = copy.copy(csv_reader_fieldnames)
        if "csv_field_templates" in config:
            for template in config["csv_field_templates"]:
                for field_name, field_value in template.items():
                    if field_name not in csv_reader_fieldnames_orig:
                        csv_reader_fieldnames.append(field_name)
        csv_writer = csv.DictWriter(
            csv_writer_file_handle,
            fieldnames=csv_reader_fieldnames,
            delimiter=config["delimiter"],
        )
        csv_writer.writeheader()
        row_num = 0
        unique_identifiers = []

        # Prepare any "csv_row_filters", which we apply to each row, below.
        if "csv_row_filters" in config and len(config["csv_row_filters"]) > 0:
            row_filters_is = dict()
            row_filters_isnot = dict()
            # First defne the field/operator pairs.
            for filter_config in config["csv_row_filters"]:
                filter_group = filter_config.split(":", 2)
                if filter_group[1] == "is":
                    filter_group_field = filter_group[0]
                    filter_group_value = filter_group[2]
                    row_filters_is[filter_group_field] = []
                if filter_group[1] == "isnot":
                    filter_group_field = filter_group[0]
                    filter_group_value = filter_group[2]
                    row_filters_isnot[filter_group_field] = []

            # Then populate the lists of filter values.
            for filter_config in config["csv_row_filters"]:
                filter_group = filter_config.split(":", 2)
                # Prepare the '' filter value.
                if filter_group[2] == "''" or filter_group[2] == '""':
                    filter_group[2] = ""
                if filter_group[1] == "is":
                    filter_group_field = filter_group[0]
                    filter_group_value = filter_group[2]
                    row_filters_is[filter_group_field].append(
                        filter_group_value.strip()
                    )
                if filter_group[1] == "isnot":
                    filter_group_field = filter_group[0]
                    filter_group_value = filter_group[2]
                    row_filters_isnot[filter_group_field].append(
                        filter_group_value.strip()
                    )

        # We subtract 1 from config['csv_start_row'] so user's expectation of the actual
        # start row match up with Python's 0-based counting.
        if config["csv_start_row"] > 0:
            csv_start_row = config["csv_start_row"] - 1
        else:
            csv_start_row = config["csv_start_row"]

        for row in itertools.islice(csv_reader, csv_start_row, config["csv_stop_row"]):
            row_num += 1

            csv_rows_to_process_allowed_tasks = ["create", "update", "add_media"]
            # If the value in config['csv_rows_to_process'] is a path to a file, skip rows not identified in the file.
            if (
                "csv_rows_to_process" in config
                and config["task"] in csv_rows_to_process_allowed_tasks
                and len(config["csv_rows_to_process"]) > 0
                and isinstance(config["csv_rows_to_process"], str)
            ):
                path_to_ids_file = os.path.abspath(config["csv_rows_to_process"])
                if os.path.exists(path_to_ids_file):
                    with open(path_to_ids_file) as fh:
                        ids_to_process = fh.read().splitlines()
                        ids_to_process = [x for x in ids_to_process if x]
                else:
                    message = f'File identified in the "csv_rows_to_process" config setting ({path_to_ids_file}) cannot be found.'
                    logging.error(message)
                    sys.exit("Error: " + message)
                if row[config["id_field"]] not in ids_to_process:
                    continue

            # If the value of in config['csv_rows_to_process'] is a list, skip the rows not in the list.
            if (
                "csv_rows_to_process" in config
                and config["task"] in csv_rows_to_process_allowed_tasks
                and len(config["csv_rows_to_process"]) > 0
                and isinstance(config["csv_rows_to_process"], list)
            ):
                config["csv_rows_to_process"] = [
                    str(x) for x in config["csv_rows_to_process"]
                ]
                if row[config["id_field"]] not in config["csv_rows_to_process"]:
                    continue

            # Apply the "is" and "isnot" csv_row_filters defined defined above. If the field/value
            # combo is in the 'isnot' list, skip this row.
            filter_out_this_csv_row = False
            if "csv_row_filters" in config and len(config["csv_row_filters"]) > 0:
                if len(row_filters_isnot) > 0:
                    for filter_field, filter_values in row_filters_isnot.items():
                        if len(filter_values) > 0 and filter_field in row:
                            # Split out multiple field values to test each one.
                            values_in_row_field = row[filter_field].split(
                                config["subdelimiter"]
                            )
                            for value_in_row_field in values_in_row_field:
                                filter_out_this_csv_row = False
                                if value_in_row_field.strip() in filter_values:
                                    filter_out_this_csv_row = True
                                else:
                                    break
                if filter_out_this_csv_row is True:
                    continue

                # If the field/value combo is not in the 'is' list, skip this row.
                if len(row_filters_is) > 0:
                    for filter_field, filter_values in row_filters_is.items():
                        if len(filter_values) > 0 and filter_field in row:
                            # Split out multiple field values to test each one.
                            values_in_row_field = row[filter_field].split(
                                config["subdelimiter"]
                            )
                            for value_in_row_field in values_in_row_field:
                                filter_out_this_csv_row = False
                                if value_in_row_field.strip() not in filter_values:
                                    filter_out_this_csv_row = True
                                else:
                                    break
                if filter_out_this_csv_row is True:
                    continue

            # Remove columns specified in config['ignore_csv_columns'].
            if len(config["ignore_csv_columns"]) > 0:
                for column_to_ignore in config["ignore_csv_columns"]:
                    if column_to_ignore in row:
                        del row[column_to_ignore]

            if "csv_field_templates" in config:
                for template in config["csv_field_templates"]:
                    for field_name, field_value in template.items():
                        if field_name not in csv_reader_fieldnames_orig:
                            row[field_name] = field_value

            # Skip CSV records whose first column begin with #.
            if not list(row.values())[0].startswith("#"):
                try:
                    unique_identifiers.append(row[config["id_field"]])

                    if (
                        "csv_value_templates" in config
                        and len(config["csv_value_templates"]) > 0
                    ):
                        row = apply_csv_value_templates(
                            config, "csv_value_templates", row
                        )

                    #  If configured to do so, populate field_viewer_override column.
                    if config["task"] == "create" and (
                        "field_viewer_override_extensions" in config
                        or "field_viewer_override_models" in config
                    ):
                        row["field_viewer_override"] = (
                            get_field_viewer_override_from_condition(config, row)
                        )

                    # Convert node URLs into node IDs.
                    if config["task"] in [
                        "update",
                        "delete",
                        "add_media",
                        "delete_media_by_node",
                    ]:
                        incoming_node_id = copy.copy(row["node_id"])
                        if value_is_numeric(row["node_id"]) is False:
                            row["node_id"] = get_nid_from_url_alias(
                                config, row["node_id"]
                            )
                            if row["node_id"] is False:
                                logging.warning(
                                    f'URL "{incoming_node_id}" not found or is not accessible, skipping update.'
                                )

                    row = clean_csv_values(config, row)
                    csv_writer.writerow(row)
                except ValueError:
                    # Note: this message is also generated in check_input().
                    message = (
                        "Row "
                        + str(row_num)
                        + " (ID "
                        + row[config["id_field"]]
                        + ') of the CSV file "'
                        + input_csv_path
                        + '" '
                        + "has more columns ("
                        + str(len(row))
                        + ") than there are headers ("
                        + str(len(csv_reader.fieldnames))
                        + ")."
                    )
                    logging.error(message)
                    print("Error: " + message)
                    sys.exit(message)

        repeats = set(
            ([x for x in unique_identifiers if unique_identifiers.count(x) > 1])
        )
        if len(repeats) > 0:
            message = (
                "Duplicate identifiers in column "
                + config["id_field"]
                + " found: "
                + ",".join(repeats)
                + "."
            )
            logging.error(message)
            sys.exit("Error: " + message)
    # "if" applies to create and update tasks for nodes; "else" applies to everything else.
    else:
        csv_writer = csv.DictWriter(
            csv_writer_file_handle,
            fieldnames=csv_reader_fieldnames,
            delimiter=config["delimiter"],
        )
        csv_writer.writeheader()
        row_num = 0
        # We subtract 1 from config['csv_start_row'] so user's expectation of the actual
        # start row match up with Python's 0-based counting.
        if config["csv_start_row"] > 0:
            csv_start_row = config["csv_start_row"] - 1
        else:
            csv_start_row = config["csv_start_row"]
        for row in itertools.islice(csv_reader, csv_start_row, config["csv_stop_row"]):
            row_num += 1
            # Remove columns specified in config['ignore_csv_columns'].
            if len(config["ignore_csv_columns"]) > 0:
                for column_to_ignore in config["ignore_csv_columns"]:
                    if column_to_ignore in row:
                        del row[column_to_ignore]

            # Skip CSV records whose first column begin with #.
            if not list(row.values())[0].startswith("#"):
                try:
                    row = clean_csv_values(config, row)
                    csv_writer.writerow(row)
                except ValueError:
                    # Note: this message is also generated in check_input().
                    message = (
                        "Row "
                        + str(row_num)
                        + " (ID "
                        + row[config["id_field"]]
                        + ') of the CSV file "'
                        + input_csv_path
                        + '" '
                        + "has more columns ("
                        + str(len(row))
                        + ") than there are headers ("
                        + str(len(csv_reader.fieldnames))
                        + ")."
                    )
                    logging.error(message)
                    sys.exit("Error: " + message)

            # Convert node URLs into node IDs.
            if config["task"] in [
                "update",
                "delete",
                "add_media",
                "delete_media_by_node",
            ]:
                if value_is_numeric(row["node_id"]) is False:
                    row["node_id"] = get_nid_from_url_alias(config, row["node_id"])

    csv_writer_file_handle.close()
    preprocessed_csv_reader_file_handle = open(
        preprocessed_csv_path, "r", encoding="utf-8"
    )
    preprocessed_csv_reader = csv.DictReader(
        preprocessed_csv_reader_file_handle,
        delimiter=config["delimiter"],
        restval="stringtopopulateextrafields",
    )
    return preprocessed_csv_reader


def find_term_in_vocab(config, vocab_id, term_name_to_find):
    """Query the Term from term name View using the vocab_id to see if term_name_to_find is
    is found in that vocabulary. If so, returns the term ID; if not returns False. If
    more than one term found, returns the term ID of the first one. Also populates global
    lists of terms (checked_terms and newly_created_terms) to reduce queries to Drupal.
    """
    """Parameters
    ----------
    config : dict
        The configuration settings defined by workbench_config.get_config().
    vocab_id: string
        The vocabulary ID to use in the query to find the term.
    field_name: string
        The field's machine name.
    term_name_to_find: string
        The term name from CSV.
    Returns
    -------
    int|boolean
        The term ID, existing or newly created. Returns False if term name
        is not found (or config['validate_terms_exist'] is False).
    """
    if "check" in config.keys() and config["check"] is True:
        if config["validate_terms_exist"] is False:
            return False

        # Attempt to detect term names (including typed relation taxonomy terms) that are namespaced. Some term names may
        # contain a colon (which is used in the incoming CSV to seprate the vocab ID from the term name). If there is
        # a ':', maybe it's part of the term name and it's not namespaced. To find out, split term_name_to_find
        # and compare the first segment with the vocab_id.
        if ":" in term_name_to_find:
            original_term_name_to_find = copy.copy(term_name_to_find)
            [tentative_vocab_id, tentative_term_name] = term_name_to_find.split(
                ":", maxsplit=1
            )
            if tentative_vocab_id.strip() == vocab_id.strip():
                term_name_to_find = tentative_term_name
            else:
                term_name_to_find = original_term_name_to_find

        """
        # Namespaced terms (inc. typed relation terms): if a vocabulary namespace is present, we need to split it out
        # from the term name. This only applies in --check since namespaced terms are parsed in prepare_term_id().
        # Assumptions: the term namespace always directly precedes the term name, and the term name may
        # contain a colon. See https://github.com/mjordan/islandora_workbench/issues/361 for related logic.
        namespaced = re.search(':', term_name_to_find)
        if namespaced:
            namespaced_term_parts = term_name_to_find.split(':')
            # Assumption is that the term name is the last part, and the namespace is the second-last.
            term_name_to_find = namespaced_term_parts[-1]
            vocab_id = namespaced_term_parts[-2]
        """

        term_name_for_check_matching = term_name_to_find.lower().strip()
        for checked_term in checked_terms:
            if (
                checked_term["vocab_id"] == vocab_id
                and checked_term["name_for_matching"] == term_name_for_check_matching
            ):
                if value_is_numeric(checked_term["tid"]):
                    return checked_term["tid"]
                else:
                    return False

    for newly_created_term in newly_created_terms:
        if (
            newly_created_term["vocab_id"] == vocab_id
            and newly_created_term["name_for_matching"]
            == term_name_to_find.lower().strip()
        ):
            return newly_created_term["tid"]

    url = (
        config["host"]
        + "/term_from_term_name?vocab="
        + vocab_id.strip()
        + "&name="
        + urllib.parse.quote_plus(term_name_to_find.strip())
        + "&_format=json"
    )
    response = issue_request(config, "GET", url)
    if response.status_code == 200:
        term_data = json.loads(response.text)
        # Term name is not found.
        if len(term_data) == 0:
            if "check" in config.keys() and config["check"] is True:
                checked_term_to_add = {
                    "tid": None,
                    "vocab_id": vocab_id,
                    "name": term_name_to_find,
                    "name_for_matching": term_name_for_check_matching,
                }
                if checked_term_to_add not in checked_terms:
                    checked_terms.append(checked_term_to_add)
            return False
        elif len(term_data) > 1:
            print(
                "Warning: See log for important message about duplicate terms within the same vocabulary."
            )
            logging.warning(
                'Query for term "%s" found %s terms with that name in the %s vocabulary. Workbench is choosing the first term ID (%s)).',
                term_name_to_find,
                len(term_data),
                vocab_id,
                term_data[0]["tid"][0]["value"],
            )
            if "check" in config.keys() and config["check"] is True:
                checked_term_to_add = {
                    "tid": term_data[0]["tid"][0]["value"],
                    "vocab_id": vocab_id,
                    "name": term_name_to_find,
                    "name_for_matching": term_name_for_check_matching,
                }
                if checked_term_to_add not in checked_terms:
                    checked_terms.append(checked_term_to_add)
            return term_data[0]["tid"][0]["value"]
        # Term name is found.
        else:
            if "check" in config.keys() and config["check"] is True:
                checked_term_to_add = {
                    "tid": term_data[0]["tid"][0]["value"],
                    "vocab_id": vocab_id,
                    "name": term_name_to_find,
                    "name_for_matching": term_name_for_check_matching,
                }
                if checked_term_to_add not in checked_terms:
                    checked_terms.append(checked_term_to_add)
            return term_data[0]["tid"][0]["value"]
    else:
        logging.warning(
            'Query for term "%s" in vocabulary "%s" returned a %s status code',
            term_name_to_find,
            vocab_id,
            response.status_code,
        )
        return False


def get_term_vocab(config, term_id):
    """Get the term's parent vocabulary ID and return it. If the term doesn't
    exist, return False.
    """
    url = config["host"] + "/taxonomy/term/" + str(term_id).strip() + "?_format=json"
    response = issue_request(config, "GET", url)
    if response.status_code == 200:
        term_data = json.loads(response.text)
        return term_data["vid"][0]["target_id"]
    else:
        logging.warning(
            'Query for term ID "%s" returned a %s status code',
            term_id,
            response.status_code,
        )
        return False


def get_term_name(config, term_id):
    """Get the term's name and return it. If the term doesn't exist, return False."""
    url = config["host"] + "/taxonomy/term/" + str(term_id).strip() + "?_format=json"
    response = issue_request(config, "GET", url)
    if response.status_code == 200:
        term_data = json.loads(response.text)
        return term_data["name"][0]["value"]
    else:
        logging.warning(
            'Query for term ID "%s" returned a %s status code',
            term_id,
            response.status_code,
        )
        return False


def get_term_uri(config, term_id):
    """Get the term's URI and return it. If the term or URI doesn't exist, return False.
    If the term has no URI, return None.
    """
    url = config["host"] + "/taxonomy/term/" + str(term_id).strip() + "?_format=json"
    response = issue_request(config, "GET", url)
    if response.status_code == 200:
        term_data = json.loads(response.text)
        if "field_external_uri" in term_data:
            uri = term_data["field_external_uri"][0]["uri"]
            return uri
        elif "field_authority_link" in term_data:
            uri = term_data["field_authority_link"][0]["uri"]
            return uri
        else:
            logging.warning(
                'Query for term ID "%s" does not have either a field_authority_link or field_exteral_uri field.',
                term_id,
            )
            return None
    else:
        logging.warning(
            'Query for term ID "%s" returned a %s status code',
            term_id,
            response.status_code,
        )
        return False


def get_term_id_from_uri(config, uri):
    """For a given URI, query the Term from URI View created by the Islandora
    Workbench Integration module. Because we don't know which field each
    taxonomy uses to store URIs (it's either field_external_uri or field_authority_link),
    we need to check both options in the "Term from URI" View.
    """
    # Some vocabularies use this View.
    terms_with_uri = []
    term_from_uri_url = (
        config["host"] + "/term_from_uri?_format=json&uri=" + uri.replace("#", "%23")
    )
    term_from_uri_response = issue_request(config, "GET", term_from_uri_url)
    if term_from_uri_response.status_code == 200:
        term_from_uri_response_body_json = term_from_uri_response.text
        term_from_uri_response_body = json.loads(term_from_uri_response_body_json)
        if len(term_from_uri_response_body) == 1:
            tid = term_from_uri_response_body[0]["tid"][0]["value"]
            return tid
        if len(term_from_uri_response_body) > 1:
            for term in term_from_uri_response_body:
                terms_with_uri.append(
                    {term["tid"][0]["value"]: term["vid"][0]["target_id"]}
                )
                tid = term_from_uri_response_body[0]["tid"][0]["value"]
            print("Warning: See log for important message about use of term URIs.")
            logging.warning(
                'Term URI "%s" is used for more than one term (with these term ID/vocabulary ID combinations: '
                + str(terms_with_uri)
                + "). Workbench is choosing the first term ID (%s)).",
                uri,
                tid,
            )
            return tid

    # And some vocabuluaries use this View.
    term_from_authority_link_url = (
        config["host"]
        + "/term_from_authority_link?_format=json&authority_link="
        + uri.replace("#", "%23")
    )
    term_from_authority_link_response = issue_request(
        config, "GET", term_from_authority_link_url
    )
    if term_from_authority_link_response.status_code == 200:
        term_from_authority_link_response_body_json = (
            term_from_authority_link_response.text
        )
        term_from_authority_link_response_body = json.loads(
            term_from_authority_link_response_body_json
        )
        if len(term_from_authority_link_response_body) == 1:
            tid = term_from_authority_link_response_body[0]["tid"][0]["value"]
            return tid
        elif len(term_from_authority_link_response_body) > 1:
            for term in term_from_authority_link_response_body:
                terms_with_uri.append(
                    {term["tid"][0]["value"]: term["vid"][0]["target_id"]}
                )
                tid = term_from_authority_link_response_body[0]["tid"][0]["value"]
            print("Warning: See log for important message about use of term URIs.")
            logging.warning(
                'Term URI "%s" is used for more than one term (with these term ID/vocabulary ID combinations: '
                + str(terms_with_uri)
                + "). Workbench is choosing the first term ID (%s)).",
                uri,
                tid,
            )
            return tid
        else:
            # URI does not match any term.
            return False

    # Non-200 response code.
    return False


def get_all_representations_of_term(
    config, vocab_id=None, name=None, term_id=None, uri=None
):
    """Parameters
    ----------
    config : dict
        The configuration settings defined by workbench_config.get_config().
    vocab_id: string
        The vocabulary ID to use in the query to find the term. Required if 'name' is the other arguments.
    name: string
        The term name.
    term_id: int
        The term ID. Does not require any other named arguments, since term IDs are unique.
    uri: string
        The term URI. Does not require any other named arguments, since term IDs (in theory) are unique.
    Returns
    -------
    dict/False
        A dictionary containing keys 'term_id', 'name', and 'uri'. False if there is insufficient
        information to get all representations of the term.
    """
    if term_id is not None and value_is_numeric(term_id):
        name = get_term_name(config, term_id)
        uri = get_term_uri(config, term_id)
    elif name is not None:
        if vocab_id is None:
            return False
        term_id = find_term_in_vocab(config, vocab_id, name)
        uri = get_term_uri(config, term_id)
    elif uri is not None:
        term_id = get_term_id_from_uri(config, uri)
        name = get_term_name(config, term_id)

    return {"term_id": term_id, "name": name, "uri": uri}


def create_term(config, vocab_id, term_name, term_csv_row=None):
    """Adds a term to the target vocabulary. Returns the new term's ID
    if successful (or if the term already exists) or False if not.
    """
    """Parameters
        ----------
        config : dict
            The configuration settings defined by workbench_config.get_config().
        vocab_id: string
            The vocabulary ID.
        term_name: string
            The term name from CSV.
        term_csv_row: OrderedDict
            ECSV row containing term field data. Only present if we are creating
            complex or child terms, not present for simple terms.
        Returns
        -------
        string|boolean
            The term ID, or False term was not created.
    """
    # Check to see if term exists; if so, return its ID, if not, proceed to create it.
    tid = find_term_in_vocab(config, vocab_id, term_name)
    if value_is_numeric(tid):
        if (config["task"] == "create" or config["task"] == "update") and config[
            "log_term_creation"
        ] is True:
            logging.info(
                'Term "%s" (term ID %s) already exists in vocabulary "%s".',
                term_name,
                tid,
                vocab_id,
            )
        if config["task"] == "create_terms":
            logging.info(
                'Term "%s" (term ID %s) already exists in vocabulary "%s".',
                term_name,
                tid,
                vocab_id,
            )
        return tid

    if vocab_id in config["protected_vocabularies"]:
        logging.warning(
            f'Term "{term_name}" is not in its designated vocabulary ({vocab_id}) and will not be added since the vocabulary is registered in the "protected_vocabularies" config setting.'
        )
        return False

    if config["allow_adding_terms"] is False:
        logging.warning(
            f'Term "{term_name}" does not exist in the vocabulary "{vocab_id}". To create new taxonomy terms, you must add "allow_adding_terms: true" to your configuration file.'
        )
        return False

    if len(term_name) > 255:
        truncated_term_name = term_name[:255]
        message = (
            'Term "'
            + term_name
            + '"'
            + "provided in the CSV data exceeds Drupal's maximum length of 255 characters."
        )
        message_2 = ' It has been trucated to "' + truncated_term_name + '".'
        logging.info(message + message_2)
        term_name = truncated_term_name

    term_field_data = get_term_field_data(config, vocab_id, term_name, term_csv_row)
    if term_field_data is False:
        # @todo: Failure details should be logged in get_term_field_data().
        logging.warning(
            'Unable to create term "'
            + term_name
            + '" because Workbench could not get term field data.'
        )
        return False

    # Common values for all terms, simple and complex.
    term = {
        "vid": [{"target_id": str(vocab_id), "target_type": "taxonomy_vocabulary"}],
        "name": [{"value": term_name}],
    }

    term.update(term_field_data)

    term_endpoint = config["host"] + "/taxonomy/term?_format=json"
    headers = {"Content-Type": "application/json"}
    response = issue_request(config, "POST", term_endpoint, headers, term, None)
    if response.status_code == 201:
        term_response_body = json.loads(response.text)
        tid = term_response_body["tid"][0]["value"]
        if (config["task"] == "create" or config["task"] == "update") and config[
            "log_term_creation"
        ] is True:
            logging.info(
                'Term %s ("%s") added to vocabulary "%s".', tid, term_name, vocab_id
            )
        if config["task"] == "create_terms":
            logging.info(
                'Term %s ("%s") added to vocabulary "%s".', tid, term_name, vocab_id
            )
        newly_created_term_name_for_matching = term_name.lower().strip()
        newly_created_terms.append(
            {
                "tid": tid,
                "vocab_id": vocab_id,
                "name": term_name,
                "name_for_matching": newly_created_term_name_for_matching,
            }
        )
        return tid
    else:
        logging.warning(
            "Term '%s' not created, HTTP response code was %s, response body was %s.",
            term_name,
            response.status_code,
            response.text,
        )
        logging.error(
            'JSON request body used in previous POST to "%s" was %s.',
            term_endpoint,
            term,
        )

        return False


def get_term_field_data(config, vocab_id, term_name, term_csv_row):
    """Assemble the dict that will be added to the 'term' dict in create_term(). status, description,
    weight, parent, default_langcode, path fields are added here, even for simple term_name-only
    terms. Check the vocabulary CSV file to see if there is a corresponding row. If the vocabulary
    has any required fields, and any of them are absent, return False.
    """
    """Parameters
        ----------
        config : dict
            The configuration settings defined by workbench_config.get_config().
        vocab_id: string
            The vocabulary ID.
        term_name: string
            The term name from CSV.
        term_csv_row: OrderedDict
            ECSV row containing term field data.
        Returns
        -------
        dict|boolean
            The dict containing the term field data, or False if this is not possible.
            @note: reason why creating JSON is not possible should be logged in this function.
    """
    if (
        term_csv_row is not None
        and "published" in term_csv_row.keys()
        and len(term_csv_row["published"]) > 0
    ):
        published_status = term_csv_row["published"]
    else:
        published_status = True

    # 'vid' and 'name' are added in create_term().
    term_field_data = {
        "status": [{"value": published_status}],
        "description": [{"value": "", "format": None}],
        "weight": [{"value": 0}],
        "parent": [{"target_type": "taxonomy_term", "target_id": None}],
        "default_langcode": [{"value": True}],
        "path": [{"alias": None, "pid": None, "langcode": "en"}],
    }

    # We're creating a simple term, with only a term name.
    if term_csv_row is None:
        return term_field_data
    # We're creating a complex term, with extra fields.
    else:
        # Importing the workbench_fields module at the top of this module with the
        # rest of the imports causes a circular import exception, so we do it here.
        import workbench_fields

        vocab_field_definitions = get_field_definitions(
            config, "taxonomy_term", vocab_id.strip()
        )

        # Build the JSON from the CSV row and create the term.
        vocab_csv_column_headers = term_csv_row.keys()
        for field_name in vocab_csv_column_headers:
            # term_name is the "id" field in the vocabulary CSV and not a field in the term JSON, so skip it.
            if field_name == "term_name":
                continue

            # "published" is a reserved column name in the vocabulary CSV and not a field in the term JSON, so skip it.
            if field_name == "published":
                continue

            # 'parent' field is present and not empty, so we need to look up the parent term. All terms
            # that are parents will have already been created back in workbench.create_terms() as long as
            # they preceded the children. If they come after the children in the CSV, we create the child
            # term anyway but log that the parent could not be found.
            if "parent" in term_csv_row and len(term_csv_row["parent"].strip()) != 0:
                parent_tid = find_term_in_vocab(
                    config, vocab_id, term_csv_row["parent"]
                )
                if value_is_numeric(parent_tid):
                    term_field_data["parent"][0]["target_id"] = str(parent_tid)
                else:
                    # Create the term, but log that its parent could not be found.
                    message = (
                        'Term "'
                        + term_csv_row["term_name"]
                        + '" added to vocabulary "'
                        + vocab_id
                        + '", but without its parent "'
                        + term_csv_row["parent"]
                        + "\", which isn't present in that vocabulary (possibly hasn't been create yet?)."
                    )
                    logging.warning(message)

            # 'parent' is not a field added to the term JSON in the field handlers, so skip it.
            if field_name == "parent":
                continue

            # Set 'description' and 'weight' JSON values if there are corresponding columns in the CSV.
            if "weight" in term_csv_row and len(term_csv_row["weight"].strip()) != 0:
                if value_is_numeric(term_csv_row["weight"]):
                    term_field_data["weight"][0]["value"] = str(term_csv_row["weight"])
                else:
                    # Create the term, but log that its weight could not be populated.
                    message = (
                        'Term "'
                        + term_csv_row["term_name"]
                        + '" added to vocabulary "'
                        + vocab_id
                        + '", but without its weight "'
                        + term_csv_row["weight"]
                        + '", which must be an integer.'
                    )
                    logging.warning(message)

            # 'weight' is not a field added to the term JSON in the field handlers, so skip it.
            if field_name == "weight":
                continue

            if (
                "description" in term_csv_row
                and len(term_csv_row["description"].strip()) != 0
            ):
                term_field_data["description"][0]["value"] = term_csv_row["description"]

            # 'description' is not a field added to the term JSON in the field handlers, so skip it.
            if field_name == "description":
                continue

            # Assemble Drupal field structures from CSV data. If new field types are added to
            # workbench_fields.py, they need to be registered in the following if/elif/else block.

            field = workbench_fields.WorkbenchFieldFactory.get_field_handler(
                vocab_field_definitions[field_name]["field_type"]
            )
            term_field_data = field.create(
                config,
                vocab_field_definitions,
                term_field_data,
                term_csv_row,
                field_name,
            )

        return term_field_data


def get_term_uuid(config, term_id):
    """Given a term ID, get the term's UUID."""
    term_url = config["host"] + "/taxonomy/term/" + str(term_id) + "?_format=json"
    response = issue_request(config, "GET", term_url)
    term = json.loads(response.text)
    uuid = term["uuid"][0]["value"]

    return uuid


def create_url_alias(config, node_id, url_alias):
    json = {
        "path": [{"value": "/node/" + str(node_id)}],
        "alias": [{"value": url_alias}],
    }

    headers = {"Content-Type": "application/json"}
    response = issue_request(
        config,
        "POST",
        config["host"] + "/entity/path_alias?_format=json",
        headers,
        json,
        None,
    )
    if response.status_code != 201:
        logging.error(
            "URL alias '%s' not created for node %s, HTTP response code was %s (it might already exist).",
            url_alias,
            config["host"] + "/node/" + str(node_id),
            response.status_code,
        )


def prepare_term_id(config, vocab_ids, field_name, term):
    """Checks to see if 'term' is numeric (i.e., a term ID) and if it is, returns it as
    is. If it's not (i.e., it's a string term name) it looks for the term name in the
    referenced vocabulary and returns its term ID if the term exists, and if it doesn't
    exist, creates the term and returns the new term ID.
    """
    """Parameters
    ----------
    config : dict
        The configuration settings defined by workbench_config.get_config().
    vocab_ids: list|boolean
        The vocabulary IDs associated with the field handling code calling this function.
    field_name: string
        The field's machine name.
    term: string
        The term name from CSV.
    Returns
    -------
    int|None
        The term ID, existing or newly created. None if there are no vocabularies
        associated with the field identified in field_name (which is the case with
        "Filter by an entity reference view" reference type fields)or if the vocab
        ID is otherwise unknown.
"""
    term = str(term)
    term = term.strip()
    if value_is_numeric(term) and field_name not in config["columns_with_term_names"]:
        return term
    entity_reference_view_endpoints = get_entity_reference_view_endpoints(config)
    if not entity_reference_view_endpoints and vocab_ids is False:
        return None
    # Special case: if the term starts with 'http', assume it's a Linked Data URI
    # and get its term ID from the URI.
    elif term.startswith("http"):
        # Note: get_term_id_from_uri() will return False if the URI doesn't match a term.
        tid_from_uri = get_term_id_from_uri(config, term)
        if value_is_numeric(tid_from_uri):
            return tid_from_uri
    else:
        if entity_reference_view_endpoints.get(field_name, False):
            headers = {"Content-Type": "application/json"}
            endpoint = entity_reference_view_endpoints.get(field_name, False)
            if ":" in term:
                [tentative_vocab_id, term_name] = term.split(":", maxsplit=1)
                tentative_vocab_id = tentative_vocab_id.strip()
                term_name = term_name.strip()
                response = issue_request(
                    config,
                    "GET",
                    endpoint + "?name=" + term_name + "&vid=" + tentative_vocab_id,
                    headers,
                )
                if response.status_code == 200:
                    term_response_body = json.loads(response.text)
                    if term_response_body:
                        return term_response_body[0]["tid"][0]["value"]
                    tid = create_term(config, tentative_vocab_id, term_name)
                    return tid
                else:
                    logging.warning(
                        "Term '%s' not found, HTTP response code was %s.",
                        term,
                        response.status_code,
                    )
                    return None
            else:
                response = issue_request(
                    config, "GET", endpoint + "?name=" + term, headers
                )
                if response.status_code == 200:
                    term_response_body = json.loads(response.text)
                    if term_response_body:
                        return term_response_body[0]["tid"][0]["value"]
                    logging.warning(
                        "Term '%s' not found. Cannot create it using entity_reference_view_endpoints without a provided vocabulary.",
                        term,
                    )
                    return None
                else:
                    logging.warning(
                        "Term '%s' not found, HTTP response code was %s.",
                        term,
                        response.status_code,
                    )
                    return None
        elif len(vocab_ids) == 1:
            # A namespace is not needed but it might be present. If there is,
            # since this vocabulary is the only one linked to its field,
            # we remove it before sending it to create_term().
            namespaced = re.search(":", term)
            if namespaced:
                [vocab_id, term_name] = term.split(":", maxsplit=1)
                if vocab_id == vocab_ids[0]:
                    tid = create_term(config, vocab_id.strip(), term_name.strip())
                    return tid
                else:
                    tid = create_term(config, vocab_ids[0].strip(), term.strip())
                    return tid
            else:
                tid = create_term(config, vocab_ids[0].strip(), term.strip())
                return tid
        else:
            # Term names used in multi-taxonomy fields. They need to be namespaced with
            # the taxonomy ID.
            #
            # If the field has more than one vocabulary linked to it, we don't know which
            # vocabulary the user wants a new term to be added to, and if the term name is
            # already used in any of the taxonomies linked to this field, we also don't know
            # which vocabulary to look for it in to get its term ID. Therefore, we always need
            # to namespace term names if they are used in multi-taxonomy fields.
            #
            # Split the namespace/vocab ID from the term name on ':'.
            if ":" in term:
                [tentative_vocab_id, term_name] = term.split(":", maxsplit=1)
                for vocab_id in vocab_ids:
                    if tentative_vocab_id == vocab_id:
                        tid = create_term(config, vocab_id.strip(), term_name.strip())
                        return tid
            else:
                if isinstance(vocab_ids, str):
                    tid = create_term(config, vocab_ids.strip(), term.strip())
                    return tid

                message = f"Because The field '{field_name}' allows more than one vocabulary the term '{term}' must be namespaced."
                message = (
                    message
                    + "See documentation at https://mjordan.github.io/islandora_workbench_docs/fields/#using-term-names-in-multi-vocabulary-fields"
                )
                logging.error(message)
                sys.exit("Error: " + message)

        # Explicitly return None if hasn't returned from one of the conditions above, e.g. if
        # the term name contains a colon and it wasn't namespaced with a valid vocabulary ID.
        return None


def get_field_vocabularies(config, field_definitions, field_name):
    """Gets IDs of vocabularies linked from the current field (could be more than one)."""
    if "vocabularies" in field_definitions[field_name]:
        vocabularies = field_definitions[field_name]["vocabularies"]
        return vocabularies
    else:
        return False


def value_is_numeric(value, allow_decimals=False):
    """Tests to see if value  is numeric."""

    """Parameters
    ----------
    value : varies
        The value to check. By design, we don't know what data type it is.
    allow_decimals: boolean
        Whether or not to allow '.' in the value. Decimal and float number types have decimals.

    Returns
    -------
    boolean
    """
    var = str(value)
    if allow_decimals is True and "." in str(value):
        var = str(value).replace(".", "")
    else:
        var = var.strip()
    if var.isnumeric():
        return True
    else:
        return False


def compare_strings(known, unknown):
    """Normalizes the unknown string and the known one, and compares
    them. If they match, returns True, if not, False. We could
    use FuzzyWuzzy or something but this is probably sufficient.
    """
    # Strips leading and trailing whitespace.
    known = known.strip()
    unknown = unknown.strip()
    # Converts to lower case.
    known = known.lower()
    unknown = unknown.lower()
    # Remove all punctuation.
    for p in string.punctuation:
        known = known.replace(p, " ")
        unknown = unknown.replace(p, " ")
    # Replaces whitespace with a single space.
    known = " ".join(known.split())
    unknown = " ".join(unknown.split())

    if unknown == known:
        return True
    else:
        return False


def get_csv_record_hash(row):
    """Concatenate values in the CSV record and get an MD5 hash on the
    resulting string.
    """
    serialized_row = ""
    for field in row:
        if isinstance(row[field], str) or isinstance(row[field], int):
            if isinstance(row[field], int):
                row[field] = str(row[field])
            row_value = row[field].strip()
            row_value = " ".join(row_value.split())
            serialized_row = serialized_row + row_value + " "

    serialized_row = bytes(serialized_row.strip().lower(), "utf-8")
    hash_object = hashlib.md5(serialized_row)
    return hash_object.hexdigest()


def validate_input_dir(config):
    # Check existence input directory.
    if os.path.isabs(config["input_dir"]):
        input_dir_path = config["input_dir"]
    else:
        input_dir_path = os.path.abspath(config["input_dir"])
    if not os.path.exists(input_dir_path):
        message = (
            'Input directory specified in the "input_dir" configuration setting ("'
            + config["input_dir"]
            + '") not found.'
        )
        logging.error(message)
        sys.exit("Error: " + message)


def validate_required_fields_have_values(config, required_drupal_fields, csv_data):
    """Loop through all fields in CSV to ensure that required field have a value in the CSV."""
    rows_with_missing_required_values = []
    for row in csv_data:
        for required_field in required_drupal_fields:
            if len(row[required_field].strip()) == 0:
                rows_with_missing_required_values.append(required_field)
                message = f"Required Drupal field \"{required_field}\" in row with ID \"{row[config['id_field']]}\" is empty."
                logging.error(message)

    if len(rows_with_missing_required_values) > 0:
        sys.exit(
            "Error: "
            + "Some required Drupal fields in your CSV file are empty. See log for more information."
        )


def validate_csv_field_cardinality(config, field_definitions, csv_data):
    """Compare values in the CSV data with the fields' cardinality. Log CSV
    fields that have more values than allowed, and warn user if
    these fields exist in their CSV data.
    """
    field_cardinalities = dict()
    csv_headers = csv_data.fieldnames
    for csv_header in csv_headers:
        if csv_header in field_definitions.keys():
            cardinality = field_definitions[csv_header]["cardinality"]
            # We don't care about cardinality of -1 (unlimited).
            if int(cardinality) > 0:
                field_cardinalities[csv_header] = cardinality

    for count, row in enumerate(csv_data, start=1):
        for field_name in field_cardinalities.keys():
            if field_name in row:
                # Don't check for the subdelimiter in title.
                if field_name == "title":
                    continue
                delimited_field_values = row[field_name].split(config["subdelimiter"])
                if (
                    field_cardinalities[field_name] == 1
                    and len(delimited_field_values) > 1
                ):
                    if config["task"] == "create":
                        message = (
                            'CSV field "'
                            + field_name
                            + '" in record with ID '
                            + row[config["id_field"]]
                            + " contains more values than the number "
                        )
                    if config["task"] == "update":
                        message = (
                            'CSV field "'
                            + field_name
                            + '" in record with node ID '
                            + row["node_id"]
                            + " contains more values than the number "
                        )
                    message_2 = (
                        "allowed for that field ("
                        + str(field_cardinalities[field_name])
                        + "). Workbench will add only the first value."
                    )
                    print("Warning: " + message + message_2)
                    logging.warning(message + message_2)
                if (
                    int(field_cardinalities[field_name]) > 1
                    and len(delimited_field_values) > field_cardinalities[field_name]
                ):
                    if config["task"] == "create":
                        message = (
                            'CSV field "'
                            + field_name
                            + '" in record with ID '
                            + row[config["id_field"]]
                            + " contains more values than the number "
                        )
                    if config["task"] == "update":
                        message = (
                            'CSV field "'
                            + field_name
                            + '" in record with node ID '
                            + row["node_id"]
                            + " contains more values than the number "
                        )
                    message_2 = (
                        "allowed for that field ("
                        + str(field_cardinalities[field_name])
                        + "). Workbench will add only the first "
                        + str(field_cardinalities[field_name])
                        + " values."
                    )
                    print("Warning: " + message + message_2)
                    logging.warning(message + message_2)


def validate_text_list_fields(config, field_definitions, csv_data):
    """For fields that are of "list_string" field type, check that values
    in CSV are in the field's "allowed_values" config setting.
    """
    list_field_allowed_values = dict()
    csv_headers = csv_data.fieldnames
    for csv_header in csv_headers:
        if csv_header in field_definitions.keys():
            if "allowed_values" in field_definitions[csv_header]:
                if field_definitions[csv_header]["allowed_values"] is not None:
                    list_field_allowed_values[csv_header] = field_definitions[
                        csv_header
                    ]["allowed_values"]

    for count, row in enumerate(csv_data, start=1):
        for field_name in list_field_allowed_values.keys():
            if field_name in row and len(row[field_name]) > 0:
                delimited_field_values = row[field_name].split(config["subdelimiter"])
                for field_value in delimited_field_values:
                    if (
                        field_name in list_field_allowed_values
                        and field_value not in list_field_allowed_values[field_name]
                    ):
                        if config["task"] == "create":
                            message = (
                                'CSV field "'
                                + field_name
                                + '" in record with ID '
                                + row[config["id_field"]]
                                + ' contains a value ("'
                                + field_value
                                + "\") that is not in the fields's allowed values."
                            )
                        if config["task"] == "update":
                            message = (
                                'CSV field "'
                                + field_name
                                + '" in record with node ID '
                                + row[config["id_field"]]
                                + ' contains a value ("'
                                + field_value
                                + "\") that is not in the fields's allowed values."
                            )
                        print("Warning: " + message)
                        logging.warning(message)


def validate_csv_field_length(config, field_definitions, csv_data):
    """Compare values in the CSV data with the fields' max_length. Log CSV
    fields that exceed their max_length, and warn user if
    these fields exist in their CSV data.
    """
    field_max_lengths = dict()
    csv_headers = csv_data.fieldnames
    for csv_header in csv_headers:
        if csv_header in field_definitions.keys():
            if "max_length" in field_definitions[csv_header]:
                max_length = field_definitions[csv_header]["max_length"]
                # We don't care about max_length of None (i.e., it's not applicable or unlimited).
                if max_length is not None:
                    field_max_lengths[csv_header] = max_length

    for count, row in enumerate(csv_data, start=1):
        for field_name in field_max_lengths.keys():
            if field_name in row:
                delimited_field_values = row[field_name].split(config["subdelimiter"])
                for field_value in delimited_field_values:
                    field_value_length = len(field_value)
                    if field_name in field_max_lengths and len(field_value) > int(
                        field_max_lengths[field_name]
                    ):
                        if config["task"] == "create":
                            message = (
                                'CSV field "'
                                + field_name
                                + '" in record with ID '
                                + row[config["id_field"]]
                                + " contains a value that is longer ("
                                + str(len(field_value))
                                + " characters)"
                            )
                        if config["task"] == "update":
                            message = (
                                'CSV field "'
                                + field_name
                                + '" in record with node ID '
                                + row["node_id"]
                                + " contains a value that is longer ("
                                + str(len(field_value))
                                + " characters)"
                            )
                        message_2 = (
                            " than allowed for that field ("
                            + str(field_max_lengths[field_name])
                            + " characters). Workbench will truncate this value prior to populating Drupal."
                        )
                        print("Warning: " + message + message_2)
                        logging.warning(message + message_2)


def validate_numeric_fields(config, field_definitions, csv_data):
    """Validate integer, decimal, and float fields."""
    numeric_fields_present = False
    for count, row in enumerate(csv_data, start=1):
        for field_name in field_definitions.keys():
            if field_definitions[field_name]["field_type"] == "integer":
                if field_name in row:
                    numeric_fields_present = True
                    delimited_field_values = row[field_name].split(
                        config["subdelimiter"]
                    )
                    for field_value in delimited_field_values:
                        if len(field_value.strip()):
                            if not value_is_numeric(field_value.strip()):
                                message = (
                                    'Value in field "'
                                    + field_name
                                    + '" in row with ID '
                                    + row[config["id_field"]]
                                    + " ("
                                    + field_value
                                    + ") is not a valid integer value."
                                )
                                logging.error(message)
                                sys.exit("Error: " + message)
            if field_definitions[field_name]["field_type"] in ["decimal", "float"]:
                if field_name in row:
                    numeric_fields_present = True
                    delimited_field_values = row[field_name].split(
                        config["subdelimiter"]
                    )
                    for field_value in delimited_field_values:
                        if len(field_value.strip()):
                            if not value_is_numeric(
                                field_value.strip(), allow_decimals=True
                            ):
                                message = (
                                    'Value in field "'
                                    + field_name
                                    + '" in row with ID '
                                    + row[config["id_field"]]
                                    + " ("
                                    + field_value
                                    + ") is not a valid "
                                    + field_definitions[field_name]["field_type"]
                                    + " value."
                                )
                                logging.error(message)
                                sys.exit("Error: " + message)

    if numeric_fields_present is True:
        message = "OK, numeric field values in the CSV file validate."
        print(message)
        logging.info(message)


def validate_geolocation_fields(config, field_definitions, csv_data):
    """Validate lat,long values in fields that are of type 'geolocation'."""
    geolocation_fields_present = False
    for count, row in enumerate(csv_data, start=1):
        for field_name in field_definitions.keys():
            if field_definitions[field_name]["field_type"] == "geolocation":
                if field_name in row:
                    geolocation_fields_present = True
                    delimited_field_values = row[field_name].split(
                        config["subdelimiter"]
                    )
                    for field_value in delimited_field_values:
                        if len(field_value.strip()):
                            if not validate_latlong_value(field_value.strip()):
                                message = (
                                    'Value in field "'
                                    + field_name
                                    + '" in row with ID '
                                    + row[config["id_field"]]
                                    + " ("
                                    + field_value
                                    + ") is not a valid lat,long pair."
                                )
                                logging.error(message)
                                sys.exit("Error: " + message)

    if geolocation_fields_present is True:
        message = "OK, geolocation field values in the CSV file validate."
        print(message)
        logging.info(message)


def validate_link_fields(config, field_definitions, csv_data):
    """Validate values in fields that are of type 'link'."""
    link_fields_present = False
    for count, row in enumerate(csv_data, start=1):
        for field_name in field_definitions.keys():
            if field_definitions[field_name]["field_type"] == "link":
                if field_name in row:
                    link_fields_present = True
                    delimited_field_values = row[field_name].split(
                        config["subdelimiter"]
                    )
                    for field_value in delimited_field_values:
                        if len(field_value.strip()):
                            if not validate_link_value(field_value.strip()):
                                message = (
                                    'Value in field "'
                                    + field_name
                                    + '" in row with ID '
                                    + row[config["id_field"]]
                                    + " ("
                                    + field_value
                                    + ") is not a valid link field value."
                                )
                                logging.error(message)
                                sys.exit("Error: " + message)

    if link_fields_present is True:
        message = "OK, link field values in the CSV file validate."
        print(message)
        logging.info(message)


def validate_authority_link_fields(config, field_definitions, csv_data):
    """Validate values in fields that are of type 'authority_link'."""
    if config["task"] == "create_terms":
        config["id_field"] = "term_name"

    authority_link_fields_present = False
    for count, row in enumerate(csv_data, start=1):
        for field_name in field_definitions.keys():
            if field_definitions[field_name]["field_type"] == "authority_link":
                if field_name in row:
                    authority_link_fields_present = True
                    delimited_field_values = row[field_name].split(
                        config["subdelimiter"]
                    )
                    for field_value in delimited_field_values:
                        if len(field_value.strip()):
                            if not validate_authority_link_value(
                                field_value.strip(),
                                field_definitions[field_name]["authority_sources"],
                            ):
                                message = (
                                    'Value in field "'
                                    + field_name
                                    + '" in row with ID "'
                                    + row[config["id_field"]]
                                    + '" ('
                                    + field_value
                                    + ") is not a valid authority link field value."
                                )
                                logging.error(message)
                                sys.exit("Error: " + message)

    if authority_link_fields_present is True:
        message = "OK, authority link field values in the CSV file validate."
        print(message)
        logging.info(message)


def validate_media_track_fields(config, csv_data):
    """Validate values in fields that are of type 'media_track'."""
    media_track_fields_present = False
    # Must accommodate multiple media track fields in the same CSV (e.g. audio and video media in the
    # same CSV, each with its own track column). Therefore, we'll need to get the field definitions
    # for more than one media bundle.
    media_track_field_definitions = dict()
    csv_column_headers = copy.copy(csv_data.fieldnames)
    for column_header in csv_column_headers:
        if column_header.startswith("media:"):
            # Assumes well-formed column headers.
            media_bundle_name_parts = column_header.split(":")
            media_bundle_name = media_bundle_name_parts[1]
            if media_bundle_name not in config["media_track_file_fields"]:
                message = (
                    'Media type "'
                    + media_bundle_name
                    + '" in the CSV column header "'
                    + column_header
                    + '" is not registered in the "media_track_file_fields" configuration setting.'
                )
                logging.error(message)
                sys.exit("Error: " + message)

            media_track_field_definitions[media_bundle_name] = get_field_definitions(
                config, "media", media_bundle_name
            )
            for count, row in enumerate(csv_data, start=1):
                for field_name in media_track_field_definitions[
                    media_bundle_name
                ].keys():
                    if (
                        media_track_field_definitions[media_bundle_name][field_name][
                            "field_type"
                        ]
                        == "media_track"
                    ):
                        fully_qualified_field_name = (
                            f"media:{media_bundle_name}:{field_name}"
                        )
                        if (
                            fully_qualified_field_name in row
                            and row[fully_qualified_field_name]
                        ):
                            media_track_fields_present = True
                            delimited_field_values = row[
                                fully_qualified_field_name
                            ].split(config["subdelimiter"])
                            for field_value in delimited_field_values:
                                if len(field_value.strip()):
                                    if validate_media_track_value(field_value) is False:
                                        message = (
                                            'Value in field "'
                                            + fully_qualified_field_name
                                            + '" in row with ID "'
                                            + row[config["id_field"]]
                                            + '" ('
                                            + field_value
                                            + ") has a media type is not a valid media track field value."
                                        )
                                        logging.error(message)
                                        sys.exit("Error: " + message)

                                    # Confirm that the media bundle name in the column header matches the media type
                                    # of the file in the 'file' column.
                                    file_media_type = set_media_type(
                                        config, row["file"], "file", row
                                    )
                                    if file_media_type != media_bundle_name:
                                        message = (
                                            'File named in the "file" field in row with ID "'
                                            + row[config["id_field"]]
                                            + '" ('
                                            + row["file"]
                                            + ") has a media type "
                                            + "("
                                            + file_media_type
                                            + ') that differs from the media type indicated in the column header "'
                                            + fully_qualified_field_name
                                            + '" ('
                                            + media_bundle_name
                                            + ")."
                                        )
                                        logging.error(message)
                                        sys.exit("Error: " + message)

                                # Confirm that config['media_use_tid'] and row-level media_use_term is for Service File (http://pcdm.org/use#ServiceFile).
                                service_file_exists = service_file_present(
                                    config, row["media_use_tid"]
                                )
                                if service_file_exists is False:
                                    message = f"{row['media_use_tid']} cannot be used as a \"media_use_tid\" value in your CSV when creating media tracks."
                                    logging.error(message)
                                    sys.exit("Error: " + message)

                                    if config["nodes_only"] is False:
                                        if len(field_value.strip()):
                                            media_track_field_value_parts = (
                                                field_value.split(":")
                                            )
                                            media_track_file_path_in_csv = (
                                                media_track_field_value_parts[3]
                                            )
                                            if os.path.isabs(
                                                media_track_file_path_in_csv
                                            ):
                                                media_track_file_path = (
                                                    media_track_file_path_in_csv
                                                )
                                            else:
                                                media_track_file_path = os.path.join(
                                                    config["input_dir"],
                                                    media_track_file_path_in_csv,
                                                )
                                            if not os.path.exists(
                                                media_track_file_path
                                            ) or not os.path.isfile(
                                                media_track_file_path
                                            ):
                                                message = (
                                                    'Media track file "'
                                                    + media_track_file_path_in_csv
                                                    + '" in row with ID "'
                                                    + row[config["id_field"]]
                                                    + '" not found.'
                                                )
                                                logging.error(message)
                                                sys.exit("Error: " + message)

                                            if (
                                                file_is_utf8(media_track_file_path)
                                                is False
                                            ):
                                                message = (
                                                    'Media track file "'
                                                    + media_track_file_path_in_csv
                                                    + '" in row with ID "'
                                                    + row[config["id_field"]]
                                                    + '" is not encoded as UTF-8 and will not be ingested.'
                                                )
                                                logging.warning(message)

    if media_track_fields_present is True:
        message = "OK, media track field values in the CSV file validate."
        print(message)
        logging.info(message)


def validate_media_track_value(media_track_value):
    """Validates that the string in "media_track_value" has valid values in its subparts."""
    """Parameters
        ----------
        media_track_value : string
            The CSV value to validate.
        Returns
        -------
        boolean
            True if it does, False if not.
    """
    valid_kinds = ["subtitles", "descriptions", "metadata", "captions", "chapters"]
    parts = media_track_value.split(":", 3)
    # First part, the label, needs to have a length; second part needs to be one of the
    # values in 'valid_kinds'; third part needs to be a valid Drupal language code; the fourth
    # part needs to end in '.vtt'.
    if (
        len(parts) == 4
        and len(parts[0]) > 0
        and validate_language_code(parts[2])
        and parts[1] in valid_kinds
        and parts[3].lower().endswith(".vtt")
    ):
        return True
    else:
        return False


def validate_latlong_value(latlong):
    # Remove leading \ that may be present if input CSV is from a spreadsheet.
    latlong = latlong.lstrip("\\")
    if re.match(
        r"^[-+]?([1-8]?\d(\.\d+)?|90(\.0+)?),\s*[-+]?(180(\.0+)?|((1[0-7]\d)|([1-9]?\d))(\.\d+)?)$",
        latlong,
    ):
        return True
    else:
        return False


def validate_link_value(link_value):
    """Validates that the value in 'link_value' starts with either 'http://' or 'https://'
    and optionally contains the url/label delimiter '%%'.
    """
    """Parameters
        ----------
        link_value : string
            The URL.
        Returns
        -------
        boolean
            True if it does, False if not.
    """
    parts = link_value.split("%%", 1)
    if re.match(r"^https?://", parts[0]):
        return True
    else:
        return False


def validate_authority_link_value(authority_link_value, authority_sources):
    """Validates that the value in 'authority_link_value' has a 'source' and that the URI
    component starts with either 'http://' or 'https://'.
    """
    """Parameters
        ----------
        authority_link_value : string
            The authority link string, with a sourcea, URI, and optionally a title.
        authority_sources : list
            The list of authority sources (e.g. lcsh, cash, viaf, etc.) configured for the field.
        Returns
        -------
        boolean
            True if it does, False if not.
    """
    parts = authority_link_value.split("%%", 2)
    if parts[0] not in authority_sources:
        return False
    if re.match(r"^https?://", parts[1]):
        return True
    else:
        return False


def validate_term_name_length(term_name, row_id, column_name):
    """Checks that the length of a term name does not exceed
    Drupal's 255 character length.
    """
    term_name = term_name.strip()
    if len(term_name) > 255:
        message = (
            'CSV field "'
            + column_name
            + '" in record with ID '
            + row_id
            + " contains a taxonomy term that exceeds Drupal's limit of 255 characters (length of term is "
            + str(len(term_name))
            + " characters)."
        )
        message_2 = ' Term provided in CSV is "' + term_name + '".'
        message_3 = " Please reduce the term's length to less than 256 characters."
        logging.error(message + message_2 + message_3)
        sys.exit("Error: " + message + " See the Workbench log for more information.")


def validate_node_created_date(config, csv_data):
    """Checks that date_string is in the format used by Drupal's 'created' node property,
    e.g., 2020-11-15T23:49:22+00:00. Also check to see if the date is in the future.
    """
    for count, row in enumerate(csv_data, start=1):
        for field_name, field_value in row.items():
            if field_name == "created" and len(field_value) > 0:
                # matches = re.match(r'^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d[+-]\d\d:\d\d$', field_value)
                if not validate_node_created_date_string(field_value):
                    message = (
                        'CSV field "created" in record with ID '
                        + row[config["id_field"]]
                        + ' contains a date "'
                        + field_value
                        + '" that is not formatted properly.'
                    )
                    logging.error(message)
                    sys.exit("Error: " + message)

                now = datetime.datetime.now()
                # Remove the GMT differential at the end of the time string.
                date_string_trimmed = re.sub(r"[+-]\d\d:\d\d$", "", field_value)
                created_date = datetime.datetime.strptime(
                    date_string_trimmed, "%Y-%m-%dT%H:%M:%S"
                )
                if created_date > now:
                    message = (
                        'CSV field "created" in record with ID '
                        + row[config["id_field"]]
                        + ' contains a date "'
                        + field_value
                        + '" that is in the future.'
                    )
                    logging.error(message)
                    sys.exit("Error: " + message)

    message = 'OK, dates in the "created" CSV field are all formated correctly and in the future.'
    print(message)
    logging.info(message)


def validate_node_created_date_string(created_date_string):
    if re.match(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d[+-]\d\d:\d\d$", created_date_string):
        return True
    else:
        return False


def validate_weight_value(weight_value):
    weight = weight_value.lstrip("0")
    if re.match(r"^\d+$", weight) and int(weight) > 0:
        return True
    else:
        return False


def validate_edtf_fields(config, field_definitions, csv_data):
    """Validate values in fields that are of type 'edtf'."""
    edtf_fields_present = False
    for count, row in enumerate(csv_data, start=1):
        for field_name in field_definitions.keys():
            if field_definitions[field_name]["field_type"] == "edtf":
                if field_name in row:
                    edtf_fields_present = True
                    delimited_field_values = row[field_name].split(
                        config["subdelimiter"]
                    )
                    for field_value in delimited_field_values:
                        if len(field_value.strip()):
                            valid = validate_edtf_date(field_value)
                            if valid is False:
                                message = (
                                    'Value in field "'
                                    + field_name
                                    + '" in row with ID '
                                    + row[config["id_field"]]
                                    + ' ("'
                                    + field_value
                                    + '") is not a valid EDTF date/time.'
                                )
                                logging.error(message)
                                if config["perform_soft_checks"] is False:
                                    sys.exit("Error: " + message)

    if edtf_fields_present is True:
        message = "OK, EDTF field values in the CSV file validate."
        print(message)
        logging.info(message)


def validate_edtf_date(date):
    date = date.strip()
    # 195X-01~
    # nnnX-nn~
    if re.match(r"^[1-2]\d\dX\-\d\d\~", date):
        return True
    # nnnX?
    if re.match(r"^[1-2]\d\dX\?", date):
        return True
    # nnXX?
    elif re.match(r"^[1-2]\dXX\?", date):
        return True
    # nXXX?
    elif re.match(r"^[1-2]XXX\?", date):
        return True
    # nXXX~
    elif re.match(r"^[1-2]XXX\~", date):
        return True
    # nnXX~
    elif re.match(r"^[1-2]\dXX\~", date):
        return True
    # nnnX~
    elif re.match(r"^[1-2]\d\dX\~", date):
        return True
    # nXXX%
    elif re.match(r"^[1-2]XXX\%", date):
        return True
    # nnXX%
    elif re.match(r"^[1-2]\dXX\%", date):
        return True
    # nnnX%
    elif re.match(r"^[1-2]\d\dX\%", date):
        return True
    # XXXX?
    elif re.match(r"^XXXX\?", date):
        return True
    # XXXX~
    elif re.match(r"^XXXX\~", date):
        return True
    # XXXX%
    elif re.match(r"^XXXX\%", date):
        return True
    elif edtf_validate.valid_edtf.is_valid(date):
        return True
    else:
        return False


def validate_url_aliases(config, csv_data):
    """Checks that URL aliases don't already exist."""
    for count, row in enumerate(csv_data, start=1):
        for field_name, field_value in row.items():
            if field_name == "url_alias" and len(field_value) > 0:
                if field_value.strip()[0] != "/":
                    message = (
                        'CSV field "url_alias" in record with ID '
                        + row[config["id_field"]]
                        + ' contains an alias "'
                        + field_value
                        + '" that is missing its leading /.'
                    )
                    logging.error(message)
                    sys.exit("Error: " + message)

                alias_ping = ping_url_alias(config, field_value)
                # @todo: Add 301 and 302 as acceptable status codes?
                if alias_ping == 200:
                    message = (
                        'CSV field "url_alias" in record with ID '
                        + row[config["id_field"]]
                        + ' contains an alias "'
                        + field_value
                        + '" that already exists.'
                    )
                    logging.error(message)
                    sys.exit("Error: " + message)

    message = "OK, URL aliases do not already exist."
    print(message)
    logging.info(message)


def validate_node_uid(config, csv_data):
    """Checks that the user identified in the 'uid' field exists in Drupal. Note that
    this does not validate any permissions the user may have.
    """
    for count, row in enumerate(csv_data, start=1):
        for field_name, field_value in row.items():
            if field_name == "uid" and len(field_value) > 0:
                # Request to /user/x?_format=json goes here; 200 means the user
                # exists, 404 means they do no.
                uid_url = config["host"] + "/user/" + str(field_value) + "?_format=json"
                uid_response = issue_request(config, "GET", uid_url)
                if uid_response.status_code == 404:
                    message = (
                        'CSV field "uid" in record with ID '
                        + row[config["id_field"]]
                        + ' contains a user ID "'
                        + field_value
                        + '" that does not exist in the target Drupal.'
                    )
                    logging.error(message)
                    sys.exit("Error: " + message)

    message = 'OK, user IDs in the "uid" CSV field all exist.'
    print(message)
    logging.info(message)


def validate_parent_ids_precede_children(config, csv_data):
    """In the page/child-level metadata method of creating compound content,
    CSV rows for parent items must come before their children in the CSV file.
    This function checks for that. Note that this check only applies to one
    level of parent/child hierarchy (i.e., parents and their immediate children).
    """
    positions = dict()
    id_field = config["id_field"]
    row_num = 0
    if "parent_id" in csv_data.fieldnames:
        for row in csv_data:
            row_num += 1
            positions[row[id_field]] = {
                "position": row_num,
                "parent_id": row["parent_id"],
            }
    else:
        return False

    # Loop through position records and check to see if the "position" of each child row
    # (i.e. a row with a value in its "parent_id" CSV column) is lower than the "position"
    # of the row identified in its "parent_id" value. If it is lower, error out.
    for row in positions.items():
        # Only child items have a value in their "parent_id" field.
        if row[1]["parent_id"] == "":
            continue
        parent_id = row[1]["parent_id"]
        if parent_id in positions:
            if row[1]["position"] < positions[parent_id]["position"]:
                message = f"Child item with CSV ID \"{row[0]}\" must come after its parent (CSV ID \"{row[1]['parent_id']}\") in the CSV file."
                logging.error(message)
                if config["perform_soft_checks"] is False:
                    sys.exit("Error: " + message)


def validate_parent_ids_in_csv_id_to_node_id_map(config, csv_data):
    """Query the CSV ID to node ID map to check for non-unique parent IDs.
    If they exist, report out but do not exit.
    """
    if (
        len(config["csv_id_to_node_id_map_allowed_hosts"]) > 0
        and config["query_csv_id_to_node_id_map_for_parents"] is True
    ):
        csv_id_to_node_id_map_allowed_hosts_message = (
            f'Limiting lookups to those with the hostname "' + config["host"] + '".'
        )
    else:
        csv_id_to_node_id_map_allowed_hosts_message = (
            f'Not limiting lookups to those with the hostname "' + config["host"] + '".'
        )

    if config["query_csv_id_to_node_id_map_for_parents"] is True:
        message = f"Validating parent IDs in the CSV ID to node ID map, please wait. {csv_id_to_node_id_map_allowed_hosts_message}"
        print(message)
    else:
        return

    # First, confirm the database exists; if not, tell the user and exit.
    if config["csv_id_to_node_id_map_path"] is not False:
        if not os.path.exists(config["csv_id_to_node_id_map_path"]):
            message = f"Can't find CSV ID to node ID database path at {config['csv_id_to_node_id_map_path']}."
            logging.error(message)
            sys.exit("Error: " + message)

    # If database exists, query it.
    if (
        config["query_csv_id_to_node_id_map_for_parents"] is True
        and config["csv_id_to_node_id_map_path"] is not False
    ):
        id_field = config["id_field"]
        parents_from_id_map = []
        parents_from_id_map_warnings = []

        for row in csv_data:
            csv_id_to_node_id_map_allowed_hosts_sql = (
                get_csv_id_to_node_id_map_allowed_hosts_sql(config)
            )

            if config["ignore_duplicate_parent_ids"] is True:
                query = (
                    "select node_id from csv_id_to_node_id_map where "
                    + csv_id_to_node_id_map_allowed_hosts_sql
                    + f' csv_id = "{row["parent_id"]}" order by timestamp desc limit 1'
                )
            else:
                query = (
                    "select node_id from csv_id_to_node_id_map where"
                    + csv_id_to_node_id_map_allowed_hosts_sql
                    + " csv_id = ?"
                )
            parent_in_id_map_result = sqlite_manager(
                config,
                operation="select",
                query=query,
                db_file_path=config["csv_id_to_node_id_map_path"],
            )

            for parent_in_id_map_row in parent_in_id_map_result:
                parents_from_id_map.append(parent_in_id_map_row["node_id"].strip())
            parents_from_id_map = list(dict.fromkeys(parents_from_id_map))
            if len(parents_from_id_map) > 1:
                parents_from_id_map_message = f'Query of ID map for parent ID "{row["parent_id"]}" returned multiple node IDs: ({", ".join(parents_from_id_map)}).'
                parents_from_id_map_warnings.append(parents_from_id_map_message)
        if len(parents_from_id_map_warnings) > 1:
            logging.warning(parents_from_id_map_warnings[-1])
            print("Warning: " + parents_from_id_map_warnings[-1])


def validate_taxonomy_field_values(config, field_definitions, csv_data):
    """Loop through all fields in field_definitions, and if a field
    is a taxonomy reference field, validate all values in the CSV
    data in that field against term IDs in the taxonomies referenced
    by the field. Does not validate Typed Relation fields
    (see validate_typed_relation_field_values()).
    """
    # Define a list to store names of CSV fields that reference vocabularies.
    fields_with_vocabularies = list()
    vocab_validation_issues = False
    # Get all the term IDs for vocabularies referenced in all fields in the CSV.
    for column_name in csv_data.fieldnames:
        if column_name in field_definitions:
            if (
                field_definitions[column_name]["field_type"] == "entity_reference"
                and "vocabularies" in field_definitions[column_name]
            ):
                vocabularies = get_field_vocabularies(
                    config, field_definitions, column_name
                )
                # If there are no vocabularies linked to the current field, 'vocabularies'
                # will be False and will throw a TypeError.
                try:
                    num_vocabs = len(vocabularies)
                    if num_vocabs > 0:
                        fields_with_vocabularies.append(column_name)
                except BaseException:
                    message = (
                        'Workbench cannot get vocabularies linked to field "'
                        + column_name
                        + '". Please confirm that field has at least one vocabulary.'
                    )
                    logging.error(message)
                    sys.exit("Error: " + message)

    # If none of the CSV fields are taxonomy reference fields, return.
    if len(fields_with_vocabularies) == 0:
        return

    # Iterate through the CSV and validate each taxonomy fields's values.
    new_term_names_in_csv_results = []
    for count, row in enumerate(csv_data, start=1):
        for column_name in fields_with_vocabularies:
            if len(row[column_name]):
                new_term_names_in_csv = validate_taxonomy_reference_value(
                    config,
                    field_definitions,
                    column_name,
                    row[column_name],
                    row[config["id_field"]],
                )
                new_term_names_in_csv_results.append(new_term_names_in_csv)

    if True in new_term_names_in_csv_results and config["allow_adding_terms"] is True:
        if config["validate_terms_exist"] is True:
            message = (
                "OK, term IDs/names in CSV file exist in their respective taxonomies"
            )
            if config["log_term_creation"] is True:
                message = (
                    message
                    + " (new terms will be created as noted in the Workbench log)."
                )
            else:
                message = (
                    message
                    + ' (new terms will be created but not noted in the Workbench log since "log_term_creation" is set to false).'
                )
            print(message)
        else:
            if config["log_term_creation"] is True:
                print(
                    "Skipping check for existence of terms (new terms will be created as noted in the Workbench log)."
                )
            else:
                print(
                    'Skipping check for existence of terms (notee: terms will be created but not noted in the Workbench log - "log_term_creation" is set to false).'
                )
            logging.warning(
                "Skipping check for existence of terms (but new terms will be created)."
            )
    else:
        # All term IDs are in their field's vocabularies.
        print("OK, term IDs/names in CSV file exist in their respective taxonomies.")
        logging.info(
            "OK, term IDs/names in CSV file exist in their respective taxonomies."
        )

    return vocab_validation_issues


def validate_vocabulary_fields_in_csv(config, vocabulary_id, vocab_csv_file_path):
    """Loop through all fields in CSV to ensure that all present fields match field
    from the vocab's field definitions, and that any required fields are present.
    Also checks that each row has the same number of columns as there are headers.
    """
    """Parameters
        ----------
        config : dict
            The configuration settings defined by workbench_config.get_config().
        vocabulary_id : string
            The ID of the vocabulary to validate.
        vocab_csv_file_path: string
            Location of vocabulary CSV file.
    """
    csv_data = get_csv_data(config, "taxonomy_fields", vocab_csv_file_path)
    csv_column_headers = copy.copy(csv_data.fieldnames)

    # Check whether each row contains the same number of columns as there are headers.
    row_count = 0
    for count, row in enumerate(csv_data, start=1):
        extra_headers = False
        field_count = 0
        row_count += 1
        for field in row:
            # 'stringtopopulateextrafields' is added by get_csv_data() if there are extra headers.
            if row[field] == "stringtopopulateextrafields":
                extra_headers = True
            else:
                field_count += 1
        if extra_headers is True:
            message = (
                "Row with ID "
                + row[config["id_field"]]
                + ') of the vocabulary CSV file "'
                + vocab_csv_file_path
                + '" has fewer columns than there are headers ('
                + str(len(csv_column_headers))
                + ")."
            )
            logging.error(message)
            sys.exit("Error: " + message)
        # Note: this message is also generated in get_csv_data() since CSV Writer thows an exception if the row has
        # form fields than headers.
        if len(csv_column_headers) < field_count:
            message = (
                "Row with term name '"
                + row["term_name"]
                + ') of the vocabulary CSV file "'
                + vocab_csv_file_path
                + '" has more columns ('
                + str(field_count)
                + ") than there are headers ("
                + str(len(csv_column_headers))
                + ")."
            )
            logging.error(message)
            sys.exit("Error: " + message)
    message = (
        "OK, all "
        + str(row_count)
        + ' rows in the vocabulary CSV file "'
        + vocab_csv_file_path
        + '" have the same number of columns as there are headers ('
        + str(len(csv_column_headers))
        + ")."
    )
    print(message)
    logging.info(message)

    # Check that the required 'term_name' and 'parent' columns are present in the CSV, and that
    # any fields defined as required in the vocabulary are also present.
    field_definitions = get_field_definitions(
        config, "taxonomy_term", vocabulary_id.strip()
    )
    for column_name in csv_column_headers:
        # Check that 'term_name' and 'parent' are in the CSV.
        if "term_name" not in csv_column_headers:
            message = (
                'Required column "term_name" not found in vocabulary CSV file "'
                + vocab_csv_file_path
                + '".'
            )
            logging.error(message)
            sys.exit("Error: " + message)
        if "parent" not in csv_column_headers:
            message = (
                'Required column "parent" not found in vocabulary CSV file "'
                + vocab_csv_file_path
                + '".'
            )
            logging.error(message)
            sys.exit("Error: " + message)
        # Then vocabulary fields that are defined as required.
        field_definition_fieldnames = field_definitions.keys()
        for field in field_definition_fieldnames:
            if (
                field_definitions[field]["required"] is True
                and field not in csv_data.fieldnames
            ):
                message = (
                    'Required column "'
                    + field
                    + '" not found in vocabulary CSV file "'
                    + vocab_csv_file_path
                    + '".'
                )
                logging.error(message)
                sys.exit("Error: " + message)

    # Check whether remaining fields in the vocabulary CSV are fields defined in the current vocabulary.
    if "field_name" in csv_column_headers:
        csv_column_headers.remove("field_name")
    if "parent" in csv_column_headers:
        csv_column_headers.remove("parent")
    for csv_field in csv_column_headers:
        if csv_field not in field_definitions.keys():
            message = (
                'CSV column "'
                + csv_field
                + '" in vocabulary CSV file "'
                + vocab_csv_file_path
                + '" is not a field in the "'
                + vocabulary_id
                + '" vocabulary.'
            )
            logging.error(message)
            sys.exit("Error: " + message)


def validate_typed_relation_field_values(config, field_definitions, csv_data):
    """Validate values in fields that are of type 'typed_relation'. Each CSV
    value must have this pattern: "string:string:int" or "string:string:string".
    If the last segment is a string, it must be term name, a namespaced term name,
    or an http URI.
    """
    # Define a list to store CSV field names that contain vocabularies.
    fields_with_vocabularies = list()
    # Get all the term IDs for vocabularies referenced in all fields in the CSV.
    vocab_validation_issues = False
    for column_name in csv_data.fieldnames:
        if column_name in field_definitions:
            if "vocabularies" in field_definitions[column_name]:
                vocabularies = get_field_vocabularies(
                    config, field_definitions, column_name
                )
                # If there are no vocabularies linked to the current field, 'vocabularies'
                # will be False and will throw a TypeError.
                try:
                    num_vocabs = len(vocabularies)
                    if num_vocabs > 0:
                        fields_with_vocabularies.append(column_name)
                except BaseException:
                    message = (
                        'Workbench cannot get vocabularies linked to field "'
                        + column_name
                        + '". Please confirm that field has at least one vocabulary.'
                    )
                    logging.error(message)
                    sys.exit("Error: " + message)
                all_tids_for_field = []

    # If none of the CSV fields are taxonomy reference fields, return.
    if len(fields_with_vocabularies) == 0:
        return

    typed_relation_fields_present = False
    new_term_names_in_csv_results = []
    for count, row in enumerate(csv_data, start=1):
        for field_name in field_definitions.keys():
            if (
                field_definitions[field_name]["field_type"] == "typed_relation"
                and "typed_relations" in field_definitions[field_name]
            ):
                if field_name in row:
                    typed_relation_fields_present = True
                    delimited_field_values = row[field_name].split(
                        config["subdelimiter"]
                    )
                    for field_value in delimited_field_values:
                        if len(field_value) == 0:
                            continue
                        # First check the required patterns.
                        if not re.match(
                            "^[0-9a-zA-Z]+:[0-9a-zA-Z]+:.+$", field_value.strip()
                        ):
                            message = (
                                'Value in field "'
                                + field_name
                                + '" in row with ID '
                                + row[config["id_field"]]
                                + " ("
                                + field_value
                                + ") does not use the structure required for typed relation fields."
                            )
                            logging.error(message)
                            sys.exit("Error: " + message)

                        # Then, check to see if the relator string (the first two parts of the
                        # value) exist in the field_definitions[fieldname]['typed_relations'] list.
                        typed_relation_value_parts = field_value.split(":", 2)
                        relator_string = (
                            typed_relation_value_parts[0]
                            + ":"
                            + typed_relation_value_parts[1]
                        )
                        if (
                            relator_string
                            not in field_definitions[field_name]["typed_relations"]
                        ):
                            message = (
                                'Value in field "'
                                + field_name
                                + '" in row with ID '
                                + row[config["id_field"]]
                                + " contains a relator ("
                                + relator_string
                                + ") that is not configured for that field."
                            )
                            logging.error(message)
                            sys.exit("Error: " + message)

                    # Iterate through the CSV and validate the taxonomy term/name/URI in each field subvalue.
                    for column_name in fields_with_vocabularies:
                        if len(row[column_name]):
                            delimited_field_values = row[column_name].split(
                                config["subdelimiter"]
                            )
                            delimited_field_values_without_relator_strings = []
                            for field_value in delimited_field_values:
                                # Strip the relator string out from field_value, leaving the vocabulary ID and term ID/name/URI.
                                term_to_check = re.sub(
                                    "^[0-9a-zA-Z]+:[0-9a-zA-Z]+:", "", field_value
                                )
                                delimited_field_values_without_relator_strings.append(
                                    term_to_check
                                )

                            field_value_to_check = config["subdelimiter"].join(
                                delimited_field_values_without_relator_strings
                            )
                            new_term_names_in_csv = validate_taxonomy_reference_value(
                                config,
                                field_definitions,
                                column_name,
                                field_value_to_check,
                                row[config["id_field"]],
                            )
                            new_term_names_in_csv_results.append(new_term_names_in_csv)

    if (
        typed_relation_fields_present is True
        and True in new_term_names_in_csv_results
        and config["allow_adding_terms"] is True
    ):
        message = "OK, term IDs/names used in typed relation fields in the CSV file exist in their respective taxonomies"
        if config["log_term_creation"] is True:
            message = (
                message + " (new terms will be created as noted in the Workbench log)."
            )
        else:
            message = (
                message
                + ' (new terms will be created but not noted in the Workbench log since "log_term_creation" is set to false).'
            )
        print(message)
    else:
        if typed_relation_fields_present is True:
            # All term IDs are in their field's vocabularies.
            print(
                "OK, term IDs/names used in typed relation fields in the CSV file exist in their respective taxonomies."
            )
            logging.info(
                "OK, term IDs/names used in typed relation fields in the CSV file exist in their respective taxonomies."
            )

    return vocab_validation_issues


def validate_taxonomy_reference_value(
    config, field_definitions, csv_field_name, csv_field_value, row_id
):
    this_fields_vocabularies = get_field_vocabularies(
        config, field_definitions, csv_field_name
    )

    # Not an entity reference field on a vocabulary or a typed relation field.
    if (
        field_definitions[csv_field_name]["field_type"]
        in ["entity_reference", "typed_relation"]
        and "vocabularies" in field_definitions[csv_field_name]
    ) is False:
        return None

    this_fields_vocabularies_string = ", ".join(this_fields_vocabularies)

    new_term_names_in_csv = False

    # Allow for multiple values in one field.
    terms_to_check = csv_field_value.split(config["subdelimiter"])
    for field_value in terms_to_check:
        # If this is a multi-taxonomy field, all term names (not IDs or URIs) must be namespaced using the vocab_id:term_name pattern,
        # regardless of whether config['allow_adding_terms'] is True. Also, we need to accommodate terms that are namespaced
        # and also contain a ':'.
        if (
            len(this_fields_vocabularies) > 1
            and value_is_numeric(field_value) is False
            and not field_value.startswith("http")
        ):
            split_field_values = field_value.split(config["subdelimiter"])
            for split_field_value in split_field_values:
                if ":" in field_value:
                    # If the : is present, validate that the namespace is one of the vocabulary IDs referenced by this field.
                    [tentative_namespace, tentative_term_name] = field_value.split(
                        ":", 1
                    )
                    if tentative_namespace not in this_fields_vocabularies:
                        message = (
                            'Vocabulary ID "'
                            + tentative_namespace
                            + '" used in CSV column "'
                            + csv_field_name
                            + '", row with ID '
                            + str(row_id)
                            + " does not match any of the vocabularies referenced by the"
                            + " corresponding Drupal field ("
                            + this_fields_vocabularies_string
                            + ")."
                        )
                        logging.error(message)
                        sys.exit("Error: " + message)
                else:
                    message = (
                        'Term names in CSV field "'
                        + csv_field_name
                        + '" require a vocabulary namespace; CSV value '
                    )
                    message_2 = (
                        '"'
                        + field_value
                        + '" in row with ID '
                        + str(row_id)
                        + " does not have one."
                    )
                    logging.error(message + message_2)
                    sys.exit("Error: " + message + message_2)

                validate_term_name_length(
                    split_field_value, str(row_id), csv_field_name
                )

        # Check to see if field_value is a member of the field's vocabularies. First, check whether field_value is a term ID.
        if (
            value_is_numeric(field_value)
            and csv_field_name not in config["columns_with_term_names"]
        ):
            field_value = field_value.strip()
            term_in_vocabs = False
            for vocab_id in this_fields_vocabularies:
                term_vocab = get_term_vocab(config, field_value)
                if term_vocab == vocab_id:
                    term_in_vocabs = True
            if term_in_vocabs is False:
                message = (
                    'CSV field "'
                    + csv_field_name
                    + '" in row with ID '
                    + str(row_id)
                    + " contains a term ID ("
                    + field_value
                    + ") that is "
                )
                if len(this_fields_vocabularies) > 1:
                    message_2 = (
                        "not in one of the referenced vocabularies ("
                        + this_fields_vocabularies_string
                        + ")."
                    )
                else:
                    message_2 = (
                        'not in the referenced vocabulary ("'
                        + this_fields_vocabularies[0]
                        + '").'
                    )
                logging.error(message + message_2)
                sys.exit("Error: " + message + message_2)
        # Then check values that are URIs.
        elif field_value.strip().startswith("http"):
            field_value = field_value.strip()
            tid_from_uri = get_term_id_from_uri(config, field_value)
            if value_is_numeric(tid_from_uri):
                term_vocab = get_term_vocab(config, tid_from_uri)
                term_in_vocabs = False
                for vocab_id in this_fields_vocabularies:
                    if term_vocab == vocab_id:
                        term_in_vocabs = True
                if term_in_vocabs is False:
                    message = (
                        'CSV field "'
                        + csv_field_name
                        + '" in row with ID '
                        + str(row_id)
                        + " contains a term URI ("
                        + field_value
                        + ") that is "
                    )
                    if len(this_fields_vocabularies) > 1:
                        message_2 = (
                            "not in one of the referenced vocabularies ("
                            + this_fields_vocabularies_string
                            + ")."
                        )
                    else:
                        message_2 = (
                            'not in the referenced vocabulary ("'
                            + this_fields_vocabularies[0]
                            + '").'
                        )
                    logging.error(message + message_2)
                    sys.exit("Error: " + message + message_2)
            else:
                message = (
                    'Term URI "'
                    + field_value
                    + '" used in CSV column "'
                    + csv_field_name
                    + '" row with ID '
                    + str(row_id)
                    + " does not match any terms."
                )
                logging.error(message)
                sys.exit("Error: " + message)
        # Finally, check values that are string term names.
        else:
            new_terms_to_add = []
            for vocabulary in this_fields_vocabularies:
                tid = find_term_in_vocab(config, vocabulary, field_value)
                if value_is_numeric(tid) is False:
                    # Single taxonomy fields.
                    if len(this_fields_vocabularies) == 1:
                        if config["allow_adding_terms"] is True:
                            # Warn if namespaced term name is not in specified vocab.
                            if tid is False:
                                new_term_names_in_csv = True
                                validate_term_name_length(
                                    field_value, str(row_id), csv_field_name
                                )
                                message = (
                                    'CSV field "'
                                    + csv_field_name
                                    + '" in row with ID '
                                    + str(row_id)
                                    + ' contains a term ("'
                                    + field_value.strip()
                                    + '") that is '
                                )

                                if (
                                    this_fields_vocabularies[0]
                                    in config["protected_vocabularies"]
                                ):
                                    message_2 = (
                                        'not in the referenced vocabulary ("'
                                        + this_fields_vocabularies[0]
                                        + '"). The term will not be created since "'
                                        + this_fields_vocabularies[0]
                                        + '" is registered in the "protected_vocabularies" config setting.'
                                    )
                                else:
                                    message_2 = (
                                        'not in the referenced vocabulary ("'
                                        + this_fields_vocabularies[0]
                                        + '"). That term will be created.'
                                    )
                                if config["validate_terms_exist"] is True:
                                    logging.warning(message + message_2)
                        else:
                            new_term_names_in_csv = True
                            message = (
                                'CSV field "'
                                + csv_field_name
                                + '" in row with ID '
                                + str(row_id)
                                + ' contains a term ("'
                                + field_value.strip()
                                + '") that is '
                            )
                            message_2 = (
                                'not in the referenced vocabulary ("'
                                + this_fields_vocabularies[0]
                                + '").'
                            )
                            logging.error(message + message_2)
                            sys.exit("Error: " + message + message_2)

                # If this is a multi-taxonomy field, all term names must be namespaced using the vocab_id:term_name pattern,
                # regardless of whether config['allow_adding_terms'] is True.
                if len(this_fields_vocabularies) > 1:
                    split_field_values = field_value.split(config["subdelimiter"])
                    for split_field_value in split_field_values:
                        # Check to see if the namespaced vocab is referenced by this field.
                        [namespace_vocab_id, namespaced_term_name] = (
                            split_field_value.split(":", 1)
                        )
                        if namespace_vocab_id not in this_fields_vocabularies:
                            message = (
                                'CSV field "'
                                + csv_field_name
                                + '" in row with ID '
                                + str(row_id)
                                + " contains a namespaced term name "
                            )
                            message_2 = (
                                '("'
                                + namespaced_term_name.strip()
                                + '") that specifies a vocabulary not associated with that field ('
                                + namespace_vocab_id
                                + ")."
                            )
                            logging.error(message + message_2)
                            sys.exit("Error: " + message + message_2)

                        tid = find_term_in_vocab(
                            config, namespace_vocab_id, namespaced_term_name
                        )

                        # Warn if namespaced term name is not in specified vocab.
                        if config["allow_adding_terms"] is True:
                            if (
                                tid is False
                                and split_field_value not in new_terms_to_add
                            ):
                                new_term_names_in_csv = True
                                message = (
                                    'CSV field "'
                                    + csv_field_name
                                    + '" in row with ID '
                                    + str(row_id)
                                    + ' contains a term ("'
                                    + namespaced_term_name.strip()
                                    + '") that is '
                                )

                                if (
                                    namespace_vocab_id
                                    in config["protected_vocabularies"]
                                ):
                                    message_2 = (
                                        'not in the referenced vocabulary ("'
                                        + namespace_vocab_id
                                        + '"). The term will not be created since "'
                                        + namespace_vocab_id
                                        + '" is registered in the "protected_vocabularies" config setting.'
                                    )
                                else:
                                    message_2 = (
                                        'not in the referenced vocabulary ("'
                                        + namespace_vocab_id
                                        + '"). That term will be created.'
                                    )
                                if config["validate_terms_exist"] is True:
                                    logging.warning(message + message_2)
                                new_terms_to_add.append(split_field_value)

                                validate_term_name_length(
                                    split_field_value,
                                    str(row_id),
                                    csv_field_name,
                                )
                        # Die if namespaced term name is not specified vocab.
                        else:
                            if tid is False:
                                message = (
                                    'CSV field "'
                                    + csv_field_name
                                    + '" in row with ID '
                                    + str(row_id)
                                    + ' contains a term ("'
                                    + namespaced_term_name.strip()
                                    + '") that is '
                                )
                                message_2 = (
                                    'not in the referenced vocabulary ("'
                                    + namespace_vocab_id
                                    + '").'
                                )
                                logging.warning(message + message_2)
                                sys.exit("Error: " + message + message_2)

    return new_term_names_in_csv


def write_to_output_csv(config, id, node_json, input_csv_row=None):
    """Appends a row to the CSV file located at config['output_csv'].
    If config['output_csv_include_input_csv'] is true, includes values
    from the input CSV.
    """
    """Parameters
        ----------
        config : dict
            The configuration settings defined by workbench_config.get_config().
        id : str
            The value of the CSV row's ID field.
        node_json : str
            The JSON representation of the node just created, provided by Drupal.
        input_csv_row : dict
            The CSV Reader representation of the current input CSV row. Note that
            this is copy.deepcopy() of the CSV row since passing the row in as is
            modifies it in global scope.
        Returns
        -------
        None
    """
    # Importing the workbench_fields module at the top of this module with the
    # rest of the imports causes a circular import exception, so we do it here.
    import workbench_fields

    if config["task"] == "create_from_files":
        config["id_field"] = "ID"

    node_dict = json.loads(node_json)
    node_field_names = list(node_dict.keys())
    node_field_names.insert(0, "langcode")
    node_field_names.insert(0, "promote")
    node_field_names.insert(0, "published")
    node_field_names.insert(0, "content_type")
    node_field_names.insert(0, "node_id")
    # "id_field" needs to be the first column header for the check below.
    node_field_names.insert(0, config["id_field"])
    # Don't include these fields from each node Drupal fields in our output
    # (but we add back in type/"content_type", status/"published", and langcode below).
    fields_to_remove = [
        "nid",
        "vid",
        "type",
        "status",
        "langcode",
        "created",
        "changed",
        "default_langcode",
        "uid",
        "sticky",
        "revision_timestamp",
        "revision_translation_affected",
        "revision_uid",
        "revision_log",
        "content_translation_source",
        "content_translation_outdated",
    ]
    for field_to_remove in fields_to_remove:
        if field_to_remove in node_field_names:
            node_field_names.remove(field_to_remove)

    # Don't include these input CSV fields in our output, except for "published", "promote",
    # and "langcode", which we populate separately below from node data.
    reserved_fields = [
        "file",
        "parent_id",
        "url_alias",
        "image_alt_text",
        "checksum",
        "published",
        "promote",
        "langcode",
    ]
    additional_files_columns = list(get_additional_files_config(config).keys())
    if len(additional_files_columns) > 0:
        reserved_fields = reserved_fields + additional_files_columns

    csvfile = open(config["output_csv"], "a+", encoding="utf-8")

    if input_csv_row is not None and config["output_csv_include_input_csv"] is True:
        input_csv_row_fieldnames = list(input_csv_row.keys())
        for reserved_field in reserved_fields:
            if reserved_field in input_csv_row:
                input_csv_row_fieldnames.remove(reserved_field)

    writer = csv.DictWriter(csvfile, fieldnames=node_field_names, lineterminator="\n")

    # Check for presence of header row, don't add it if it's already there.
    with open(config["output_csv"]) as f:
        first_line = f.readline()
    if not first_line.startswith(config["id_field"]):
        writer.writeheader()

    # Assemble the CSV record to write.
    row = dict()
    row[config["id_field"]] = id
    row["node_id"] = node_dict["nid"][0]["value"]
    row["uuid"] = node_dict["uuid"][0]["value"]
    row["title"] = node_dict["title"][0]["value"]
    if node_dict["status"][0]["value"] is True:
        row["published"] = "1"
    else:
        row["published"] = "0"
    if node_dict["promote"][0]["value"] is True:
        row["promote"] = "1"
    else:
        row["promote"] = "0"
    row["content_type"] = node_dict["type"][0]["target_id"]
    row["langcode"] = node_dict["langcode"][0]["value"]

    if input_csv_row is not None and config["output_csv_include_input_csv"] is True:
        field_definitions = get_field_definitions(config, "node")
        for reserved_field in reserved_fields:
            if reserved_field in input_csv_row:
                del input_csv_row[reserved_field]
        # Then append the input row to the new node data.
        for field_name in node_dict:
            if field_name.startswith("field_"):
                row[field_name] = serialize_field_json(
                    config, field_definitions, field_name, node_dict[field_name]
                )

        row.update(input_csv_row)
    writer.writerow(row)
    csvfile.close()


def get_sequence_indicator_from_filename(config, file_name):
    """Extracts the last segment of a page filename like some-ID-003.jpg."""
    """Parameters
        ----------
        config : dict
            The configuration settings defined by workbench_config.get_config().
        file_name : str
            The filename to extract the sequence indicator from.
        Returns
        -------
        str
    """
    filename_without_extension = os.path.splitext(file_name)[0]
    filename_segments = filename_without_extension.split(
        config["paged_content_sequence_separator"]
    )
    weight = filename_segments[-1]
    weight = weight.lstrip("0")
    return str(weight)


def create_children_from_directory(config, parent_csv_record, parent_node_id):
    path_to_rollback_csv_file = get_rollback_csv_filepath(config)
    prepare_csv_id_to_node_id_map(config)

    # These objects will have a title (derived from the page filename), an ID based on the parent's id, and a config-defined
    # Islandora model. Content type and status are inherited as is from parent, as are other required fields. Fields
    # specified in the csv_value_templates_for_paged_content config setting are also applied to paged children. The
    # weight assigned to the page is the last segment in the filename, split from the rest of the filename using the
    # character defined in the 'paged_content_sequence_separator' config option.
    parent_id = parent_csv_record[config["id_field"]]
    page_dir_name = parent_csv_record[config["page_files_source_dir_field"]]
    page_dir_path = os.path.join(config["input_dir"], page_dir_name)

    if "paged_content_additional_page_media" in config:
        if "paged_content_image_file_extension" in config:
            page_files = [
                f
                for f in os.listdir(page_dir_path)
                if f.endswith(
                    config["paged_content_image_file_extension"].lstrip(".").strip()
                )
            ]
        else:
            page_files = os.listdir(page_dir_path)
    else:
        page_files = os.listdir(page_dir_path)

    # Identify any required fields that are in the parent CSV.
    required_fields = get_required_bundle_fields(config, "node", config["content_type"])

    for page_file_name in page_files:
        if page_file_name.strip().lower() in [
            fn.strip().lower() for fn in config["paged_content_ignore_files"]
        ]:
            continue

        # Only want files, not directories.
        if os.path.isdir(os.path.join(page_dir_path, page_file_name)):
            continue

        if (
            config["recovery_mode_starting_from_node_id"] is not False
            and value_is_numeric(config["recovery_mode_starting_from_node_id"]) is True
            and parent_id is not None
        ):
            nid_in_map = recovery_mode_id_in_csv_id_to_node_id_map(
                config, page_file_name, parent_id
            )
            if nid_in_map is not False:
                message = f"Page/child file {page_file_name} has already been ingested at ({config['host']}/node/{nid_in_map}), skipping it."
                logging.info(message)
                continue

        weight = get_sequence_indicator_from_filename(config, page_file_name)
        filename_without_extension = os.path.splitext(page_file_name)[0]

        # This "identifier" is the CSV ID, not a Drupal field. It may be overwritten
        # by a CSV value template below.
        page_identifier = parent_id + "_" + filename_without_extension

        page_title = get_page_title_from_template(
            config, parent_csv_record["title"], weight
        )

        inherited_fields = copy.copy(required_fields)

        csv_row_to_apply_to_paged_children = copy.deepcopy(parent_csv_record)
        csv_row_to_apply_to_paged_children["file"] = page_file_name
        if validate_weight_value(weight) is False:
            logging.warning(
                f'Sequence indicator in page filename "{os.path.join(page_dir_path, page_file_name)}" is not a valid "field_weight" value; that field will not be populated on the page node.'
            )
            weight = ""
        csv_row_to_apply_to_paged_children["field_weight"] = weight

        # Add any fields to the page's row that are defined in config["csv_value_templates_for_paged_content"].
        if (
            "csv_value_templates_for_paged_content" in config
            and len(config["csv_value_templates_for_paged_content"]) > 0
        ):
            for paged_items_template in config["csv_value_templates_for_paged_content"]:
                for (
                    paged_items_template_field_name,
                    paged_items_template_template,
                ) in paged_items_template.items():
                    if paged_items_template_field_name not in inherited_fields:
                        if paged_items_template_field_name in parent_csv_record:
                            inherited_fields.append(paged_items_template_field_name)
                            csv_row_to_apply_to_paged_children[
                                paged_items_template_field_name
                            ] = parent_csv_record[paged_items_template_field_name]

        if (
            "csv_value_templates_for_paged_content" in config
            and len(config["csv_value_templates_for_paged_content"]) > 0
        ):
            csv_row_to_apply_to_paged_children = apply_csv_value_templates(
                config,
                "csv_value_templates_for_paged_content",
                csv_row_to_apply_to_paged_children,
            )

        node_json = {
            "type": [
                {
                    "target_id": config["paged_content_page_content_type"],
                    "target_type": "node_type",
                }
            ],
            "title": [{"value": page_title}],
            "field_member_of": [{"target_id": parent_node_id, "target_type": "node"}],
            "field_weight": [{"value": weight}],
        }

        # Add field_model if that field exists in the child's content type.
        entity_fields = get_entity_fields(
            config, "node", config["paged_content_page_content_type"]
        )
        if "field_model" in entity_fields:
            if not value_is_numeric(
                config["paged_content_page_model_tid"].strip()
            ) and config["paged_content_page_model_tid"].strip().startswith("http"):
                paged_content_model_tid = get_term_id_from_uri(
                    config, config["paged_content_page_model_tid"].strip()
                )
            else:
                paged_content_model_tid = config["paged_content_page_model_tid"].strip()
            node_json["field_model"] = [
                {"target_id": paged_content_model_tid, "target_type": "taxonomy_term"}
            ]

        # Add viewer override if defined in CSV or config.
        if "paged_content_page_viewer_override" in config:
            if (
                value_is_numeric(config["paged_content_page_viewer_override"]) is False
                and config["paged_content_page_viewer_override"].startswith("http")
                is True
            ):
                page_viewer_override_tid_info = get_all_representations_of_term(
                    config,
                    vocab_id="islandora_display",
                    uri=config["paged_content_page_viewer_override"],
                )
                page_viewer_override_tid = page_viewer_override_tid_info["term_id"]
            elif (
                value_is_numeric(config["paged_content_page_viewer_override"]) is False
                and config["paged_content_page_viewer_override"].startswith("http")
                is False
            ):
                page_viewer_override_tid_info = get_all_representations_of_term(
                    config,
                    vocab_id="islandora_display",
                    name=config["paged_content_page_viewer_override"],
                )
                page_viewer_override_tid = page_viewer_override_tid_info["term_id"]
            else:
                page_viewer_override_tid = config["paged_content_page_viewer_override"]

        viewer_override_fieldname = config["viewer_override_fieldname"]
        if (
            viewer_override_fieldname in parent_csv_record
            and "paged_content_page_viewer_override" in config
        ):
            node_json[viewer_override_fieldname] = [
                {
                    "target_id": page_viewer_override_tid,
                    "target_type": "taxonomy_term",
                }
            ]
        if (
            viewer_override_fieldname in parent_csv_record
            and "paged_content_page_viewer_override" not in config
        ):
            node_json[viewer_override_fieldname] = [
                {
                    "target_id": parent_csv_record["field_viewer_override"],
                    "target_type": "taxonomy_term",
                }
            ]
        if (
            viewer_override_fieldname not in parent_csv_record
            and "paged_content_page_viewer_override" in config
        ):
            node_json[viewer_override_fieldname] = [
                {
                    "target_id": page_viewer_override_tid,
                    "target_type": "taxonomy_term",
                }
            ]

        # Some optional base fields, inherited from the parent object.
        if "uid" in parent_csv_record:
            if len(parent_csv_record["uid"]) > 0:
                node_json["uid"] = [{"target_id": parent_csv_record["uid"]}]

        if "created" in parent_csv_record:
            if len(parent_csv_record["created"]) > 0:
                node_json["created"] = [{"value": parent_csv_record["created"]}]

        if len(inherited_fields) > 0:
            field_definitions = get_field_definitions(config, "node")
            # Importing the workbench_fields module at the top of this module with the
            # rest of the imports causes a circular import exception, so we do it here.
            import workbench_fields

            for inherited_field in inherited_fields:
                # These fields are populated above.
                if inherited_field in [
                    "title",
                    "field_model",
                    "uid",
                    "created",
                    config["viewer_override_fieldname"],
                ]:
                    continue

                # Assemble Drupal field structures from CSV data. If new field types are added to
                # workbench_fields.py, they need to be registered in the following if/elif/else block.

                field = workbench_fields.WorkbenchFieldFactory.get_field_handler(
                    field_definitions[inherited_field]["field_type"]
                )
                node_json = field.create(
                    config,
                    field_definitions,
                    node_json,
                    csv_row_to_apply_to_paged_children,
                    inherited_field,
                )

        node_headers = {"Content-Type": "application/json"}
        node_endpoint = "/node?_format=json"
        node_response = issue_request(
            config, "POST", node_endpoint, node_headers, node_json, None
        )
        if node_response.status_code == 201:
            node_uri = node_response.headers["location"]
            print('+ Node for child "' + page_title + '" created at ' + node_uri + ".")
            logging.info('Node for child "%s" created at %s.', page_title, node_uri)
            if "output_csv" in config.keys():
                write_to_output_csv(config, page_identifier, node_response.text)

            node_nid = get_nid_from_url_alias(config, node_uri)

            populate_csv_id_to_node_id_map(
                config, parent_id, parent_node_id, page_file_name, node_nid
            )

            page_file_path = os.path.join(page_dir_name, page_file_name)
            write_rollback_node_id(
                config,
                node_nid,
                "",
                page_title,
                page_file_path,
                parent_node_id,
                path_to_rollback_csv_file,
            )

            fake_csv_record = collections.OrderedDict()
            fake_csv_record["title"] = page_title
            fake_csv_record["file"] = page_file_path
            fake_csv_record[config["id_field"]] = parent_csv_record[config["id_field"]]
            media_response_status_code = create_media(
                config, page_file_path, "file", node_nid, fake_csv_record
            )
            allowed_media_response_codes = [201, 204]
            if media_response_status_code in allowed_media_response_codes:
                if media_response_status_code is False:
                    print(
                        f"- ERROR: Media for {page_file_path} not created. See log for more information."
                    )
                    logging.error(
                        "Media for %s not created. HTTP response code was %s.",
                        page_file_path,
                        media_response_status_code,
                    )
                    continue
                else:
                    logging.info("Media for %s created.", page_file_path)
                    print(f"+ Media for {page_file_path} created.")

            if config["paged_content_from_directories"] is True:
                if "paged_content_additional_page_media" in config:
                    for extension_mapping in config[
                        "paged_content_additional_page_media"
                    ]:
                        for (
                            additional_page_media_use_term,
                            additional_page_media_extension,
                        ) in extension_mapping.items():
                            if str(additional_page_media_use_term).startswith("http"):
                                additional_page_media_use_tid = get_term_id_from_uri(
                                    config, additional_page_media_use_term
                                )
                            else:
                                additional_page_media_use_tid = (
                                    additional_page_media_use_term
                                )
                            page_file_base_path = os.path.splitext(page_file_path)[0]
                            additional_page_media_file_path = (
                                page_file_base_path
                                + "."
                                + additional_page_media_extension.strip()
                            )
                            if check_file_exists(
                                config, additional_page_media_file_path
                            ):
                                media_response_status_code = create_media(
                                    config,
                                    additional_page_media_file_path,
                                    None,
                                    node_nid,
                                    fake_csv_record,
                                    media_use_tid=additional_page_media_use_tid,
                                )
                                if (
                                    media_response_status_code
                                    in allowed_media_response_codes
                                ):
                                    if media_response_status_code is False:
                                        print(
                                            f"- ERROR: Media for {additional_page_media_file_path} not created. See log for more information."
                                        )
                                        logging.error(
                                            "Media for %s not created. HTTP response code was %s.",
                                            page_file_base_path
                                            + "."
                                            + additional_page_media_extension,
                                            media_response_status_code,
                                        )
                                        continue
                                    else:
                                        logging.info(
                                            "Media for %s created.",
                                            additional_page_media_file_path,
                                        )
                                        print(
                                            f"+ Media for {additional_page_media_file_path} created."
                                        )
                            else:
                                logging.warning(
                                    f"{additional_page_media_file_path} not found."
                                )

        else:
            print(
                f"Error: Node for page {page_identifier} not created. See log for more information."
            )
            logging.error(
                'Node for page "%s" not created, HTTP response code was %s, response body was %s',
                page_identifier,
                node_response.status_code,
                node_response.text,
            )
            logging.error(
                'JSON request body used in previous POST to "%s" was %s.',
                node_endpoint,
                node_json,
            )

        # Execute node-specific post-create scripts, if any are configured.
        if "node_post_create" in config and len(config["node_post_create"]) > 0:
            for command in config["node_post_create"]:
                post_task_output, post_task_return_code = (
                    execute_entity_post_task_script(
                        command,
                        config["config_file"],
                        node_response.status_code,
                        node_response.text,
                    )
                )
                if post_task_return_code == 0:
                    logging.info(
                        "Post node create script " + command + " executed successfully."
                    )
                else:
                    logging.error(
                        "Post node create script "
                        + command
                        + " failed with exit code "
                        + str(post_task_return_code)
                        + "."
                    )


def get_rollback_csv_filepath(config):
    if "rollback_csv_filename_template" in config:
        config_filename, task_config_ext = os.path.splitext(config["config_file"])
        input_csv_filename, input_csv_ext = os.path.splitext(config["input_csv"])

        rollback_csv_filename_template = string.Template(
            config["rollback_csv_filename_template"]
        )
        try:
            if config["task"] == "create":
                rollback_csv_filename_basename = str(
                    rollback_csv_filename_template.substitute(
                        {
                            "config_filename": config_filename,
                            "input_csv_filename": input_csv_filename,
                            "csv_start_row": str(config["csv_start_row"]),
                            "csv_stop_row": str(config["csv_stop_row"]),
                        }
                    )
                )
            if config["task"] == "create_from_files":
                rollback_csv_filename_basename = str(
                    rollback_csv_filename_template.substitute(
                        {
                            "config_filename": config_filename,
                        }
                    )
                )
        except Exception as e:
            # We need to account for the very common case where the user has included "valid identifier characters"
            # (as defined in https://peps.python.org/pep-0292/) as part of their template. The most common case will
            # likely be underscores separating the template placeholders.
            message = f'One or more parts of the configured rollback csv filename template ({config["rollback_csv_filename_template"]}) need adjusting.'
            logging.error(
                f"{message} A {e.__class__.__name__} exception occured with the error message {e}. Please refer to the Workbench documentation for suggestions."
            )
            sys.exit(
                f"Error: {message} Please refer to your Workbench log and to the Workbench documentation for suggestions."
            )
    else:
        rollback_csv_filename_basename = "rollback"

    if config["timestamp_rollback"] is True or (
        config["recovery_mode_starting_from_node_id"] is not False
        and value_is_numeric(config["recovery_mode_starting_from_node_id"]) is True
    ):
        now_string = EXECUTION_START_TIME.strftime("%Y_%m_%d_%H_%M_%S")

    if config["timestamp_rollback"] is True:
        rollback_csv_filename = f"{rollback_csv_filename_basename}.{now_string}.csv"
    elif (
        config["recovery_mode_starting_from_node_id"] is not False
        and value_is_numeric(config["recovery_mode_starting_from_node_id"]) is True
    ):
        rollback_csv_filename = (
            f"{rollback_csv_filename_basename}.{now_string}.recovery_mode.csv"
        )
    else:
        rollback_csv_filename = f"{rollback_csv_filename_basename}.csv"

    if os.environ.get("ISLANDORA_WORKBENCH_SECONDARY_TASKS") is not None:
        secondary_tasks = json.loads(os.environ["ISLANDORA_WORKBENCH_SECONDARY_TASKS"])
        if os.path.abspath(config["current_config_file_path"]) in secondary_tasks:
            config_file_id = get_config_file_identifier(config)
            rollback_csv_filename = rollback_csv_filename + "." + config_file_id

    if "rollback_csv_file_path" in config and len(config["rollback_csv_file_path"]) > 0:
        if config["timestamp_rollback"] is True:
            rollback_csv_file_path_head, rollback_csv_file_path_tail = os.path.split(
                config["rollback_csv_file_path"]
            )
            rollback_csv_file_basename, rollback_csv_file_ext = os.path.splitext(
                rollback_csv_file_path_tail
            )
            rollback_csv_file_path = os.path.join(
                rollback_csv_file_path_head,
                f"{rollback_csv_file_basename}.{now_string}{rollback_csv_file_ext}",
            )
            return os.path.abspath(rollback_csv_file_path)
        else:
            return os.path.abspath(config["rollback_csv_file_path"])
    else:
        return os.path.abspath(
            os.path.join(
                config["rollback_dir"] or config["input_dir"], rollback_csv_filename
            )
        )


def get_rollback_config_filepath(config):
    if "rollback_config_filename_template" in config:
        config_filename, task_config_ext = os.path.splitext(config["config_file"])
        input_csv_filename, input_csv_ext = os.path.splitext(config["input_csv"])

        rollback_config_filename_template = string.Template(
            config["rollback_config_filename_template"]
        )
        try:
            if config["task"] == "create":
                rollback_config_filename_basename = str(
                    rollback_config_filename_template.substitute(
                        {
                            "config_filename": config_filename,
                            "input_csv_filename": input_csv_filename,
                            "csv_start_row": str(config["csv_start_row"]),
                            "csv_stop_row": str(config["csv_stop_row"]),
                        }
                    )
                )
            if config["task"] == "create_from_files":
                rollback_config_filename_basename = str(
                    rollback_config_filename_template.substitute(
                        {
                            "config_filename": config_filename,
                        }
                    )
                )
        except Exception as e:
            # We need to account for the very common case where the user has included "valid identifier characters"
            # (as defined in https://peps.python.org/pep-0292/) as part of their template. The most common case will
            # likely be underscores separating the template placeholders.
            message = f'One or more parts of the configured rollback configuration filename template ({config["rollback_config_filename_template"]}) need adjusting.'
            logging.error(
                f"{message} A {e.__class__.__name__} exception occured with the error message {e}. Please refer to the Workbench documentation for suggestions."
            )
            sys.exit(
                f"Error: {message} Please refer to your Workbench log and to the Workbench documentation for suggestions."
            )
    else:
        rollback_config_filename_basename = "rollback"

    # Get workbench's current directory, to use as the default directory for the rollback config file.
    # We only override this location if "rollback_config_file_path" is set in the config.
    if "rollback_config_file_path" not in config:
        rb_config_file_dir = sys.path[0]
    else:
        rb_config_file_dir = ""

    if config["timestamp_rollback"] is True or (
        config["recovery_mode_starting_from_node_id"] is not False
        and value_is_numeric(config["recovery_mode_starting_from_node_id"]) is True
    ):
        now_string = EXECUTION_START_TIME.strftime("%Y_%m_%d_%H_%M_%S")

    if config["timestamp_rollback"] is True:
        rollback_config_filepath = os.path.join(
            f"{rb_config_file_dir}",
            f"{rollback_config_filename_basename}.{now_string}.yml",
        )
    elif (
        config["recovery_mode_starting_from_node_id"] is not False
        and value_is_numeric(config["recovery_mode_starting_from_node_id"]) is True
    ):
        rollback_config_filepath = os.path.join(
            f"{rb_config_file_dir}",
            f"{rollback_config_filename_basename}.{now_string}.recovery_mode.yml",
        )
    else:
        rollback_config_filepath = os.path.join(
            f"{rb_config_file_dir}", f"{rollback_config_filename_basename}.yml"
        )

    if (
        "rollback_config_file_path" in config
        and len(config["rollback_config_file_path"]) > 0
    ):
        if config["timestamp_rollback"] is True:
            rollback_config_file_path_head, rollback_config_file_path_tail = (
                os.path.split(config["rollback_config_file_path"])
            )
            rollback_config_file_basename, rollback_config_file_ext = os.path.splitext(
                rollback_config_file_path_tail
            )
            rollback_config_file_path = os.path.join(
                rollback_config_file_path_head,
                f"{rollback_config_file_basename}.{now_string}{rollback_config_file_ext}",
            )
            return os.path.abspath(rollback_config_file_path)
        else:
            rollback_config_filepath = os.path.abspath(
                config["rollback_config_file_path"]
            )

    return rollback_config_filepath


def write_rollback_config(config, path_to_rollback_csv_file):
    rollback_config_filename = get_rollback_config_filepath(config)

    logging.info(f"Writing rollback configuration file to {rollback_config_filename}.")
    rollback_config_file = open(rollback_config_filename, "w")
    rollback_comments = get_rollback_config_comments(config)
    rollback_config_file.write(rollback_comments)

    if config["include_password_in_rollback_config_file"] is True:
        password = config["password"]
    else:
        password = None

    yaml.dump(
        {
            "task": "delete",
            "host": config["host"],
            "username": config["username"],
            "password": password,
            "input_dir": config["input_dir"],
            "standalone_media_url": config["standalone_media_url"],
            "secure_ssl_only": config["secure_ssl_only"],
            "input_csv": path_to_rollback_csv_file,
        },
        rollback_config_file,
    )


def prep_rollback_csv(config, path_to_rollback_csv_file):
    try:
        if os.path.exists(path_to_rollback_csv_file):
            os.remove(path_to_rollback_csv_file)
        rollback_csv_file = open(path_to_rollback_csv_file, "a+")
        if config["rollback_file_include_node_info"] is False:
            rollback_csv_file.write("node_id" + "\n")
        else:
            rollback_csv_file.write(
                f"node_id,{config['id_field']},title,field_member_of,file" + "\n"
            )
        rollback_csv_comments = get_rollback_config_comments(config)
        rollback_csv_file.write(rollback_csv_comments)
        rollback_csv_file.close()
    except Exception as e:
        message = (
            "Workbench was unable save rollback CSV to "
            + path_to_rollback_csv_file
            + "."
        )
        logging.error(message)
        sys.exit("Error: " + message)


def write_rollback_node_id(
    config,
    node_id,
    id,
    node_title,
    node_file_path,
    member_of,
    path_to_rollback_csv_file,
):
    """Appends a row to the CSV file located at path_to_rollback_csv_file."""
    """Parameters
        ----------
        config : dict
            The configuration settings defined by workbench_config.get_config().
        node_id : str
            The node ID to write to the file.
        id : str
            The CSV ID to write to the file. Empty for pages created from directories,
            or for files used in create_from files tasks.
        node_title : str
            The title of the node.
        node_file_path : str
            The relative path to the value of the CSV "file" column, or for page/child
            nodes created from subdirectories, the path to the subdirectory and file.
        member_of : str
            The value of "field_member_of" for the node.
        path_to_rollback_csv_file : string
            The path to the CSV file.
        Returns
        -------
        None
    """
    path_to_rollback_csv_file = get_rollback_csv_filepath(config)
    if config["rollback_file_include_node_info"] is False:
        rollback_csv_file = open(path_to_rollback_csv_file, "a+")
        rollback_csv_file.write(str(node_id) + "\n")
    else:
        rollback_csv_file = open(
            path_to_rollback_csv_file, "a+", newline="", encoding="utf-8"
        )
        rollback_csv_writer = csv.DictWriter(
            rollback_csv_file,
            fieldnames=[
                "node_id",
                config["id_field"],
                "title",
                "field_member_of",
                "file",
            ],
        )
        rollback_csv_writer.writerow(
            {
                "node_id": node_id,
                config["id_field"]: id,
                "title": node_title,
                "field_member_of": member_of,
                "file": node_file_path,
            }
        )

    rollback_csv_file.close()


def get_rollback_config_comments(config):
    comments = list()
    task = config["task"]
    config_file = config["config_file"]
    input_csv = config["input_csv"]
    time_string = now_string = EXECUTION_START_TIME.strftime("%Y:%m:%d %H:%M:%S")

    comments.append(f'# Generated by a "{task}" task started {time_string} using')
    comments.append(f'config file "{config_file}" and input CSV "{input_csv}".')
    if (
        "rollback_file_comments" in config
        and config["rollback_file_comments"] is not None
        and len(config["rollback_file_comments"]) > 0
    ):
        comments.extend(config["rollback_file_comments"])

    return "\n# ".join(comments) + "\n"


def get_csv_from_google_sheet(config):
    url_parts = config["input_csv"].split("/")
    url_parts[6] = "export?gid=" + str(config["google_sheets_gid"]) + "&format=csv"
    csv_url = "/".join(url_parts)
    response = requests.get(url=csv_url, allow_redirects=True)

    if response.status_code == 404:
        message = (
            "Workbench cannot find the Google spreadsheet at "
            + config["input_csv"]
            + ". Please check the URL."
        )
        logging.error(message)
        sys.exit("Error: " + message)

    # Sheets that aren't publicly readable return a 302 and then a 200 with a bunch of HTML for humans to look at.
    if response.content.strip().startswith(b"<!doctype html"):
        message = (
            "The Google spreadsheet at "
            + config["input_csv"]
            + ' is not accessible.\nPlease check its "Share" settings.'
        )
        logging.error(message)
        sys.exit("Error: " + message)

    if os.environ.get("ISLANDORA_WORKBENCH_SECONDARY_TASKS") is not None:
        secondary_tasks = json.loads(os.environ["ISLANDORA_WORKBENCH_SECONDARY_TASKS"])
        config_file_id = get_config_file_identifier(config)
        if os.path.abspath(config["current_config_file_path"]) in secondary_tasks:
            config_file_id = get_config_file_identifier(config)
            exported_csv_path = os.path.join(
                config["temp_dir"],
                config["google_sheets_csv_filename"] + "." + config_file_id,
            )
        else:
            exported_csv_path = os.path.join(
                config["temp_dir"], config["google_sheets_csv_filename"]
            )
    else:
        exported_csv_path = os.path.join(
            config["temp_dir"], config["google_sheets_csv_filename"]
        )

    open(exported_csv_path, "wb+").write(response.content)


def get_csv_from_excel(config):
    """Read the input Excel 2010 (or later) file and write it out as CSV."""
    if os.path.isabs(config["input_csv"]):
        input_excel_path = config["input_csv"]
    else:
        input_excel_path = os.path.join(config["input_dir"], config["input_csv"])

    if not os.path.exists(input_excel_path):
        message = "Error: Excel file " + input_excel_path + " not found."
        logging.error(message)
        sys.exit(message)

    excel_file_path = config["input_csv"]
    wb = openpyxl.load_workbook(filename=input_excel_path)
    ws = wb[config["excel_worksheet"]]

    headers = []
    header_row = ws[1]
    ws.delete_rows(0)
    for header_cell in header_row:
        headers.append(header_cell.value)

    records = []
    for row in ws:
        record = {}
        for x in range(len(header_row)):
            if headers[x] is not None and row[x] is not None:
                record[headers[x]] = row[x].value
        records.append(record)

    if os.environ.get("ISLANDORA_WORKBENCH_SECONDARY_TASKS") is not None:
        secondary_tasks = json.loads(os.environ["ISLANDORA_WORKBENCH_SECONDARY_TASKS"])
        config_file_id = get_config_file_identifier(config)
        if os.path.abspath(config["current_config_file_path"]) in secondary_tasks:
            config_file_id = get_config_file_identifier(config)
            exported_csv_path = os.path.join(
                config["temp_dir"], config["excel_csv_filename"] + "." + config_file_id
            )
        else:
            exported_csv_path = os.path.join(
                config["temp_dir"], config["excel_csv_filename"]
            )
    else:
        exported_csv_path = os.path.join(
            config["temp_dir"], config["excel_csv_filename"]
        )

    csv_writer_file_handle = open(exported_csv_path, "w+", newline="", encoding="utf-8")
    csv_writer = csv.DictWriter(csv_writer_file_handle, fieldnames=headers)
    csv_writer.writeheader()
    for record in records:
        if (config["id_field"] in record or "node_id" in record) and record[
            config["id_field"]
        ] is not None:
            csv_writer.writerow(record)
    csv_writer_file_handle.close()


def get_extracted_csv_file_path(config):
    """For secondary tasks were input is either a Google Sheet or an Excel file,
    get the path to the extracted CSV.
    """
    """Parameters
        ----------
        config : dict
            The configuration settings defined by workbench_config.get_config().
        Returns
        -------
        string|bool
            A file path with the current config file's unique ID appended to it.
            False if config['input_csv'] is not a Google Sheet or Excel file.
    """
    if config["input_csv"].startswith("http"):
        exported_csv_filename = config["google_sheets_csv_filename"]
    elif config["input_csv"].endswith("xlsx"):
        exported_csv_filename = config["excel_csv_filename"]
    else:
        return False

    if os.environ.get("ISLANDORA_WORKBENCH_SECONDARY_TASKS") is not None:
        secondary_tasks = json.loads(os.environ["ISLANDORA_WORKBENCH_SECONDARY_TASKS"])
        if os.path.abspath(config["current_config_file_path"]) in secondary_tasks:
            config_file_id = get_config_file_identifier(config)
            exported_csv_filename = exported_csv_filename + "." + config_file_id

    return os.path.join(config["temp_dir"], exported_csv_filename)


def get_extension_from_mimetype(config, mimetype):
    """For a given MIME type, return the corresponding file extension. mimetypes.add_type()
    is not working, e.g. mimetypes.add_type('image/jpeg', '.jpg'). Maybe related to
     https://bugs.python.org/issue4963? In the meantime, provide our own MIMETYPE to extension
     mapping for common types, then let mimetypes guess at others.
    """
    """Parameters
        ----------
        config : dict
            The configuration settings defined by workbench_config.get_config().
        mimetype: string
            The MIME type to get the corresponding extension for.
        Returns
        -------
        string|bool
            The extension, with a leading '.', or None if no extension can be determined.
    """
    map = {
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg",
        "image/jp2": ".jp2",
        "image/png": ".png",
        "image/tif": ".tif",
        "image/tiff": ".tif",
        "audio/mpeg": ".mp3",
        "text/plain": ".txt",
        "application/xml": ".xml",
        "application/octet-stream": ".bin",
    }
    if "mimetype_extensions" in config and len(config["mimetype_extensions"]) > 0:
        for mtype, ext in config["mimetype_extensions"].items():
            map[mtype] = ext

    if mimetype in map:
        return map[mimetype]
    else:
        return mimetypes.guess_extension(mimetype)

    return None


def get_mimetype_from_extension(config, file_path, lazy=False):
    """For a given file path, return the corresponding MIME type."""
    """Parameters
        ----------
        config : dict
            The configuration settings defined by workbench_config.get_config().
            The 'extensions_to_mimetypes' setting allows assignment of MIME types
            in config.
        file_path: string
            The path to the local file to get the MIME type for.
        lazy: bool
            If True, and no entry for a given extension exists in the map, return
            "application/octet-stream" as a default if non MIME type can be determined.
            If False, let Python's mimetypes library guess.
        Returns
        -------
        string|None
            The MIME type, or None if the MIME type can be determined.
    """
    if os.path.isabs(file_path) is True:
        filepath = file_path
    else:
        filepath = os.path.join(config["input_dir"], file_path)

    if os.path.exists(filepath):
        root, ext = os.path.splitext(filepath)
        ext = ext.lstrip(".").lower()
    else:
        logging.error(
            f"Attempt to get MIME type for file {filepath} failed because file does not exist."
        )
        return None

    # A MIME type used in Islandora but not recognized by Python's mimetypes library.
    map = {"hocr": "text/vnd.hocr+html"}

    # Modify the map as per config.
    if (
        "extensions_to_mimetypes" in config
        and len(config["extensions_to_mimetypes"]) > 0
    ):
        for extension, mtype in config["extensions_to_mimetypes"].items():
            extension = extension.lstrip(".").lower()
            map[extension] = mtype

    if ext in map:
        return map[ext]
    else:
        if lazy is False:
            return mimetypes.guess_type(filepath)[0]
        else:
            return "application/octet-stream"

    return None


def get_deduped_file_path(path):
    """Given a file path, return a version of it that contains a version of
    the same name with an incremented integer inserted before the extension.
    """
    """Parameters
        ----------
        path : string
            The file path we want to dedupe.
        Returns
        -------
        string
            The deduped version of 'path', i.e., the original path with an
            underscore and an incremented digit inserted before the extension.
    """
    [base_path, extension] = os.path.splitext(path)

    numbers = re.findall(r"_\d+$", base_path)
    if len(numbers) == 0:
        incremented_path = base_path + "_1" + extension
    else:
        number = int(numbers[0].lstrip("_")) + 1
        base_path_parts = base_path.split("_")
        del base_path_parts[-1]
        incremented_path = "_".join(base_path_parts) + "_" + str(number) + extension

    return incremented_path


def check_file_exists(config, filename):
    """Cconfirms file exists and is a file (not a directory).
    For remote/downloaded files, checks for a 200 response from a HEAD request.

    Does not check whether filename value is blank.
    """
    """Parameters
        ----------
        config : dict
            The configuration settings defined by workbench_config.get_config().
        filename: string
            The filename or path.
        Returns
        -------
        boolean
            True if the file exists, false if not.
    """
    # If file is supposed to already on the server we'll be notified later if it is missing.
    if filename.startswith(config["file_systems"]):
        return True

    # It's a remote file.
    if filename.startswith("http"):
        try:
            headers = {"User-Agent": config["user_agent"]}

            head_response = requests.head(
                filename,
                allow_redirects=True,
                verify=config["secure_ssl_only"],
                headers=headers,
            )
            if head_response.status_code == 200:
                return True
            else:
                return False
        except requests.exceptions.Timeout as err_timeout:
            message = (
                "Workbench timed out trying to reach "
                + filename
                + ". Details in next log entry."
            )
            logging.error(message)
            logging.error(err_timeout)
            return False
        except requests.exceptions.ConnectionError as error_connection:
            message = (
                "Workbench cannot connect to "
                + filename
                + ". Details in next log entry."
            )
            logging.error(message)
            logging.error(error_connection)
            return False
    # It's a local file.
    else:
        if os.path.isabs(filename):
            file_path = filename
        else:
            file_path = os.path.join(config["input_dir"], filename)

        if os.path.isfile(file_path):
            return True
        else:
            return False

    # Fall back to False if existence of file can't be determined.
    logging.warning(
        f'Cannot determine if file "{filename}" exists, assuming it does not.'
    )
    return False


def get_preprocessed_file_path(
    config, file_fieldname, node_csv_row, node_id=None, make_dir=True
):
    """For remote/downloaded files (other than from providers defined in config['oembed_providers]),
    generates the path to the local temporary copy and returns that path. For local files or oEmbed URLs,
    just returns the value of node_csv_row['file'].
    """
    """Parameters
        ----------
        config : dict
            The configuration settings defined by workbench_config.get_config().
        file_fieldname: string
            The name of the CSV column containing the filename.
        node_csv_row : OrderedDict
            The CSV row for the current item.
        node_id: string
            The node ID of the node being processed.
        make_dir: bool
            Whether or not to create a directory for the node's files.
        Returns
        -------
        string
            The path (absolute or relative) to the file.
    """
    file_path_from_csv = node_csv_row[file_fieldname].strip()
    if config["task"] == "add_media":
        config["id_field"] = "node_id"

    # Test whether file_path_from_csv is from one of the oEmbed providers
    # and if so, return it here.
    for oembed_provider in config["oembed_providers"]:
        for provider_url, mtype in oembed_provider.items():
            if file_path_from_csv.startswith(provider_url):
                return file_path_from_csv

    # It's a remote file.
    if file_path_from_csv.startswith("http"):
        if config["task"] == "add_media":
            subdir = os.path.join(
                config["temp_dir"],
                re.sub("[^A-Za-z0-9]+", "_", str(node_csv_row["node_id"])),
            )
        elif config["task"] == "update_media":
            subdir = os.path.join(
                config["temp_dir"],
                re.sub("[^A-Za-z0-9]+", "_", node_csv_row["media_id"]),
            )
        else:
            subdir = os.path.join(
                config["temp_dir"],
                re.sub("[^A-Za-z0-9]+", "_", node_csv_row[config["id_field"]]),
            )
        if make_dir:
            Path(subdir).mkdir(parents=True, exist_ok=True)

        if "check" in config.keys() and config["check"] is True:
            try:
                os.rmdir(subdir)
            except Exception as e:
                # This can happen if subdirectories from previous runs of Workbench exist.
                message = f'Subdirectory "{subdir}" could not be deleted. See log for more info.'
                logging.warning(f'Subdirectory "{subdir}" could not be deleted: {e}.')

        remote_extension_with_dot = get_remote_file_extension(
            config, file_path_from_csv
        )
        remote_filename_parts = os.path.splitext(file_path_from_csv)

        if (
            "use_node_title_for_remote_filename" in config
            and config["use_node_title_for_remote_filename"] is True
        ):
            # CSVs for add_media tasks don't contain 'title', so we need to get it.
            if config["task"] == "add_media":
                node_csv_row["title"] = get_node_title_from_nid(
                    config, node_csv_row["node_id"]
                )
                if node_csv_row["title"] is False:
                    message = (
                        "Cannot access node "
                        + str(node_id)
                        + ", so cannot get its title for use in media filename. Using filename instead."
                    )
                    logging.warning(message)
                    node_csv_row["title"] = os.path.basename(
                        node_csv_row[file_fieldname].strip()
                    )

            filename = re.sub("[^A-Za-z0-9]+", "_", node_csv_row["title"])
            filename = filename.strip("_")
            downloaded_file_path = os.path.join(
                subdir, filename + remote_extension_with_dot
            )
        elif (
            "use_nid_in_remote_filename" in config
            and config["use_nid_in_remote_filename"] is True
        ):
            filename = f"{node_id}{remote_extension_with_dot}"
            downloaded_file_path = os.path.join(subdir, filename)
        elif (
            config["field_for_remote_filename"] is not False
            and config["field_for_remote_filename"] in node_csv_row
            and len(node_csv_row[config["field_for_remote_filename"]]) > 0
        ):
            field_for_remote_filename_string = node_csv_row[
                config["field_for_remote_filename"]
            ][:255]
            sanitized_filename = re.sub(
                "[^0-9a-zA-Z]+", "_", field_for_remote_filename_string
            )
            downloaded_file_path = os.path.join(
                subdir, sanitized_filename.strip("_") + remote_extension_with_dot
            )
        else:
            # For files from Islandora Legacy ending in /view, we use the CSV ID as the filename.
            if len(remote_filename_parts[1]) == 0:
                filename = node_csv_row[config["id_field"]] + remote_extension_with_dot
            else:
                # For other files, we use the last part of the path preceding the file extension.
                url_path_parts = remote_filename_parts[0].split("/")
                filename = url_path_parts[-1] + remote_extension_with_dot
            downloaded_file_path = os.path.join(subdir, filename)

        # Check to see if a file with this path already exists; if so, insert an
        # incremented digit into the file path before the extension.
        if os.path.exists(downloaded_file_path):
            downloaded_file_path = get_deduped_file_path(downloaded_file_path)

        return downloaded_file_path
    # It's a local file.
    else:
        if os.path.isabs(file_path_from_csv):
            file_path = file_path_from_csv
        else:
            file_path = os.path.join(config["input_dir"], file_path_from_csv)
        return file_path


def get_node_media_ids(config, node_id, media_use_tids=None):
    """Gets a list of media IDs for a node."""
    """Parameters
        ----------
        config : dict
            The configuration settings defined by workbench_config.get_config().
        node_id : string
            The ID of the node to delete media from.
        media_use_tids : list
            Term IDs from the Islandora Media Use vocabulary. If present, media
            with one of these tids will be added to the returned list of media IDs.
            If empty, all media will be included in the returned list of media IDs.
        Returns
        -------
        list
            List of media IDs.
    """
    if media_use_tids is None:
        media_use_tids = []

    media_id_list = list()
    url = f"{config['host']}/node/{node_id}/media?_format=json"
    response = issue_request(config, "GET", url)
    if response.status_code == 200:
        body = json.loads(response.text)
        for media in body:
            if len(media_use_tids) == 0:
                media_id_list.append(media["mid"][0]["value"])
            else:
                for media_use_tid_json in media["field_media_use"]:
                    if media_use_tid_json["target_id"] in media_use_tids:
                        media_id_list.append(media["mid"][0]["value"])
        return media_id_list
    else:
        message = f"Attempt to get media for node ID {node_id} returned a {response.status_code} status code."
        print("Error: " + message)
        logging.warning(message)
        return False


def download_remote_file(config, url, file_fieldname, node_csv_row, node_id):
    headers = {"User-Agent": config["user_agent"]}

    sections = urllib.parse.urlparse(url)
    try:
        if config["secure_ssl_only"] is False:
            requests.packages.urllib3.disable_warnings()
        # Do not cache the responses for downloaded files in requests_cache
        with requests_cache.disabled():
            response = requests.get(
                url,
                allow_redirects=True,
                stream=True,
                verify=config["secure_ssl_only"],
                headers=headers,
            )
    except requests.exceptions.Timeout as err_timeout:
        message = (
            "Workbench timed out trying to reach "
            + sections.netloc
            + " while connecting to "
            + url
            + ". Please verify that URL and check your network connection."
        )
        logging.error(message)
        logging.error(err_timeout)
        print("Error: " + message)
        return False
    except requests.exceptions.ConnectionError as error_connection:
        message = (
            "Workbench cannot connect to "
            + sections.netloc
            + " while connecting to "
            + url
            + ". Please verify that URL and check your network connection."
        )
        logging.error(message)
        logging.error(error_connection)
        print("Error: " + message)
        return False

    downloaded_file_path = get_preprocessed_file_path(
        config, file_fieldname, node_csv_row, node_id
    )
    with open(downloaded_file_path, "wb+") as output_file:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                output_file.write(chunk)

    return downloaded_file_path


def get_remote_file_extension(config, file_url):
    """For remote files that have no extension, such as http://acme.com/islandora/object/some:pid/datastream/OBJ/download,
    assign an extension, with a leading dot. If the file has an extension, return it, also with dot.
    """
    # If the file has an extension, just return it.
    extension = os.path.splitext(file_url)[1]
    extension = extension.lstrip(".").lower()
    if len(extension) > 0:
        return "." + extension

    # If it doesn't have an extension, assign one based on its MIME type. Request's docs at
    # https://requests.readthedocs.io/en/latest/user/quickstart/#response-headers say that
    # headers can be accessed regardless of capitalization, but that's not the case (ha).
    try:
        head_response = requests.head(
            file_url, allow_redirects=True, verify=config["secure_ssl_only"]
        )
        mimetype = head_response.headers["Content-Type"]
        if mimetype is None:
            mimetype = head_response.headers["content-type"]
            if mimetype is None:
                message = f'Cannot reliably get MIME type of file "{file_url}" from remote server.'
                logging.error(message)
                sys.exit("Error: " + message)

        # In case servers return stuff beside the MIME type in Content-Type header.
        # Assumes they use ; to separate stuff and that what we're looking for is
        # in the first position.
        if ";" in mimetype:
            mimetype_parts = mimetype.split(";")
            mimetype = mimetype_parts[0].strip()
    except KeyError:
        mimetype = "application/octet-stream"

    extension_with_dot = get_extension_from_mimetype(config, mimetype)

    if extension_with_dot is None:
        message = f'Workbench does not recognize the MIME type "{mimetype}" received from the remote server for the file "{file_url}". '
        message = (
            message
            + 'You can assign an extension to this MIME type using the "mimetype_extensions" config setting.'
        )
        logging.error(message)
        sys.exit("Error: " + message)

    return extension_with_dot


def get_csv_id_to_node_id_map_allowed_hosts_sql(config):
    """Derive a query snippet for SQL SELECT queries from values in the "csv_id_to_node_id_map_allowed_hosts" config
    setting. This snippet is inserted into queries against the CSV ID to node ID map to limit results to rows that
    have the one of the hosts named in "csv_id_to_node_id_map_allowed_hosts" in their "host" column. This snippet is
    intended to be located in the middle of the query, specifically, it ends in "and".
    """
    """Parameters
        ----------
        config : dict
            The configuration settings defined by workbench_config.get_config().
        Returns
        -------
        The SQL query string, e.g. " host is null or host in ("https://localhost","https://localhost.dev") and "
        Note that this is a literal string, and does not contain any parameterized SQL query placeholders.
        If "csv_id_to_node_id_map_allowed_hosts" is an empty list, this snippet is empty, which in effect
        does not limit the SQL query against the CSV ID to node ID map to specific "host" field values.
    """
    allowed_hosts = copy.copy(config["csv_id_to_node_id_map_allowed_hosts"])
    if len(config["csv_id_to_node_id_map_allowed_hosts"]) > 0:
        # "" represents an empty host value.
        if "" in config["csv_id_to_node_id_map_allowed_hosts"]:
            allowed_hosts.remove("")
            empty_host_query_string = "host is null or "
        else:
            empty_host_query_string = ""
        hosts_in_parameter = ",".join(f'"{h}"' for h in allowed_hosts)
        sql_snippet = f" {empty_host_query_string} host in ({hosts_in_parameter}) and "
    else:
        sql_snippet = ""

    return sql_snippet


def get_field_viewer_override_from_condition(config, row):
    """Derive value for the field_viewer_override CSV column based on conditions defined in configuration."""
    """Parameters
        ----------
        config : dict
            The configuration settings defined by workbench_config.get_config().
        row: OrderedDict
            A CSV row. For pages/children created from subdirectories, this
            is a version of the parent's row so we can get $csv_value values for non-required fields.
        Returns
        -------
        The term ID, term name, or ther URI for the term from the Islandora Display vocabulary (whatever was
        used in the configuration setting).
    """
    # If the field_viewer_override column is populated, don't change it.
    if "field_viewer_override" in row and len(row["field_viewer_override"].strip()) > 0:
        return row["field_viewer_override"]

    return_value = ""
    # Get the field_viewer_override value from the row's field_model value first.
    if (
        "field_viewer_override_models" in config
        and config["field_viewer_override_models"] is not None
        and len(config["field_viewer_override_models"]) > 0
    ):
        for override in config["field_viewer_override_models"]:
            for islandora_display_term_id, conditions in override.items():
                conditions = [x.lower() for x in conditions]
                if row["field_model"].lower() in conditions:
                    # If multiple matches, last match pertains.
                    return_value = islandora_display_term_id

    # Then get field_viewer_override value from the extension in the row's "file" field, replacing the earlier assigned term ID/name/URI if necessary.
    if (
        "field_viewer_override_extensions" in config
        and config["field_viewer_override_extensions"] is not None
        and len(config["field_viewer_override_extensions"]) > 0
    ):
        if len(row["file"].strip()) == 0:
            return row["field_viewer_override"]

        if row["file"].strip().startswith("http"):
            extension = get_remote_file_extension(config, row["file"])
            extension = extension.lstrip(".").lower()
        else:
            _filename, extension = os.path.splitext(row["file"])
            extension = extension.lstrip(".").lower()

        for override in config["field_viewer_override_extensions"]:
            for islandora_display_term_id, conditions in override.items():
                conditions = [x.lower() for x in conditions]
                conditions = [x.lstrip(".") for x in conditions]
                if extension in conditions:
                    # If multiple matches, last match pertains.
                    return_value = islandora_display_term_id

    return return_value


def get_media_list(config, node_id, media_list=None):
    """Retrieve media list for a node if not provided."""
    if media_list is not None:
        return media_list
    media_list_url = f"{config['host']}/node/{node_id}/media?_format=json"
    response = issue_request(config, "GET", media_list_url)
    if response.status_code != 200:
        logging.error(
            f"Media list request failed for node {node_id}: {response.status_code}"
        )
        return None
    try:
        return json.loads(response.text)
    except json.decoder.JSONDecodeError as e:
        logging.error(f"Media query for node {node_id} failed: {e}")
        return None


def resolve_media_use_term_id(config, media_use_term_id, node_id):
    """Resolve media use term ID from URI or configuration."""
    if media_use_term_id is None:
        media_use_term_id = config.get("export_file_media_use_term_id")
        if media_use_term_id is None:
            logging.error(
                f"No media use term ID provided or configured for node {node_id}."
            )
            return None
    if isinstance(media_use_term_id, str) and media_use_term_id.startswith("http"):
        term_id = get_term_id_from_uri(config, media_use_term_id)
        if term_id is None:
            logging.error(
                f"Failed to convert URI {media_use_term_id} to term ID for node {node_id}."
            )
            return None
        return term_id
    return media_use_term_id


def find_file_url_in_media(config, media_list, media_use_term_id, node_id):
    """Find the file URL in media entries matching the use term."""
    for media in media_list:
        for file_field in file_fields:
            if file_field in media:
                media_use_terms = media.get("field_media_use", [])
                media_use_ids = [term.get("target_id") for term in media_use_terms]
                if media_use_term_id in media_use_ids:
                    file_info = media[file_field]
                    if len(file_info) > 0:
                        file_url = file_info[0].get("url")
                        if file_url:
                            return file_url
    logging.debug(
        f"No valid media found for node {node_id} with use term {media_use_term_id}"
    )
    return None


def get_media_file_url(config, node_id, media_use_term_id=None, media_list=None):
    """Retrieve and validate the URL of a media file from Drupal."""
    media_list = get_media_list(config, node_id, media_list)
    if media_list is None:
        return False

    resolved_term_id = resolve_media_use_term_id(config, media_use_term_id, node_id)
    if resolved_term_id is None:
        return False

    file_url = find_file_url_in_media(config, media_list, resolved_term_id, node_id)
    if not file_url:
        return False

    try:
        head_response = requests.head(
            file_url,
            allow_redirects=True,
            verify=config["secure_ssl_only"],
            timeout=10,
        )
        if head_response.status_code != 200:
            logging.error(
                f"URL validation failed for node {node_id}: {file_url} (HTTP {head_response.status_code})"
            )
            return False
    except Exception as e:
        logging.error(f"HEAD request failed for {file_url}: {str(e)}")
        return False

    logging.info(f"URL validated for node {node_id}: {file_url}")
    return file_url


def download_file_from_drupal(config, node_id, media_use_term_id=None, media_list=None):
    """Download a media file from Drupal."""
    if config.get("export_file_directory") is None:
        logging.error("export_file_directory is not configured")
        return False

    if not os.path.exists(config["export_file_directory"]):
        try:
            os.mkdir(config["export_file_directory"])
        except Exception as e:
            message = f'Path "export_file_directory" ("{config["export_file_directory"]}") is not writable: {str(e)}'
            logging.error(message)
            sys.exit("Error: " + message + " See log for more detail.")
    else:
        logging.info(
            f'Path "export_file_directory" ("{config["export_file_directory"]}") already exists.'
        )

    media_list = get_media_list(config, node_id, media_list)
    if media_list is None:
        return False

    resolved_term_id = resolve_media_use_term_id(config, media_use_term_id, node_id)
    if resolved_term_id is None:
        return False

    file_url = find_file_url_in_media(config, media_list, resolved_term_id, node_id)
    if not file_url:
        return False

    url_filename = os.path.basename(file_url)
    downloaded_file_path = os.path.join(config["export_file_directory"], url_filename)
    if os.path.exists(downloaded_file_path):
        downloaded_file_path = get_deduped_file_path(downloaded_file_path)

    try:
        with open(downloaded_file_path, "wb+") as f:
            file_download_response = requests.get(
                file_url,
                allow_redirects=True,
                verify=config["secure_ssl_only"],
            )
            if file_download_response.status_code == 200:
                f.write(file_download_response.content)
                filename_for_logging = os.path.basename(downloaded_file_path)
                logging.info(
                    f'File "{filename_for_logging}" downloaded for node {node_id}.'
                )
                return (
                    downloaded_file_path
                    if os.path.isabs(config["export_file_directory"])
                    else filename_for_logging
                )
            else:
                logging.error(
                    f"File download failed for node {node_id}: {file_url} (HTTP {file_download_response.status_code})"
                )
                return False
    except Exception as e:
        logging.error(f"File download failed for node {node_id}: {str(e)}")
        return False


def get_file_hash_from_drupal(config, file_uuid, algorithm):
    """Query the Integration module's hash controller at '/islandora_workbench_integration/file_hash'
    to get the hash of the file identified by file_uuid.
    """
    """Parameters
        ----------
        config : dict
            The configuration settings defined by workbench_config.get_config().
        file_uuid : string
            The file's UUID.
        algorithm : string
            One of 'md5', 'sha1', or 'sha256'
        Returns
        -------
        string
            The requested hash.
    """
    url = (
        config["host"]
        + "/islandora_workbench_integration/file_hash?file_uuid="
        + file_uuid
        + "&algorithm="
        + algorithm
    )
    response = issue_request(config, "GET", url)
    if response.status_code == 200:
        response_body = json.loads(response.text)
        return response_body[0]["checksum"]
    else:
        logging.warning(
            "Request to get %s hash for file %s returned a %s status code",
            algorithm,
            file_uuid,
            response.status_code,
        )
        return False


def get_file_hash_from_local(config, file_path, algorithm):
    """Get the file's hash/checksum."""
    """Parameters
        ----------
        config : dict
            The configuration settings defined by workbench_config.get_config().
        file_path : string
            The file's path.
        algorithm : string
            One of 'md5', 'sha1', or 'sha256'
        Returns
        -------
        string
            The requested hash.
    """
    if algorithm == "md5":
        hash_object = hashlib.md5()
    if algorithm == "sha1":
        hash_object = hashlib.sha1()
    if algorithm == "sha256":
        hash_object = hashlib.sha256()

    with open(file_path, "rb") as file:
        while True:
            chunk = file.read(hash_object.block_size)
            if not chunk:
                break
            hash_object.update(chunk)

    return hash_object.hexdigest()


def create_temp_dir(config):
    if os.path.exists(config["temp_dir"]):
        temp_dir_exists_message = "already exists"
        make_temp_dir = False
    else:
        temp_dir_exists_message = "does not exist, will create it"
        make_temp_dir = True

    if config["temp_dir"] == config["input_dir"]:
        logging.info(
            f"Using directory defined in the 'input_dir' config setting ({config['input_dir']}) as the temporary directory ({temp_dir_exists_message})."
        )
    else:
        logging.info(
            f"Using directory defined in the 'temp_dir' config setting ({config['temp_dir']}) as the temporary directory ({temp_dir_exists_message})."
        )

    if make_temp_dir is True:
        Path(config["temp_dir"]).mkdir(exist_ok=True)


def check_csv_file_exists(config, csv_file_target, file_path=None):
    """Confirms a CSV file exists."""
    """Parameters
        ----------
        config : dict
            The configuration settings defined by workbench_config.get_config().
        csv_file_target: string
            Either 'node_fields' or 'taxonomy_fields'.
        file_path: string
            The path to the file to check (applies only to vocabulary CSVs).
        Returns
        -------
        string
            The absolute file path to the CSV file.
    """
    if csv_file_target == "node_fields":
        if os.path.isabs(config["input_csv"]):
            input_csv = config["input_csv"]
        # For Google Sheets, the "extraction" is fired over in workbench.
        elif config["input_csv"].startswith("http"):
            input_csv = get_extracted_csv_file_path(config)
            message = (
                "Extracting CSV data from "
                + config["input_csv"]
                + " (worksheet gid "
                + str(config["google_sheets_gid"])
                + ") to "
                + input_csv
                + "."
            )
            print(message)
            logging.info(message)
        elif config["input_csv"].endswith("xlsx"):
            input_csv = get_extracted_csv_file_path(config)
            message = (
                "Extracting CSV data from "
                + config["input_csv"]
                + " to "
                + input_csv
                + "."
            )
            print(message)
            logging.info(message)
        else:
            input_csv = os.path.join(config["input_dir"], config["input_csv"])

        if os.path.exists(input_csv):
            message = "OK, CSV file " + input_csv + " found."
            print(message)
            logging.info(message)
            return input_csv
        else:
            message = "CSV file " + input_csv + " not found."
            logging.error(message)
            sys.exit("Error: " + message)
    if csv_file_target == "taxonomy_fields":
        # For Google Sheets and Excel, the "extraction" is fired in workbench.
        if os.path.isabs(file_path):
            input_csv = file_path
        else:
            input_csv = os.path.join(config["input_dir"], file_path)

        if os.path.exists(input_csv):
            message = "OK, vocabulary CSV file " + input_csv + " found."
            print(message)
            logging.info(message)
            return input_csv
        else:
            message = "Vocabulary CSV file " + input_csv + " not found."
            logging.error(message)
            sys.exit("Error: " + message)


def get_csv_template(config, args):
    field_definitions = get_field_definitions(config, "node")

    field_labels = collections.OrderedDict()
    field_labels["REMOVE THIS COLUMN (KEEP THIS ROW)"] = "LABEL (REMOVE THIS ROW)"
    for field_name in field_definitions:
        if field_definitions[field_name]["label"] != "":
            field_labels[field_name] = field_definitions[field_name]["label"]
        else:
            field_labels[field_name] = ""

    required = collections.OrderedDict()
    required["REMOVE THIS COLUMN (KEEP THIS ROW)"] = (
        "REQUIRED IN CREATE TASKS (REMOVE THIS ROW)"
    )
    for field_name in field_definitions:
        if field_definitions[field_name]["required"] != "":
            if field_definitions[field_name]["required"] is True:
                required[field_name] = "Yes"
            else:
                required[field_name] = "No"
    required["title"] = "Yes"
    required["uid"] = "No"
    required["langcode"] = "No"
    required["created"] = "No"
    required[config["id_field"]] = "Yes"
    if config["nodes_only"] is True:
        required["file"] = "Yes"
    else:
        required["file"] = "No"

    mapping = dict()
    mapping["string"] = "Free text"
    mapping["string_long"] = "Free text"
    mapping["text"] = "Free text"
    mapping["text_long"] = "Free text"
    mapping["geolocation"] = "+49.16,-123.93"
    mapping["entity_reference"] = "100 [or term name or http://foo.com/someuri]"
    mapping["edtf"] = "2020-10-28"
    mapping["typed_relation"] = "relators:art:30"
    mapping["integer"] = 100

    sample_data = collections.OrderedDict()
    sample_data["REMOVE THIS COLUMN (KEEP THIS ROW)"] = "SAMPLE DATA (REMOVE THIS ROW)"
    sample_data[config["id_field"]] = "0001"
    sample_data["file"] = "myimage.jpg"
    sample_data["uid"] = "21"
    sample_data["langcode"] = "fr"
    sample_data["created"] = "2020-11-15T23:49:22+00:00"
    sample_data["title"] = "Free text"

    for field_name in field_definitions:
        if field_definitions[field_name]["field_type"] in mapping:
            sample_data[field_name] = mapping[
                field_definitions[field_name]["field_type"]
            ]
        else:
            sample_data[field_name] = ""

    csv_file_path = os.path.join(
        config["input_dir"], config["input_csv"] + ".csv_file_template"
    )
    csv_file = open(csv_file_path, "a+", encoding="utf-8")
    writer = csv.DictWriter(
        csv_file, fieldnames=sample_data.keys(), lineterminator="\n"
    )
    writer.writeheader()
    # We want the labels and required rows to appear as the second and third rows so
    # add them before we add the sample data.
    writer.writerow(field_labels)
    writer.writerow(required)
    writer.writerow(sample_data)

    cardinality = collections.OrderedDict()
    cardinality["REMOVE THIS COLUMN (KEEP THIS ROW)"] = (
        "NUMBER OF VALUES ALLOWED (REMOVE THIS ROW)"
    )
    cardinality[config["id_field"]] = "1"
    cardinality["file"] = "1"
    cardinality["uid"] = "1"
    cardinality["langcode"] = "1"
    cardinality["created"] = "1"
    cardinality["title"] = "1"
    for field_name in field_definitions:
        if field_definitions[field_name]["cardinality"] == -1:
            cardinality[field_name] = "unlimited"
        else:
            cardinality[field_name] = field_definitions[field_name]["cardinality"]
    writer.writerow(cardinality)

    docs = dict()
    docs["string"] = "Single-valued fields"
    docs["string_long"] = "Single-valued fields"
    docs["text"] = "Single-valued fields"
    docs["text_long"] = "Single-valued fields"
    docs["geolocation"] = "Geolocation fields"
    docs["entity_reference"] = "Taxonomy reference fields"
    docs["edtf"] = "EDTF fields"
    docs["typed_relation"] = "Typed Relation fields"
    docs["integer"] = "Single-valued fields"

    docs_tips = collections.OrderedDict()
    docs_tips["REMOVE THIS COLUMN (KEEP THIS ROW)"] = (
        "SECTION IN DOCUMENTATION (REMOVE THIS ROW)"
    )
    docs_tips[config["id_field"]] = "Required fields"
    docs_tips["file"] = "Required fields"
    docs_tips["uid"] = "Base fields"
    docs_tips["langcode"] = "Base fields"
    docs_tips["created"] = "Base fields"
    docs_tips["title"] = "Base fields"
    for field_name in field_definitions:
        if field_definitions[field_name]["field_type"] in docs:
            doc_reference = docs[field_definitions[field_name]["field_type"]]
            docs_tips[field_name] = doc_reference
        else:
            docs_tips[field_name] = ""
    docs_tips["field_member_of"] = ""
    writer.writerow(docs_tips)

    csv_file.close()
    print("CSV template saved at " + csv_file_path + ".")
    sys.exit()


def get_page_title_from_template(config, parent_title, weight):
    """Generates a page title from a simple template."""
    """Parameters
        ----------
        config : dict
            The configuration settings defined by workbench_config.get_config().
        parent_title : string
            The parent node's title.
        weight: string
            The weight value for the given page.
        Returns
        -------
        string
            The output of the template.
    """
    page_title_template = string.Template(config["page_title_template"])
    page_title = str(
        page_title_template.substitute({"parent_title": parent_title, "weight": weight})
    )
    return page_title


def apply_csv_value_templates(config, template_config_setting, row):
    """Applies templates to values in a CSV row. Template variables available are: $csv_value, $file,
    $filename_without_extension, $weight, $random_alphanumeric_string, $random_number_string, and
    $uuid_string.
    """
    """Parameters
        ----------
        config : dict
            The configuration settings defined by workbench_config.get_config().
        template_config_setting: str
            The config setting to get the templates from. One of 'csv_value_templates' or
            'csv_value_templates_for_paged_content'.
        row: OrderedDict
            A CSV row to apply the template(s) to. For pages/children created from subdirectories, this
            is a version of the parent's row so we can get $csv_value values for non-required fields.
        Returns
        -------
        dict
            The row with CSV value templates applied.
    """
    templates = dict()
    for template in config[template_config_setting]:
        for field_name, value_template in template.items():
            templates[field_name] = value_template

    for field in row:
        if field in templates:
            incoming_subvalues = row[field].split(config["subdelimiter"])
            outgoing_subvalues = []
            for subvalue in incoming_subvalues:
                alphanumeric_string = "".join(
                    random.choices(
                        string.ascii_letters + string.digits,
                        k=config["csv_value_templates_rand_length"],
                    )
                )
                number_string = "".join(
                    random.choices(
                        string.digits, k=config["csv_value_templates_rand_length"]
                    )
                )
                uuid_string = str(uuid.uuid4())

                if "file" in row:
                    row_file_value = row["file"]
                else:
                    row_file_value = ""

                if "file" in row:
                    path, extension = os.path.splitext(row["file"])
                    filename_without_extension = os.path.basename(path)
                else:
                    filename_without_extension = ""

                if "field_weight" in row:
                    weight = row["field_weight"]
                else:
                    weight = ""

                if len(subvalue) > 0:
                    field_template = string.Template(templates[field])
                    subvalue = str(
                        field_template.substitute(
                            {
                                "csv_value": subvalue,
                                "file": row_file_value,
                                "filename_without_extension": filename_without_extension,
                                "weight": weight,
                                "random_alphanumeric_string": alphanumeric_string,
                                "random_number_string": number_string,
                                "uuid_string": uuid_string,
                            }
                        )
                    )
                    outgoing_subvalues.append(subvalue)

                # Handle empty CSV values, first for parent-level items and then for page/child items from
                # subdirectories (which will always have empty CSV values except for required fields).
                if len(row[field]) == 0:
                    if (
                        template_config_setting == "csv_value_templates"
                        and field in config["allow_csv_value_templates_if_field_empty"]
                    ):
                        field_template = string.Template(templates[field])
                        subvalue = str(
                            field_template.substitute(
                                {
                                    "csv_value": subvalue,
                                    "file": row_file_value,
                                    "filename_without_extension": filename_without_extension,
                                    "weight": weight,
                                    "random_alphanumeric_string": alphanumeric_string,
                                    "random_number_string": number_string,
                                    "uuid_string": uuid_string,
                                }
                            )
                        )
                        outgoing_subvalues.append(subvalue)

                    if (
                        template_config_setting
                        == "csv_value_templates_for_paged_content"
                    ):
                        field_template = string.Template(templates[field])
                        subvalue = str(
                            field_template.substitute(
                                {
                                    "csv_value": subvalue,
                                    "file": row_file_value,
                                    "filename_without_extension": filename_without_extension,
                                    "weight": weight,
                                    "random_alphanumeric_string": alphanumeric_string,
                                    "random_number_string": number_string,
                                    "uuid_string": uuid_string,
                                }
                            )
                        )
                        outgoing_subvalues.append(subvalue)

            templated_string = config["subdelimiter"].join(outgoing_subvalues)
            row[field] = templated_string

    return row


def serialize_field_json(config, field_definitions, field_name, field_data):
    """Serializes JSON from a Drupal field into a string consistent with Workbench's CSV-field input format."""
    """Parameters
        ----------
        config : dict
            The configuration settings defined by workbench_config.get_config().
        field_definitions : dict
            The field definitions object defined by get_field_definitions().
        field_name : string
            The Drupal fieldname/CSV column header.
        field_data : string
            Raw JSON from the field named 'field_name'.
        Returns
        -------
        string
            A string structured same as the Workbench CSV field data for the field type.
    """
    # Importing the workbench_fields module at the top of this module with the
    # rest of the imports causes a circular import exception, so we do it here.
    import workbench_fields

    # Assemble CSV output Drupal field data. If new field types are added to
    # workbench_fields.py, they need to be registered in the following if/elif/else block.

    serialized_field = workbench_fields.WorkbenchFieldFactory.get_field_handler(
        field_definitions[field_name]["field_type"]
    )
    csv_field_data = serialized_field.serialize(
        config, field_definitions, field_name, field_data
    )

    return csv_field_data


def csv_subset_warning(config):
    """Create a message indicating that a subset of the input CSV data will be used,
    specific to the current configuration settings."""

    preprocessed_input_csv_file_path = get_preprocessed_input_csv_file_path(config)
    review_message = f'You should review "{preprocessed_input_csv_file_path}" to ensure the correct rows will be processed.'

    if "csv_row_filters" in config and len(config["csv_row_filters"]) > 0:
        message = f'Using a subset of input CSV defined in your "csv_row_filters" setting. {review_message}'
        logging.info(message)
        return

    if "csv_rows_to_process" in config:
        if len(config["csv_rows_to_process"]) > 0 and isinstance(
            config["csv_rows_to_process"], str
        ):
            path_to_ids_file = os.path.abspath(config["csv_rows_to_process"])
            if os.path.exists(path_to_ids_file):
                with open(path_to_ids_file) as fh:
                    ids_to_process = fh.read().splitlines()
                    ids_to_process = [x for x in ids_to_process if x]
                message = (
                    f'Using a subset of input CSV rows listed in "{path_to_ids_file}".'
                )
                print(message)
                logging.info(message)
                return
            else:
                message = f'File identified in the "csv_rows_to_process" config setting ({path_to_ids_file}) cannot be found.'
                logging.error(message)
                sys.exit("Error: " + message)

        if len(config["csv_rows_to_process"]) > 0 and isinstance(
            config["csv_rows_to_process"], list
        ):
            message = f'Using a subset of input CSV defined in your "csv_rows_to_process" setting. {review_message}'
            print(message)
            logging.info(message)
            return

    if config["csv_start_row"] != 0 or config["csv_stop_row"] is not None:
        csv_data = list(get_csv_data(config))
        start_row_id = csv_data[0][config["id_field"]]
        stop_row_id = csv_data[-1][config["id_field"]]

        message = f"Using a subset of the input CSV (will start at row {config['csv_start_row']} / row ID \"{start_row_id}\", stop at row {config['csv_stop_row']} / row ID \"{stop_row_id}\")."
        if config["csv_start_row"] != 0 and config["csv_stop_row"] is None:
            message = f"Using a subset of the input CSV (will start at row {config['csv_start_row']} / row ID {start_row_id})."
        if config["csv_start_row"] == 0 and config["csv_stop_row"] is not None:
            message = f"Using a subset of the input CSV (will stop at row {config['csv_stop_row']} / row ID {stop_row_id})."
        print(message)
        logging.info(message)
        return


def get_entity_reference_view_endpoints(config):
    """Gets entity reference View endpoints from config."""
    """Parameters
        ----------
        config : dict
            The configuration settings defined by workbench_config.get_config().
        Returns
        -------
        dict
            Dictionary with Drupal field names as keys and View REST endpoints as values.
    """
    endpoint_mappings = dict()
    if "entity_reference_view_endpoints" not in config:
        return endpoint_mappings

    for endpoint_mapping in config["entity_reference_view_endpoints"]:
        for field_name, endpoint in endpoint_mapping.items():
            endpoint_mappings[field_name] = endpoint

    return endpoint_mappings


def get_node_exists_verification_view_endpoint(config):
    """Gets from conifig the View endpoints and CSV field to match to determine if a matching node already exists."""
    """Parameters
        ----------
        config : dict
            The configuration settings defined by workbench_config.get_config().
        Returns
        -------
        tuple|False
            Tuple containing Drupal field name and View REST endpoints as values. If there are multiple mappings,
            the returned tuple will contain the field_name and endpoint values of only the last mapping. If the config
            can't be loaded into a tuple, returns False.
    """
    for endpoint_mapping in config["node_exists_verification_view_endpoint"]:
        for field_name, endpoint in endpoint_mapping.items():
            endpoint_mapping = (field_name, endpoint)

    if type(endpoint_mapping) is tuple:
        return endpoint_mapping
    else:
        return False


def get_percentage(part, whole):
    return 100 * float(part) / float(whole)


def get_config_file_identifier(config):
    """Gets a unique identifier of the current config file. Used in names of temp files, etc."""
    """Parameters
        ----------
        config : dict
            The configuration settings defined by workbench_config.get_config().
        Returns
        -------
        string
            A string based on the config file's path, with directory slashes and backslashes
            replaced with underscores.
    """
    split_path = os.path.splitdrive(
        os.path.splitext(config["current_config_file_path"])[0]
    )
    config_file_id = re.sub(r"[/\\]", "_", split_path[1].strip("/\\"))

    return config_file_id


def calculate_response_time_trend(config, response_time):
    """Gets the average response time from the most recent 20 HTTP requests."""
    """Parameters
        ----------
        config : dict
            The configuration settings defined by workbench_config.get_config().
        response_time : Response time of current request, in seconds.
            The string to test.
        Returns
        -------
        int|None
            The average response time of the most recent 20 requests.
    """
    http_response_times.append(response_time)
    if len(http_response_times) > 20:
        sample = http_response_times[-20:]
    else:
        sample = http_response_times
    if config["log_response_time_sample"] is True:
        logging.info("Response time trend sample: %s", sample)
    if len(sample) > 0:
        average = sum(sample) / len(sample)
        return average


def string_is_ascii(input):
    """Check if a string contains only ASCII characters."""
    """Parameters
        ----------
        input : str
            The string to test.
        Returns
        -------
        boolean
            True if all characters are within the ASCII character set,
            False otherwise.
    """
    return all(ord(c) < 128 for c in input)


def file_is_utf8(file_path):
    """Check if a file is encoded as UTF-8, or backward-compatible encodings such as ASCII. BOM is ignored."""
    """Parameters
        ----------
        file_path : str
            The absolute or relative path to the file.
        Returns
        -------
        boolean
            True if file is encoded as UTF-8. False if not or if file cannot be found.
    """
    if os.path.exists(file_path):
        with open(file_path, "rb") as f:
            try:
                f.read().decode("utf-8-sig")
                file_is_utf8 = True
            except UnicodeDecodeError:
                file_is_utf8 = False
            return file_is_utf8
    else:
        logging.error(
            f'File "{file_path}" not found; Workbench cannot determine if it is encoded as UTF-8.'
        )
        return False


def quick_delete_node(config, args):
    logging.info("--quick_delete_node task started for " + args.quick_delete_node)

    if value_is_numeric(args.quick_delete_node) is True:
        response = issue_request(
            config, "GET", args.quick_delete_node + "?_format=json"
        )
        if response.status_code != 200:
            message = f"Sorry, {args.quick_delete_node} can't be accessed. Please confirm the node exists and is accessible to the user defined in your Workbench configuration."
            logging.error(
                message + f" (HTTP response code was {response.status_code}.)"
            )
            sys.exit("Error: " + message)
    else:
        node_id = get_nid_from_url_alias(config, args.quick_delete_node)
        if node_id is False:
            message = f"Sorry, {args.quick_delete_node} can't be accessed. Please confirm the node exists and is accessible to the user defined in your Workbench configuration."
            logging.error(message)
            sys.exit("Error: " + message)
        else:
            response = issue_request(
                config, "GET", f'{config["host"]}/node/{node_id}' + "?_format=json"
            )
            if response.status_code != 200:
                message = f"Sorry, {args.quick_delete_node} can't be accessed. Please confirm the node exists and is accessible to the user defined in your Workbench configuration."
                logging.error(
                    message + f" (HTTP response code was {response.status_code}.)"
                )
                sys.exit("Error: " + message)

    entity = json.loads(response.text)
    if "type" in entity:
        if entity["type"][0]["target_type"] == "node_type":
            # Delete the node's media first.
            if config["delete_media_with_nodes"] is True:
                media_endpoint = (
                    config["host"] + "/node/" + str(node_id) + "/media?_format=json"
                )
                media_response = issue_request(config, "GET", media_endpoint)
                media_response_body = json.loads(media_response.text)
                media_messages = []
                for media in media_response_body:
                    if "mid" in media:
                        media_id = media["mid"][0]["value"]
                        media_delete_status_code = remove_media_and_file(
                            config, media_id
                        )
                        if media_delete_status_code == 204:
                            media_messages.append(
                                "+ Media "
                                + config["host"]
                                + "/media/"
                                + str(media_id)
                                + " deleted."
                            )

            # Then the node.
            node_endpoint = config["host"] + "/node/" + str(node_id) + "?_format=json"
            node_response = issue_request(config, "DELETE", node_endpoint)
            if node_response.status_code == 204:
                if config["progress_bar"] is False:
                    print("Node " + args.quick_delete_node + " deleted.")
                logging.info("Node %s deleted.", args.quick_delete_node)
            if (
                config["delete_media_with_nodes"] is True
                and config["progress_bar"] is False
            ):
                if len(media_messages):
                    for media_message in media_messages:
                        print(media_message)
        else:
            message = f"{args.quick_delete_node} does not apear to be a node."
            logging.error(message)
            sys.exit("Error: " + message)
    else:
        message = f"{args.quick_delete_node} does not apear to be a node."
        logging.error(message)
        sys.exit("Error: " + message)

    sys.exit()


def quick_delete_media(config, args):
    logging.info("--quick_delete_mediatask started for " + args.quick_delete_media)

    if config["standalone_media_url"] is False and not args.quick_delete_media.endswith(
        "/edit"
    ):
        message = f"You need to add '/edit' to the end of your media URL (e.g. {args.quick_delete_media}/edit)."
        logging.error(message)
        sys.exit("Error: " + message)

    if config["standalone_media_url"] is True and args.quick_delete_media.endswith(
        "/edit"
    ):
        message = f"You need to remove '/edit' to the end of your media URL."
        logging.error(message)
        sys.exit("Error: " + message)

    ping_response = issue_request(
        config, "GET", args.quick_delete_media + "?_format=json"
    )
    if ping_response.status_code == 404:
        message = f"Cannot find {args.quick_delete_media}. Please verify the media URL and try again."
        logging.error(message + f"HTTP response code was {ping_response.status_code}.")
        sys.exit("Error: " + message)

    entity = json.loads(ping_response.text)
    if "mid" not in entity:
        message = f"{args.quick_delete_media} does not apear to be a media."
        logging.error(message)
        sys.exit("Error: " + message)

    media_id = get_mid_from_media_url_alias(config, args.quick_delete_media)
    media_delete_status_code = remove_media_and_file(config, media_id)
    if media_delete_status_code == 204:
        message = f"Media {args.quick_delete_media} and associated file deleted."
        print(message)
        logging.info(message)
    else:
        message = f"Media {args.quick_delete_media} and associated file not deleted. See Workbench log for more detail."
        print("Error: " + message)
        logging.error(message + f"HTTP response code was {media_delete_status_code}.")

    sys.exit()


def create_contact_sheet_thumbnail(config, source_filename):
    """Determines the thumbnail image to use for a given filename, and copies
    the image to the output directory.
    """
    """Parameters
        ----------
        config : dict
            The configuration settings defined by workbench_config.get_config().
        source_filename: string
            The value of the CSV row's "file" column, or the reserved value "compound".
        Returns
        -------
        string
            The file name of the thumbnail image file.
    """
    generic_icons_dir = os.path.join("assets", "contact_sheet", "generic_icons")

    if len(source_filename.strip()) == 0:
        no_file_icon_filename = "tn_generic_no_file.png"
        no_file_icon_path = os.path.join(
            config["contact_sheet_output_dir"], no_file_icon_filename
        )
        if not os.path.exists(no_file_icon_path):
            shutil.copyfile(
                os.path.join(generic_icons_dir, no_file_icon_filename),
                no_file_icon_path,
            )
        return no_file_icon_filename

    if source_filename == "compound":
        compound_icon_filename = "tn_generic_compound.png"
        compound_icon_path = os.path.join(
            config["contact_sheet_output_dir"], compound_icon_filename
        )
        if not os.path.exists(compound_icon_path):
            shutil.copyfile(
                os.path.join(generic_icons_dir, compound_icon_filename),
                compound_icon_path,
            )
        return compound_icon_filename

    # todo: get these from config['media_types']
    pdf_extensions = [".pdf"]
    video_extensions = [".mp4"]
    audio_extensions = [".mp3"]
    image_extensions = [".png", ".jpg", ".jpeg", ".tif", ".tiff", ".jp2"]

    source_file_name, source_file_extension = os.path.splitext(source_filename)
    if source_file_extension.lower() in image_extensions:
        """
        # Note: this block can be used to generate thumbnails for images if "from PIL import Image".
        image_source_path = os.path.join(input_dir, source_filename)
        image_source = Image.open(image_source_path)
        image_tn = image_source.copy()
        image_tn.thumbnail((200, 200))
        filename_info = os.path.splitext(row['file'])
        tn_filename = f'tn_{filename_info[0]}.png'
        tn_filepath = os.path.join(output_dir, tn_filename)
        image_tn.save(tn_filepath)
        tn_filepath = tn_filename
        """
        image_icon_filename = "tn_generic_image.png"
        image_icon_path = os.path.join(
            config["contact_sheet_output_dir"], image_icon_filename
        )
        if not os.path.exists(image_icon_path):
            shutil.copyfile(
                os.path.join(generic_icons_dir, image_icon_filename), image_icon_path
            )
        tn_filepath = image_icon_filename
    elif source_file_extension.lower() in pdf_extensions:
        pdf_icon_filename = "tn_generic_pdf.png"
        pdf_icon_path = os.path.join(
            config["contact_sheet_output_dir"], pdf_icon_filename
        )
        if not os.path.exists(pdf_icon_path):
            shutil.copyfile(
                os.path.join(generic_icons_dir, pdf_icon_filename), pdf_icon_path
            )
        tn_filepath = pdf_icon_filename
    elif source_file_extension.lower() in audio_extensions:
        audio_icon_filename = "tn_generic_audio.png"
        audio_icon_path = os.path.join(
            config["contact_sheet_output_dir"], audio_icon_filename
        )
        if not os.path.exists(audio_icon_path):
            shutil.copyfile(
                os.path.join(generic_icons_dir, audio_icon_filename), audio_icon_path
            )
        tn_filepath = audio_icon_filename
    elif source_file_extension.lower() in video_extensions:
        video_icon_filename = "tn_generic_video.png"
        video_icon_path = os.path.join(
            config["contact_sheet_output_dir"], video_icon_filename
        )
        if not os.path.exists(video_icon_path):
            shutil.copyfile(
                os.path.join(generic_icons_dir, video_icon_filename), video_icon_path
            )
        tn_filepath = video_icon_filename
    else:
        binary_icon_filename = "tn_generic_binary.png"
        binary_icon_path = os.path.join(
            config["contact_sheet_output_dir"], binary_icon_filename
        )
        if not os.path.exists(binary_icon_path):
            shutil.copyfile(
                os.path.join(generic_icons_dir, binary_icon_filename), binary_icon_path
            )
        tn_filepath = binary_icon_filename

    return tn_filepath


def generate_contact_sheet_from_csv(config):
    """Generates a contact sheet from CSV data."""
    """Parameters
        ----------
        config : dict
            The configuration settings defined by workbench_config.get_config().
    """
    css_file_path = config["contact_sheet_css_path"]
    css_file_name = os.path.basename(css_file_path)

    generic_icons_dir = os.path.join("assets", "contact_sheet", "generic_icons")

    if not os.path.exists(config["contact_sheet_output_dir"]):
        try:
            os.mkdir(config["contact_sheet_output_dir"])
        except Exception as e:
            message = (
                'Path in configuration option "contact_sheet_output_dir" ("'
                + config["contact_sheet_output_dir"]
                + '") is not writable.'
            )
            logging.error(message + " " + str(e))
            sys.exit("Error: " + message + " See log for more detail.")

    csv_data = get_csv_data(config)

    compound_items = list()
    csv_data_to_get_children = get_csv_data(config)
    if config["paged_content_from_directories"]:
        # Collect the IDs of top-level items for use in the "Using subdirectories" method
        # of creating compound/paged content.
        for get_children_row in csv_data_to_get_children:
            compound_items.append(get_children_row[config["id_field"]])
    else:
        # Collect the IDs of items whose IDs are in other (child) items' "parent_id" column,
        # a.k.a. compound items created using the "With page/child-level metadata" method.
        if "parent_id" in csv_data.fieldnames:
            for get_children_row in csv_data_to_get_children:
                compound_items.append(get_children_row["parent_id"])

        deduplicated_compound_items = list(set(compound_items))
        compound_items = deduplicated_compound_items
        if "" in compound_items:
            compound_items.remove("")

    # Create a dict containing all the output file data.
    contact_sheet_output_files = dict()
    contact_sheet_output_files["main_contact_sheet"] = {}
    contact_sheet_output_files["main_contact_sheet"]["path"] = os.path.join(
        config["contact_sheet_output_dir"], "contact_sheet.htm"
    )
    contact_sheet_output_files["main_contact_sheet"]["file_handle"] = open(
        contact_sheet_output_files["main_contact_sheet"]["path"], "w"
    )
    contact_sheet_output_files["main_contact_sheet"]["markup"] = ""
    for compound_item_id in compound_items:
        if compound_item_id != "":
            contact_sheet_output_files[compound_item_id] = {}
            compound_item_contact_sheet_path = os.path.join(
                config["contact_sheet_output_dir"],
                f"{compound_item_id}_contact_sheet.htm",
            )
            contact_sheet_output_files[compound_item_id][
                "path"
            ] = compound_item_contact_sheet_path
            contact_sheet_output_files[compound_item_id]["file_handle"] = open(
                os.path.join(compound_item_contact_sheet_path), "w"
            )
            contact_sheet_output_files[compound_item_id]["markup"] = ""

    for output_file in contact_sheet_output_files.keys():
        contact_sheet_output_files[output_file]["file_handle"] = open(
            contact_sheet_output_files[output_file]["path"], "a"
        )
        contact_sheet_output_files[output_file]["file_handle"].write(
            f"<html>\n<head>\n<title>Islandora Workbench contact sheet</title>"
        )
        contact_sheet_output_files[output_file]["file_handle"].write(
            f'\n<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />'
        )
        contact_sheet_output_files[output_file]["file_handle"].write(
            f'\n<link rel="stylesheet" media="all" href="{css_file_name}" />\n</head>\n'
        )

        if output_file != "main_contact_sheet":
            # "output_file" is the same as the CSV ID of the parent of items in the current contact sheet.
            members_of_div = (
                f'<div class="header">Members of '
                + f'CSV entry <a alt="Members of" href="contact_sheet.htm">{output_file}</a>.</div>\n'
            )
            contact_sheet_output_files[output_file]["file_handle"].write(members_of_div)

        contact_sheet_output_files[output_file]["file_handle"].write(
            '<div class="cards">\n'
        )

    for row in csv_data:
        if config["paged_content_from_directories"]:
            # Note: parent items (i.e. items with rows in the CSV) are processed below.
            if row[config["id_field"]] in compound_items:
                # Get all the page files for this parent and create a new contact sheet containing them.
                page_files_dir_path = os.path.join(
                    config["input_dir"], row[config["id_field"]]
                )
                page_files = os.listdir(page_files_dir_path)

                # Page files need to be sorted by weight in the contact sheet.
                page_file_weights_map = {}
                for page_file_name in page_files:
                    weight = get_sequence_indicator_from_filename(
                        config, page_file_name
                    )
                    # Cast weight as int so we can sort it easily.
                    page_file_weights_map[int(weight)] = page_file_name
                    page_title = row["title"] + ", page " + weight

                sorted_weights = sorted(page_file_weights_map.keys())

                for page_sort_order in sorted_weights:
                    page_output_file = row[config["id_field"]]
                    filename_without_extension = os.path.splitext(
                        page_file_weights_map[page_sort_order]
                    )[0]
                    tn_filename = create_contact_sheet_thumbnail(
                        config, page_file_weights_map[page_sort_order]
                    )

                    # Start .card.
                    contact_sheet_output_files[page_output_file][
                        "markup"
                    ] = '\n<div class="card">\n'
                    contact_sheet_output_files[page_output_file][
                        "markup"
                    ] += f'<img alt="{filename_without_extension}" src="{tn_filename}" />'
                    # Start .fields
                    contact_sheet_output_files[page_output_file][
                        "markup"
                    ] += f'\n<div class="fields">'
                    contact_sheet_output_files[page_output_file]["markup"] += (
                        f'\n<div class="field system"><span class="field-label">file</span>: '
                        + f"{page_file_weights_map[page_sort_order]}</div>"
                    )
                    contact_sheet_output_files[page_output_file]["markup"] += (
                        f'\n<div class="field system"><span class="field-label">title</span>: '
                        + f"{page_title}</div>"
                    )
                    contact_sheet_output_files[page_output_file]["markup"] += (
                        f'\n<div class="field system"><span class="field-label">field_weight</span>: '
                        + f"{page_sort_order}</div>"
                    )
                    # Close .fields
                    contact_sheet_output_files[page_output_file][
                        "markup"
                    ] += f"\n<!-- .fields -->\n</div>"
                    # Close .card
                    contact_sheet_output_files[page_output_file][
                        "markup"
                    ] += f"\n<!-- .card -->\n</div>"
                    contact_sheet_output_files[page_output_file]["file_handle"].write(
                        contact_sheet_output_files[page_output_file]["markup"] + "\n"
                    )
        else:
            if "parent_id" in row:
                if row["parent_id"] == "":
                    output_file = "main_contact_sheet"
                    if row[config["id_field"]] in compound_items:
                        tn_filename = create_contact_sheet_thumbnail(config, "compound")
                    else:
                        tn_filename = create_contact_sheet_thumbnail(
                            config, row["file"]
                        )
                else:
                    output_file = row["parent_id"]
                    if row[config["id_field"]] in compound_items:
                        tn_filename = create_contact_sheet_thumbnail(config, "compound")
                    else:
                        tn_filename = create_contact_sheet_thumbnail(
                            config, row["file"]
                        )
            else:
                output_file = "main_contact_sheet"
                tn_filename = create_contact_sheet_thumbnail(config, row["file"])

        # During 'paged_content_from_directories' parent items (i.e. items with rows in the CSV)
        # are processed from this point on.
        csv_id = row[config["id_field"]]
        title = row["title"]

        # Ensure that parent items get the compound icon.
        if config["paged_content_from_directories"]:
            output_file = "main_contact_sheet"
            tn_filename = create_contact_sheet_thumbnail(config, "compound")

        # start .card
        contact_sheet_output_files[output_file]["markup"] = '\n<div class="card">\n'
        contact_sheet_output_files[output_file][
            "markup"
        ] += f'<img alt="{title}" src="{tn_filename}" />'

        # Start .fields
        contact_sheet_output_files[output_file]["markup"] += f'\n<div class="fields">'
        if row[config["id_field"]] in compound_items:
            contact_sheet_output_files[output_file]["markup"] += (
                f'<div class="field system"><span class="field-label"></span>'
                + f'<a alt="members" href="{row[config["id_field"]]}_contact_sheet.htm">members</a></div>'
            )
        contact_sheet_output_files[output_file][
            "markup"
        ] += f'\n<div class="field system"><span class="field-label">{config["id_field"]}</span>: {csv_id}</div>'
        if config["paged_content_from_directories"] is False and len(row["file"]) > 0:
            contact_sheet_output_files[output_file][
                "markup"
            ] += f'\n<div class="field system"><span class="field-label">file</span>: {row["file"]}</div>'
        else:
            contact_sheet_output_files[output_file][
                "markup"
            ] += f'\n<div class="field system"><span class="field-label">file</span>:</div>'
        contact_sheet_output_files[output_file][
            "markup"
        ] += f'\n<div class="field"><span class="field-label">title:</span> {title}</div>'
        for fieldname in row:
            # These three fields have already been rendered.
            if fieldname not in [config["id_field"], "title", "file"]:
                if len(row[fieldname].strip()) == 0:
                    continue
                if len(row[fieldname]) > 30:
                    field_value = row[fieldname][:30]
                    row_value_with_enhanced_subdelimiter = row[fieldname].replace(
                        config["subdelimiter"], " &square; "
                    )
                    field_value = field_value.replace(
                        config["subdelimiter"], " &square; "
                    )
                    contact_sheet_output_files[output_file]["markup"] += (
                        f'\n<div class="field"><span class="field-label">{fieldname}:</span> '
                        + f'{field_value} <a href="" title="{row_value_with_enhanced_subdelimiter}">[...]</a></div>'
                    )
                else:
                    field_value = row[fieldname]
                    field_value = field_value.replace(
                        config["subdelimiter"], " &square; "
                    )
                    contact_sheet_output_files[output_file][
                        "markup"
                    ] += f'\n<div class="field"><span class="field-label">{fieldname}:</span> {field_value}</div>'
        # Close .fields
        contact_sheet_output_files[output_file][
            "markup"
        ] += f"\n<!-- .fields -->\n</div>"
        # Close .card
        contact_sheet_output_files[output_file]["markup"] += f"\n<!-- .card -->\n</div>"
        contact_sheet_output_files[output_file]["file_handle"].write(
            contact_sheet_output_files[output_file]["markup"] + "\n"
        )
        # Zero out the card markup before starting the next CSV row.
        contact_sheet_output_files[output_file]["markup"] = ""

    for output_file in contact_sheet_output_files.keys():
        # Close .cards
        contact_sheet_output_files[output_file]["file_handle"].write(
            f"\n<!-- .cards -->\n</div>"
        )
        contact_sheet_output_files[output_file]["file_handle"].write(
            '\n<div class="footer">Icons courtesy of <a href="https://icons8.com/">icons8</a>.</div>'
        )
        now = datetime.datetime.now()
        contact_sheet_output_files[output_file]["file_handle"].write(
            f'\n<div class="footer">Generated {now}.</div>'
        )
        contact_sheet_output_files[output_file]["file_handle"].write("\n</html>")
        contact_sheet_output_files[output_file]["file_handle"].close()

    shutil.copyfile(
        os.path.join(css_file_path),
        os.path.join(config["contact_sheet_output_dir"], css_file_name),
    )


def sqlite_manager(
    config,
    operation="select",
    table_name=None,
    query=None,
    values=(),
    db_file_path=None,
    warn_table_exists=False,
):
    """Perform operations on an SQLite database."""
    """
    Params
        config: dict
            The configuration settings defined by workbench_config.get_config().
        operation: string
            One of 'create_database', 'remove_database', 'create_table, 'alter_table', 'insert', 'select', 'update', 'delete'.
            'create_table, 'alter_table', 'insert', 'select', 'update', and 'delete' operations need to be passed a full
            query to execute.
        table_name: string
            The name of the table to create. Used only in 'create_table' queries.
        query: string
            The parameterized query, expressed as a tuple, e.g., "SELECT foo from bar where foo = ?".
            'insert', 'select', 'update', 'delete', and 'alter_table' operations need to be passed a query to execute.
            Note: "alter table" queries cannot use parameter placeholders for table or column names; they need to be
            hard-coded in queries, e.g., "alter table 'names' add column 'foo' integer".
        values: tuple
            The positional values to interpolate into the query, e.g., "('baz',)" or "('baz', 'bar')".
        db_file_path: string
            The relative or absolute path to the database file. If the path is relative, the file
            is written to that path relative to the system's temporary directory.
        warn_table_exists: boolean
            Log a warning if a table that you are asking to be created already exists. Useful for debugging.
    Return
        bool|list|sqlite3.Cursor object
            True if the 'create_database' or 'remove_database' operation was successful, False if an
            operation could not be completed, a list of sqlite3.Row objects for 'select' and 'update'
            queries, or an sqlite3.Cursor object for 'insert' and 'delete' queries.
    """
    if isinstance(db_file_path, str) is not True:
        return False

    if db_file_path is None:
        db_file_path = config["sqlite_db_filename"]

    db_path = os.path.abspath(db_file_path)

    # Only create the database if the database file does not exist. Note: Sqlite3 creates the db file
    # automatically in its .connect method, so you only need to use this operation if you want to
    # create the db prior to creating a table. No need to use it as a prerequisite for creating a table.
    if operation == "create_database":
        # Already exists and is a file (assumes it's an SQLite database file).
        if os.path.isfile(db_path):
            return False
        else:
            sqlite3.connect(db_path)
            logging.info(f'SQLite database "{db_path}" created.')
            return True
    elif operation == "remove_database":
        if os.path.isfile(db_path):
            os.remove(db_path)
            logging.info(f'SQLite database "{db_path}" deleted.')
            return True
    elif operation == "create_table":
        con = sqlite3.connect(db_path)
        cur = con.cursor()
        args = (table_name,)
        tables = cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?", args
        ).fetchall()
        # Only create the table if it doesn't exist.
        if tables == []:
            res = cur.execute(query)
            con.close()
            return res
        else:
            con.close()
            if warn_table_exists is True:
                logging.warning(
                    f'SQLite database "{db_path}" already contains a table named "{table_name}".'
                )
            return False
    elif operation == "alter_table":
        # Note: "alter table" queries cannot use parameter placeholders for table or column names; they need to be
        # hard-coded in queries, e.g., "alter table 'names' add column 'foo' integer".
        try:
            con = sqlite3.connect(db_path)
            cur = con.cursor()
            res = cur.execute(query, values)
            con.commit()
            con.close()
            return res
        except sqlite3.OperationalError as e:
            message = f"Error executing SQLite alter table query against database at {db_path}: {e}"
            logging.error(message)
            sys.exit(message)
    elif operation == "select":
        try:
            con = sqlite3.connect(db_path)
            con.row_factory = sqlite3.Row
            # Uncomment for debugging.
            # con.set_trace_callback(print)
            cur = con.cursor()
            res = cur.execute(query, values).fetchall()
            con.close()
            return res
        except sqlite3.OperationalError as e:
            message = f"Error executing SQLite select query against database at {db_path}: {e}"
            logging.error(message)
            sys.exit(message)
    else:
        # 'insert', 'update', 'delete' queries.
        try:
            con = sqlite3.connect(db_path)
            con.row_factory = sqlite3.Row
            cur = con.cursor()
            res = cur.execute(query, values)
            con.commit()
            con.close()
            return res
        except sqlite3.OperationalError as e:
            message = f"Error executing SQLite {operation} query against database at {db_path}: {e}"
            logging.error(message)
            sys.exit(message)


def prepare_csv_id_to_node_id_map(config):
    """Creates the SQLite database used to map CSV row IDs to newly create node IDs."""
    if config["csv_id_to_node_id_map_path"] is False:
        return None

    # sqlite_manager only creates a table if it doesn't exist.
    create_table_sql = (
        "CREATE TABLE csv_id_to_node_id_map (timestamp TIMESTAMP DEFAULT (datetime('now','localtime')) NOT NULL, "
        + " config_file TEXT, parent_csv_id TEXT, parent_node_id TEXT, csv_id TEXT, node_id TEXT, host TEXT)"
    )
    sqlite_manager(
        config,
        operation="create_table",
        table_name="csv_id_to_node_id_map",
        query=create_table_sql,
        db_file_path=config["csv_id_to_node_id_map_path"],
    )

    # Check to see if the last column in the csv_id_to_node_id_map table is "host"
    # and if not, add that column.
    check_for_host_column_result = sqlite_manager(
        config,
        operation="select",
        db_file_path=config["csv_id_to_node_id_map_path"],
        query="select * from pragma_table_info(?)",
        values=("csv_id_to_node_id_map",),
    )
    if check_for_host_column_result[-1][1] != "host":
        sqlite_manager(
            config,
            operation="alter_table",
            db_file_path=config["csv_id_to_node_id_map_path"],
            query="alter table csv_id_to_node_id_map add column host TEXT",
        )
        logging.info(
            f'Added column "host" to the CSV ID to node ID map at {config["csv_id_to_node_id_map_path"]}.'
        )


def populate_csv_id_to_node_id_map(
    config, parent_csv_row_id, parent_node_id, csv_row_id, node_id
):
    """Inserts a row into the SQLite database used to map CSV row IDs to newly create node IDs."""
    if config["csv_id_to_node_id_map_path"] is False:
        return None

    sql_query = "INSERT INTO csv_id_to_node_id_map (config_file, parent_csv_id, parent_node_id, csv_id, node_id, host) VALUES (?, ?, ?, ?, ?, ?)"
    sqlite_manager(
        config,
        operation="insert",
        query=sql_query,
        values=(
            config["config_file"],
            str(parent_csv_row_id),
            str(parent_node_id),
            str(csv_row_id),
            str(node_id),
            config["host"],
        ),
        db_file_path=config["csv_id_to_node_id_map_path"],
    )


def recovery_mode_id_in_csv_id_to_node_id_map(config, csv_id, parent_csv_id=None):
    """Query the CSV ID to node ID map to check for a CSV ID, or in the case of pages/children
       in directories, for the filename. Used only during recovery mode.

       Note: If the CSV ID / filename exists in more than one row, only the most
       recent corresponding node ID is returned.

    Params
    ----------
        config : dict
            The configuration settings defined by workbench_config.get_config().
        csv_id : string
            The ID from the input CSV, or in the case of pages/children in directories, the
            filename.
        parent_csv_id: None|string
            The parent ID, used only for pages/children in directories to disambiguate
            non-unique filenames across directories processed during the same job.
    Return
    ------
        bool|str
            The item's node_id if the item is in the map, False if not.
    """
    # Confirm the database exists; if not, tell the user and exit.
    if config["csv_id_to_node_id_map_path"] is not False:
        if not os.path.exists(config["csv_id_to_node_id_map_path"]):
            message = f"Can't find CSV ID to node ID database at {config['csv_id_to_node_id_map_path']}."
            logging.error(message)
            sys.exit("Error: " + message)

    # If database exists, query it. Ordering desc by timestamp will get us the latest row if more
    # than one row meets the other criteria. "+ 0" casts the node_id column value as an integer.

    csv_id_to_node_id_map_allowed_hosts_sql = (
        get_csv_id_to_node_id_map_allowed_hosts_sql(config)
    )

    if parent_csv_id is None:
        query = (
            "select node_id from csv_id_to_node_id_map where "
            + csv_id_to_node_id_map_allowed_hosts_sql
            + " csv_id = ? and node_id + 0 >= ? order by timestamp desc limit 1"
        )
        if len(config["csv_id_to_node_id_map_allowed_hosts"]) > 0:
            sql_values = (
                csv_id,
                int(config["recovery_mode_starting_from_node_id"]),
            )
        else:
            sql_values = csv_id, int(config["recovery_mode_starting_from_node_id"])
    else:
        query = (
            "select node_id from csv_id_to_node_id_map where "
            + csv_id_to_node_id_map_allowed_hosts_sql
            + " parent_csv_id = ? and csv_id = ? and node_id + 0 >= ? order by timestamp desc limit 1"
        )
        if len(config["csv_id_to_node_id_map_allowed_hosts"]) > 0:
            sql_values = (
                parent_csv_id,
                csv_id,
                int(config["recovery_mode_starting_from_node_id"]),
            )
        else:
            sql_values = (
                parent_csv_id,
                csv_id,
                int(config["recovery_mode_starting_from_node_id"]),
            )
    csv_id_map_result = sqlite_manager(
        config,
        operation="select",
        query=query,
        values=sql_values,
        db_file_path=config["csv_id_to_node_id_map_path"],
    )
    if len(csv_id_map_result) > 0:
        return str(csv_id_map_result[0][0])
    else:
        return False


def get_term_field_values(config, term_id):
    """Get a term's field data so we can use it during PATCH updates,
    which replace a field's values.
    """
    url = config["host"] + "/taxonomy/term/" + term_id + "?_format=json"
    response = issue_request(config, "GET", url)
    term_fields = json.loads(response.text)
    return term_fields


def preprocess_csv(config, row, field):
    """Execute field preprocessor scripts, if any are configured. Note that these scripts
    are applied to the entire value from the CSV field and not split field values,
    e.g., if a field is multivalued, the preprocesor must split it and then reassemble
    it back into a string before returning it. Note that preprocessor scripts work only
    on string data and not on binary data like images, etc. and only on custom fields
    (so not title).
    """
    if "preprocessors" in config and field in config["preprocessors"]:
        command = config["preprocessors"][field]
        output, return_code = preprocess_field_data(
            config["subdelimiter"], row[field], command
        )
        if return_code == 0:
            preprocessor_input = copy.deepcopy(row[field])
            logging.info(
                'Preprocess command %s executed, taking "%s" as input and returning "%s".',
                command,
                preprocessor_input,
                output.decode().strip(),
            )
            return output.decode().strip()
        else:
            message = (
                "Preprocess command "
                + command
                + " failed with return code "
                + str(return_code)
            )
            logging.error(message)
            return row[field]


def get_node_media_summary(config, nid):
    """Generates a formatted summary of what media a node has.

    Params
    ----------
        config : dict
            The configuration settings defined by workbench_config.get_config().
        nid : string
            Node ID of the node being linked to by the media.
    Return
    ------
        str
            The summary.
    """
    try:
        media_use_terms = []
        url = f"/node/{nid}/media?_format=json"
        response = issue_request(config, "GET", url)
        media_list = json.loads(response.text)
        for media in media_list:
            for media_use_term in media["field_media_use"]:
                term_name = get_term_name(config, media_use_term["target_id"])
                media_use_terms.append(term_name)
        media_use_terms.sort()
        return "; ".join(media_use_terms).strip()
    except Exception as e:
        message = f"Getting media list for \"{config['host']}{url}\" returned an error."
        print(f"Error: {message} See log for more detail.")
        logging.error(f"{message} Detail: {e}")


def service_file_present(config, input):
    service_uri = "http://pcdm.org/use#ServiceFile"
    candidates = input.split("|")
    for candidate in candidates:
        candidate = candidate.strip()
        if candidate == service_uri:
            return True
        if candidate.isnumeric():
            if get_term_uri(config, candidate) == service_uri:
                return True
        name_data = get_all_representations_of_term(
            config, vocab_id="islandora_media_use", name=candidate
        )
        if name_data["uri"] and name_data["uri"] == service_uri:
            return True
    return False


def download_remote_archive_file(config, remote_archive_url):
    message = f'Downloading Zip archive "{remote_archive_url}"...'
    print(message)
    logging.info(message)
    sections = urllib.parse.urlparse(remote_archive_url)
    archive_filename = os.path.basename(sections.path)
    if archive_filename.lower().endswith(".zip") is False:
        archive_filename = archive_filename + ".zip"
    try:
        if config["secure_ssl_only"] is False:
            requests.packages.urllib3.disable_warnings()
        # Do not cache the responses for downloaded files in requests_cache
        with requests_cache.disabled():
            response = requests.get(
                remote_archive_url,
                allow_redirects=True,
                stream=True,
                verify=config["secure_ssl_only"],
            )
    except requests.exceptions.Timeout as err_timeout:
        message = (
            "Workbench timed out trying to reach "
            + sections.netloc
            + " while connecting to "
            + remote_archive_url
            + ". Please verify that URL and check your network connection."
        )
        logging.error(message)
        logging.error(err_timeout)
        print("Error: " + message)
        return False
    except requests.exceptions.ConnectionError as error_connection:
        message = (
            "Workbench cannot connect to "
            + sections.netloc
            + " while connecting to "
            + remote_archive_url
            + ". Please verify that URL and check your network connection."
        )
        logging.error(message)
        logging.error(error_connection)
        print("Error: " + message)
        return False

    downloaded_file_path = os.path.join(config["temp_dir"], archive_filename)
    with open(downloaded_file_path, "wb+") as output_file:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                output_file.write(chunk)

    return downloaded_file_path


def unzip_archive(config, archive_file_path):
    if archive_file_path is False:
        return None
    if os.path.exists(archive_file_path):
        if zipfile.is_zipfile(archive_file_path) is True:
            with zipfile.ZipFile(archive_file_path, "r") as zip_ref:
                zip_ref.extractall(config["input_dir"])
                message = f'Zip archive "{archive_file_path}" extracted to "{config["input_dir"]}".'
                print("OK, " + message)
                logging.info(message)

            if config["delete_zip_archive_after_extraction"] is True:
                try:
                    os.remove(archive_file_path)
                    logging.info(f'Zip archive "{archive_file_path}" deleted."')
                except Exception as e:
                    logging.error(
                        f'Could not remove input archive file "{archive_file_path}": {e}.'
                    )
        else:
            message = f'"{archive_file_path}" does not appear to be a valid Zip file.'
            logging.error(message)
            sys.exit("Error: " + message)
    else:
        message = f'Zip archive "{archive_file_path}" not extracted to "{config["input_dir"]}": cannot find zip archive.'
        logging.error(message)
        sys.exit("Error: " + message)


def prompt_user(config):
    for user_prompt in config["user_prompts"]:
        response = input(user_prompt)
        if response.lower() != "y":
            logging.info(
                f'Exiting because user responded "{response}" to prompt "{user_prompt}".'
            )
            sys.exit("Exiting at user prompts.")


def check_for_workbench_updates(config):
    if config["check_for_workbench_updates"] is False:
        return

    # Get current local branch name.
    git_branch_cmd = ["git", "rev-parse", "--abbrev-ref", "HEAD"]
    current_branch_name = subprocess.check_output(git_branch_cmd)
    current_branch_name = current_branch_name.decode().strip()
    if current_branch_name != "main":
        message = f'Workbench cannot check when your local "main" Git branch was last updated, since you are currently in the "{current_branch_name}" branch.'
        logging.warning(message)
        return

    # Get last 30 commits in local branch. We use 30 because that's that page size of the Github API commits endpoint.
    git_log_cmd = [
        "git",
        "log",
        "--pretty=format:%h,%cd",
        "--date=format:%Y-%m-%d",
        "-30",
    ]
    git_log_cmd_output = subprocess.check_output(git_log_cmd)
    git_log_output = git_log_cmd_output.decode().strip()
    git_log_output_lines = git_log_output.splitlines()
    latest_git_log_entry = git_log_output_lines[0]
    latest_local_commit, latest_local_commit_date = latest_git_log_entry.split(",")

    # Get the last 30 commits from the main branch in Github.
    github_main_commits_url = (
        "https://api.github.com/repos/mjordan/islandora_workbench/commits"
    )
    github_main_commits_response = requests.get(github_main_commits_url)
    github_main_commits_list = json.loads(github_main_commits_response.content)
    remote_main_branch_commits = list()
    for c in github_main_commits_list:
        short_sha = c["sha"][:7]
        remote_main_branch_commits.append(short_sha)

    # Get the position of the latest local commit in the remote list of commits,
    # and construct corresponding output for the user and the log.
    if latest_local_commit in remote_main_branch_commits:
        latest_local_commit_position_in_remote_main_branch_commits = (
            remote_main_branch_commits.index(latest_local_commit)
        )
        if latest_local_commit_position_in_remote_main_branch_commits > 0:
            # Get date of most recent remote commit and include it in the message.
            github_main_latest_commit_url = f"https://api.github.com/repos/mjordan/islandora_workbench/commits/{remote_main_branch_commits[0]}"
            github_main_latest_commit_response = requests.get(
                github_main_latest_commit_url
            )
            github_main_latest_commit = json.loads(
                github_main_latest_commit_response.content
            )
            github_main_latest_commit_date = github_main_latest_commit["commit"][
                "author"
            ]["date"].split("T", 1)[0]
            message = f'Your version of Workbench is {latest_local_commit_position_in_remote_main_branch_commits} commits behind the "main" branch in Github, which was last updated {github_main_latest_commit_date}.'
            print("Warning: " + message)
            logging.warning(message)
        else:
            message = "Looks like your copy of Workbench is up to date."
            logging.info(message)
    else:
        message = 'Looks like your copy of Workbench is at least 30 commits behind the "main" branch in Github. Your copy appears to have been last updated {latest_local_commit_date}.'
