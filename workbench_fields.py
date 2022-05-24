import json
import copy
from workbench_utils import *


class SimpleField():
    """Functions for handling fields with text and other "simple" Drupal field data types,
       e.g. fields that have a "{'value': 'xxx'}" structure such as plain text fields, ETDF
       fields. All functions return a "entity" dictionary that is passed to Requests' "json"
       parameter.

       Note: this class assumes that the entity has the field identified in 'custom_field'.
       Callers should pre-emptively confirm that. For an example, see code near the top
       of workbench.update().
    """
    def create(self, config, field_definitions, entity, row, custom_field):
        """Parameters
           ----------
            config : dict
                The configuration object defined by set_config_defaults().
            field_definitions : dict
                The field definitions object defined by get_field_definitions().
            entity : dict
                The dict that will be POSTed to Drupal as JSON.
            row : OrderedDict.
                The current CSV record.
            custom_field : string
                The Drupal fieldname/CSV column header.
            Returns
            -------
            dictionary
                A dictionary represeting the entity that is POSTed to Drupal as JSON.
        """
        id_field = row[config['id_field']]
        # Cardinality is unlimited.
        if field_definitions[custom_field]['cardinality'] == -1:
            if config['subdelimiter'] in row[custom_field]:
                field_values = []
                subvalues = row[custom_field].split(config['subdelimiter'])
                for subvalue in subvalues:
                    subvalue = truncate_csv_value(custom_field, id_field, field_definitions[custom_field], subvalue)
                    field_values.append({'value': subvalue})
                entity[custom_field] = field_values
            else:
                row[custom_field] = truncate_csv_value(custom_field, id_field, field_definitions[custom_field], row[custom_field])
                entity[custom_field] = [{'value': row[custom_field]}]
        # Cardinality has a limit, including 1.
        else:
            if config['subdelimiter'] in row[custom_field]:
                field_values = []
                subvalues = row[custom_field].split(config['subdelimiter'])
                if len(subvalues) > int(field_definitions[custom_field]['cardinality']):
                    log_field_cardinality_violation(custom_field, id_field, field_definitions[custom_field]['cardinality'])
                subvalues = subvalues[:field_definitions[custom_field]['cardinality']]
                for subvalue in subvalues:
                    subvalue = truncate_csv_value(custom_field, id_field, field_definitions[custom_field], subvalue)
                    field_values.append({'value': subvalue})
                entity[custom_field] = field_values
            else:
                row[custom_field] = truncate_csv_value(custom_field, id_field, field_definitions[custom_field], row[custom_field])
                entity[custom_field] = [{'value': row[custom_field]}]

        return entity

    def update(self, config, field_definitions, entity, row, custom_field, entity_field_values):
        """Note: this method appends incoming CSV values to existing values, replaces existing field
           values with incoming values, or deletes all values from fields, depending on whether
           config['update_mode'] is 'append', 'replace', or 'delete'. It doesn not replace individual
           values within fields.
        """
        """Parameters
           ----------
            config : dict
                The configuration object defined by set_config_defaults().
            field_definitions : dict
                The field definitions object defined by get_field_definitions().
            entity : dict
                The dict that will be POSTed to Drupal as JSON.
            row : OrderedDict.
                The current CSV record.
            custom_field : string
                The Drupal fieldname/CSV column header.
            entity_field_values : list
                List of dictionaries containing existing value(s) for custom_field in the entity being updated.
            Returns
            -------
            dictionary
                A dictionary represeting the entity that is PATCHed to Drupal as JSON.
        """
        if config['update_mode'] == 'delete':
            entity[custom_field] = []
            return entity

        # Cardinality has a limit.
        if field_definitions[custom_field]['cardinality'] > 0:
            if config['update_mode'] == 'append':
                if config['subdelimiter'] in row[custom_field]:
                    subvalues = row[custom_field].split(config['subdelimiter'])
                    for subvalue in subvalues:
                        subvalue = truncate_csv_value(custom_field, row['node_id'], field_definitions[custom_field], subvalue)
                        entity[custom_field].append({'value': subvalue})
                    if len(entity[custom_field]) > int(field_definitions[custom_field]['cardinality']):
                        log_field_cardinality_violation(custom_field, row['node_id'], field_definitions[custom_field]['cardinality'])
                        entity[custom_field] = entity[custom_field][:field_definitions[custom_field]['cardinality']]
                else:
                    row[custom_field] = truncate_csv_value(custom_field, row['node_id'], field_definitions[custom_field], row[custom_field])
                    entity[custom_field].append({'value': row[custom_field]})
                    if len(entity[custom_field]) > int(field_definitions[custom_field]['cardinality']):
                        log_field_cardinality_violation(custom_field, row['node_id'], field_definitions[custom_field]['cardinality'])
                        entity[custom_field] = entity[custom_field][:field_definitions[custom_field]['cardinality']]

            if config['update_mode'] == 'replace':
                if config['subdelimiter'] in row[custom_field]:
                    field_values = []
                    subvalues = row[custom_field].split(config['subdelimiter'])
                    if len(subvalues) > int(field_definitions[custom_field]['cardinality']):
                        log_field_cardinality_violation(custom_field, row['node_id'], field_definitions[custom_field]['cardinality'])
                    subvalues = subvalues[:field_definitions[custom_field]['cardinality']]
                    for subvalue in subvalues:
                        subvalue = truncate_csv_value(custom_field, row['node_id'], field_definitions[custom_field], subvalue)
                        field_values.append({'value': subvalue})
                        entity[custom_field] = field_values
                else:
                    row[custom_field] = truncate_csv_value(custom_field, row['node_id'], field_definitions[custom_field], row[custom_field])
                    entity[custom_field] = [{'value': row[custom_field]}]

        # Cardinatlity is unlimited.
        else:
            if config['update_mode'] == 'append':
                if config['subdelimiter'] in row[custom_field]:
                    field_values = []
                    subvalues = row[custom_field].split(config['subdelimiter'])
                    for subvalue in subvalues:
                        subvalue = truncate_csv_value(custom_field, row['node_id'], field_definitions[custom_field], subvalue)
                        field_values.append({'value': subvalue})
                        entity[custom_field] = entity_field_values + field_values
                else:
                    row[custom_field] = truncate_csv_value(custom_field, row['node_id'], field_definitions[custom_field], row[custom_field])
                    entity[custom_field] = entity_field_values + [{'value': row[custom_field]}]
            if config['update_mode'] == 'replace':
                if config['subdelimiter'] in row[custom_field]:
                    field_values = []
                    subvalues = row[custom_field].split(config['subdelimiter'])
                    for subvalue in subvalues:
                        subvalue = truncate_csv_value(custom_field, row['node_id'], field_definitions[custom_field], subvalue)
                        field_values.append({'value': subvalue})
                        entity[custom_field] = field_values
                else:
                    row[custom_field] = truncate_csv_value(custom_field, row['node_id'], field_definitions[custom_field], row[custom_field])
                    entity[custom_field] = [{'value': row[custom_field]}]

        return entity


