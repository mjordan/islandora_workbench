import json
from workbench_utils import *


class SimpleField():
    """Functions for handling fields with text and other "simple" Drupal field data types,
       e.g. fields that have a "{'value': 'xxx'}" structure. All functions return a
       "node" dictionary that is passed to Requests' "json" parameter.
    """
    def create(self, config, field_definitions, node, row, custom_field):
        """Parameters
           ----------
            config : dict
                The configuration object defined by set_config_defaults().
            field_definitions : dict
                The field definitions object defined by get_field_definitions().
            node : dict
                The dict that will be POSTed to Drupal as JSON.
            row : OrderedDict.
                The current CSV record.
            custom_field : string
                The Drupal fieldname/CSV column header.
            Returns
            -------
            dictionary
                A dictionary represeting the node that is POSTed to Drupal as JSON.
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
                node[custom_field] = field_values
            else:
                row[custom_field] = truncate_csv_value(custom_field, id_field, field_definitions[custom_field], row[custom_field])
                node[custom_field] = [{'value': row[custom_field]}]
        # Cardinality has a limit.
        elif int(field_definitions[custom_field]['cardinality']) > 1:
            if config['subdelimiter'] in row[custom_field]:
                field_values = []
                subvalues = row[custom_field].split(config['subdelimiter'])
                if len(subvalues) > int(field_definitions[custom_field]['cardinality']):
                    log_field_cardinality_violation(custom_field, id_field, field_definitions[custom_field]['cardinality'])
                subvalues = subvalues[:field_definitions[custom_field]['cardinality']]
                for subvalue in subvalues:
                    subvalue = truncate_csv_value(custom_field, id_field, field_definitions[custom_field], subvalue)
                    field_values.append({'value': subvalue})
                node[custom_field] = field_values
            else:
                row[custom_field] = truncate_csv_value(custom_field, id_field, field_definitions[custom_field], row[custom_field])
                node[custom_field] = [{'value': row[custom_field]}]
        # Cardinality is 1.
        else:
            subvalues = row[custom_field].split(config['subdelimiter'])
            first_subvalue = subvalues[0]
            first_subvalue = truncate_csv_value(custom_field, id_field, field_definitions[custom_field], first_subvalue)
            node[custom_field] = [{'value': first_subvalue}]
            if len(subvalues) > 1:
                log_field_cardinality_violation(custom_field, id_field, '1')

        return node

    def update(self, config, field_definitions, node, row, custom_field, node_field_values):
        """Note: this method both adds incoming CSV values to existing values and replaces entire
           fields with incoming values, depending on whether config['update_mode'] is 'append'
           or 'replace'. It doesn not replace specific values.
        """
        """Parameters
           ----------
            config : dict
                The configuration object defined by set_config_defaults().
            field_definitions : dict
                The field definitions object defined by get_field_definitions().
            node : dict
                The dict that will be POSTed to Drupal as JSON.
            row : OrderedDict.
                The current CSV record.
            custom_field : string
                The Drupal fieldname/CSV column header.
            node_field_values : list
                List of dictionaries containing value(s) for custom_field in the node being updated.
            Returns
            -------
            dictionary
                A dictionary represeting the node that is POSTed to Drupal as JSON.
        """
        if field_definitions[custom_field]['cardinality'] == 1:
            # Fields with cardinality of 1 are always replaced with incoming values, they are never appended to.
            if custom_field == 'title':
                node[custom_field] = [{'value': row[custom_field]}]
            else:
                if config['update_mode'] == 'delete':
                    node[custom_field] = []
                else:
                    subvalues = row[custom_field].split(config['subdelimiter'])
                    subvalues[0] = truncate_csv_value(custom_field, row['node_id'], field_definitions[custom_field], subvalues[0])
                    node[custom_field] = [{'value': subvalues[0]}]
                    if len(subvalues) > 1:
                        log_field_cardinality_violation(custom_field, row['node_id'], '1')
        elif int(field_definitions[custom_field]['cardinality']) > 1:
            if config['update_mode'] == 'append':
                # Append to existing values.
                if config['subdelimiter'] in row[custom_field]:
                    field_values = []
                    subvalues = row[custom_field].split(config['subdelimiter'])
                    for subvalue in subvalues:
                        subvalue = truncate_csv_value(custom_field, row['node_id'], field_definitions[custom_field], subvalue)
                        field_values.append({'value': subvalue})
                    node[custom_field] = node_field_values + field_values
                    if len(node[custom_field]) > int(field_definitions[custom_field]['cardinality']):
                        log_field_cardinality_violation(custom_field, row['node_id'], field_definitions[custom_field]['cardinality'])
                        node[custom_field] = node[custom_field][:field_definitions[custom_field]['cardinality']]
                else:
                    row[custom_field] = truncate_csv_value(custom_field, row['node_id'], field_definitions[custom_field], row[custom_field])
                    node[custom_field] = node_field_values + [{'value': row[custom_field]}]
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
                        node[custom_field] = field_values
                else:
                    row[custom_field] = truncate_csv_value(custom_field, row['node_id'], field_definitions[custom_field], row[custom_field])
                    node[custom_field] = [{'value': row[custom_field]}]
            if config['update_mode'] == 'delete':
                node[custom_field] = []
        # Cardinatlity is unlimited.
        else:
            if config['update_mode'] == 'append':
                # Append to existing values.
                if config['subdelimiter'] in row[custom_field]:
                    field_values = []
                    subvalues = row[custom_field].split(config['subdelimiter'])
                    for subvalue in subvalues:
                        subvalue = truncate_csv_value(custom_field, row['node_id'], field_definitions[custom_field], subvalue)
                        field_values.append({'value': subvalue})
                        node[custom_field] = node_field_values + field_values
                else:
                    row[custom_field] = truncate_csv_value(custom_field, row['node_id'], field_definitions[custom_field], row[custom_field])
                    node[custom_field] = node_field_values + [{'value': row[custom_field]}]
            if config['update_mode'] == 'replace':
                # Replace existing values.
                if config['subdelimiter'] in row[custom_field]:
                    field_values = []
                    subvalues = row[custom_field].split(config['subdelimiter'])
                    for subvalue in subvalues:
                        subvalue = truncate_csv_value(custom_field, row['node_id'], field_definitions[custom_field], subvalue)
                        field_values.append({'value': subvalue})
                        node[custom_field] = field_values
                else:
                    row[custom_field] = truncate_csv_value(custom_field, row['node_id'], field_definitions[custom_field], row[custom_field])
                    node[custom_field] = [{'value': row[custom_field]}]
            if config['update_mode'] == 'delete':
                node[custom_field] = []

        return node


class GeolocationField():
    """Functions for handling fields with 'geolocation' Drupal field data type.
       All functions return a "node" dictionary that is passed to Requests'
       "json" parameter.
    """
    def create(self, config, field_definitions, node, row, custom_field):
        """Parameters
           ----------
            config : dict
                The configuration object defined by set_config_defaults().
            field_definitions : dict
                The field definitions object defined by get_field_definitions().
            node : dict
                The dict that will be POSTed to Drupal as JSON.
            row : OrderedDict.
                The current CSV record.
            custom_field : string
                The Drupal fieldname/CSV column header.
            Returns
            -------
            dictionary
                A dictionary represeting the node that is POSTed to Drupal as JSON.
        """
        id_field = row[config['id_field']]
        # Cardinality is unlimited.
        if field_definitions[custom_field]['cardinality'] == -1:
            if config['subdelimiter'] in row[custom_field]:
                field_values = []
                subvalues = split_geolocation_string(config, row[custom_field])
                for subvalue in subvalues:
                    field_values.append(subvalue)
                node[custom_field] = field_values
            else:
                field_value = split_geolocation_string(config, row[custom_field])
                node[custom_field] = field_value
        # Cardinality has a limit.
        elif int(field_definitions[custom_field]['cardinality']) > 1:
            if config['subdelimiter'] in row[custom_field]:
                field_values = []
                subvalues = split_geolocation_string(config, row[custom_field])
                subvalues = subvalues[:field_definitions[custom_field]['cardinality']]
                if len(subvalues) > int(field_definitions[custom_field]['cardinality']):
                    log_field_cardinality_violation(custom_field, id_field, field_definitions[custom_field]['cardinality'])
                for subvalue in subvalues:
                    field_values.append(subvalue)
                node[custom_field] = field_values
            else:
                field_value = split_geolocation_string(config, row[custom_field])
                node[custom_field] = field_value
        # Cardinality is 1. Fields with cardinality of 1 are always replaced with
        # incoming values, they are never appended to.
        else:
            field_values = split_geolocation_string(config, row[custom_field])
            if len(field_values) > 1:
                log_field_cardinality_violation(custom_field, id_field, '1')
                field_values = field_values[:1]
            node[custom_field] = field_values

        return node

    def update(self, config, field_definitions, node, row, custom_field, node_field_values):
        """Note: this method both adds incoming CSV values to existing values and replaces entire
           fields with incoming values, depending on whether config['update_mode'] is 'append'
           or 'replace'. It doesn not replace specific values.
        """
        """Parameters
           ----------
            config : dict
                The configuration object defined by set_config_defaults().
            field_definitions : dict
                The field definitions object defined by get_field_definitions().
            node : dict
                The dict that will be POSTed to Drupal as JSON.
            row : OrderedDict.
                The current CSV record.
            custom_field : string
                The Drupal fieldname/CSV column header.
            node_field_values : list
                List of dictionaries containing value(s) for custom_field in the node being updated.
            Returns
            -------
            dictionary
                A dictionary represeting the node that is POSTed to Drupal as JSON.
        """
        # Cardinality is unlimited.
        if field_definitions[custom_field]['cardinality'] == -1:
            if config['update_mode'] == 'replace':
                if config['subdelimiter'] in row[custom_field]:
                    field_values = []
                    subvalues = split_geolocation_string(config, row[custom_field])
                    for subvalue in subvalues:
                        field_values.append(subvalue)
                    node[custom_field] = field_values
                else:
                    field_value = split_geolocation_string(config, row[custom_field])
                    node[custom_field] = field_value
            if config['update_mode'] == 'append':
                if config['subdelimiter'] in row[custom_field]:
                    field_values = []
                    subvalues = split_geolocation_string(config, row[custom_field])
                    for subvalue in subvalues:
                        field_values.append(subvalue)
                    if custom_field in node:
                        node[custom_field] + field_values
                    else:
                        node[custom_field] = field_values
                else:
                    field_value = split_geolocation_string(config, row[custom_field])
                    if custom_field in node:
                        node[custom_field] = node[custom_field] + field_value
                    else:
                        node[custom_field] = field_value
            if config['update_mode'] == 'delete':
                node[custom_field] = []
        # Cardinality has a limit.
        elif int(field_definitions[custom_field]['cardinality']) > 1:
            if config['subdelimiter'] in row[custom_field]:
                field_values = []
                subvalues = split_geolocation_string(config, row[custom_field])
                if len(subvalues) > int(field_definitions[custom_field]['cardinality']):
                    log_field_cardinality_violation(custom_field, row['node_id'], field_definitions[custom_field]['cardinality'])
                subvalues = subvalues[:field_definitions[custom_field]['cardinality']]
                for subvalue in subvalues:
                    field_values.append(subvalue)
                node[custom_field] = field_values
            else:
                field_value = split_geolocation_string(config, row[custom_field])
                node[custom_field] = field_value
        # Cardinality is 1.
        else:
            if config['update_mode'] == 'delete':
                    node[custom_field] = []
            else:
                field_values = split_geolocation_string(config, row[custom_field])
                node[custom_field] = [field_values[0]]
                if len(field_values) > 1:
                    log_field_cardinality_violation(custom_field, row['node_id'], field_definitions[custom_field]['cardinality'])

        return node


class TypedRelationField():
    """Functions for handling fields with 'typed_relation' Drupal field data type.
       All functions return a "node" dictionary that is passed to Requests' "json"
       parameter.
    """
    def create(self, config, field_definitions, node, row, custom_field):
        """Parameters
           ----------
            config : dict
                The configuration object defined by set_config_defaults().
            field_definitions : dict
                The field definitions object defined by get_field_definitions().
            node : dict
                The dict that will be POSTed to Drupal as JSON.
            row : OrderedDict.
                The current CSV record.
            custom_field : string
                The Drupal fieldname/CSV column header.
            Returns
            -------
            dictionary
                A dictionary represeting the node that is POSTed to Drupal as JSON.
        """
        pass

    def update(self, config, field_definitions, node, row, custom_field, node_field_values):
        """Note: this method both adds incoming CSV values to existing values and replaces entire
           fields with incoming values, depending on whether config['update_mode'] is 'append'
           or 'replace'. It doesn not replace specific values.
        """
        """Parameters
           ----------
            config : dict
                The configuration object defined by set_config_defaults().
            field_definitions : dict
                The field definitions object defined by get_field_definitions().
            node : dict
                The dict that will be POSTed to Drupal as JSON.
            row : OrderedDict.
                The current CSV record.
            custom_field : string
                The Drupal fieldname/CSV column header.
            node_field_values : list
                List of dictionaries containing value(s) for custom_field in the node being updated.
            Returns
            -------
            dictionary
                A dictionary represeting the node that is POSTed to Drupal as JSON.
        """
        pass


class EntityReferenceField():
    """Functions for handling fields with 'entity_reference' Drupal field data type.
       All functions return a "node" dictionary that is passed to Requests' "json"
       parameter.
    """
    def create(self, config, field_definitions, node, row, custom_field):
        """Parameters
           ----------
            config : dict
                The configuration object defined by set_config_defaults().
            field_definitions : dict
                The field definitions object defined by get_field_definitions().
            node : dict
                The dict that will be POSTed to Drupal as JSON.
            row : OrderedDict.
                The current CSV record.
            custom_field : string
                The Drupal fieldname/CSV column header.
            Returns
            -------
            dictionary
                A dictionary represeting the node that is POSTed to Drupal as JSON.
        """
        pass

    def update(self, config, field_definitions, node, row, custom_field, node_field_values):
        """Note: this method both adds incoming CSV values to existing values and replaces entire
           fields with incoming values, depending on whether config['update_mode'] is 'append'
           or 'replace'. It doesn not replace specific values.
        """
        """Parameters
           ----------
            config : dict
                The configuration object defined by set_config_defaults().
            field_definitions : dict
                The field definitions object defined by get_field_definitions().
            node : dict
                The dict that will be POSTed to Drupal as JSON.
            row : OrderedDict.
                The current CSV record.
            custom_field : string
                The Drupal fieldname/CSV column header.
            node_field_values : list
                List of dictionaries containing value(s) for custom_field in the node being updated.
            Returns
            -------
            dictionary
                A dictionary represeting the node that is POSTed to Drupal as JSON.
        """
        pass
