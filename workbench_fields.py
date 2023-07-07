"""Classes for Drupal field operations.

   Support for additional field types should be added as new classes here,
   with accompanying tests in field_tests.py and field_tests_values.py.

   Note: If new field types are added to this class, corresponding logic must be
   added to functions in other Workbench modules (e.g. workbench_utils, workbench)
   that create or update nodes.
"""

import json
import copy
from workbench_utils import *


class SimpleField():
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
        if row[field_name] is None:
            return entity

        if field_name in config['field_text_format_ids']:
            text_format = config['field_text_format_ids'][field_name]
        else:
            text_format = config['text_format_id']

        id_field = row[config['id_field']]
        # Cardinality is unlimited.
        if field_definitions[field_name]['cardinality'] == -1:
            if config['subdelimiter'] in row[field_name]:
                field_values = []
                subvalues = row[field_name].split(config['subdelimiter'])
                subvalues = self.remove_invalid_values(config, field_definitions, field_name, subvalues)
                subvalues = self.dedupe_values(subvalues)
                for subvalue in subvalues:
                    subvalue = truncate_csv_value(field_name, id_field, field_definitions[field_name], subvalue)
                    if field_definitions[field_name]['formatted_text'] is True:
                        field_values.append({'value': subvalue, 'format': text_format})
                    else:
                        field_values.append({'value': subvalue})
                entity[field_name] = field_values
            else:
                row[field_name] = truncate_csv_value(field_name, id_field, field_definitions[field_name], row[field_name])
                if field_definitions[field_name]['formatted_text'] is True:
                    entity[field_name] = [{'value': row[field_name], 'format': text_format}]
                else:
                    entity[field_name] = [{'value': row[field_name]}]

        # Cardinality has a limit, including 1.
        else:
            if config['subdelimiter'] in row[field_name]:
                field_values = []
                subvalues = row[field_name].split(config['subdelimiter'])
                subvalues = self.remove_invalid_values(config, field_definitions, field_name, subvalues)
                subvalues = self.dedupe_values(subvalues)
                if len(subvalues) > int(field_definitions[field_name]['cardinality']):
                    log_field_cardinality_violation(field_name, id_field, field_definitions[field_name]['cardinality'])
                subvalues = subvalues[:field_definitions[field_name]['cardinality']]
                for subvalue in subvalues:
                    subvalue = truncate_csv_value(field_name, id_field, field_definitions[field_name], subvalue)
                    if field_definitions[field_name]['formatted_text'] is True:
                        field_values.append({'value': subvalue, 'format': text_format})
                    else:
                        field_values.append({'value': subvalue})
                field_values = self.dedupe_values(field_values)
                entity[field_name] = field_values
            else:
                row[field_name] = truncate_csv_value(field_name, id_field, field_definitions[field_name], row[field_name])
                if field_definitions[field_name]['formatted_text'] is True:
                    entity[field_name] = [{'value': row[field_name], 'format': text_format}]
                else:
                    entity[field_name] = [{'value': row[field_name]}]

        return entity

    def update(self, config, field_definitions, entity, row, field_name, entity_field_values):
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
        if config['update_mode'] == 'delete':
            entity[field_name] = []
            return entity

        if row[field_name] is None:
            return entity

        if field_name in config['field_text_format_ids']:
            text_format = config['field_text_format_ids'][field_name]
        else:
            text_format = config['text_format_id']

        # Cardinality has a limit.
        if field_definitions[field_name]['cardinality'] > 0:
            if config['update_mode'] == 'append':
                if config['subdelimiter'] in row[field_name]:
                    subvalues = row[field_name].split(config['subdelimiter'])
                    subvalues = self.remove_invalid_values(config, field_definitions, field_name, subvalues)
                    for subvalue in subvalues:
                        subvalue = truncate_csv_value(field_name, row['node_id'], field_definitions[field_name], subvalue)
                        if field_definitions[field_name]['formatted_text'] is True:
                            entity[field_name].append({'value': subvalue, 'format': text_format})
                        else:
                            entity[field_name].append({'value': subvalue})
                    entity[field_name] = self.dedupe_values(entity[field_name])
                    if len(entity[field_name]) > int(field_definitions[field_name]['cardinality']):
                        log_field_cardinality_violation(field_name, row['node_id'], field_definitions[field_name]['cardinality'])
                        entity[field_name] = entity[field_name][:field_definitions[field_name]['cardinality']]
                else:
                    row[field_name] = self.remove_invalid_values(config, field_definitions, field_name, row[field_name])
                    row[field_name] = truncate_csv_value(field_name, row['node_id'], field_definitions[field_name], row[field_name])
                    if field_definitions[field_name]['formatted_text'] is True:
                        entity[field_name].append({'value': row[field_name], 'format': text_format})
                    else:
                        entity[field_name].append({'value': row[field_name]})
                    entity[field_name] = self.dedupe_values(entity[field_name])
                    if len(entity[field_name]) > int(field_definitions[field_name]['cardinality']):
                        log_field_cardinality_violation(field_name, row['node_id'], field_definitions[field_name]['cardinality'])
                        entity[field_name] = entity[field_name][:field_definitions[field_name]['cardinality']]

            if config['update_mode'] == 'replace':
                if config['subdelimiter'] in row[field_name]:
                    field_values = []
                    subvalues = row[field_name].split(config['subdelimiter'])
                    subvalues = self.remove_invalid_values(config, field_definitions, field_name, subvalues)
                    subvalues = self.dedupe_values(subvalues)
                    if len(subvalues) > int(field_definitions[field_name]['cardinality']):
                        log_field_cardinality_violation(field_name, row['node_id'], field_definitions[field_name]['cardinality'])
                        subvalues = subvalues[:field_definitions[field_name]['cardinality']]
                    for subvalue in subvalues:
                        subvalue = truncate_csv_value(field_name, row['node_id'], field_definitions[field_name], subvalue)
                        if field_definitions[field_name]['formatted_text'] is True:
                            field_values.append({'value': subvalue, 'format': text_format})
                        else:
                            field_values.append({'value': subvalue})
                    field_values = self.dedupe_values(field_values)
                    entity[field_name] = field_values
                else:
                    row[field_name] = truncate_csv_value(field_name, row['node_id'], field_definitions[field_name], row[field_name])
                    if 'formatted_text' in field_definitions[field_name] and field_definitions[field_name]['formatted_text'] is True:
                        entity[field_name] = [{'value': row[field_name], 'format': text_format}]
                    else:
                        entity[field_name] = [{'value': row[field_name]}]

        # Cardinatlity is unlimited.
        else:
            if config['update_mode'] == 'append':
                if config['subdelimiter'] in row[field_name]:
                    field_values = []
                    subvalues = row[field_name].split(config['subdelimiter'])
                    subvalues = self.remove_invalid_values(config, field_definitions, field_name, subvalues)
                    for subvalue in subvalues:
                        subvalue = truncate_csv_value(field_name, row['node_id'], field_definitions[field_name], subvalue)
                        if field_definitions[field_name]['formatted_text'] is True:
                            field_values.append({'value': subvalue, 'format': text_format})
                        else:
                            field_values.append({'value': subvalue})
                    entity[field_name] = entity_field_values + field_values
                    entity[field_name] = self.dedupe_values(entity[field_name])
                else:
                    row[field_name] = truncate_csv_value(field_name, row['node_id'], field_definitions[field_name], row[field_name])
                    if field_definitions[field_name]['formatted_text'] is True:
                        entity[field_name] = entity_field_values + [{'value': row[field_name], 'format': text_format}]
                    else:
                        entity[field_name] = entity_field_values + [{'value': row[field_name]}]
                    entity[field_name] = self.dedupe_values(entity[field_name])
            if config['update_mode'] == 'replace':
                if config['subdelimiter'] in row[field_name]:
                    field_values = []
                    subvalues = row[field_name].split(config['subdelimiter'])
                    subvalues = self.remove_invalid_values(config, field_definitions, field_name, subvalues)
                    for subvalue in subvalues:
                        subvalue = truncate_csv_value(field_name, row['node_id'], field_definitions[field_name], subvalue)
                        if field_definitions[field_name]['formatted_text'] is True:
                            field_values.append({'value': subvalue, 'format': text_format})
                        else:
                            field_values.append({'value': subvalue})
                    entity[field_name] = field_values
                    entity[field_name] = self.dedupe_values(entity[field_name])
                else:
                    row[field_name] = truncate_csv_value(field_name, row['node_id'], field_definitions[field_name], row[field_name])
                    if field_definitions[field_name]['formatted_text'] is True:
                        entity[field_name] = [{'value': row[field_name], 'format': text_format}]
                    else:
                        entity[field_name] = [{'value': row[field_name]}]

        return entity

    def dedupe_values(self, values):
        """Removes duplicate entries from 'values'.
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
        return deduplicate_field_values(values)

    def remove_invalid_values(self, config, field_definitions, field_name, values):
        """Removes invalid entries from 'values'.
        """
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
        if 'field_type' not in field_definitions[field_name]:
            return values

        if field_definitions[field_name]['field_type'] == 'edtf':
            valid_values = list()
            for subvalue in values:
                if validate_edtf_date(subvalue) is True:
                    valid_values.append(subvalue)
                else:
                    message = 'Value "' + subvalue + '" in field "' + field_name + '" is not a valid EDTF field value.'
                    logging.warning(message)
            return valid_values
        elif field_definitions[field_name]['field_type'] == 'list_string':
            valid_values = list()
            for subvalue in values:
                if subvalue in field_definitions[field_name]['allowed_values']:
                    valid_values.append(subvalue)
                else:
                    message = 'Value "' + subvalue + '" in field "' + field_name + '" is not in the field\'s list of allowed values.'
                    logging.warning(message)
            return valid_values
        else:
            # For now, just return values if the field is not an EDTF field.
            return values

    def serialize(self, config, field_definitions, field_name, field_data):
        """Serialized values into a format consistent with Workbench's CSV-field input format.
        """
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
        """
        if 'field_type' not in field_definitions[field_name]:
            return values

        subvalues = list()
        for subvalue in field_data:
            if 'value' in subvalue:
                subvalues.append(subvalue['value'])
            else:
                logging.warning("Field data " + str(field_data) + ' in field "' + field_name + '" cannot be serialized by the SimpleField handler.')
                return ''

        if len(subvalues) > 1:
            return config['subdelimiter'].join(subvalues)
        elif len(subvalues) == 0:
            return None
        else:
            return subvalues[0]


