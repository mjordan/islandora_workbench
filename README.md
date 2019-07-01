# Islandora Workbench

A command-line tool that allows management of Islandora content via its REST interface. Started as a Python port of https://github.com/mjordan/claw_rest_ingester, but has additional functionality.

## Requirements

* Python 3 or higher
* The [ruamel.yaml](https://yaml.readthedocs.io/en/latest/index.html) library
* The [Requests](https://2.python-requests.org/en/master/) library
* An [Islandora 8](https://islandora.ca/) repository

## Usage

`./workbench --config config.yml`

where `--config` is the path to a YAML file like this:

```yaml
task: create
host: "http://localhost:8000"
username: admin
password: islandora
input_dir: input_data
input_csv: metadata.csv
delimiter: ","
media_use_tid: 16
drupal_filesystem: "fedora://"
model_tid: 24
```

* `task` is one of 'create' or 'delete'.
* `host` is the hostname, including port number if not 80, of your Islandora repository.
* `username` is the username used to authenticate the requests.
* `password` is the user's password.
* `input_dir` is the full or relative path to the directory containing the images and metadata CSV file.
* `input_csv` is the filename of the CSV metadata file, which must be in the directory named in '--input_dir'.
* `delimiter` is the delimiter used in the CSV file, for example, "," or "\t".
* `media_use_tid` is the term ID for the Media Use term you want to apply to the media.
* `model_tid` is the term ID for the Model you want your nodes to be.
* `drupal_filesystem` is either 'fedora://' or 'public://'.

All of these configuration options are required for the "create" task. The "update", "delete", and "add_media" tasks do not require all of the options, as illustrated below.

## Creating nodes from the sample data

Using the sample data and configuration file, the output of `./workbench --config create.yml` should look something like:

```
Node for 'Small boats in Havana Harbour' created at http://localhost:8000/node/52.
+File media for IMG_1410.tif created.
Node for 'Manhatten Island' created at http://localhost:8000/node/53.
+File media for IMG_2549.jp2 created.
Node for 'Looking across Burrard Inlet' created at http://localhost:8000/node/54.
+Image media for IMG_2940.JPG created.
Node for 'Amsterdam waterfront' created at http://localhost:8000/node/55.
+Image media for IMG_2958.JPG created.
Node for 'Alcatraz Island' created at http://localhost:8000/node/56.
+Image media for IMG_5083.JPG created.
```

## Using your own input data

### The files

The directory that contains the data to be ingested (identified by the `input_dir` config option) needs to be arranged like this:

```
your_folder/
├── image1.JPG
├── pic_saturday.jpg
├── image-27262.jpg
├── IMG_2958.JPG
├── someimage.jpg
└── metadata.csv
```

The names of the image/PDF/video/etc. files can take any form you want since they are included in the `file` column of the CSV file. Files of any extension are allowed.

### The CSV file

Metadata that is added to the nodes is contained in the CSV file. The two required fields are `file` (as mentioned above) and `title`. Field values do not need to be wrapped in double quotation marks (`"`), unless they contain an instance of the delimiter character.

You can include additional fields that will be added to the nodes. The column headings in the CSV file must match machine names of fields that exist in the target Islandora content type. Currently, only text fields can be added, that is, taxonomy terms or referenced entities cannont. For example, using the fields defined by the Islandora Defaults module for the "Repository Item" content type, your CSV file could look like this:

```csv
file,title,field_description,field_rights,field_extent
myfile.jpg,My nice image,"A fine image, yes?",Do whatever you want with it.,There's only one image.
```

## Updating nodes

You can update nodes by providing a CSV file with a `node_id` column plus field data you want to update. The other column headings in the CSV file must match machine names of fields that exist in the target Islandora content type. Currently, only text fields can be added, that is, taxonomy terms or referenced entities cannont. For example, using the fields defined by the Islandora Defaults module for the "Repository Item" content type, your CSV file could look like this:

```csv
node_id,field_description,field_rights
100,This is my new title,I have changed my mind. This item is yours to keep.
```

The config file for update operations looks like this (note the `task` option is 'update'):

```yaml
task: update
host: "http://localhost:8000"
username: admin
password: islandora
input_dir: input_data
input_csv: update.csv
delimiter: ','
```

## Deleting nodes

You can delete nodes by providing a CSV file that contains a single column, `node_id`, like this:

```csv
node_id
95
96
200
```

The config file for update operations looks like this (note the `task` option is 'delete'):

```yaml
task: delete
host: "http://localhost:8000"
username: admin
password: islandora
input_dir: input_data
input_csv: delete.csv
```

## Adding media to nodes

You can add media to nodes by providing a CSV file with a `node_id` column plus a `file` field that contains the name of the file you want to add. For example, your CSV file could look like this:

```csv
node_id,file
100,test.txt
```

The config file for update operations looks like this (note the `task` option is 'add_media'):

```yaml
task: add_media
host: "http://localhost:8000"
username: admin
password: islandora
input_dir: input_data
input_csv: add_media.csv
media_use_tid: 14
drupal_filesystem: "fedora://"
delimiter: ","
```

## Contributing

Bug reports, improvements, feature requests, and PRs welcome. Before you open a pull request, please open an issue.

If you open a PR, please check your code with pycodestyle:

`pycodestyle --show-source --show-pep8 workbench`

## License

The Unlicense.
