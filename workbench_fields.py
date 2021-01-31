import json
from workbench_utils import *


class Simple():
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
        elif field_definitions[custom_field]['cardinality'] > 1:
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
                List of values for custom_field present in the node being updated.
            Returns
            -------
            dictionary
                A dictionary represeting the node that is POSTed to Drupal as JSON.
        """
        """
        if config['update_mode'] == 'replace':
            pass
        if config['update_mode'] == 'append':
            pass
        pass
        """
        if field_definitions[custom_field]['cardinality'] == 1:
            # Fields with cardinality of 1 are always replaced with incoming values, they are never appended to.
            if custom_field == 'title':
                node[custom_field] = [{'value': row[custom_field]}]
            else:
                subvalues = row[custom_field].split(config['subdelimiter'])
                subvalues[0] = truncate_csv_value(custom_field, row['node_id'], field_definitions[custom_field], subvalues[0])
                node[custom_field] = [{'value': subvalues[0]}]
                if len(subvalues) > 1:
                    log_field_cardinality_violation(custom_field, row['node_id'], '1')
        elif field_definitions[custom_field]['cardinality'] > 1:
            # Append to existing values.
            if config['subdelimiter'] in row[custom_field]:
                field_values = []
                subvalues = row[custom_field].split(config['subdelimiter'])
                if len(subvalues) > int(field_definitions[custom_field]['cardinality']):
                    log_field_cardinality_violation(custom_field, row['node_id'], field_definitions[custom_field]['cardinality'])
                subvalues = subvalues[:field_definitions[custom_field]['cardinality']]
                for subvalue in subvalues:
                    subvalue = truncate_csv_value(custom_field, row['node_id'], field_definitions[custom_field], subvalue)
                    field_values.append({'value': subvalue})
                    node[custom_field] = node_field_values[custom_field] + field_values
            else:
                row[custom_field] = truncate_csv_value(custom_field, row['node_id'], field_definitions[custom_field], row[custom_field])
                node[custom_field] = node_field_values[custom_field] + [{'value': row[custom_field]}]
        # Cardinatlity is unlimited.
        else:
            # Append to existing values.
            if config['subdelimiter'] in row[custom_field]:
                field_values = []
                subvalues = row[custom_field].split(config['subdelimiter'])
                for subvalue in subvalues:
                    subvalue = truncate_csv_value(custom_field, row['node_id'], field_definitions[custom_field], subvalue)
                    field_values.append({'value': subvalue})
                    node[custom_field] = node_field_values[custom_field] + field_values
            else:
                row[custom_field] = truncate_csv_value(
                    custom_field, row['node_id'], field_definitions[custom_field], row[custom_field])
                node[custom_field] = node_field_values[custom_field] + [{'value': row[custom_field]}]

        return node
