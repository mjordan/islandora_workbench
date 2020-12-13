Workbench uses a YAML configuration whose location is indicated in the `--config` parameter. This file defines the various options it will use to create, update, or delete Islandora content (such as which CSV file to use and what directory your images are in). The simplest configuration file would look like this:

```yaml
task: create
host: "http://localhost:8000"
username: admin
password: islandora
```

The settings defined in a configuration file are:

| Setting | Required | Default value | Description |
| --- | --- | --- | --- |
| task | ✔️ | | One of 'create', 'create_from_files', update', delete', 'add_media', or 'delete_media' |
| host | ✔️ | | The hostname, including port number if not 80, of your Islandora repository. |
| username |  ✔️ | | The username used to authenticate the requests. This Drupal user should be a member of the "Administrator" role. If you want to create nodes that are owned by a specific Drupal user, include their numeric user ID in the `uid` column in your CSV. |
| password |  ✔️ | | The user's password. |
| content_type |  | islandora_object | The machine name of the Drupal node content type you are creating or updating. |
| input_dir |  | input_data | The full or relative path to the directory containing the files and metadata CSV file. |
| input_csv |  | metadata.csv | Path to the CSV metadata file. Can be absolute, or if just the filename is provided, will be assumed to be in the directory named in `input_dir`. Can also be the URL to a Google spreadsheet (see the "Using Google Sheets as input data" section below for more information). |
| google_sheets_csv_filename |  | google_sheet.csv | Local CSV filename for data from a Google spreadsheet. See the "Using Google Sheets as input data" section below for more information. |
| log_file_path | | workbench.log | The path to the log file, absolute or relative to `workbench`. See the "Logging" section below for more information. |
| id_field |  | id | The name of the field in the CSV that uniquely identifies each record. |
| delimiter |  | , [comma]| The delimiter used in the CSV file, for example, "," or "\t". If omitted, defaults to ",". |
| subdelimiter |  | &#124; [pipe]| The subdelimiter used in the CSV file to define multiple values in one field. If omitted, defaults to "&#124;". |
| nodes_only |  | false | Include this option in `create` tasks, set to `true`, if you want to only create nodes and not their accompanying media. See the "Creating nodes but not media" section below for more information. 'fedora://'. |
| drupal_filesystem | | fedora:// | One of 'fedora://', 'public://', or 'private://'. |
| output_csv | | | The full or relative path to a CSV file with one record per node created by Workbench. See "The output CSV file" section below for more information. |
| media_use_tid | | `http://pcdm.org/use#OriginalFile`  | The term ID for the term from the "Islandora Media Use" vocabulary you want to apply to the media being created. You can provide a term URI instead of a term ID, for example `"http://pcdm.org/use#OriginalFile"`. |
| media_type [singular] |  | | Overrides, for all media being created, Workbench's default definition of whether the media being created is an image, file, document, audio, or video. Used in the `create`, `add_media`, and `create_from_files` tasks. More detail provided in the "Setting Media Types" section below. |
| media_types [plural] |  | | Overrides default media type definitions on a per file extension basis. Used in the `create`, `add_media`, and `create_from_files` tasks. More detail provided in the "Setting Media Types" section below. |
| allow_missing_files |  | false | Determines if empty `file` values are allowed. If set to true, empty file values are allowed and will result in nodes without attached media. Defaults to false (which means all file values must contain the name of a file that exists in the `input_data` directory). |
| allow_adding_terms |  | false | Determines if Workbench will add taxonomy terms if they do not exist in the target vocabulary. See more information in the "Taxonomy fields" section below. |
| published | | true | Whether nodes are published or not. Applies to `create` task only. Set to false if you want the nodes to be unpublished. Note that whether or not a node is published can also be set at a node level in the CSV file in the status base field, as described in the "Base Fields" section below. Values in the CSV override the value of published set here. |
| validate_title_length |  | true | Whether or not to check if title values in the CSV exceed Drupal's maximum allowed length of 255 characters. Defaults to true. Set to false if you are using a module that lets you override Drupal's maximum title length, such as [Node Title Length](https://www.drupal.org/project/title_length) or [Entity Title Length](https://www.drupal.org/project/entity_title_length). Also, if your task is `update`, you should set this to false if `title` is not one of the fields you are updating. |
| pause |  | | Defines the number of seconds to pause between each REST request to Drupal. Include it in your configuration to lessen the impact of Islandora Workbench on your site during large jobs, for example pause: 1.5. |
| delete_media_with_nodes |  | true | When a node is deleted using a `delete` task, by default, all if its media are automatically deleted. Set this option to false to not delete all of a node's media (you do not generally want to keep the media without the node). |
| paged_content_from_directories |  | false | Set to true if you are using the "Without page-level metadata" method of creating paged content. See the section "Creating paged content" below for more information. |
| paged_content_sequence_seprator |  | - [hyphen]| The character used to separate the page sequence number from the rest of the filename. Used when creating paged content with the "Without page-level metadata" method. See the section "Creating paged content" below for more information. |
| paged_content_page_model_tid |  | | Required if `paged_content_from_directories` is true. The the term ID from the Islandora Models taxonomy to assign to pages. See the section "Creating paged content" below for more information. |
| paged_content_page_display_hints |  | | The term ID from the Islandora Display taxonomy to assign to pages. If not included, defaults to the value of the `field_display_hints` in the parent's record in the CSV file. See the section "Creating paged content" below for more information. |
| paged_content_page_content_type |  | | Set to the machine name of the Drupal node content type for pages created using the "Without page-level metadata" method if it is different than the content type of the parent (which is specified in the content_type setting). See the section "Creating paged content" below for more information. |
| log_json |  | false | Whether or not to log the raw JSON POSTed, PUT, or PATCHed to Drupal. Useful for debugging. |
| user_agent |  | Islandora Workbench | String to use as the User-Agent header in HTTP requests. |
| allow_redirects |  | true | Whether or not to allow Islandora Workbench to respond to HTTP redirects. |
| bootstrap |  | | Absolute path to one or more scripts that execute prior to Workbench connecting to Drupal. Scripts can be in any language, and need to be executable. For an example of using this feature to run a script that generates sample Islandora content, see the "Generating sample Islandora content" section below. |
| model [singular]|  |  | Used in the `create_from_files` task only. Defines the term ID from the the "Islandora Models" vocabulary for all nodes created using this task. Note: one of `model` or `models` is required. More detail provided in the "Creating nodes from files only" section below.|
| models [plural] |  |  | Used in the `create_from_files` task only. Provides a mapping bewteen file extensions and terms in the "Islandora Models" vocabulary. Note: one of `model` or `models` is required. More detail provided in the "Creating nodes from files only" section below.|
| csv_field_templates |  |  | Used in the `create` and `update` tasks only. A list of Drupal field machine names and corresponding values that are copied into the CSV input file. More detail provided in the "Using CSV field templates" section below.|