class GeolocationField():
    """Functions for handling fields with 'geolocation' Drupal field data type.
       All functions return a "entity" dictionary that is passed to Requests'
       "json" parameter.

       Note: this class assumes that the entity has the field identified in 'custom_field'.
       Callers should pre-emptively confirm that. For an example, see code near the top
       of workbench.update().
    """
    def create(self, config, field_definitions, entity, row, custom_field):
        """Parameters
           ----------
            config : dict
                The configuration object defined by set_config_defaults().
            field_definitions : dict
                The field definitions object defined by get_field_definitions().
            entity : dict
                The dict that will be POSTed to Drupal as JSON.
            row : OrderedDict.
                The current CSV record.
            custom_field : string
                The Drupal fieldname/CSV column header.
            Returns
            -------
            dictionary
                A dictionary represeting the entity that is POSTed to Drupal as JSON.
        """
        id_field = row[config['id_field']]
        # Cardinality is unlimited.
        if field_definitions[custom_field]['cardinality'] == -1:
            if config['subdelimiter'] in row[custom_field]:
                field_values = []
                subvalues = split_geolocation_string(config, row[custom_field])
                for subvalue in subvalues:
                    field_values.append(subvalue)
                entity[custom_field] = field_values
            else:
                field_value = split_geolocation_string(config, row[custom_field])
                entity[custom_field] = field_value
        # Cardinality has a limit.
        else:
            if config['subdelimiter'] in row[custom_field]:
                subvalues = split_geolocation_string(config, row[custom_field])
                if len(subvalues) > int(field_definitions[custom_field]['cardinality']):
                    subvalues = subvalues[:field_definitions[custom_field]['cardinality']]
                    log_field_cardinality_violation(custom_field, id_field, field_definitions[custom_field]['cardinality'])
                entity[custom_field] = subvalues
            else:
                field_value = split_geolocation_string(config, row[custom_field])
                entity[custom_field] = field_value

        return entity

    def update(self, config, field_definitions, entity, row, custom_field, entity_field_values):
        """Note: this method appends incoming CSV values to existing values, replaces existing field
           values with incoming values, or deletes all values from fields, depending on whether
           config['update_mode'] is 'append', 'replace', or 'delete'. It doesn not replace individual
           values within fields.
        """
        """Parameters
           ----------
            config : dict
                The configuration object defined by set_config_defaults().
            field_definitions : dict
                The field definitions object defined by get_field_definitions().
            entity : dict
                The dict that will be POSTed to Drupal as JSON.
            row : OrderedDict.
                The current CSV record.
            custom_field : string
                The Drupal fieldname/CSV column header.
            entity_field_values : list
                List of dictionaries containing existing value(s) for custom_field in the entity being updated.
            Returns
            -------
            dictionary
                A dictionary represeting the entity that is PATCHed to Drupal as JSON.
        """
        if config['update_mode'] == 'delete':
            entity[custom_field] = []
            return entity

        # Cardinality is unlimited.
        if field_definitions[custom_field]['cardinality'] == -1:
            if config['update_mode'] == 'replace':
                if config['subdelimiter'] in row[custom_field]:
                    field_values = []
                    subvalues = split_geolocation_string(config, row[custom_field])
                    for subvalue in subvalues:
                        field_values.append(subvalue)
                    entity[custom_field] = field_values
                else:
                    field_value = split_geolocation_string(config, row[custom_field])
                    entity[custom_field] = field_value
            if config['update_mode'] == 'append':
                field_values = split_geolocation_string(config, row[custom_field])
                if custom_field in entity:
                    for field_value in field_values:
                        entity_field_values.append(field_value)
                    entity[custom_field] = entity_field_values
        # Cardinality has a limit.
        else:
            if config['update_mode'] == 'replace':
                subvalues = split_geolocation_string(config, row[custom_field])
                if config['subdelimiter'] in row[custom_field]:
                    field_values = []
                    for subvalue in subvalues:
                        field_values.append(subvalue)
                    if len(field_values) > int(field_definitions[custom_field]['cardinality']):
                        log_field_cardinality_violation(custom_field, row['node_id'], field_definitions[custom_field]['cardinality'])
                        field_values = field_values[:field_definitions[custom_field]['cardinality']]
                    entity[custom_field] = field_values
                else:
                    entity[custom_field] = subvalues

            if config['update_mode'] == 'append':
                subvalues = split_geolocation_string(config, row[custom_field])
                if config['subdelimiter'] in row[custom_field]:
                    for subvalue in subvalues:
                        entity_field_values.append(subvalue)
                    if len(entity[custom_field]) > int(field_definitions[custom_field]['cardinality']):
                        entity[custom_field] = entity_field_values[:field_definitions[custom_field]['cardinality']]
                        log_field_cardinality_violation(custom_field, row['node_id'], field_definitions[custom_field]['cardinality'])
                else:
                    for subvalue in subvalues:
                        entity_field_values.append(subvalue)
                    if len(entity_field_values) > int(field_definitions[custom_field]['cardinality']):
                        entity[custom_field] = entity_field_values[:field_definitions[custom_field]['cardinality']]
                        log_field_cardinality_violation(custom_field, row['node_id'], field_definitions[custom_field]['cardinality'])

        return entity