class GeolocationField():
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
        if row[field_name] is None:
            return entity

        id_field = row[config['id_field']]
        # Cardinality is unlimited.
        if field_definitions[field_name]['cardinality'] == -1:
            if config['subdelimiter'] in row[field_name]:
                field_values = []
                subvalues = split_geolocation_string(config, row[field_name])
                subvalues = self.dedupe_values(subvalues)
                for subvalue in subvalues:
                    field_values.append(subvalue)
                entity[field_name] = field_values
            else:
                field_value = split_geolocation_string(config, row[field_name])
                entity[field_name] = field_value
        # Cardinality has a limit.
        else:
            if config['subdelimiter'] in row[field_name]:
                subvalues = split_geolocation_string(config, row[field_name])
                subvalues = self.dedupe_values(subvalues)
                if len(subvalues) > int(field_definitions[field_name]['cardinality']):
                    subvalues = subvalues[:field_definitions[field_name]['cardinality']]
                    log_field_cardinality_violation(field_name, id_field, field_definitions[field_name]['cardinality'])
                entity[field_name] = subvalues
            else:
                field_value = split_geolocation_string(config, row[field_name])
                entity[field_name] = field_value

        return entity

    def update(self, config, field_definitions, entity, row, field_name, entity_field_values):
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
        if config['update_mode'] == 'delete':
            entity[field_name] = []
            return entity

        if row[field_name] is None:
            return entity

        # Cardinality is unlimited.
        if field_definitions[field_name]['cardinality'] == -1:
            if config['update_mode'] == 'replace':
                if config['subdelimiter'] in row[field_name]:
                    field_values = []
                    subvalues = split_geolocation_string(config, row[field_name])
                    subvalues = self.dedupe_values(subvalues)
                    for subvalue in subvalues:
                        field_values.append(subvalue)
                    field_values = self.dedupe_values(field_values)
                    entity[field_name] = field_values
                else:
                    field_value = split_geolocation_string(config, row[field_name])
                    entity[field_name] = field_value
            if config['update_mode'] == 'append':
                field_values = split_geolocation_string(config, row[field_name])
                if field_name in entity:
                    for field_value in field_values:
                        entity_field_values.append(field_value)
                    entity[field_name] = self.dedupe_values(entity_field_values)
        # Cardinality has a limit.
        else:
            if config['update_mode'] == 'replace':
                subvalues = split_geolocation_string(config, row[field_name])
                subvalues = self.dedupe_values(subvalues)
                if config['subdelimiter'] in row[field_name]:
                    field_values = []
                    for subvalue in subvalues:
                        field_values.append(subvalue)
                    if len(field_values) > int(field_definitions[field_name]['cardinality']):
                        log_field_cardinality_violation(field_name, row['node_id'], field_definitions[field_name]['cardinality'])
                        field_values = field_values[:field_definitions[field_name]['cardinality']]
                    entity[field_name] = field_values
                else:
                    entity[field_name] = subvalues

            if config['update_mode'] == 'append':
                subvalues = split_geolocation_string(config, row[field_name])
                subvalues = self.dedupe_values(subvalues)
                if config['subdelimiter'] in row[field_name]:
                    for subvalue in subvalues:
                        entity_field_values.append(subvalue)
                    if len(entity[field_name]) > int(field_definitions[field_name]['cardinality']):
                        entity[field_name] = entity_field_values[:field_definitions[field_name]['cardinality']]
                        log_field_cardinality_violation(field_name, row['node_id'], field_definitions[field_name]['cardinality'])
                else:
                    for subvalue in subvalues:
                        entity_field_values.append(subvalue)
                    if len(entity_field_values) > int(field_definitions[field_name]['cardinality']):
                        entity[field_name] = entity_field_values[:field_definitions[field_name]['cardinality']]
                        log_field_cardinality_violation(field_name, row['node_id'], field_definitions[field_name]['cardinality'])

        return entity

    def dedupe_values(self, values):
        """Removes duplicate entries from 'values'.
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
        return deduplicate_field_values(values)

    def remove_invalid_values(self, config, field_definitions, field_name, values):
        """Removes invalid entries from 'values'.
        """
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
                message = 'Value "' + subvalue + '" in field "' + field_name + '" is not a valid Geolocation field value.'
                logging.warning(message)
        return valid_values

    def serialize(self, config, field_definitions, field_name, field_data):
        """Serialized values into a format consistent with Workbench's CSV-field input format.
        """
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
        """
        if 'field_type' not in field_definitions[field_name]:
            return values

        subvalues = list()
        for subvalue in field_data:
            subvalues.append(str(subvalue['lat']) + ',' + str(subvalue['lng']))

        if len(subvalues) > 1:
            return config['subdelimiter'].join(subvalues)
        elif len(subvalues) == 0:
            return None
        else:
            return subvalues[0]


