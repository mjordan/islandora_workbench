"""Classes for Drupal field operations.

   Support for additional field types should be added as new classes here,
   with accompanying tests in field_tests.py and field_tests_values.py.

   Note: If new field types are added to workbench_fields.py, corresponding logic must
   be added to functions in other Workbench modules (e.g. workbench_utils, workbench)
   that create, update, or export Drupal entities. Those places are commented in the
   code with either:

   # Assemble Drupal field structures from CSV data. If new field types are added to
   # workbench_fields.py, they need to be registered in the following if/elif/else block.

   or

   # Assemble CSV output Drupal field data. If new field types are added to
   # workbench_fields.py, they need to be registered in the following if/elif/else block.
"""

import json
from workbench_utils import *


class SimpleField:
    """Functions for handling fields with text and other "simple" Drupal field data types,
    e.g. fields that have a "{'value': 'xxx'}" structure such as plain text fields, ETDF
    fields. All functions return a "entity" dictionary that is passed to Requests' "json"
    parameter.

    Note that text fields that are "formatted" (i.e., use text formats/output filters)
    require a 'format' key in their JSON in addition to the 'value' key. Otherwise, markup
    or other text filters won't be applied when rendered.

    Note: this class assumes that the entity has the field identified in 'field_name'.
    Callers should pre-emptively confirm that. For an example, see code near the top
    of workbench.update().

    Also note: the required Drupal field 'title' is not processed by this class.
    """

    def create(self, config, field_definitions, entity, row, field_name):
        """Parameters
        ----------
         config : dict
             The configuration settings defined by workbench_config.get_config().
         field_definitions : dict
             The field definitions object defined by get_field_definitions().
         entity : dict
             The dict that will be POSTed to Drupal as JSON.
         row : OrderedDict.
             The current CSV record.
         field_name : string
             The Drupal fieldname/CSV column header.
         Returns
         -------
         dictionary
             A dictionary represeting the entity that is POSTed to Drupal as JSON.
        """
        if not row[field_name]:
            return entity

        if field_name in config["field_text_format_ids"]:
            text_format = config["field_text_format_ids"][field_name]
        else:
            text_format = config["text_format_id"]

        id_field = row.get(config.get("id_field", "not_applicable"), "not_applicable")
        field_values = []
        subvalues = str(row[field_name]).split(config["subdelimiter"])
        subvalues = self.remove_invalid_values(
            config, field_definitions, field_name, subvalues
        )
        subvalues = self.dedupe_values(subvalues)

        cardinality = int(field_definitions[field_name].get("cardinality", -1))
        if -1 < cardinality < len(subvalues):
            log_field_cardinality_violation(field_name, id_field, str(cardinality))
            subvalues = subvalues[:cardinality]
        for subvalue in subvalues:
            subvalue = truncate_csv_value(
                field_name, id_field, field_definitions[field_name], subvalue
            )
            if (
                "formatted_text" in field_definitions[field_name]
                and field_definitions[field_name]["formatted_text"] is True
            ):
                field_values.append({"value": subvalue, "format": text_format})
            else:
                if field_definitions[field_name][
                    "field_type"
                ] == "integer" and value_is_numeric(subvalue):
                    subvalue = int(subvalue)
                if field_definitions[field_name][
                    "field_type"
                ] == "float" and value_is_numeric(subvalue, allow_decimals=True):
                    subvalue = float(subvalue)
                field_values.append({"value": subvalue})
        field_values = self.dedupe_values(field_values)
        entity[field_name] = field_values

        return entity

    def update(
        self, config, field_definitions, entity, row, field_name, entity_field_values
    ):
        """Note: this method appends incoming CSV values to existing values, replaces existing field
        values with incoming values, or deletes all values from fields, depending on whether
        config['update_mode'] is 'append', 'replace', or 'delete'. It doesn not replace individual
        values within fields.
        """
        """Parameters
           ----------
            config : dict
                The configuration settings defined by workbench_config.get_config().
            field_definitions : dict
                The field definitions object defined by get_field_definitions().
            entity : dict
                The dict that will be POSTed to Drupal as JSON.
            row : OrderedDict.
                The current CSV record.
            field_name : string
                The Drupal fieldname/CSV column header.
            entity_field_values : list
                List of dictionaries containing existing value(s) for field_name in the entity being updated.
            Returns
            -------
            dictionary
                A dictionary represeting the entity that is PATCHed to Drupal as JSON.
        """
        if config["update_mode"] == "delete":
            entity[field_name] = []
            return entity

        if not row[field_name]:
            return entity

        if field_name not in entity:
            entity[field_name] = []

        if field_name in config["field_text_format_ids"]:
            text_format = config["field_text_format_ids"][field_name]
        else:
            text_format = config["text_format_id"]

        if config["task"] == "update_terms":
            entity_id_field = "term_id"
        if config["task"] == "update":
            entity_id_field = "node_id"
        if config["task"] == "update_media":
            entity_id_field = "media_id"

        cardinality = int(field_definitions[field_name].get("cardinality", -1))
        if config["update_mode"] == "append":
            subvalues = str(row[field_name]).split(config["subdelimiter"])
            subvalues = self.remove_invalid_values(
                config, field_definitions, field_name, subvalues
            )
            for subvalue in subvalues:
                subvalue = truncate_csv_value(
                    field_name,
                    row[entity_id_field],
                    field_definitions[field_name],
                    subvalue,
                )
                if (
                    "formatted_text" in field_definitions[field_name]
                    and field_definitions[field_name]["formatted_text"] is True
                ):
                    entity[field_name].append(
                        {"value": subvalue, "format": text_format}
                    )
                else:
                    if field_definitions[field_name][
                        "field_type"
                    ] == "integer" and value_is_numeric(subvalue):
                        subvalue = int(subvalue)
                    if field_definitions[field_name][
                        "field_type"
                    ] == "float" and value_is_numeric(subvalue, allow_decimals=True):
                        subvalue = float(subvalue)
                    entity[field_name].append({"value": subvalue})
            entity[field_name] = self.dedupe_values(entity[field_name])
            if -1 < cardinality < len(entity[field_name]):
                log_field_cardinality_violation(
                    field_name, row[entity_id_field], str(cardinality)
                )
                entity[field_name] = entity[field_name][:cardinality]
        if config["update_mode"] == "replace":
            field_values = []
            subvalues = str(row[field_name]).split(config["subdelimiter"])
            subvalues = self.remove_invalid_values(
                config, field_definitions, field_name, subvalues
            )
            subvalues = self.dedupe_values(subvalues)
            if -1 < cardinality < len(subvalues):
                log_field_cardinality_violation(
                    field_name, row[entity_id_field], str(cardinality)
                )
                subvalues = subvalues[:cardinality]
            for subvalue in subvalues:
                subvalue = truncate_csv_value(
                    field_name,
                    row[entity_id_field],
                    field_definitions[field_name],
                    subvalue,
                )
                if (
                    "formatted_text" in field_definitions[field_name]
                    and field_definitions[field_name]["formatted_text"] is True
                ):
                    field_values.append({"value": subvalue, "format": text_format})
                else:
                    if field_definitions[field_name][
                        "field_type"
                    ] == "integer" and value_is_numeric(subvalue):
                        subvalue = int(subvalue)
                    if field_definitions[field_name][
                        "field_type"
                    ] == "float" and value_is_numeric(subvalue, allow_decimals=True):
                        subvalue = float(subvalue)
                    field_values.append({"value": subvalue})
            field_values = self.dedupe_values(field_values)
            entity[field_name] = field_values

        return entity

    def dedupe_values(self, values):
        """Removes duplicate entries from 'values'."""
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
        return deduplicate_field_values(values)

    def remove_invalid_values(self, config, field_definitions, field_name, values):
        """Removes invalid entries from 'values'."""
        """Parameters
           ----------
            config : dict
                The configuration settings defined by workbench_config.get_config().
            field_definitions : dict
                The field definitions object defined by get_field_definitions().
            field_name : string
                The Drupal fieldname/CSV column header.
            values : list
                List containing strings split from CSV values.
            Returns
            -------
            list
                A list of valid field values.
        """
        if "field_type" not in field_definitions[field_name]:
            return values

        if field_definitions[field_name]["field_type"] == "edtf":
            valid_values = list()
            for subvalue in values:
                if validate_edtf_date(subvalue) is True:
                    valid_values.append(subvalue)
                else:
                    message = (
                        'Value "'
                        + subvalue
                        + '" in field "'
                        + field_name
                        + '" is not a valid EDTF field value.'
                    )
                    logging.warning(message)
            return valid_values
        elif field_definitions[field_name]["field_type"] == "integer":
            valid_values = list()
            for subvalue in values:
                if value_is_numeric(subvalue) is True:
                    valid_values.append(subvalue)
                else:
                    message = (
                        'Value "'
                        + subvalue
                        + '" in field "'
                        + field_name
                        + '" is not a valid integer field value.'
                    )
                    logging.warning(message)
            return valid_values
        elif field_definitions[field_name]["field_type"] in ["decimal", "float"]:
            valid_values = list()
            for subvalue in values:
                if value_is_numeric(subvalue, allow_decimals=True) is True:
                    valid_values.append(subvalue)
                else:
                    message = (
                        'Value "'
                        + subvalue
                        + '" in field "'
                        + field_name
                        + '" is not a valid '
                        + field_definitions[field_name]["field_type"]
                        + " field value."
                    )
                    logging.warning(message)
            return valid_values
        elif field_definitions[field_name]["field_type"] == "list_string":
            valid_values = list()
            for subvalue in values:
                if subvalue in field_definitions[field_name]["allowed_values"]:
                    valid_values.append(subvalue)
                else:
                    message = (
                        'Value "'
                        + subvalue
                        + '" in field "'
                        + field_name
                        + "\" is not in the field's list of allowed values."
                    )
                    logging.warning(message)
            return valid_values
        else:
            # For now, just return values if the field is not an EDTF field.
            return values

    def serialize(self, config, field_definitions, field_name, field_data):
        """Serialized values into a format consistent with Workbench's CSV-field input format."""
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
                A string structured same as the Workbench CSV field data for this field type,
                or None if there is nothing to return.
        """
        if "field_type" not in field_definitions[field_name]:
            return None

        subvalues = list()
        for subvalue in field_data:
            if "value" in subvalue:
                subvalues.append(subvalue["value"])
            else:
                logging.warning(
                    "Field data "
                    + str(field_data)
                    + ' in field "'
                    + field_name
                    + '" cannot be serialized by the SimpleField handler.'
                )
                return ""

        if len(subvalues) > 1:
            return config["subdelimiter"].join(subvalues)
        elif len(subvalues) == 0:
            return None
        else:
            return subvalues[0]


class GeolocationField:
    """Functions for handling fields with 'geolocation' Drupal field data type.
    All functions return a "entity" dictionary that is passed to Requests'
    "json" parameter.

    Note: this class assumes that the entity has the field identified in 'field_name'.
    Callers should pre-emptively confirm that. For an example, see code near the top
    of workbench.update().
    """

    def create(self, config, field_definitions, entity, row, field_name):
        """Parameters
        ----------
         config : dict
             The configuration settings defined by workbench_config.get_config().
         field_definitions : dict
             The field definitions object defined by get_field_definitions().
         entity : dict
             The dict that will be POSTed to Drupal as JSON.
         row : OrderedDict.
             The current CSV record.
         field_name : string
             The Drupal fieldname/CSV column header.
         Returns
         -------
         dictionary
             A dictionary represeting the entity that is POSTed to Drupal as JSON.
        """
        if not row[field_name]:
            return entity

        id_field = row.get(config.get("id_field", "not_applicable"), "not_applicable")
        subvalues = split_geolocation_string(config, row[field_name])
        subvalues = self.dedupe_values(subvalues)

        cardinality = int(field_definitions[field_name].get("cardinality", -1))
        if -1 < cardinality < len(subvalues):
            subvalues = subvalues[:cardinality]
            log_field_cardinality_violation(
                field_name,
                id_field,
                cardinality,
            )
        entity[field_name] = subvalues

        return entity

    def update(
        self, config, field_definitions, entity, row, field_name, entity_field_values
    ):
        """Note: this method appends incoming CSV values to existing values, replaces existing field
        values with incoming values, or deletes all values from fields, depending on whether
        config['update_mode'] is 'append', 'replace', or 'delete'. It doesn not replace individual
        values within fields.
        """
        """Parameters
           ----------
            config : dict
                The configuration settings defined by workbench_config.get_config().
            field_definitions : dict
                The field definitions object defined by get_field_definitions().
            entity : dict
                The dict that will be POSTed to Drupal as JSON.
            row : OrderedDict.
                The current CSV record.
            field_name : string
                The Drupal fieldname/CSV column header.
            entity_field_values : list
                List of dictionaries containing existing value(s) for field_name in the entity being updated.
            Returns
            -------
            dictionary
                A dictionary represeting the entity that is PATCHed to Drupal as JSON.
        """
        if config["update_mode"] == "delete":
            entity[field_name] = []
            return entity

        if not row[field_name]:
            return entity

        if field_name not in entity:
            entity[field_name] = []

        if config["task"] == "update_terms":
            entity_id_field = "term_id"
        if config["task"] == "update":
            entity_id_field = "node_id"
        if config["task"] == "update_media":
            entity_id_field = "media_id"

        cardinality = int(field_definitions[field_name].get("cardinality", -1))
        if config["update_mode"] == "replace":
            subvalues = split_geolocation_string(config, row[field_name])
            subvalues = self.dedupe_values(subvalues)
            field_values = []
            for subvalue in subvalues:
                field_values.append(subvalue)
            if -1 < cardinality < len(field_values):
                log_field_cardinality_violation(
                    field_name, row[entity_id_field], str(cardinality)
                )
                field_values = field_values[:cardinality]
            entity[field_name] = field_values

        if config["update_mode"] == "append":
            subvalues = split_geolocation_string(config, row[field_name])
            subvalues = self.dedupe_values(subvalues)
            for subvalue in subvalues:
                entity_field_values.append(subvalue)
            if -1 < cardinality < len(entity_field_values):
                entity_field_values = entity_field_values[:cardinality]
                log_field_cardinality_violation(
                    field_name, row[entity_id_field], str(cardinality)
                )
            entity[field_name] = entity_field_values

        entity[field_name] = self.dedupe_values(entity[field_name])
        return entity

    def dedupe_values(self, values):
        """Removes duplicate entries from 'values'."""
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
        return deduplicate_field_values(values)

    def remove_invalid_values(self, config, field_definitions, field_name, values):
        """Removes invalid entries from 'values'."""
        """Parameters
           ----------
            config : dict
                The configuration settings defined by workbench_config.get_config().
            field_definitions : dict
                The field definitions object defined by get_field_definitions().
            field_name : string
                The Drupal fieldname/CSV column header.
            values : list
                List containing strings split from CSV values.
            Returns
            -------
            list
                A list of valid field values.
        """
        valid_values = list()
        for subvalue in values:
            if validate_latlong_value(subvalue) is True:
                valid_values.append(subvalue)
            else:
                message = (
                    'Value "'
                    + subvalue
                    + '" in field "'
                    + field_name
                    + '" is not a valid Geolocation field value.'
                )
                logging.warning(message)
        return valid_values

    def serialize(self, config, field_definitions, field_name, field_data):
        """Serialized values into a format consistent with Workbench's CSV-field input format."""
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
                A string structured same as the Workbench CSV field data for this field type,
                or None if there is nothing to return.
        """
        if "field_type" not in field_definitions[field_name]:
            return None

        subvalues = list()
        for subvalue in field_data:
            subvalues.append(str(subvalue["lat"]) + "," + str(subvalue["lng"]))

        if len(subvalues) > 1:
            return config["subdelimiter"].join(subvalues)
        elif len(subvalues) == 0:
            return None
        else:
            return subvalues[0]


class LinkField:
    """Functions for handling fields with 'link' Drupal field data type.
    All functions return a "entity" dictionary that is passed to Requests'
    "json" parameter.

    Note: this class assumes that the entity has the field identified in 'field_name'.
    Callers should pre-emptively confirm that. For an example, see code near the top
    of workbench.update().
    """

    def create(self, config, field_definitions, entity, row, field_name):
        """Parameters
        ----------
         config : dict
             The configuration settings defined by workbench_config.get_config().
         field_definitions : dict
             The field definitions object defined by get_field_definitions().
         entity : dict
             The dict that will be POSTed to Drupal as JSON.
         row : OrderedDict.
             The current CSV record.
         field_name : string
             The Drupal fieldname/CSV column header.
         Returns
         -------
         dictionary
             A dictionary represeting the entity that is POSTed to Drupal as JSON.
        """
        if not row[field_name]:
            return entity

        id_field = row.get(config.get("id_field", "not_applicable"), "not_applicable")

        subvalues = split_link_string(config, row[field_name])
        subvalues = self.dedupe_values(subvalues)

        cardinality = int(field_definitions[field_name].get("cardinality", -1))
        if -1 < cardinality < len(subvalues):
            subvalues = subvalues[:cardinality]
            log_field_cardinality_violation(
                field_name,
                id_field,
                cardinality,
            )
        entity[field_name] = subvalues

        return entity

    def update(
        self, config, field_definitions, entity, row, field_name, entity_field_values
    ):
        """Note: this method appends incoming CSV values to existing values, replaces existing field
        values with incoming values, or deletes all values from fields, depending on whether
        config['update_mode'] is 'append', 'replace', or 'delete'. It doesn not replace individual
        values within fields.
        """
        """Parameters
           ----------
            config : dict
                The configuration settings defined by workbench_config.get_config().
            field_definitions : dict
                The field definitions object defined by get_field_definitions().
            entity : dict
                The dict that will be POSTed to Drupal as JSON.
            row : OrderedDict.
                The current CSV record.
            field_name : string
                The Drupal fieldname/CSV column header.
            entity_field_values : list
                List of dictionaries containing existing value(s) for field_name in the entity being updated.
            Returns
            -------
            dictionary
                A dictionary represeting the entity that is PATCHed to Drupal as JSON.
        """
        if config["update_mode"] == "delete":
            entity[field_name] = []
            return entity

        if not row[field_name]:
            return entity

        if field_name not in entity:
            entity[field_name] = []

        if config["task"] == "update_terms":
            entity_id_field = "term_id"
        if config["task"] == "update":
            entity_id_field = "node_id"
        if config["task"] == "update_media":
            entity_id_field = "media_id"

        cardinality = int(field_definitions[field_name].get("cardinality", -1))
        if config["update_mode"] == "replace":
            field_values = []
            subvalues = split_link_string(config, row[field_name])
            subvalues = self.dedupe_values(subvalues)
            if -1 < cardinality < len(subvalues):
                log_field_cardinality_violation(
                    field_name, row[entity_id_field], str(cardinality)
                )
                subvalues = subvalues[:cardinality]
            for subvalue in subvalues:
                field_values.append(subvalue)
            entity[field_name] = field_values
        if config["update_mode"] == "append":
            subvalues = split_link_string(config, row[field_name])
            subvalues = self.dedupe_values(subvalues)
            for subvalue in subvalues:
                entity_field_values.append(subvalue)
            if -1 < cardinality < len(entity_field_values):
                entity_field_values = entity_field_values[:cardinality]
                log_field_cardinality_violation(
                    field_name, row[entity_id_field], str(cardinality)
                )
            entity[field_name] = entity_field_values

        return entity

    def dedupe_values(self, values):
        """Removes duplicate entries from 'values'."""
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
        return deduplicate_field_values(values)

    def remove_invalid_values(self, config, field_definitions, field_name, values):
        """Removes invalid entries from 'values'."""
        """Parameters
           ----------
            config : dict
                The configuration settings defined by workbench_config.get_config().
            field_definitions : dict
                The field definitions object defined by get_field_definitions().
            field_name : string
                The Drupal fieldname/CSV column header.
            values : list
                List containing strings split from CSV values.
            Returns
            -------
            list
                A list of valid field values.
        """
        valid_values = list()
        for subvalue in values:
            if validate_link_value(subvalue) is True:
                valid_values.append(subvalue)
            else:
                message = (
                    'Value "'
                    + subvalue
                    + '" in field "'
                    + field_name
                    + '" is not a valid Link field value.'
                )
                logging.warning(message)
        return valid_values

    def serialize(self, config, field_definitions, field_name, field_data):
        """Serialized values into a format consistent with Workbench's CSV-field input format."""
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
                A string structured same as the Workbench CSV field data for this field type.
                or None if there is nothing to return.
        """
        if "field_type" not in field_definitions[field_name]:
            return None

        subvalues = list()
        for subvalue in field_data:
            if (
                "title" in subvalue
                and subvalue["title"] is not None
                and subvalue["title"] != ""
            ):
                subvalues.append(subvalue["uri"] + "%%" + subvalue["title"])
            else:
                subvalues.append(subvalue["uri"])

        if len(subvalues) > 1:
            return config["subdelimiter"].join(subvalues)
        elif len(subvalues) == 0:
            return None
        else:
            return subvalues[0]


class EntityReferenceField:
    """Functions for handling fields with 'entity_reference' Drupal field data type.
    All functions return a "entity" dictionary that is passed to Requests' "json"
    parameter.

    Note: this class assumes that the entity has the field identified in 'field_name'.
    Callers should pre-emptively confirm that. For an example, see code near the top
    of workbench.update().
    """

    def create(self, config, field_definitions, entity, row, field_name):
        """Parameters
        ----------
         config : dict
             The configuration settings defined by workbench_config.get_config().
         field_definitions : dict
             The field definitions object defined by get_field_definitions().
         entity : dict
             The dict that will be POSTed to Drupal as JSON.
         row : OrderedDict.
             The current CSV record.
         field_name : string
             The Drupal fieldname/CSV column header.
         Returns
         -------
         dictionary
             A dictionary represeting the entity that is POSTed to Drupal as JSON.
        """
        if not row[field_name]:
            return entity

        id_field = row.get(config.get("id_field", "not_applicable"), "not_applicable")
        if field_definitions[field_name]["target_type"] == "taxonomy_term":
            target_type = "taxonomy_term"
            field_vocabs = get_field_vocabularies(config, field_definitions, field_name)
            prepared_tids = []
            delimited_values = str(row[field_name]).split(config["subdelimiter"])
            for delimited_value in delimited_values:
                tid = prepare_term_id(config, field_vocabs, field_name, delimited_value)
                if value_is_numeric(tid):
                    tid = str(tid)
                    prepared_tids.append(tid)
                else:
                    continue
            row[field_name] = config["subdelimiter"].join(prepared_tids)

        if field_definitions[field_name]["target_type"] == "node":
            target_type = "node_type"

        if field_definitions[field_name]["target_type"] == "media":
            target_type = "media_type"

        if field_definitions[field_name]["target_type"] == "domain":
            target_type = "domain"

        field_values = []
        subvalues = str(row[field_name]).split(config["subdelimiter"])
        subvalues = self.dedupe_values(subvalues)
        for subvalue in subvalues:
            subvalue = str(subvalue)
            field_values.append({"target_id": subvalue, "target_type": target_type})

        cardinality = int(field_definitions[field_name].get("cardinality", -1))
        if -1 < cardinality < len(field_values):
            entity[field_name] = field_values[:cardinality]
            log_field_cardinality_violation(field_name, id_field, str(cardinality))
        else:
            entity[field_name] = field_values

        return entity

    def update(
        self, config, field_definitions, entity, row, field_name, entity_field_values
    ):
        """Note: this method appends incoming CSV values to existing values, replaces existing field
        values with incoming values, or deletes all values from fields, depending on whether
        config['update_mode'] is 'append', 'replace', or 'delete'. It doesn not replace individual
        values within fields.
        """
        """Parameters
           ----------
            config : dict
                The configuration settings defined by workbench_config.get_config().
            field_definitions : dict
                The field definitions object defined by get_field_definitions().
            entity : dict
                The dict that will be POSTed to Drupal as JSON.
            row : OrderedDict.
                The current CSV record.
            field_name : string
                The Drupal fieldname/CSV column header.
            entity_field_values : list
                List of dictionaries containing existing value(s) for field_name in the entity being updated.
            Returns
            -------
            dictionary
                A dictionary represeting the entity that is PATCHed to Drupal as JSON.
        """
        if config["update_mode"] == "delete":
            entity[field_name] = []
            return entity

        if not row[field_name]:
            return entity

        if field_name not in entity:
            entity[field_name] = []

        if config["task"] == "update_terms":
            entity_id_field = "term_id"
        if config["task"] == "update":
            entity_id_field = "node_id"
        if config["task"] == "update_media":
            entity_id_field = "media_id"

        if field_definitions[field_name]["target_type"] == "taxonomy_term":
            target_type = "taxonomy_term"
            field_vocabs = get_field_vocabularies(config, field_definitions, field_name)
            prepared_tids = []
            delimited_values = str(row[field_name]).split(config["subdelimiter"])
            for delimited_value in delimited_values:
                tid = prepare_term_id(config, field_vocabs, field_name, delimited_value)
                if value_is_numeric(tid):
                    tid = str(tid)
                    prepared_tids.append(tid)
                else:
                    continue
            row[field_name] = config["subdelimiter"].join(prepared_tids)

        if field_definitions[field_name]["target_type"] == "node":
            target_type = "node_type"

        if field_definitions[field_name]["target_type"] == "media":
            target_type = "media_type"

        if field_definitions[field_name]["target_type"] == "domain":
            target_type = "domain"

        cardinality = int(field_definitions[field_name].get("cardinality", -1))
        if config["update_mode"] == "replace":
            field_values = []
            subvalues = str(row[field_name]).split(config["subdelimiter"])
            subvalues = self.dedupe_values(subvalues)
            for subvalue in subvalues:
                field_values.append(
                    {"target_id": str(subvalue), "target_type": target_type}
                )
            if -1 < cardinality < len(field_values):
                entity[field_name] = field_values[:cardinality]
                log_field_cardinality_violation(
                    field_name, row[entity_id_field], str(cardinality)
                )
            else:
                entity[field_name] = field_values

        if config["update_mode"] == "append":
            subvalues = str(row[field_name]).split(config["subdelimiter"])
            for subvalue in subvalues:
                entity_field_values.append(
                    {"target_id": str(subvalue), "target_type": target_type}
                )
            entity_field_values = self.dedupe_values(entity_field_values)
            if -1 < cardinality < len(entity_field_values):
                entity[field_name] = entity_field_values[:cardinality]
                log_field_cardinality_violation(
                    field_name, row[entity_id_field], str(cardinality)
                )
            else:
                entity[field_name] = entity_field_values

        return entity

    def dedupe_values(self, values):
        """Removes duplicate entries from 'values'."""
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
        return deduplicate_field_values(values)

    def remove_invalid_values(self, config, field_definitions, field_name, values):
        """Removes invalid entries from 'values'."""
        """Parameters
           ----------
            config : dict
                The configuration settings defined by workbench_config.get_config().
            field_definitions : dict
                The field definitions object defined by get_field_definitions().
            field_name : string
                The Drupal fieldname/CSV column header.
            values : list
                List containing strings split from CSV values.
            Returns
            -------
            list
                A list of valid field values.
        """
        """
        valid_values = list()
        for subvalue in values:
            if validate_link_value(subvalue) is True:
                valid_values.append(subvalue)
            else:
                message = 'Value "' + subvalue + '" in field "' + field_name + '" is not a valid Entity Reference field value.'
                logging.warning(message)
        return valid_values
        """
        return values

    def serialize(self, config, field_definitions, field_name, field_data):
        """Serialized values into a format consistent with Workbench's CSV-field input format."""
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
                A string structured same as the Workbench CSV field data for this field type,
                or None if there is nothing to return.
        """
        if "field_type" not in field_definitions[field_name]:
            return None

        subvalues = list()
        for subvalue in field_data:
            if (
                config["export_csv_term_mode"] == "name"
                and subvalue["target_type"] == "taxonomy_term"
            ):
                # Output term names, with vocab IDs (aka namespaces).
                vocab_id = get_term_vocab(config, subvalue["target_id"])
                term_name = get_term_name(config, subvalue["target_id"])
                if vocab_id is not False and term_name is not False:
                    subvalues.append(vocab_id + ":" + term_name)
            else:
                # Output term IDs.
                if ping_term(config, subvalue["target_id"]) is True:
                    subvalues.append(str(subvalue["target_id"]))

        if len(subvalues) > 1:
            return config["subdelimiter"].join(subvalues)
        elif len(subvalues) == 0:
            return None
        else:
            return subvalues[0]


class TypedRelationField:
    """Functions for handling fields with 'typed_relation' Drupal field data type.
    All functions return a "entity" dictionary that is passed to Requests' "json"
    parameter.

    Currently this field type only supports Typed Relation Taxonomies (not other
    Typed Relation entity types).

    Note: this class assumes that the entity has the field identified in 'field_name'.
    Callers should pre-emptively confirm that. For an example, see code near the top
    of workbench.update().
    """

    def create(self, config, field_definitions, entity, row, field_name):
        """Parameters
        ----------
         config : dict
             The configuration settings defined by workbench_config.get_config().
         field_definitions : dict
             The field definitions object defined by get_field_definitions().
         entity : dict
             The dict that will be POSTed to Drupal as JSON.
         row : OrderedDict.
             The current CSV record.
         field_name : string
             The Drupal fieldname/CSV column header.
         Returns
         -------
         dictionary
             A dictionary represeting the entity that is POSTed to Drupal as JSON.
        """
        if not row[field_name]:
            return entity

        id_field = row.get(config.get("id_field", "not_applicable"), "not_applicable")
        # Currently only supports Typed Relation taxonomy entities.
        if field_definitions[field_name]["target_type"] == "taxonomy_term":
            target_type = "taxonomy_term"
            field_vocabs = get_field_vocabularies(config, field_definitions, field_name)
            field_values = []
            subvalues = split_typed_relation_string(
                config, row[field_name], target_type
            )
            subvalues = self.dedupe_values(subvalues)
            cardinality = int(field_definitions[field_name].get("cardinality", -1))
            if -1 < cardinality < len(subvalues):
                log_field_cardinality_violation(field_name, id_field, str(cardinality))
                subvalues = subvalues[:cardinality]
            for subvalue in subvalues:
                subvalue["target_id"] = prepare_term_id(
                    config, field_vocabs, field_name, subvalue["target_id"]
                )
                field_values.append(subvalue)
            entity[field_name] = field_values

        return entity

    def update(
        self, config, field_definitions, entity, row, field_name, entity_field_values
    ):
        """Note: this method appends incoming CSV values to existing values, replaces existing field
        values with incoming values, or deletes all values from fields, depending on whether
        config['update_mode'] is 'append', 'replace', or 'delete'. It doesn not replace individual
        values within fields.
        """
        """Parameters
           ----------
            config : dict
                The configuration settings defined by workbench_config.get_config().
            field_definitions : dict
                The field definitions object defined by get_field_definitions().
            entity : dict
                The dict that will be POSTed to Drupal as JSON.
            row : OrderedDict.
                The current CSV record.
            field_name : string
                The Drupal fieldname/CSV column header.
            entity_field_values : list
                List of dictionaries containing existing value(s) for field_name in the entity being updated.
            Returns
            -------
            dictionary
                A dictionary represeting the entity that is PATCHed to Drupal as JSON.
        """
        if config["update_mode"] == "delete":
            entity[field_name] = []
            return entity

        if not row[field_name]:
            return entity

        if field_name not in entity:
            entity[field_name] = []

        if config["task"] == "update_terms":
            entity_id_field = "term_id"
        if config["task"] == "update":
            entity_id_field = "node_id"
        if config["task"] == "update_media":
            entity_id_field = "media_id"

        # Currently only supports Typed Relation taxonomy entities.
        if field_definitions[field_name]["target_type"] == "taxonomy_term":
            target_type = "taxonomy_term"
            field_vocabs = get_field_vocabularies(config, field_definitions, field_name)

        cardinality = int(field_definitions[field_name].get("cardinality", -1))
        if config["update_mode"] == "replace":
            subvalues = split_typed_relation_string(
                config, row[field_name], target_type
            )
            subvalues = self.dedupe_values(subvalues)
            field_values = []
            for subvalue in subvalues:
                subvalue["target_id"] = prepare_term_id(
                    config, field_vocabs, field_name, subvalue["target_id"]
                )
                field_values.append(subvalue)
            if -1 < cardinality < len(field_values):
                field_values = field_values[:cardinality]
                log_field_cardinality_violation(
                    field_name, row[entity_id_field], str(cardinality)
                )
            entity[field_name] = field_values
        if config["update_mode"] == "append":
            field_values = []
            subvalues = split_typed_relation_string(
                config, row[field_name], target_type
            )
            for subvalue in subvalues:
                subvalue["target_id"] = prepare_term_id(
                    config, field_vocabs, field_name, subvalue["target_id"]
                )
                entity_field_values.append(subvalue)
            entity_field_values = self.dedupe_values(entity_field_values)
            if -1 < cardinality < len(entity_field_values):
                entity[field_name] = entity_field_values[:cardinality]
                log_field_cardinality_violation(
                    field_name, row[entity_id_field], str(cardinality)
                )
            else:
                entity[field_name] = entity_field_values

        return entity

    def dedupe_values(self, values):
        """Removes duplicate entries from 'values'."""
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
        return deduplicate_field_values(values)

    def remove_invalid_values(self, config, field_definitions, field_name, values):
        """Removes invalid entries from 'values'."""
        """Parameters
           ----------
            config : dict
                The configuration settings defined by workbench_config.get_config().
            field_definitions : dict
                The field definitions object defined by get_field_definitions().
            field_name : string
                The Drupal fieldname/CSV column header.
            values : list
                List containing strings split from CSV values.
            Returns
            -------
            list
                A list of valid field values.
        """
        """
        valid_values = list()
        for subvalue in values:
            if validate_link_value(subvalue) is True:
                valid_values.append(subvalue)
            else:
                message = 'Value "' + subvalue + '" in field "' + field_name + '" is not a valid Typed Relation field value.'
                logging.warning(message)
        return valid_values
        """
        return values

    def serialize(self, config, field_definitions, field_name, field_data):
        """Serialized values into a format consistent with Workbench's CSV-field input format."""
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
                A string structured same as the Workbench CSV field data for this field type,
                or None if there is nothing to return.
        """
        if "field_type" not in field_definitions[field_name]:
            return None

        subvalues = list()
        for subvalue in field_data:
            if config["export_csv_term_mode"] == "name":
                vocab_id = get_term_vocab(config, subvalue["target_id"])
                term_name = get_term_name(config, subvalue["target_id"])
                subvalues.append(
                    str(subvalue["rel_type"]) + ":" + vocab_id + ":" + term_name
                )
            else:
                # Term IDs.
                subvalues.append(
                    str(subvalue["rel_type"]) + ":" + str(subvalue["target_id"])
                )

        if len(subvalues) > 1:
            return config["subdelimiter"].join(subvalues)
        elif len(subvalues) == 0:
            return None
        else:
            return subvalues[0]


class AuthorityLinkField:
    """Functions for handling fields with 'authority_link' Drupal field data type.
    All functions return a "entity" dictionary that is passed to Requests' "json"
    parameter.

    Note: this class assumes that the entity has the field identified in 'field_name'.
    Callers should pre-emptively confirm that. For an example, see code near the top
    of workbench.update().
    """

    def create(self, config, field_definitions, entity, row, field_name):
        """Parameters
        ----------
         config : dict
             The configuration settings defined by workbench_config.get_config().
         field_definitions : dict
             The field definitions object defined by get_field_definitions().
         entity : dict
             The dict that will be POSTed to Drupal as JSON.
         row : OrderedDict.
             The current CSV record.
         field_name : string
             The Drupal fieldname/CSV column header.
         Returns
         -------
         dictionary
             A dictionary represeting the entity that is POSTed to Drupal as JSON.
        """
        if not row[field_name]:
            return entity

        id_field = row.get(config.get("id_field", "not_applicable"), "not_applicable")
        subvalues = split_authority_link_string(config, row[field_name])
        subvalues = self.dedupe_values(subvalues)

        cardinality = int(field_definitions[field_name].get("cardinality", -1))
        if -1 < cardinality < len(subvalues):
            subvalues = subvalues[:cardinality]
            log_field_cardinality_violation(field_name, id_field, str(cardinality))
        entity[field_name] = subvalues

        return entity

    def update(
        self, config, field_definitions, entity, row, field_name, entity_field_values
    ):
        """Note: this method appends incoming CSV values to existing values, replaces existing field
        values with incoming values, or deletes all values from fields, depending on whether
        config['update_mode'] is 'append', 'replace', or 'delete'. It doesn not replace individual
        values within fields.
        """
        """Parameters
           ----------
            config : dict
                The configuration settings defined by workbench_config.get_config().
            field_definitions : dict
                The field definitions object defined by get_field_definitions().
            entity : dict
                The dict that will be POSTed to Drupal as JSON.
            row : OrderedDict.
                The current CSV record.
            field_name : string
                The Drupal fieldname/CSV column header.
            entity_field_values : list
                List of dictionaries containing existing value(s) for field_name in the entity being updated.
            Returns
            -------
            dictionary
                A dictionary represeting the entity that is PATCHed to Drupal as JSON.
        """
        if config["update_mode"] == "delete":
            entity[field_name] = []
            return entity

        if not row[field_name]:
            return entity

        if field_name not in entity:
            entity[field_name] = []

        if config["task"] == "update_terms":
            entity_id_field = "term_id"
        if config["task"] == "update":
            entity_id_field = "node_id"
        if config["task"] == "update_media":
            entity_id_field = "media_id"

        cardinality = int(field_definitions[field_name].get("cardinality", -1))
        if config["update_mode"] == "replace":
            field_values = []
            subvalues = split_authority_link_string(config, row[field_name])
            subvalues = self.dedupe_values(subvalues)
            if -1 < cardinality < len(subvalues):
                log_field_cardinality_violation(
                    field_name, row[entity_id_field], str(cardinality)
                )
                subvalues = subvalues[:cardinality]
            for subvalue in subvalues:
                field_values.append(subvalue)
            entity[field_name] = field_values
        if config["update_mode"] == "append":
            subvalues = split_authority_link_string(config, row[field_name])
            for subvalue in subvalues:
                entity_field_values.append(subvalue)
            if -1 < cardinality < len(entity_field_values):
                log_field_cardinality_violation(
                    field_name, row[entity_id_field], str(cardinality)
                )
                entity[field_name] = entity_field_values[:cardinality]
            else:
                entity[field_name] = entity_field_values

        return entity

    def dedupe_values(self, values):
        """Removes duplicate entries from 'values'."""
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
        return deduplicate_field_values(values)

    def remove_invalid_values(self, config, field_definitions, field_name, values):
        """Removes invalid entries from 'values'."""
        """Parameters
           ----------
            config : dict
                The configuration settings defined by workbench_config.get_config().
            field_definitions : dict
                The field definitions object defined by get_field_definitions().
            field_name : string
                The Drupal fieldname/CSV column header.
            values : list
                List containing strings split from CSV values.
            Returns
            -------
            list
                A list of valid field values.
        """
        valid_values = list()
        for subvalue in values:
            if (
                validate_authority_link_value(
                    subvalue, field_definitions[field_name]["authority_sources"]
                )
                is True
            ):
                valid_values.append(subvalue)
            else:
                message = (
                    'Value "'
                    + subvalue
                    + '" in field "'
                    + field_name
                    + '" is not a valid Authority Link field value.'
                )
                logging.warning(message)
        return valid_values

    def serialize(self, config, field_definitions, field_name, field_data):
        """Serialized values into a format consistent with Workbench's CSV-field input format."""
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
                A string structured same as the Workbench CSV field data for this field type,
                or None if there is nothing to return.
        """
        if "field_type" not in field_definitions[field_name]:
            return None

        subvalues = list()
        for subvalue in field_data:
            if "title" in subvalue and subvalue["title"] is not None:
                subvalues.append(
                    subvalue["source"]
                    + "%%"
                    + subvalue["uri"]
                    + "%%"
                    + subvalue["title"]
                )
            else:
                subvalues.append(subvalue["source"] + "%%" + subvalue["uri"])

        if len(subvalues) > 1:
            return config["subdelimiter"].join(subvalues)
        elif len(subvalues) == 0:
            return None
        else:
            return subvalues[0]


class MediaTrackField:
    """Functions for handling fields with "media_track" Drupal (Islandora) field data type.
    All functions return a "entity" dictionary that is passed to Requests' "json"
    parameter.

    Note: this class assumes that the entity has the field identified in "field_name".
    Callers should pre-emptively confirm that. For an example, see code near the top
    of workbench.update().
    """

    def create(self, config, field_definitions, entity, row, field_name):
        """Parameters
        ----------
         config : dict
             The configuration settings defined by workbench_config.get_config().
         field_definitions : dict
             The field definitions object defined by get_field_definitions().
         entity : dict
             The dict that will be POSTed to Drupal as JSON.
         row : OrderedDict.
             The current CSV record.
         field_name : string
             The Drupal fieldname/CSV column header.
         Returns
         -------
         dictionary
             A dictionary represeting the entity that is POSTed to Drupal as JSON.
        """
        if not row[field_name]:
            return entity

        id_field = row.get(config.get("id_field", "not_applicable"), "not_applicable")
        subvalues = split_media_track_string(config, row[field_name])
        subvalues = self.dedupe_values(subvalues)
        cardinality = int(field_definitions[field_name].get("cardinality", -1))
        if -1 < cardinality < len(subvalues):
            subvalues = subvalues[:cardinality]
            log_field_cardinality_violation(
                field_name,
                id_field,
                cardinality,
            )
        entity[field_name] = subvalues

        return entity

    def update(
        self, config, field_definitions, entity, row, field_name, entity_field_values
    ):
        """Note: this method appends incoming CSV values to existing values, replaces existing field
        values with incoming values, or deletes all values from fields, depending on whether
        config['update_mode'] is 'append', 'replace', or 'delete'. It doesn not replace individual
        values within fields.
        """
        """Parameters
           ----------
            config : dict
                The configuration settings defined by workbench_config.get_config().
            field_definitions : dict
                The field definitions object defined by get_field_definitions().
            entity : dict
                The dict that will be POSTed to Drupal as JSON.
            row : OrderedDict.
                The current CSV record.
            field_name : string
                The Drupal fieldname/CSV column header.
            entity_field_values : list
                List of dictionaries containing existing value(s) for field_name in the entity being updated.
            Returns
            -------
            dictionary
                A dictionary represeting the entity that is PATCHed to Drupal as JSON.
        """
        if config["update_mode"] == "delete":
            entity[field_name] = []
            return entity

        if not row[field_name]:
            return entity

        if field_name not in entity:
            entity[field_name] = []

        cardinality = int(field_definitions[field_name].get("cardinality", -1))
        if config["update_mode"] == "replace":
            field_values = []
            subvalues = split_media_track_string(config, row[field_name])
            subvalues = self.dedupe_values(subvalues)
            if -1 < cardinality < len(subvalues):
                log_field_cardinality_violation(
                    field_name, row["node_id"], str(cardinality)
                )
                subvalues = subvalues[:cardinality]
            for subvalue in subvalues:
                field_values.append(subvalue)
            entity[field_name] = field_values
        if config["update_mode"] == "append":
            subvalues = split_media_track_string(config, row[field_name])
            for subvalue in subvalues:
                entity_field_values.append(subvalue)
            if -1 < cardinality < len(entity_field_values):
                entity[field_name] = entity_field_values[:cardinality]
                log_field_cardinality_violation(
                    field_name, row["node_id"], str(cardinality)
                )
            else:
                entity[field_name] = entity_field_values
        return entity

    def dedupe_values(self, values):
        """Removes duplicate entries from 'values'."""
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
        return deduplicate_field_values(values)

    def remove_invalid_values(self, config, field_definitions, field_name, values):
        """Removes invalid entries from 'values'."""
        """Parameters
           ----------
            config : dict
                The configuration settings defined by workbench_config.get_config().
            field_definitions : dict
                The field definitions object defined by get_field_definitions().
            field_name : string
                The Drupal fieldname/CSV column header.
            values : list
                List containing strings split from CSV values.
            Returns
            -------
            list
                A list of valid field values.
        """
        valid_values = list()
        for subvalue in values:
            if (
                validate_media_track_value(
                    subvalue, field_definitions[field_name]["authority_sources"]
                )
                is True
            ):
                valid_values.append(subvalue)
            else:
                message = (
                    'Value "'
                    + subvalue
                    + '" in field "'
                    + field_name
                    + '" is not a valid Authority Link field value.'
                )
                logging.warning(message)
        return valid_values

    def serialize(self, config, field_definitions, field_name, field_data):
        """Serialized values into a format consistent with Workbench's CSV-field input format."""
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
                A string structured same as the Workbench CSV field data for this field type,
                or None if there is nothing to return.
        """
        if "field_type" not in field_definitions[field_name]:
            return None

        subvalues = list()
        for subvalue in field_data:
            if all(
                "label" in subvalue,
                subvalue["label"] is not None,
                "kind" in subvalue,
                subvalue["kind"] is not None,
                "srclang" in subvalue,
                subvalue["srclang"] is not None,
                "url" in subvalue,
                subvalue["url"] is not None,
            ):
                serialized = f"{subvalue['label']}:{subvalue['kind']}:{subvalue['srclang']}:{os.path.basename(subvalue['url'])}"
                subvalues.append(serialized)
            else:
                subvalues.append(
                    f"{subvalue['label']}:{subvalue['kind']}:{subvalue['srclang']}:{os.path.basename(subvalue['url'])}"
                )

        if len(subvalues) > 1:
            return config["subdelimiter"].join(subvalues)
        elif len(subvalues) == 0:
            return None
        else:
            return subvalues[0]


class EntityReferenceRevisionsField:
    """Functions for handling fields with 'entity_reference_revisions' Drupal field
    data type. This field *can* reference nodes, taxonomy terms, and media, but
    workbench only supports paragraphs for now.

    All functions return a "entity" dictionary that is passed to Requests' "json"
    parameter.
    """

    paragraph_field_definitions = {}

    def create(self, config, field_definitions, entity, row, field_name):
        """Parameters
        ----------
         config : dict
             The configuration settings defined by workbench_config.get_config().
         field_definitions : dict
             The field definitions object defined by get_field_definitions().
         entity : dict
             The dict that will be POSTed to Drupal as JSON.
         row : OrderedDict.
             The current CSV record.
         field_name : string
             The Drupal fieldname/CSV column header.
         Returns
         -------
         dictionary
             A dictionary represeting the entity that is POSTed to Drupal as JSON.
        """
        if not row[field_name]:
            logging.warning(f'Did not find "{field_name}" in row.')
            return entity
        id_field = row.get(config.get("id_field", "not_applicable"), "not_applicable")

        # This field *can* reference nodes, taxonomy terms, and media, but workbench
        # only supports paragraphs for now.
        if not field_definitions[field_name]["target_type"] == "paragraph":
            return entity

        # We allow fields to overide the global subdelimiter.
        paragraph_configs = (
            config.get("paragraph_fields", {})
            .get(field_definitions[field_name]["entity_type"], {})
            .get(field_name, {})
        )
        subdelimiter = (
            paragraph_configs.get("subdelimiter", None) or config["subdelimiter"]
        )

        subvalues = str(row[field_name]).split(subdelimiter)

        # @todo self.dedup_values

        # Enforce cardinality.
        cardinality = int(field_definitions[field_name].get("cardinality", -1))
        if -1 < cardinality < len(subvalues):
            log_field_cardinality_violation(field_name, id_field, str(cardinality))
            subvalues = subvalues[:cardinality]

        # Paragraphs are essentially field bundles, like any other entity,
        # the difference is that this node "owns" the entity rather
        # than simply references it. So we need to parse the row data
        # and populate the paragraph entity, which looks a lot like
        # creating a node from the CSV row...

        # Cache paragraph field definitions
        paragraph_type = paragraph_configs.get("type")
        if not paragraph_type:
            logging.warn(
                f'Could not determine target paragraph type for field "{field_name}"'
            )
            return entity

        if not self.paragraph_field_definitions.get(paragraph_type):
            self.paragraph_field_definitions[paragraph_type] = get_field_definitions(
                config, "paragraph", paragraph_type
            )

        reference_revisions = []
        for subvalue in subvalues:
            # Zip together the fields and their values.
            paragraph = dict(
                zip(
                    paragraph_configs.get("field_order", {}),
                    subvalue.split(paragraph_configs.get("field_delimiter", ":")),
                )
            )

            # Process each field's value.
            for p_field, value in paragraph.items():
                # This certainly isn't DRY, but here we go.

                # Entity reference fields (taxonomy_term and node).
                if (
                    self.paragraph_field_definitions[paragraph_type][p_field][
                        "field_type"
                    ]
                    == "entity_reference"
                ):
                    entity_reference_field = EntityReferenceField()
                    paragraph = entity_reference_field.create(
                        config,
                        self.paragraph_field_definitions[paragraph_type],
                        paragraph,
                        paragraph,
                        p_field,
                    )

                # Entity reference revision fields (paragraphs).
                elif (
                    self.paragraph_field_definitions[paragraph_type][p_field][
                        "field_type"
                    ]
                    == "entity_reference_revisions"
                ):
                    entity_reference_revisions_field = EntityReferenceRevisionsField()
                    paragraph = entity_reference_field.create(
                        config,
                        self.paragraph_field_definitions[paragraph_type],
                        paragraph,
                        paragraph,
                        p_field,
                    )

                # Typed relation fields.
                elif (
                    self.paragraph_field_definitions[paragraph_type][p_field][
                        "field_type"
                    ]
                    == "typed_relation"
                ):
                    typed_relation_field = TypedRelationField()
                    paragraph = typed_relation_field.create(
                        config,
                        self.paragraph_field_definitions[paragraph_type],
                        paragraph,
                        paragraph,
                        p_field,
                    )

                # Geolocation fields.
                elif (
                    self.paragraph_field_definitions[paragraph_type][p_field][
                        "field_type"
                    ]
                    == "geolocation"
                ):
                    geolocation_field = GeolocationField()
                    paragraph = geolocation_field.create(
                        config,
                        self.paragraph_field_definitions[paragraph_type],
                        paragraph,
                        paragraph,
                        p_field,
                    )

                # Link fields.
                elif (
                    self.paragraph_field_definitions[paragraph_type][p_field][
                        "field_type"
                    ]
                    == "link"
                ):
                    link_field = LinkField()
                    paragraph = link_field.create(
                        config,
                        self.paragraph_field_definitions[paragraph_type],
                        paragraph,
                        paragraph,
                        p_field,
                    )

                # Authority Link fields.
                elif (
                    self.paragraph_field_definitions[paragraph_type][p_field][
                        "field_type"
                    ]
                    == "authority_link"
                ):
                    link_field = AuthorityLinkField()
                    paragraph = link_field.create(
                        config,
                        self.paragraph_field_definitions[paragraph_type],
                        paragraph,
                        paragraph,
                        p_field,
                    )

                # For non-entity reference and non-typed relation fields (text, integer, boolean etc.).
                else:
                    simple_field = SimpleField()
                    paragraph = simple_field.create(
                        config,
                        self.paragraph_field_definitions[paragraph_type],
                        paragraph,
                        paragraph,
                        p_field,
                    )

            # Set parent information.
            paragraph.update(
                {
                    "type": [{"target_id": paragraph_configs.get("type")}],
                    "parent_field_name": [{"value": field_name}],
                }
            )

            # Create the paragraph.
            p_response = issue_request(
                config,
                "POST",
                "/entity/paragraph?_format=json",
                {"Content-Type": "application/json"},
                paragraph,
                None,
            )
            if p_response.status_code == 201:
                paragraph = p_response.json()
                reference_revisions.append(
                    {
                        "target_id": paragraph["id"][0]["value"],
                        "target_revision_id": paragraph["revision_id"][0]["value"],
                    }
                )
            elif p_response.status_code == 403:
                message = "Not authorized to create paragraphs. Please ensure the paragraphs_type_permissions module is enable and the user has sufficient permissions."
                print(message)
                logging.error(message)
            else:
                message = p_response.json().get("message", "Unknown")
                logging.warn(
                    f'Could not create paragraph for "{field_name}" in row "{id_field}": {message}'
                )

        entity[field_name] = reference_revisions
        return entity

    def update(
        self, config, field_definitions, entity, row, field_name, entity_field_values
    ):
        """Note: this method appends incoming CSV values to existing values, replaces existing field
        values with incoming values, or deletes all values from fields, depending on whether
        config['update_mode'] is 'append', 'replace', or 'delete'. It doesn not replace individual
        values within fields.
        """
        """Parameters
           ----------
            config : dict
                The configuration settings defined by workbench_config.get_config().
            field_definitions : dict
                The field definitions object defined by get_field_definitions().
            entity : dict
                The dict that will be POSTed to Drupal as JSON.
            row : OrderedDict.
                The current CSV record.
            field_name : string
                The Drupal fieldname/CSV column header.
            entity_field_values : list
                List of dictionaries containing existing value(s) for field_name in the entity being updated.
            Returns
            -------
            dictionary
                A dictionary represeting the entity that is PATCHed to Drupal as JSON.
        """
        if config["update_mode"] == "delete":
            entity[field_name] = []
            return entity

        if not row[field_name]:
            return entity

        if field_name not in entity:
            entity[field_name] = []

        if config["update_mode"] == "replace":
            return self.create(config, field_definitions, entity, row, field_name)

        if config["update_mode"] == "append":
            # Save away existing values
            entity = self.create(config, field_definitions, entity, row, field_name)
            entity[field_name] = entity_field_values + entity[field_name]
            # Enforce cardinality
            cardinality = int(field_definitions[field_name].get("cardinality", -1))
            if -1 < cardinality < len(entity[field_name]):
                log_field_cardinality_violation(
                    field_name,
                    row.get(config.get("id_field", "not_applicable"), "not_applicable"),
                    str(cardinality),
                )
                entity[field_name] = entity[field_name][slice(0, cardinality)]
            return entity

    def dedupe_values(self, values):
        """Removes duplicate entries from 'values'."""
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
        return deduplicate_field_values(values)

    def serialize(self, config, field_definitions, field_name, field_data):
        """Serialized values into a format consistent with Workbench's CSV-field input format."""
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
                A string structured same as the Workbench CSV field data for this field type,
                or None if there is nothing to return.
        """
        if "field_type" not in field_definitions[field_name]:
            return None

        # We allow fields to overide the global subdelimiter.
        paragraph_configs = (
            config.get("paragraph_fields", {})
            .get(field_definitions[field_name]["entity_type"], {})
            .get(field_name, {})
        )
        subdelimiter = (
            paragraph_configs.get("subdelimiter", None) or config["subdelimiter"]
        )

        # Cache paragraph field definitions
        paragraph_type = paragraph_configs.get("type")
        if not paragraph_type:
            logging.warn(
                f'Could not determine target paragraph type for field "field_name". Returning data from Drupal.'
            )
            return json.dumps(field_data)
        if not self.paragraph_field_definitions.get(paragraph_type):
            self.paragraph_field_definitions[paragraph_type] = get_field_definitions(
                config, "paragraph", paragraph_type
            )

        subvalues = list()
        for subvalue in field_data:
            # Retrieve the paragraph so we can serialize it.
            target_id = subvalue.get("target_id")
            p_response = issue_request(
                config, "GET", f"/entity/paragraph/{target_id}?_format=json"
            )
            if p_response.status_code == 200:
                paragraph = p_response.json()
                paragraph_parts = []
                for field in paragraph_configs.get("field_order", {}):
                    logging.info(
                        f"Serializing paragraph field: {field}:"
                        + json.dumps(paragraph.get(field))
                    )
                    if not paragraph.get(field):
                        continue
                    # Entity reference fields (taxonomy term and node).
                    if (
                        self.paragraph_field_definitions[paragraph_type][field][
                            "field_type"
                        ]
                        == "entity_reference"
                    ):
                        serialized_field = EntityReferenceField()
                        paragraph_parts.append(
                            serialized_field.serialize(
                                config,
                                self.paragraph_field_definitions[paragraph_type],
                                field,
                                paragraph.get(field),
                            )
                        )
                    # Entity reference revision fields (mostly paragraphs).
                    elif (
                        self.paragraph_field_definitions[paragraph_type][field][
                            "field_type"
                        ]
                        == "entity_reference_revisions"
                    ):
                        serialized_field = EntityReferenceRevisionsField()
                        paragraph_parts.append(
                            serialized_field.serialize(
                                config,
                                self.paragraph_field_definitions[paragraph_type],
                                field,
                                paragraph.get(field),
                            )
                        )
                    # Typed relation fields (currently, only taxonomy term)
                    elif (
                        self.paragraph_field_definitions[paragraph_type][field][
                            "field_type"
                        ]
                        == "typed_relation"
                    ):
                        serialized_field = TypedRelationField()
                        paragraph_parts.append(
                            serialized_field.serialize(
                                config,
                                self.paragraph_field_definitions[paragraph_type],
                                field,
                                paragraph.get(field),
                            )
                        )
                    # Geolocation fields.
                    elif (
                        self.paragraph_field_definitions[paragraph_type][field][
                            "field_type"
                        ]
                        == "geolocation"
                    ):
                        serialized_field = GeolocationField()
                        paragraph_parts.append(
                            serialized_field.serialize(
                                config,
                                self.paragraph_field_definitions[paragraph_type],
                                field,
                                paragraph.get(field),
                            )
                        )
                    # Link fields.
                    elif (
                        self.paragraph_field_definitions[paragraph_type][field][
                            "field_type"
                        ]
                        == "link"
                    ):
                        serialized_field = LinkField()
                        paragraph_parts.append(
                            serialized_field.serialize(
                                config,
                                self.paragraph_field_definitions[paragraph_type],
                                field,
                                paragraph.get(field),
                            )
                        )
                    # Authority Link fields.
                    elif (
                        self.paragraph_field_definitions[paragraph_type][field][
                            "field_type"
                        ]
                        == "authority_link"
                    ):
                        serialized_field = AuthorityLinkField()
                        paragraph_parts.append(
                            serialized_field.serialize(
                                config,
                                self.paragraph_field_definitions[paragraph_type],
                                field,
                                paragraph.get(field),
                            )
                        )
                    # Simple fields.
                    else:
                        paragraph_parts.append(
                            SimpleField().serialize(
                                config,
                                self.paragraph_field_definitions[paragraph_type],
                                field,
                                paragraph.get(field),
                            )
                        )
                subvalues.append(
                    paragraph_configs.get("field_delimiter", ":").join(paragraph_parts)
                )
            else:
                # Something went wrong, so we'll just return the Drupal field data we already have.
                message = p_response.json().get("message", "Unknown")
                logging.warn(
                    f'Could not retrieve paragraph for "{field_name}": {message}'
                )
                subvalues.append(subvalue)
        if len(subvalues) > 1:
            return subdelimiter.join(subvalues)
        elif len(subvalues) == 0:
            return None
        return subvalues[0]