class LinkField():
    """Functions for handling fields with 'link' Drupal field data type.
       All functions return a "entity" dictionary that is passed to Requests'
       "json" parameter.

       Note: this class assumes that the entity has the field identified in 'custom_field'.
       Callers should pre-emptively confirm that. For an example, see code near the top
       of workbench.update().
    """
    def create(self, config, field_definitions, entity, row, custom_field):
        """Parameters
           ----------
            config : dict
                The configuration object defined by set_config_defaults().
            field_definitions : dict
                The field definitions object defined by get_field_definitions().
            entity : dict
                The dict that will be POSTed to Drupal as JSON.
            row : OrderedDict.
                The current CSV record.
            custom_field : string
                The Drupal fieldname/CSV column header.
            Returns
            -------
            dictionary
                A dictionary represeting the entity that is POSTed to Drupal as JSON.
        """
        id_field = row[config['id_field']]
        # Cardinality is unlimited.
        if field_definitions[custom_field]['cardinality'] == -1:
            if config['subdelimiter'] in row[custom_field]:
                subvalues = split_link_string(config, row[custom_field])
                entity[custom_field] = subvalues
            else:
                field_value = split_link_string(config, row[custom_field])
                entity[custom_field] = field_value
        # Cardinality has a limit, including 1.
        else:
            if config['subdelimiter'] in row[custom_field]:
                subvalues = split_link_string(config, row[custom_field])
                if len(subvalues) > int(field_definitions[custom_field]['cardinality']):
                    subvalues = subvalues[:field_definitions[custom_field]['cardinality']]
                    log_field_cardinality_violation(custom_field, id_field, field_definitions[custom_field]['cardinality'])
                entity[custom_field] = subvalues
            else:
                field_value = split_link_string(config, row[custom_field])
                entity[custom_field] = field_value

        return entity

    def update(self, config, field_definitions, entity, row, custom_field, entity_field_values):
        """Note: this method appends incoming CSV values to existing values, replaces existing field
           values with incoming values, or deletes all values from fields, depending on whether
           config['update_mode'] is 'append', 'replace', or 'delete'. It doesn not replace individual
           values within fields.
        """
        """Parameters
           ----------
            config : dict
                The configuration object defined by set_config_defaults().
            field_definitions : dict
                The field definitions object defined by get_field_definitions().
            entity : dict
                The dict that will be POSTed to Drupal as JSON.
            row : OrderedDict.
                The current CSV record.
            custom_field : string
                The Drupal fieldname/CSV column header.
            entity_field_values : list
                List of dictionaries containing existing value(s) for custom_field in the entity being updated.
            Returns
            -------
            dictionary
                A dictionary represeting the entity that is PATCHed to Drupal as JSON.
        """
        if config['update_mode'] == 'delete':
            entity[custom_field] = []
            return entity

        # Cardinality is unlimited.
        if field_definitions[custom_field]['cardinality'] == -1:
            if config['update_mode'] == 'replace':
                if config['subdelimiter'] in row[custom_field]:
                    field_values = []
                    subvalues = split_link_string(config, row[custom_field])
                    for subvalue in subvalues:
                        field_values.append(subvalue)
                    entity[custom_field] = field_values
                else:
                    field_value = split_link_string(config, row[custom_field])
                    entity[custom_field] = field_value
            if config['update_mode'] == 'append':
                if config['subdelimiter'] in row[custom_field]:
                    field_values = []
                    subvalues = split_link_string(config, row[custom_field])
                    for subvalue in subvalues:
                        field_values.append(subvalue)
                    if custom_field in entity:
                        for field_subvalue in field_values:
                            entity_field_values.append(field_subvalue)
                        entity[custom_field] = entity_field_values
                else:
                    field_value = split_link_string(config, row[custom_field])
                    if custom_field in entity:
                        for field_subvalue in field_value:
                            entity_field_values.append(field_subvalue)
                        entity[custom_field] = entity_field_values
        # Cardinality has a limit.
        else:
            if config['update_mode'] == 'replace':
                if config['subdelimiter'] in row[custom_field]:
                    field_values = []
                    subvalues = split_link_string(config, row[custom_field])
                    if len(subvalues) > int(field_definitions[custom_field]['cardinality']):
                        log_field_cardinality_violation(custom_field, row['node_id'], field_definitions[custom_field]['cardinality'])
                    subvalues = subvalues[:field_definitions[custom_field]['cardinality']]
                    for subvalue in subvalues:
                        field_values.append(subvalue)
                    entity[custom_field] = field_values
                else:
                    field_value = split_link_string(config, row[custom_field])
                    entity[custom_field] = field_value
            if config['update_mode'] == 'append':
                subvalues = split_link_string(config, row[custom_field])
                for subvalue in subvalues:
                    entity_field_values.append(subvalue)
                entity[custom_field] = entity_field_values[:field_definitions[custom_field]['cardinality']]
                if len(entity[custom_field]) > int(field_definitions[custom_field]['cardinality']):
                    log_field_cardinality_violation(custom_field, row['node_id'], field_definitions[custom_field]['cardinality'])

        return entity


