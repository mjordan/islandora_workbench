"""Class to encapsulate Workbench configuration definitions."""

import logging
from ruamel.yaml import YAML, YAMLError
import os
import sys
import tempfile
from getpass import getpass
from workbench_utils import *
from rich.console import Console
from rich.table import Table


class WorkbenchConfig:
    def __init__(self, args):
        self.args = args
        self.path_check()
        self.config = self.get_config()
        self.validate()
        logging.basicConfig(
            filename=self.config["log_file_path"],
            level=logging.INFO,
            filemode="a",
            format="%(asctime)s - %(levelname)s - %(message)s",
            datefmt="%d-%b-%y %H:%M:%S",
        )

    # Get fully constructed config dictionary.
    def get_config(self):
        config = self.get_default_config()
        user_mods = self.get_user_config()
        # If the password is not set in the config file, or in the environment
        # variable, prompt the user for the password.
        try:
            if "password" not in user_mods:
                if "ISLANDORA_WORKBENCH_PASSWORD" in os.environ:
                    config["password"] = os.environ["ISLANDORA_WORKBENCH_PASSWORD"]
                else:
                    config["password"] = getpass(
                        f"Password for Drupal user {user_mods['username']}:"
                    )
        except KeyboardInterrupt:
            try:
                sys.exit(0)
            except SystemExit:
                os._exit(0)

        # Blend defaults with user mods
        for key, value in user_mods.items():
            config[key] = value

        # Modify some conditional values.
        if "temp_dir" not in user_mods.keys():
            config["temp_dir"] = tempfile.gettempdir()
        if user_mods["task"] in ["add_media", "update", "delete", "export_csv"]:
            config["id_field"] = "node_id"
        if "task" == "delete_media":
            config["id_field"] = "media_id"
        if user_mods["task"] == "create_terms":
            config["id_field"] = "term_name"
            config["allow_adding_terms"] = True
        # @todo: These two overrides aren't working. For now, they are set within workbench.update_terms().
        if "task" == "update_terms":
            config["id_field"] = "term_id"
        if "paged_content_page_content_type" not in user_mods:
            config["paged_content_page_content_type"] = config["content_type"]
        # Add preprocessor, if specified.
        if "preprocessors" in user_mods:
            config["preprocessors"] = {}
            for preprocessor in user_mods["preprocessors"]:
                for key, value in preprocessor.items():
                    config["preprocessors"][key] = value

        config["host"] = config["host"].rstrip("/")
        if "csv_id_to_node_id_map_allowed_hosts" in user_mods:
            config["csv_id_to_node_id_map_allowed_hosts"] = user_mods[
                "csv_id_to_node_id_map_allowed_hosts"
            ]
        else:
            config["csv_id_to_node_id_map_allowed_hosts"] = ["", config["host"]]
        config["current_config_file_path"] = os.path.abspath(self.args.config)
        config["field_text_format_ids"] = self.get_field_level_text_output_formats()

        if "csv_id_to_node_id_map_dir" in user_mods:
            config["csv_id_to_node_id_map_dir"] = user_mods["csv_id_to_node_id_map_dir"]
        if "csv_id_to_node_id_map_filename" in user_mods:
            config["csv_id_to_node_id_map_filename"] = user_mods[
                "csv_id_to_node_id_map_filename"
            ]
        if "csv_id_to_node_id_map_path" in user_mods:
            config["csv_id_to_node_id_map_path"] = user_mods[
                "csv_id_to_node_id_map_path"
            ]
        else:
            config["csv_id_to_node_id_map_path"] = os.path.join(
                config["csv_id_to_node_id_map_dir"],
                config["csv_id_to_node_id_map_filename"],
            )

        if "page_files_source_dir_field" in user_mods:
            config["page_files_source_dir_field"] = user_mods[
                "page_files_source_dir_field"
            ]
        else:
            config["page_files_source_dir_field"] = config["id_field"]

        config["config_file"] = self.args.config

        return config

    # Get user input as dictionary.
    def get_user_config(self):
        yaml = YAML()
        with open(self.args.config, "r") as stream:
            try:
                loaded = yaml.load(stream)
            except YAMLError as exc:
                print(
                    f"There appears to be a YAML syntax error in your configuration file, {self.args.config}. Remove the username and\npassword, and run the file through https://codebeautify.org/yaml-validator/ or your YAML validator of choice."
                )
                sys.exit()

        # 'media_file_fields' has been replaced with 'media_fields' and 'media_type_file_fields'.
        # This is aliasing code that can be removed at some point in the future.
        if "media_file_fields" in loaded:
            media_fields = self.get_media_fields()
            for media_field in loaded["media_file_fields"]:
                for media_type, media_field in media_field.items():
                    media_fields[media_type] = media_field
            loaded["media_fields"] = media_fields
            loaded["media_type_file_fields"] = media_fields
        if os.path.isabs(self.args.config):
            loaded["config_file_path"] = self.args.config
        else:
            loaded["config_file_path"] = os.path.join(os.getcwd(), self.args.config)
        return loaded

    # Returns standard media fields.
    def get_media_fields(self):
        return dict(
            {
                "file": "field_media_file",
                "document": "field_media_document",
                "image": "field_media_image",
                "audio": "field_media_audio_file",
                "video": "field_media_video_file",
                "extracted_text": "field_media_file",
                "fits_technical_metadata": "field_media_file",
                "remote_video": "field_media_oembed_video",
            }
        )

    # Returns standard media extensions for given media type.
    def get_media_types(self):
        return [
            {"image": ["png", "gif", "jpg", "jpeg"]},
            {"document": ["pdf", "doc", "docx", "ppt", "pptx"]},
            {"file": ["tif", "tiff", "jp2", "zip", "tar"]},
            {"audio": ["mp3", "wav", "aac"]},
            {
                "video": [
                    "mp4",
                    "mov",
                    "wmv",
                    "avi",
                    "mts",
                    "flv",
                    "f4v",
                    "swf",
                    "mkv",
                    "webm",
                    "ogv",
                    "mpeg",
                ]
            },
            {"extracted_text": ["txt"]},
        ]

    # Returns standard field name for media track files for given media type.
    def get_media_track_file_fields(self):
        return {"audio": "field_track", "video": "field_track"}

    # Gets the field->text output format mapping dict from the optional 'field_text_format_ids'
    # config setting. If the setting is absent, returns an empty dict.
    def get_field_level_text_output_formats(self):
        user_config = self.get_user_config()
        field_text_output_map = {}
        if "field_text_format_ids" in user_config:
            for map_entry in user_config["field_text_format_ids"]:
                for fieldname, text_format_id in map_entry.items():
                    field_text_output_map[fieldname] = text_format_id
        return field_text_output_map

    # Returns the standard allowed oEmbed provider URLs for a given media type. These
    # are used to identify URLs in the 'file' CSV column as being remote media.
    def get_oembed_media_types(self):
        return [{"remote_video": ["https://www.youtube.com/", "https://youtu.be"]}]

    # Returns default configs, to be updated by user-supplied config.
    def get_default_config(self):
        return {
            "input_dir": "input_data",
            "input_csv": "metadata.csv",
            "media_use_tid": "http://pcdm.org/use#OriginalFile",
            # 'drupal_filesystem' is used only in Drupal 8.x - 9.1; after that,
            # the filesystem is automatically detected from the media's configuration.
            "drupal_filesystem": "fedora://",
            "id_field": "id",
            "content_type": "islandora_object",
            "delimiter": ",",
            "subdelimiter": "|",
            "log_file_path": "workbench.log",
            "log_file_mode": "a",
            "allow_missing_files": False,
            # See Issue 620. Allows the "--check" function to keep running past errors that can be handled
            #  well with batch operations, rather than having to fix it in real-time when one error is hit.
            "perform_soft_checks": False,
            "update_mode": "replace",
            "max_node_title_length": 255,
            "max_image_alt_text_length": 255,
            "paged_content_from_directories": False,
            "delete_media_with_nodes": True,
            "allow_adding_terms": False,
            "columns_with_term_names": [],
            "protected_vocabularies": [],
            "nodes_only": False,
            "log_response_time": False,
            "adaptive_pause_threshold": 2,
            "log_response_time_sample": False,
            "log_request_url": False,
            "log_json": False,
            "log_response_body": False,
            "log_response_status_code": False,
            "log_headers": False,
            "log_term_creation": True,
            "log_file_name_and_line_number": False,
            "progress_bar": False,
            "show_percentage_of_csv_input_processed": False,
            "prompt_user_before_delete_task": False,
            "user_agent": "Islandora Workbench",
            "allow_redirects": True,
            "secure_ssl_only": True,
            "google_sheets_csv_filename": "google_sheet.csv",
            "google_sheets_gid": "0",
            "excel_worksheet": "Sheet1",
            "excel_csv_filename": "excel.csv",
            "ignore_csv_columns": list(),
            "use_node_title_for_media": False,
            "use_nid_in_media_title": False,
            "use_node_title_for_media_title": False,
            "field_for_remote_filename": False,
            "field_for_media_title": False,
            "delete_tmp_upload": False,
            "input_data_zip_archives": [],
            "delete_zip_archive_after_extraction": True,
            "list_missing_drupal_fields": False,
            "secondary_tasks": None,
            "sqlite_db_filename": "workbench_temp_data.db",
            "csv_id_to_node_id_map_dir": tempfile.gettempdir(),
            "csv_id_to_node_id_map_filename": "csv_id_to_node_id_map.db",
            "fixity_algorithm": None,
            "validate_fixity_during_check": False,
            "output_csv_include_input_csv": False,
            "export_file_url_instead_of_download": False,
            "timestamp_rollback": False,
            "rollback_dir": None,
            "rollback_file_include_node_info": False,
            "enable_http_cache": True,
            "http_cache_storage": "memory",
            "http_cache_storage_expire_after": 1200,
            "http_max_retries": 3,
            "http_retry_on_status_codes": [500, 502, 503, 504],
            "http_backoff_factor": 1,
            "http_retry_allowed_methods": [
                "HEAD",
                "GET",
                "POST",
                "PUT",
                "PATCH",
                "DELETE",
            ],
            "validate_terms_exist": True,
            "validate_parent_node_exists": True,
            "media_types": self.get_media_types(),
            "preprocessors": {},
            "check": self.args.check,
            "get_csv_template": self.args.get_csv_template,
            "paged_content_sequence_separator": "-",
            "media_type_file_fields": self.get_media_fields(),
            "media_track_file_fields": self.get_media_track_file_fields(),
            "media_fields": self.get_media_fields(),
            "delete_media_by_node_media_use_tids": [],
            "export_csv_term_mode": "tid",
            "export_csv_file_path": None,
            "export_csv_field_list": [],
            "export_file_directory": None,
            "export_file_media_use_term_id": "http://pcdm.org/use#OriginalFile",
            "standalone_media_url": False,
            "require_entity_reference_views": True,
            "csv_start_row": 0,
            "csv_stop_row": None,
            "path_to_python": "python",
            "path_to_workbench_script": os.path.join(os.getcwd(), "workbench"),
            "oembed_providers": self.get_oembed_media_types(),
            "contact_sheet_output_dir": "contact_sheet_output",
            "contact_sheet_css_path": os.path.join(
                "assets", "contact_sheet", "contact-sheet.css"
            ),
            "page_title_template": "$parent_title, page $weight",
            "csv_headers": "names",
            "clean_csv_values_skip": [],
            "text_format_id": "basic_html",
            "ignore_existing_parent_ids": True,
            "query_csv_id_to_node_id_map_for_parents": False,
            "ignore_duplicate_parent_ids": True,
            "redirect_status_code": 301,
            "csv_value_templates": [],
            "csv_value_templates_for_paged_content": [],
            "csv_value_templates_rand_length": 5,
            "allow_csv_value_templates_if_field_empty": [],
            "remind_user_to_run_check": False,
            "completion_message": None,
            "media_type_by_media_use": False,
            "paged_content_ignore_files": ["Thumbs.db"],
            "include_password_in_rollback_config_file": False,
            "remove_password_from_config_file": False,
            "recovery_mode_starting_from_node_id": False,
            "viewer_override_fieldname": "field_viewer_override",
            "check_for_workbench_updates": False,
            "file_systems": ("public", "private"),
        }

    # Tests validity and existence of configuration file path.
    def path_check(self):
        # Check existence of configuration file.
        if not os.path.exists(self.args.config):
            # Since the main logger gets its log file location from this file, we
            # need to define a local logger to write to the default log file location,
            # 'workbench.log'.
            logging.basicConfig(
                filename="workbench.log",
                format="%(asctime)s - %(levelname)s - %(message)s",
                datefmt="%d-%b-%y %H:%M:%S",
            )
            message = 'Error: Configuration file "' + self.args.config + '" not found.'
            logging.error(message)
            sys.exit(message)

    # Validates config.
    def validate(self):
        error_messages = []
        type_check = issue_request(
            self.config,
            "GET",
            f"{self.config['host']}/entity/entity_form_display/node.{self.config['content_type']}.default?_format=json",
        )
        if type_check.status_code == 404:
            message = f"Content type {self.config['content_type']} does not exist on {self.config['host']}."
            error_messages.append(message)
        mutators = [
            "use_node_title_for_media",
            "use_nid_in_media_title",
            "field_for_media_title",
        ]
        selected = [mutator for mutator in mutators if self.config[mutator]]
        if len(selected) > 1:
            message = f"You may only select one of {mutators}.\n  - This config  has selected {selected}."
            error_messages.append(message)

        if error_messages:
            output = ""
            for error_message in error_messages:
                output += f"{error_message}\n"
            sys.exit("Error: " + output)

    # Convenience function for debugging - Prints config to console screen.
    def print_config(self):
        table = Table(title="Workbench Configuration")
        table.add_column("Parameter", justify="left")
        table.add_column("Value", justify="left")
        for key, value in self.config.items():
            table.add_row(key, str(value))
        console = Console()
        console.print(table)