class LinkField():
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
        if row[field_name] is None:
            return entity

        id_field = row[config['id_field']]
        # Cardinality is unlimited.
        if field_definitions[field_name]['cardinality'] == -1:
            if config['subdelimiter'] in row[field_name]:
                subvalues = split_link_string(config, row[field_name])
                subvalues = self.dedupe_values(subvalues)
                entity[field_name] = subvalues
            else:
                field_value = split_link_string(config, row[field_name])
                entity[field_name] = field_value
        # Cardinality has a limit, including 1.
        else:
            if config['subdelimiter'] in row[field_name]:
                subvalues = split_link_string(config, row[field_name])
                subvalues = self.dedupe_values(subvalues)
                if len(subvalues) > int(field_definitions[field_name]['cardinality']):
                    subvalues = subvalues[:field_definitions[field_name]['cardinality']]
                    log_field_cardinality_violation(field_name, id_field, field_definitions[field_name]['cardinality'])
                entity[field_name] = subvalues
            else:
                field_value = split_link_string(config, row[field_name])
                entity[field_name] = field_value

        return entity

    def update(self, config, field_definitions, entity, row, field_name, entity_field_values):
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
        if config['update_mode'] == 'delete':
            entity[field_name] = []
            return entity

        if row[field_name] is None:
            return entity

        # Cardinality is unlimited.
        if field_definitions[field_name]['cardinality'] == -1:
            if config['update_mode'] == 'replace':
                if config['subdelimiter'] in row[field_name]:
                    field_values = []
                    subvalues = split_link_string(config, row[field_name])
                    subvalues = self.dedupe_values(subvalues)
                    for subvalue in subvalues:
                        field_values.append(subvalue)
                    entity[field_name] = field_values
                else:
                    field_value = split_link_string(config, row[field_name])
                    entity[field_name] = field_value
            if config['update_mode'] == 'append':
                if config['subdelimiter'] in row[field_name]:
                    field_values = []
                    subvalues = split_link_string(config, row[field_name])
                    for subvalue in subvalues:
                        field_values.append(subvalue)
                    if field_name in entity:
                        for field_subvalue in field_values:
                            entity_field_values.append(field_subvalue)
                        entity_field_values = subvalues = self.dedupe_values(entity_field_values)
                        entity[field_name] = entity_field_values
                else:
                    field_value = split_link_string(config, row[field_name])
                    if field_name in entity:
                        for field_subvalue in field_value:
                            entity_field_values.append(field_subvalue)
                        entity[field_name] = entity_field_values
        # Cardinality has a limit.
        else:
            if config['update_mode'] == 'replace':
                if config['subdelimiter'] in row[field_name]:
                    field_values = []
                    subvalues = split_link_string(config, row[field_name])
                    subvalues = self.dedupe_values(subvalues)
                    if len(subvalues) > int(field_definitions[field_name]['cardinality']):
                        log_field_cardinality_violation(field_name, row['node_id'], field_definitions[field_name]['cardinality'])
                    subvalues = subvalues[:field_definitions[field_name]['cardinality']]
                    for subvalue in subvalues:
                        field_values.append(subvalue)
                    entity[field_name] = field_values
                else:
                    field_value = split_link_string(config, row[field_name])
                    entity[field_name] = field_value
            if config['update_mode'] == 'append':
                subvalues = split_link_string(config, row[field_name])
                for subvalue in subvalues:
                    entity_field_values.append(subvalue)
                entity[field_name] = entity_field_values[:field_definitions[field_name]['cardinality']]
                if len(entity[field_name]) > int(field_definitions[field_name]['cardinality']):
                    log_field_cardinality_violation(field_name, row['node_id'], field_definitions[field_name]['cardinality'])

        return entity

    def dedupe_values(self, values):
        """Removes duplicate entries from 'values'.
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
        return deduplicate_field_values(values)

    def remove_invalid_values(self, config, field_definitions, field_name, values):
        """Removes invalid entries from 'values'.
        """
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
                message = 'Value "' + subvalue + '" in field "' + field_name + '" is not a valid Link field value.'
                logging.warning(message)
        return valid_values

    def serialize(self, config, field_definitions, field_name, field_data):
        """Serialized values into a format consistent with Workbench's CSV-field input format.
        """
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
        """
        if 'field_type' not in field_definitions[field_name]:
            return values

        subvalues = list()
        for subvalue in field_data:
            if 'title' in subvalue and subvalue['title'] is not None and subvalue['title'] != '':
                subvalues.append(subvalue['uri'] + '%%' + subvalue['title'])
            else:
                subvalues.append(subvalue['uri'])

        if len(subvalues) > 1:
            return config['subdelimiter'].join(subvalues)
        elif len(subvalues) == 0:
            return None
        else:
            return subvalues[0]