class EntityReferenceField():
    """Functions for handling fields with 'entity_reference' Drupal field data type.
       All functions return a "entity" dictionary that is passed to Requests' "json"
       parameter.

       Note: this class assumes that the entity has the field identified in 'custom_field'.
       Callers should pre-emptively confirm that. For an example, see code near the top
       of workbench.update().
    """
    def create(self, config, field_definitions, entity, row, custom_field):
        """Parameters
           ----------
            config : dict
                The configuration object defined by set_config_defaults().
            field_definitions : dict
                The field definitions object defined by get_field_definitions().
            entity : dict
                The dict that will be POSTed to Drupal as JSON.
            row : OrderedDict.
                The current CSV record.
            custom_field : string
                The Drupal fieldname/CSV column header.
            Returns
            -------
            dictionary
                A dictionary represeting the entity that is POSTed to Drupal as JSON.
        """
        id_field = row[config['id_field']]
        if field_definitions[custom_field]['target_type'] == 'taxonomy_term':
            target_type = 'taxonomy_term'
            field_vocabs = get_field_vocabularies(config, field_definitions, custom_field)
            if config['subdelimiter'] in row[custom_field]:
                prepared_tids = []
                delimited_values = row[custom_field].split(config['subdelimiter'])
                for delimited_value in delimited_values:
                    tid = prepare_term_id(config, field_vocabs, delimited_value)
                    if value_is_numeric(tid):
                        tid = str(tid)
                        prepared_tids.append(tid)
                    else:
                        continue
                row[custom_field] = config['subdelimiter'].join(prepared_tids)
            else:
                row[custom_field] = prepare_term_id(config, field_vocabs, row[custom_field])
                if value_is_numeric(row[custom_field]):
                    row[custom_field] = str(row[custom_field])

        if field_definitions[custom_field]['target_type'] == 'node':
            target_type = 'node_type'

        if field_definitions[custom_field]['target_type'] == 'media':
            target_type = 'media_type'

        # Cardinality is unlimited.
        if field_definitions[custom_field]['cardinality'] == -1:
            if config['subdelimiter'] in row[custom_field]:
                field_values = []
                subvalues = row[custom_field].split(config['subdelimiter'])
                for subvalue in subvalues:
                    field_values.append({'target_id': subvalue, 'target_type': target_type})
                entity[custom_field] = field_values
            else:
                entity[custom_field] = [{'target_id': row[custom_field], 'target_type': target_type}]
        # Cardinality has a limit.
        elif field_definitions[custom_field]['cardinality'] > 0:
            if config['subdelimiter'] in row[custom_field]:
                field_values = []
                subvalues = row[custom_field].split(config['subdelimiter'])
                for subvalue in subvalues:
                    field_values.append({'target_id': subvalue, 'target_type': target_type})
                if len(field_values) > int(field_definitions[custom_field]['cardinality']):
                    entity[custom_field] = field_values[:field_definitions[custom_field]['cardinality']]
                    log_field_cardinality_violation(custom_field, id_field, field_definitions[custom_field]['cardinality'])
                else:
                    entity[custom_field] = field_values
            else:
                entity[custom_field] = [{'target_id': row[custom_field], 'target_type': target_type}]
        # Cardinality is 1.
        else:
            subvalues = row[custom_field].split(config['subdelimiter'])
            entity[custom_field] = [{'target_id': subvalues[0], 'target_type': target_type}]
            if len(subvalues) > 1:
                log_field_cardinality_violation(custom_field, id_field, '1')

        return entity

    def update(self, config, field_definitions, entity, row, custom_field, entity_field_values):
        """Note: this method appends incoming CSV values to existing values, replaces existing field
           values with incoming values, or deletes all values from fields, depending on whether
           config['update_mode'] is 'append', 'replace', or 'delete'. It doesn not replace individual
           values within fields.
        """
        """Parameters
           ----------
            config : dict
                The configuration object defined by set_config_defaults().
            field_definitions : dict
                The field definitions object defined by get_field_definitions().
            entity : dict
                The dict that will be POSTed to Drupal as JSON.
            row : OrderedDict.
                The current CSV record.
            custom_field : string
                The Drupal fieldname/CSV column header.
            entity_field_values : list
                List of dictionaries containing existing value(s) for custom_field in the entity being updated.
            Returns
            -------
            dictionary
                A dictionary represeting the entity that is PATCHed to Drupal as JSON.
        """
        if config['update_mode'] == 'delete':
            entity[custom_field] = []
            return entity

        if field_definitions[custom_field]['target_type'] == 'taxonomy_term':
            target_type = 'taxonomy_term'
            field_vocabs = get_field_vocabularies(config, field_definitions, custom_field)
            if config['subdelimiter'] in row[custom_field]:
                prepared_tids = []
                delimited_values = row[custom_field].split(config['subdelimiter'])
                for delimited_value in delimited_values:
                    tid = prepare_term_id(config, field_vocabs, delimited_value)
                    if value_is_numeric(tid):
                        tid = str(tid)
                        prepared_tids.append(tid)
                    else:
                        continue
                row[custom_field] = config['subdelimiter'].join(prepared_tids)
            else:
                row[custom_field] = prepare_term_id(config, field_vocabs, row[custom_field])
                if value_is_numeric(row[custom_field]):
                    row[custom_field] = str(row[custom_field])

        if field_definitions[custom_field]['target_type'] == 'node':
            target_type = 'node_type'

        # Cardinality has a limit.
        if field_definitions[custom_field]['cardinality'] > 0:
            if config['update_mode'] == 'replace':
                if config['subdelimiter'] in row[custom_field]:
                    field_values = []
                    subvalues = row[custom_field].split(config['subdelimiter'])
                    for subvalue in subvalues:
                        field_values.append({'target_id': subvalue, 'target_type': target_type})
                    if len(field_values) > int(field_definitions[custom_field]['cardinality']):
                        entity[custom_field] = field_values[:field_definitions[custom_field]['cardinality']]
                        log_field_cardinality_violation(custom_field, row['node_id'], field_definitions[custom_field]['cardinality'])
                    else:
                        entity[custom_field] = field_values
                else:
                    entity[custom_field] = [{'target_id': row[custom_field], 'target_type': target_type}]
            if config['update_mode'] == 'append':
                if config['subdelimiter'] in row[custom_field]:
                    subvalues = row[custom_field].split(config['subdelimiter'])
                    for subvalue in subvalues:
                        entity_field_values.append({'target_id': subvalue, 'target_type': target_type})
                    if len(entity_field_values) > int(field_definitions[custom_field]['cardinality']):
                        entity[custom_field] = entity_field_values[:field_definitions[custom_field]['cardinality']]
                        log_field_cardinality_violation(custom_field, row['node_id'], field_definitions[custom_field]['cardinality'])
                    else:
                        entity[custom_field] = entity_field_values
                else:
                    entity_field_values.append({'target_id': row[custom_field], 'target_type': target_type})
                    if len(entity_field_values) > int(field_definitions[custom_field]['cardinality']):
                        entity[custom_field] = entity_field_values[:field_definitions[custom_field]['cardinality']]
                        log_field_cardinality_violation(custom_field, row['node_id'], field_definitions[custom_field]['cardinality'])
                    else:
                        entity[custom_field] = entity_field_values

        # Cardinality is unlimited.
        else:
            if config['update_mode'] == 'replace':
                if config['subdelimiter'] in row[custom_field]:
                    field_values = []
                    subvalues = row[custom_field].split(config['subdelimiter'])
                    for subvalue in subvalues:
                        field_values.append({'target_id': subvalue, 'target_type': target_type})
                        entity[custom_field] = field_values
                else:
                    entity[custom_field] = [{'target_id': row[custom_field], 'target_type': target_type}]
            if config['update_mode'] == 'append':
                if config['subdelimiter'] in row[custom_field]:
                    field_values = []
                    subvalues = row[custom_field].split(config['subdelimiter'])
                    for subvalue in subvalues:
                        entity_field_values.append({'target_id': subvalue, 'target_type': target_type})
                    entity[custom_field] = entity_field_values
                else:
                    entity_field_values.append({'target_id': row[custom_field], 'target_type': target_type})
                    entity[custom_field] = entity_field_values

        return entity


