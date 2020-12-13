## Using CSV field templates

In `create` and `update` tasks, you can configure field templates that are applied to each node as if the fields were present in your CSV file. The templates are configured in the `csv_field_templates` option. An example looks like this:

```
csv_field_templates:
 - field_rights: "The author of this work dedicate any and all copyright interest to the public domain."
 - field_member_of: 205
 - field_model: 25
 - field_tags: 231|257
```

Values in CSV field templates are structured the same as field values in your CSV (e.g., in the example above, `field_tags` is multivalued), and are validated against Drupal's configuration in the same way that values present in your CSV are validated.

If a column with the field name used in a template is present in the CSV file, Workbench ignores the template and uses the data in the CSV file.