class EntityReferenceField():
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
        if row[field_name] is None:
            return entity

        id_field = row[config['id_field']]
        if field_definitions[field_name]['target_type'] == 'taxonomy_term':
            target_type = 'taxonomy_term'
            field_vocabs = get_field_vocabularies(config, field_definitions, field_name)
            if config['subdelimiter'] in row[field_name]:
                prepared_tids = []
                delimited_values = row[field_name].split(config['subdelimiter'])
                for delimited_value in delimited_values:
                    tid = prepare_term_id(config, field_vocabs, field_name, delimited_value)
                    if value_is_numeric(tid):
                        tid = str(tid)
                        prepared_tids.append(tid)
                    else:
                        continue
                row[field_name] = config['subdelimiter'].join(prepared_tids)
            else:
                row[field_name] = prepare_term_id(config, field_vocabs, field_name, row[field_name])
                if value_is_numeric(row[field_name]):
                    row[field_name] = str(row[field_name])

        if field_definitions[field_name]['target_type'] == 'node':
            target_type = 'node_type'

        if field_definitions[field_name]['target_type'] == 'media':
            target_type = 'media_type'

        # Cardinality is unlimited.
        if field_definitions[field_name]['cardinality'] == -1:
            if config['subdelimiter'] in str(row[field_name]):
                field_values = []
                subvalues = row[field_name].split(config['subdelimiter'])
                subvalues = self.dedupe_values(subvalues)
                for subvalue in subvalues:
                    subvalue = str(subvalue)
                    field_values.append({'target_id': subvalue, 'target_type': target_type})
                entity[field_name] = field_values
            else:
                entity[field_name] = [{'target_id': str(row[field_name]), 'target_type': target_type}]
        # Cardinality has a limit.
        elif field_definitions[field_name]['cardinality'] > 0:
            if config['subdelimiter'] in str(row[field_name]):
                field_values = []
                subvalues = row[field_name].split(config['subdelimiter'])
                subvalues = self.dedupe_values(subvalues)
                for subvalue in subvalues:
                    subvalue = str(subvalue)
                    field_values.append({'target_id': subvalue, 'target_type': target_type})
                if len(field_values) > int(field_definitions[field_name]['cardinality']):
                    entity[field_name] = field_values[:field_definitions[field_name]['cardinality']]
                    log_field_cardinality_violation(field_name, id_field, field_definitions[field_name]['cardinality'])
                else:
                    entity[field_name] = field_values
            else:
                entity[field_name] = [{'target_id': str(row[field_name]), 'target_type': target_type}]
        # Cardinality is 1.
        else:
            subvalues = row[field_name].split(config['subdelimiter'])
            entity[field_name] = [{'target_id': str(subvalues[0]), 'target_type': target_type}]
            if len(subvalues) > 1:
                log_field_cardinality_violation(field_name, id_field, '1')

        return entity

    def update(self, config, field_definitions, entity, row, field_name, entity_field_values):
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
        if config['update_mode'] == 'delete':
            entity[field_name] = []
            return entity

        if row[field_name] is None:
            return entity

        if field_definitions[field_name]['target_type'] == 'taxonomy_term':
            target_type = 'taxonomy_term'
            field_vocabs = get_field_vocabularies(config, field_definitions, field_name)
            if config['subdelimiter'] in str(row[field_name]):
                prepared_tids = []
                delimited_values = row[field_name].split(config['subdelimiter'])
                for delimited_value in delimited_values:
                    tid = prepare_term_id(config, field_vocabs, field_name, delimited_value)
                    if value_is_numeric(tid):
                        tid = str(tid)
                        prepared_tids.append(tid)
                    else:
                        continue
                row[field_name] = config['subdelimiter'].join(prepared_tids)
            else:
                row[field_name] = prepare_term_id(config, field_vocabs, field_name, row[field_name])
                if value_is_numeric(row[field_name]):
                    row[field_name] = str(row[field_name])

        if field_definitions[field_name]['target_type'] == 'node':
            target_type = 'node_type'

        # Cardinality has a limit.
        if field_definitions[field_name]['cardinality'] > 0:
            if config['update_mode'] == 'replace':
                if config['subdelimiter'] in str(row[field_name]):
                    field_values = []
                    subvalues = row[field_name].split(config['subdelimiter'])
                    subvalues = self.dedupe_values(subvalues)
                    for subvalue in subvalues:
                        field_values.append({'target_id': str(subvalue), 'target_type': target_type})
                    if len(field_values) > int(field_definitions[field_name]['cardinality']):
                        entity[field_name] = field_values[:field_definitions[field_name]['cardinality']]
                        log_field_cardinality_violation(field_name, row['node_id'], field_definitions[field_name]['cardinality'])
                    else:
                        entity[field_name] = field_values
                else:
                    entity[field_name] = [{'target_id': row[field_name], 'target_type': target_type}]
            if config['update_mode'] == 'append':
                if config['subdelimiter'] in str(row[field_name]):
                    subvalues = row[field_name].split(config['subdelimiter'])
                    for subvalue in subvalues:
                        entity_field_values.append({'target_id': str(subvalue), 'target_type': target_type})
                    entity_field_values = self.dedupe_values(entity_field_values)
                    if len(entity_field_values) > int(field_definitions[field_name]['cardinality']):
                        entity[field_name] = entity_field_values[:field_definitions[field_name]['cardinality']]
                        log_field_cardinality_violation(field_name, row['node_id'], field_definitions[field_name]['cardinality'])
                    else:
                        entity[field_name] = entity_field_values
                else:
                    entity_field_values.append({'target_id': str(row[field_name]), 'target_type': target_type})
                    entity_field_values = self.dedupe_values(entity_field_values)
                    if len(entity_field_values) > int(field_definitions[field_name]['cardinality']):
                        entity[field_name] = entity_field_values[:field_definitions[field_name]['cardinality']]
                        log_field_cardinality_violation(field_name, row['node_id'], field_definitions[field_name]['cardinality'])
                    else:
                        entity[field_name] = entity_field_values

        # Cardinality is unlimited.
        else:
            if config['update_mode'] == 'replace':
                if config['subdelimiter'] in str(row[field_name]):
                    field_values = []
                    subvalues = row[field_name].split(config['subdelimiter'])
                    subvalues = self.dedupe_values(subvalues)
                    for subvalue in subvalues:
                        field_values.append({'target_id': str(subvalue), 'target_type': target_type})
                        entity[field_name] = field_values
                else:
                    entity[field_name] = [{'target_id': str(row[field_name]), 'target_type': target_type}]
            if config['update_mode'] == 'append':
                if config['subdelimiter'] in str(row[field_name]):
                    field_values = []
                    subvalues = row[field_name].split(config['subdelimiter'])
                    for subvalue in subvalues:
                        entity_field_values.append({'target_id': str(subvalue), 'target_type': target_type})
                    entity[field_name] = self.dedupe_values(entity_field_values)
                else:
                    entity_field_values.append({'target_id': str(row[field_name]), 'target_type': target_type})
                    entity[field_name] = self.dedupe_values(entity_field_values)

        return entity

    def dedupe_values(self, values):
        """Removes duplicate entries from 'values'.
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
        return deduplicate_field_values(values)

    def remove_invalid_values(self, config, field_definitions, field_name, values):
        """Removes invalid entries from 'values'.
        """
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
        '''
        valid_values = list()
        for subvalue in values:
            if validate_link_value(subvalue) is True:
                valid_values.append(subvalue)
            else:
                message = 'Value "' + subvalue + '" in field "' + field_name + '" is not a valid Entity Reference field value.'
                logging.warning(message)
        return valid_values
        '''
        return values

    def serialize(self, config, field_definitions, field_name, field_data):
        """Serialized values into a format consistent with Workbench's CSV-field input format.
        """
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
        """
        if 'field_type' not in field_definitions[field_name]:
            return values

        subvalues = list()
        for subvalue in field_data:
            if config['export_csv_term_mode'] == 'name' and subvalue['target_type'] == 'taxonomy_term':
                # Output term names, with vocab IDs (aka namespaces).
                vocab_id = get_term_vocab(config, subvalue['target_id'])
                term_name = get_term_name(config, subvalue['target_id'])
                if vocab_id is not False and term_name is not False:
                    subvalues.append(vocab_id + ':' + term_name)
            else:
                # Output term IDs.
                if ping_term(config, subvalue['target_id']) is True:
                    subvalues.append(str(subvalue['target_id']))

        if len(subvalues) > 1:
            return config['subdelimiter'].join(subvalues)
        elif len(subvalues) == 0:
            return None
        else:
            return subvalues[0]