class TypedRelationField():
    """Functions for handling fields with 'typed_relation' Drupal field data type.
       All functions return a "entity" dictionary that is passed to Requests' "json"
       parameter.

       Currently this field type only supports Typed Relation Taxonomies (not other
       Typed Relation entity types).

       Note: this class assumes that the entity has the field identified in 'custom_field'.
       Callers should pre-emptively confirm that. For an example, see code near the top
       of workbench.update().
    """
    def create(self, config, field_definitions, entity, row, custom_field):
        """Parameters
           ----------
            config : dict
                The configuration object defined by set_config_defaults().
            field_definitions : dict
                The field definitions object defined by get_field_definitions().
            entity : dict
                The dict that will be POSTed to Drupal as JSON.
            row : OrderedDict.
                The current CSV record.
            custom_field : string
                The Drupal fieldname/CSV column header.
            Returns
            -------
            dictionary
                A dictionary represeting the entity that is POSTed to Drupal as JSON.
        """
        id_field = row[config['id_field']]
        # Currently only supports Typed Relation taxonomy entities.
        if field_definitions[custom_field]['target_type'] == 'taxonomy_term':
            target_type = 'taxonomy_term'
            field_vocabs = get_field_vocabularies(config, field_definitions, custom_field)
            # Cardinality is unlimited.
            if field_definitions[custom_field]['cardinality'] == -1:
                field_values = []
                subvalues = split_typed_relation_string(config, row[custom_field], target_type)
                if config['subdelimiter'] in row[custom_field]:
                    for subvalue in subvalues:
                        subvalue['target_id'] = prepare_term_id(config, field_vocabs, subvalue['target_id'])
                        field_values.append(subvalue)
                    entity[custom_field] = field_values
                else:
                    subvalues[0]['target_id'] = prepare_term_id(config, field_vocabs, subvalues[0]['target_id'])
                    entity[custom_field] = subvalues
            # Cardinality has a limit.
            elif field_definitions[custom_field]['cardinality'] > 1:
                if config['subdelimiter'] in row[custom_field]:
                    field_values = []
                    subvalues = split_typed_relation_string(config, row[custom_field], target_type)
                    if len(subvalues) > field_definitions[custom_field]['cardinality']:
                        log_field_cardinality_violation(custom_field, id_field, field_definitions[custom_field]['cardinality'])
                        subvalues = subvalues[:field_definitions[custom_field]['cardinality']]
                    for subvalue in subvalues:
                        subvalue['target_id'] = prepare_term_id(config, field_vocabs, subvalue['target_id'])
                        field_values.append(subvalue)
                    entity[custom_field] = field_values
                else:
                    field_value = split_typed_relation_string(config, row[custom_field], target_type)
                    field_value[0]['target_id'] = prepare_term_id(config, field_vocabs, field_value[0]['target_id'])
                    entity[custom_field] = field_value
            # Cardinality is 1.
            else:
                subvalues = split_typed_relation_string(config, row[custom_field], target_type)
                subvalues[0]['target_id'] = prepare_term_id(config, field_vocabs, subvalues[0]['target_id'])
                entity[custom_field] = [subvalues[0]]
                if len(subvalues) > 1:
                    log_field_cardinality_violation(custom_field, id_field, '1')

        return entity

    def update(self, config, field_definitions, entity, row, custom_field, entity_field_values):
        """Note: this method appends incoming CSV values to existing values, replaces existing field
           values with incoming values, or deletes all values from fields, depending on whether
           config['update_mode'] is 'append', 'replace', or 'delete'. It doesn not replace individual
           values within fields.
        """
        """Parameters
           ----------
            config : dict
                The configuration object defined by set_config_defaults().
            field_definitions : dict
                The field definitions object defined by get_field_definitions().
            entity : dict
                The dict that will be POSTed to Drupal as JSON.
            row : OrderedDict.
                The current CSV record.
            custom_field : string
                The Drupal fieldname/CSV column header.
            entity_field_values : list
                List of dictionaries containing existing value(s) for custom_field in the entity being updated.
            Returns
            -------
            dictionary
                A dictionary represeting the entity that is PATCHed to Drupal as JSON.
        """
        if config['update_mode'] == 'delete':
            entity[custom_field] = []
            return entity

        # Currently only supports Typed Relation taxonomy entities.
        if field_definitions[custom_field]['target_type'] == 'taxonomy_term':
            target_type = 'taxonomy_term'
            field_vocabs = get_field_vocabularies(config, field_definitions, custom_field)

        # Cardinality has a limit.
        if field_definitions[custom_field]['cardinality'] > 0:
            if config['update_mode'] == 'replace':
                subvalues = split_typed_relation_string(config, row[custom_field], target_type)
                if config['subdelimiter'] in row[custom_field]:
                    field_values = []
                    for subvalue in subvalues:
                        subvalue['target_id'] = prepare_term_id(config, field_vocabs, subvalue['target_id'])
                        field_values.append(subvalue)
                    if len(field_values) > int(field_definitions[custom_field]['cardinality']):
                        field_values = field_values[:field_definitions[custom_field]['cardinality']]
                        log_field_cardinality_violation(custom_field, row['node_id'], field_definitions[custom_field]['cardinality'])
                    entity[custom_field] = field_values
                else:
                    subvalues[0]['target_id'] = prepare_term_id(config, field_vocabs, subvalues[0]['target_id'])
                    entity[custom_field] = subvalues
            if config['update_mode'] == 'append':
                if config['subdelimiter'] in row[custom_field]:
                    field_values = []
                    subvalues = split_typed_relation_string(config, row[custom_field], target_type)
                    for subvalue in subvalues:
                        subvalue['target_id'] = prepare_term_id(config, field_vocabs, subvalue['target_id'])
                        entity_field_values.append(subvalue)
                    if len(entity_field_values) > int(field_definitions[custom_field]['cardinality']):
                        entity[custom_field] = entity_field_values[:field_definitions[custom_field]['cardinality']]
                        log_field_cardinality_violation(custom_field, row['node_id'], field_definitions[custom_field]['cardinality'])
                    else:
                        entity[custom_field] = entity_field_values
                else:
                    csv_typed_relation_value = split_typed_relation_string(config, row[custom_field], target_type)
                    csv_typed_relation_value[0]['target_id'] = prepare_term_id(config, field_vocabs, csv_typed_relation_value[0]['target_id'])
                    entity_field_values.append(csv_typed_relation_value[0])
                    if len(entity_field_values) > int(field_definitions[custom_field]['cardinality']):
                        entity[custom_field] = entity_field_values[:field_definitions[custom_field]['cardinality']]
                        log_field_cardinality_violation(custom_field, row['node_id'], field_definitions[custom_field]['cardinality'])
                    else:
                        entity[custom_field] = entity_field_values

        # Cardinality is unlimited.
        else:
            if config['update_mode'] == 'replace':
                subvalues = split_typed_relation_string(config, row[custom_field], target_type)
                if config['subdelimiter'] in row[custom_field]:
                    field_values = []
                    for subvalue in subvalues:
                        subvalue['target_id'] = prepare_term_id(config, field_vocabs, subvalue['target_id'])
                        field_values.append(subvalue)
                    entity[custom_field] = field_values
                else:
                    subvalues[0]['target_id'] = prepare_term_id(config, field_vocabs, subvalues[0]['target_id'])
                    entity[custom_field] = subvalues
            if config['update_mode'] == 'append':
                subvalues = split_typed_relation_string(config, row[custom_field], target_type)
                if config['subdelimiter'] in row[custom_field]:
                    field_values = []
                    for subvalue in subvalues:
                        subvalue['target_id'] = prepare_term_id(config, field_vocabs, subvalue['target_id'])
                        entity_field_values.append(subvalue)
                    entity[custom_field] = entity_field_values
                else:
                    subvalues[0]['target_id'] = prepare_term_id(config, field_vocabs, subvalues[0]['target_id'])
                    entity_field_values.append(subvalues[0])
                    entity[custom_field] = entity_field_values

        return entity
