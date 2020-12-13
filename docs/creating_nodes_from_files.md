## Creating nodes from files only

If you want to ingest some files without a metadata CSV you can do so using the `create_from_files`. A common application of this ability is in automated workflows where Islandora objects are created from files saved to a watch folder, and metadata is added later.

Nodes created using this task have only the following properties/fields populated:

* Content type: this is defined in the configuration file, using the `content_type` setting.
* Title: this is derived from the filename minus the extension. Spaces are allowed in the filenames.
* Published: published by default, or overridden in the configuration file using the `published` setting.
* Model: defined in the configuration file using either the `model` or `models` setting.

The media attached to the nodes is the file, with its type (image, document, audio, video, file) assigned by the `media_types` configuration setting and its Media Use tag defined in the `media_use_tid` setting.

The configuration options for the `create_from_files` task are the same as the options used in the `create` task (with one exception: `input_csv` is not required). The only option specific to this task is `models`, which is a mapping from terms IDs (or term URIs) in the "Islandora Models" vocabulary to file extensions. Note that either the  `models` or `model` configuration option is required in the `create_from_files` task. `model` is conventient when all of the objects you are creating are the same Islandora Model. Here is a sample configuration file for this task:

```yaml
task: create_from_files
host: "http://localhost:8000"
username: admin
password: islandora
output_csv: /tmp/output.csv
# model: 25
models:
 - 23: ['zip', 'tar', '']
 - 27: ['pdf', 'doc', 'docx', 'ppt', 'pptx']
 - 25: ['tif', 'tiff', 'jp2', 'png', 'gif', 'jpg', 'jpeg']
 - 22: ['mp3', 'wav', 'aac']
 - 26: ['mp4']
```

You can also use the URIs assigned to terms in the Islandora Models vocabulary, for example:

```yaml
models:
 - 'http://purl.org/coar/resource_type/c_1843': ['zip', 'tar', '']
 - 'https://schema.org/DigitalDocument': ['pdf', 'doc', 'docx', 'ppt', 'pptx']
 - 'http://purl.org/coar/resource_type/c_c513': ['tif', 'tiff', 'jp2', 'png', 'gif', 'jpg', 'jpeg']
 - 'http://purl.org/coar/resource_type/c_18cc': ['mp3', 'wav', 'aac']
 - 'http://purl.org/coar/resource_type/c_12ce': ['mp4']
 ```

In the workflow described at the beginning of this section, you might want to include the `output_csv` option in the configuration file, since the resulting CSV file can be populated with metadata later and used in an `update` task to add it to the stub nodes.