class TypedRelationField():
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
        if row[field_name] is None:
            return entity

        id_field = row[config['id_field']]
        # Currently only supports Typed Relation taxonomy entities.
        if field_definitions[field_name]['target_type'] == 'taxonomy_term':
            target_type = 'taxonomy_term'
            field_vocabs = get_field_vocabularies(config, field_definitions, field_name)
            # Cardinality is unlimited.
            if field_definitions[field_name]['cardinality'] == -1:
                field_values = []
                subvalues = split_typed_relation_string(config, row[field_name], target_type)
                subvalues = self.dedupe_values(subvalues)
                if config['subdelimiter'] in row[field_name]:
                    for subvalue in subvalues:
                        subvalue['target_id'] = prepare_term_id(config, field_vocabs, field_name, subvalue['target_id'])
                        field_values.append(subvalue)
                    entity[field_name] = field_values
                else:
                    subvalues[0]['target_id'] = prepare_term_id(config, field_vocabs, field_name, subvalues[0]['target_id'])
                    entity[field_name] = subvalues
            # Cardinality has a limit.
            elif field_definitions[field_name]['cardinality'] > 1:
                if config['subdelimiter'] in row[field_name]:
                    field_values = []
                    subvalues = split_typed_relation_string(config, row[field_name], target_type)
                    subvalues = self.dedupe_values(subvalues)
                    if len(subvalues) > field_definitions[field_name]['cardinality']:
                        log_field_cardinality_violation(field_name, id_field, field_definitions[field_name]['cardinality'])
                        subvalues = subvalues[:field_definitions[field_name]['cardinality']]
                    for subvalue in subvalues:
                        subvalue['target_id'] = prepare_term_id(config, field_vocabs, field_name, subvalue['target_id'])
                        field_values.append(subvalue)
                    entity[field_name] = field_values
                else:
                    field_value = split_typed_relation_string(config, row[field_name], target_type)
                    field_value[0]['target_id'] = prepare_term_id(config, field_vocabs, field_name, field_value[0]['target_id'])
                    entity[field_name] = field_value
            # Cardinality is 1.
            else:
                subvalues = split_typed_relation_string(config, row[field_name], target_type)
                subvalues = self.dedupe_values(subvalues)
                subvalues[0]['target_id'] = prepare_term_id(config, field_vocabs, field_name, subvalues[0]['target_id'])
                entity[field_name] = [subvalues[0]]
                if len(subvalues) > 1:
                    log_field_cardinality_violation(field_name, id_field, '1')

        return entity

    def update(self, config, field_definitions, entity, row, field_name, entity_field_values):
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
        if config['update_mode'] == 'delete':
            entity[field_name] = []
            return entity

        if row[field_name] is None:
            return entity

        # Currently only supports Typed Relation taxonomy entities.
        if field_definitions[field_name]['target_type'] == 'taxonomy_term':
            target_type = 'taxonomy_term'
            field_vocabs = get_field_vocabularies(config, field_definitions, field_name)

        # Cardinality has a limit.
        if field_definitions[field_name]['cardinality'] > 0:
            if config['update_mode'] == 'replace':
                subvalues = split_typed_relation_string(config, row[field_name], target_type)
                subvalues = self.dedupe_values(subvalues)
                if config['subdelimiter'] in row[field_name]:
                    field_values = []
                    for subvalue in subvalues:
                        subvalue['target_id'] = prepare_term_id(config, field_vocabs, field_name, subvalue['target_id'])
                        field_values.append(subvalue)
                    if len(field_values) > int(field_definitions[field_name]['cardinality']):
                        field_values = field_values[:field_definitions[field_name]['cardinality']]
                        log_field_cardinality_violation(field_name, row['node_id'], field_definitions[field_name]['cardinality'])
                    entity[field_name] = field_values
                else:
                    subvalues[0]['target_id'] = prepare_term_id(config, field_vocabs, field_name, subvalues[0]['target_id'])
                    entity[field_name] = subvalues
            if config['update_mode'] == 'append':
                if config['subdelimiter'] in row[field_name]:
                    field_values = []
                    subvalues = split_typed_relation_string(config, row[field_name], target_type)
                    for subvalue in subvalues:
                        subvalue['target_id'] = prepare_term_id(config, field_vocabs, field_name, subvalue['target_id'])
                        entity_field_values.append(subvalue)
                    entity_field_values = self.dedupe_values(entity_field_values)
                    if len(entity_field_values) > int(field_definitions[field_name]['cardinality']):
                        entity[field_name] = entity_field_values[:field_definitions[field_name]['cardinality']]
                        log_field_cardinality_violation(field_name, row['node_id'], field_definitions[field_name]['cardinality'])
                    else:
                        entity[field_name] = entity_field_values
                else:
                    csv_typed_relation_value = split_typed_relation_string(config, row[field_name], target_type)
                    csv_typed_relation_value[0]['target_id'] = prepare_term_id(config, field_vocabs, field_name, csv_typed_relation_value[0]['target_id'])
                    entity_field_values.append(csv_typed_relation_value[0])
                    entity_field_values = self.dedupe_values(entity_field_values)
                    if len(entity_field_values) > int(field_definitions[field_name]['cardinality']):
                        entity[field_name] = entity_field_values[:field_definitions[field_name]['cardinality']]
                        log_field_cardinality_violation(field_name, row['node_id'], field_definitions[field_name]['cardinality'])
                    else:
                        entity[field_name] = entity_field_values

        # Cardinality is unlimited.
        else:
            if config['update_mode'] == 'replace':
                subvalues = split_typed_relation_string(config, row[field_name], target_type)
                subvalues = self.dedupe_values(subvalues)
                if config['subdelimiter'] in row[field_name]:
                    field_values = []
                    for subvalue in subvalues:
                        subvalue['target_id'] = prepare_term_id(config, field_vocabs, field_name, subvalue['target_id'])
                        field_values.append(subvalue)
                    entity[field_name] = field_values
                else:
                    subvalues[0]['target_id'] = prepare_term_id(config, field_vocabs, field_name, subvalues[0]['target_id'])
                    entity[field_name] = subvalues
            if config['update_mode'] == 'append':
                subvalues = split_typed_relation_string(config, row[field_name], target_type)
                if config['subdelimiter'] in row[field_name]:
                    field_values = []
                    for subvalue in subvalues:
                        subvalue['target_id'] = prepare_term_id(config, field_vocabs, field_name, subvalue['target_id'])
                        entity_field_values.append(subvalue)
                    entity[field_name] = self.dedupe_values(entity_field_values)
                else:
                    subvalues[0]['target_id'] = prepare_term_id(config, field_vocabs, field_name, subvalues[0]['target_id'])
                    entity_field_values.append(subvalues[0])
                    entity[field_name] = self.dedupe_values(entity_field_values)

        return entity

    def dedupe_values(self, values):
        """Removes duplicate entries from 'values'.
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
        return deduplicate_field_values(values)

    def remove_invalid_values(self, config, field_definitions, field_name, values):
        """Removes invalid entries from 'values'.
        """
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
        '''
        valid_values = list()
        for subvalue in values:
            if validate_link_value(subvalue) is True:
                valid_values.append(subvalue)
            else:
                message = 'Value "' + subvalue + '" in field "' + field_name + '" is not a valid Typed Relation field value.'
                logging.warning(message)
        return valid_values
        '''
        return values

    def serialize(self, config, field_definitions, field_name, field_data):
        """Serialized values into a format consistent with Workbench's CSV-field input format.
        """
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
        """
        if 'field_type' not in field_definitions[field_name]:
            return values

        subvalues = list()
        for subvalue in field_data:
            if config['export_csv_term_mode'] == 'name':
                vocab_id = get_term_vocab(config, subvalue['target_id'])
                term_name = get_term_name(config, subvalue['target_id'])
                subvalues.append(str(subvalue['rel_type']) + ':' + vocab_id + ':' + term_name)
            else:
                # Term IDs.
                subvalues.append(str(subvalue['rel_type']) + ':' + str(subvalue['target_id']))

        if len(subvalues) > 1:
            return config['subdelimiter'].join(subvalues)
        elif len(subvalues) == 0:
            return None
        else:
            return subvalues[0]


class AuthorityLinkField():
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
        if row[field_name] is None:
            return entity

        id_field = row[config['id_field']]
        # Cardinality is unlimited.
        if field_definitions[field_name]['cardinality'] == -1:
            if config['subdelimiter'] in row[field_name]:
                subvalues = split_authority_link_string(config, row[field_name])
                subvalues = self.dedupe_values(subvalues)
                entity[field_name] = subvalues
            else:
                field_value = split_authority_link_string(config, row[field_name])
                entity[field_name] = field_value
        # Cardinality has a limit, including 1.
        else:
            if config['subdelimiter'] in row[field_name]:
                subvalues = split_authority_link_string(config, row[field_name])
                subvalues = self.dedupe_values(subvalues)
                if len(subvalues) > int(field_definitions[field_name]['cardinality']):
                    subvalues = subvalues[:field_definitions[field_name]['cardinality']]
                    log_field_cardinality_violation(field_name, id_field, field_definitions[field_name]['cardinality'])
                entity[field_name] = subvalues
            else:
                field_value = split_authority_link_string(config, row[field_name])
                entity[field_name] = field_value

        return entity

    def update(self, config, field_definitions, entity, row, field_name, entity_field_values):
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
        if config['update_mode'] == 'delete':
            entity[field_name] = []
            return entity

        if row[field_name] is None:
            return entity

        # Cardinality is unlimited.
        if field_definitions[field_name]['cardinality'] == -1:
            if config['update_mode'] == 'replace':
                if config['subdelimiter'] in row[field_name]:
                    field_values = []
                    subvalues = split_authority_link_string(config, row[field_name])
                    subvalues = self.dedupe_values(subvalues)
                    for subvalue in subvalues:
                        field_values.append(subvalue)
                    entity[field_name] = field_values
                else:
                    field_value = split_authority_link_string(config, row[field_name])
                    entity[field_name] = field_value
            if config['update_mode'] == 'append':
                if config['subdelimiter'] in row[field_name]:
                    field_values = []
                    subvalues = split_authority_link_string(config, row[field_name])
                    for subvalue in subvalues:
                        field_values.append(subvalue)
                    if field_name in entity:
                        for field_subvalue in field_values:
                            entity_field_values.append(field_subvalue)
                        entity_field_values = self.dedupe_values(entity_field_values)
                        entity[field_name] = entity_field_values
                else:
                    field_value = split_authority_link_string(config, row[field_name])
                    if field_name in entity:
                        for field_subvalue in field_value:
                            entity_field_values.append(field_subvalue)
                        entity[field_name] = entity_field_values
        # Cardinality has a limit.
        else:
            if config['update_mode'] == 'replace':
                if config['subdelimiter'] in row[field_name]:
                    field_values = []
                    subvalues = split_authority_link_string(config, row[field_name])
                    subvalues = self.dedupe_values(subvalues)
                    if len(subvalues) > int(field_definitions[field_name]['cardinality']):
                        log_field_cardinality_violation(field_name, row['node_id'], field_definitions[field_name]['cardinality'])
                    subvalues = subvalues[:field_definitions[field_name]['cardinality']]
                    for subvalue in subvalues:
                        field_values.append(subvalue)
                    entity[field_name] = field_values
                else:
                    field_value = split_authority_link_string(config, row[field_name])
                    entity[field_name] = field_value
            if config['update_mode'] == 'append':
                subvalues = split_authority_link_string(config, row[field_name])
                for subvalue in subvalues:
                    entity_field_values.append(subvalue)
                entity[field_name] = entity_field_values[:field_definitions[field_name]['cardinality']]
                if len(entity[field_name]) > int(field_definitions[field_name]['cardinality']):
                    log_field_cardinality_violation(field_name, row['node_id'], field_definitions[field_name]['cardinality'])

        return entity

    def dedupe_values(self, values):
        """Removes duplicate entries from 'values'.
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
        return deduplicate_field_values(values)

    def remove_invalid_values(self, config, field_definitions, field_name, values):
        """Removes invalid entries from 'values'.
        """
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
            if validate_authority_link_value(subvalue, field_definitions[field_name]['authority_sources']) is True:
                valid_values.append(subvalue)
            else:
                message = 'Value "' + subvalue + '" in field "' + field_name + '" is not a valid Authority Link field value.'
                logging.warning(message)
        return valid_values

    def serialize(self, config, field_definitions, field_name, field_data):
        """Serialized values into a format consistent with Workbench's CSV-field input format.
        """
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
        """
        if 'field_type' not in field_definitions[field_name]:
            return values

        subvalues = list()
        for subvalue in field_data:
            if 'title' in subvalue and subvalue['title'] is not None:
                subvalues.append(subvalue['source'] + '%%' + subvalue['uri'] + '%%' + subvalue['title'])
            else:
                subvalues.append(subvalue['source'] + '%%' + subvalue['uri'])

        if len(subvalues) > 1:
            return config['subdelimiter'].join(subvalues)
        elif len(subvalues) == 0:
            return None
        else:
            return subvalues[0]


class MediaTrackField():
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
        if row[field_name] is None:
            return entity

        id_field = row[config['id_field']]
        # Cardinality is unlimited.
        if field_definitions[field_name]['cardinality'] == -1:
            if config['subdelimiter'] in row[field_name]:
                subvalues = split_media_track_string(config, row[field_name])
                subvalues = self.dedupe_values(subvalues)
                entity[field_name] = subvalues
            else:
                field_value = split_media_track_string(config, row[field_name])
                entity[field_name] = field_value
        # Cardinality has a limit, including 1.
        else:
            if config['subdelimiter'] in row[field_name]:
                subvalues = split_media_track_string(config, row[field_name])
                subvalues = self.dedupe_values(subvalues)
                if len(subvalues) > int(field_definitions[field_name]['cardinality']):
                    subvalues = subvalues[:field_definitions[field_name]['cardinality']]
                    log_field_cardinality_violation(field_name, id_field, field_definitions[field_name]['cardinality'])
                entity[field_name] = subvalues
            else:
                field_value = split_media_track_string(config, row[field_name])
                entity[field_name] = field_value

        return entity

    def update(self, config, field_definitions, entity, row, field_name, entity_field_values):
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
        if config['update_mode'] == 'delete':
            entity[field_name] = []
            return entity

        if row[field_name] is None:
            return entity

        # Cardinality is unlimited.
        if field_definitions[field_name]['cardinality'] == -1:
            if config['update_mode'] == 'replace':
                if config['subdelimiter'] in row[field_name]:
                    field_values = []
                    subvalues = split_media_track_string(config, row[field_name])
                    subvalues = self.dedupe_values(subvalues)
                    for subvalue in subvalues:
                        field_values.append(subvalue)
                    entity[field_name] = field_values
                else:
                    field_value = split_media_track_string(config, row[field_name])
                    entity[field_name] = field_value
            if config['update_mode'] == 'append':
                if config['subdelimiter'] in row[field_name]:
                    field_values = []
                    subvalues = split_media_track_string(config, row[field_name])
                    for subvalue in subvalues:
                        field_values.append(subvalue)
                    if field_name in entity:
                        for field_subvalue in field_values:
                            entity_field_values.append(field_subvalue)
                        entity_field_values = self.dedupe_values(entity_field_values)
                        entity[field_name] = entity_field_values
                else:
                    field_value = split_media_track_string(config, row[field_name])
                    if field_name in entity:
                        for field_subvalue in field_value:
                            entity_field_values.append(field_subvalue)
                        entity[field_name] = entity_field_values
        # Cardinality has a limit.
        else:
            if config['update_mode'] == 'replace':
                if config['subdelimiter'] in row[field_name]:
                    field_values = []
                    subvalues = split_media_track_string(config, row[field_name])
                    subvalues = self.dedupe_values(subvalues)
                    if len(subvalues) > int(field_definitions[field_name]['cardinality']):
                        log_field_cardinality_violation(field_name, row['node_id'], field_definitions[field_name]['cardinality'])
                    subvalues = subvalues[:field_definitions[field_name]['cardinality']]
                    for subvalue in subvalues:
                        field_values.append(subvalue)
                    entity[field_name] = field_values
                else:
                    field_value = split_media_track_string(config, row[field_name])
                    entity[field_name] = field_value
            if config['update_mode'] == 'append':
                subvalues = split_media_track_string(config, row[field_name])
                for subvalue in subvalues:
                    entity_field_values.append(subvalue)
                entity[field_name] = entity_field_values[:field_definitions[field_name]['cardinality']]
                if len(entity[field_name]) > int(field_definitions[field_name]['cardinality']):
                    log_field_cardinality_violation(field_name, row['node_id'], field_definitions[field_name]['cardinality'])

        return entity

    def dedupe_values(self, values):
        """Removes duplicate entries from 'values'.
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
        return deduplicate_field_values(values)

    def remove_invalid_values(self, config, field_definitions, field_name, values):
        """Removes invalid entries from 'values'.
        """
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
            if validate_media_track_value(subvalue, field_definitions[field_name]['authority_sources']) is True:
                valid_values.append(subvalue)
            else:
                message = 'Value "' + subvalue + '" in field "' + field_name + '" is not a valid Authority Link field value.'
                logging.warning(message)
        return valid_values

    def serialize(self, config, field_definitions, field_name, field_data):
        """Serialized values into a format consistent with Workbench's CSV-field input format.
        """
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
        """
        if 'field_type' not in field_definitions[field_name]:
            return values

        subvalues = list()
        for subvalue in field_data:
            if all('label' in subvalue, subvalue['label'] is not None,
                   'kind' in subvalue, subvalue['kind'] is not None,
                   'srclang' in subvalue, subvalue['srclang'] is not None,
                   'url' in subvalue, subvalue['url'] is not None):
                serialized = f"{subvalue['label']}:{subvalue['kind']}:{subvalue['srclang']}:{os.path.basename(subvalue['url'])}"
                subvalues.append(serialized)
            else:
                subvalues.append(f"{subvalue['label']}:{subvalue['kind']}:{subvalue['srclang']}:{os.path.basename(subvalue['url'])}")

        if len(subvalues) > 1:
            return config['subdelimiter'].join(subvalues)
        elif len(subvalues) == 0:
            return None
        else:
            return subvalues[0]
