# Islandora Workbench

A Python port of https://github.com/mjordan/claw_rest_ingester.

## Requirements

* Python 3 or higher
* The [Requests](https://2.python-requests.org/en/master/) library
* An Islandora 8 repository

## Usage

`./workbench --hostname http://localhost:8000 --username admin --password islandora --input_dir input_data --csv_filename metadata.csv --media_use_tid 16 --model_tid 24 --drupal_filesystem fedora://`

where

* `--hostname` is the hostname, including port number if not 80, of your Islandora repository.
* `--username` is the username used to authenticate the requests.
* `--password` is the user's password.
* `--input_dir` is the full or relative path to the directory containing the images and metadata CSV file.
* `--csv_filename` is the filename of the CSV metadata file, which must be in the directory named in '--input_dir'.
* `--media_use_tid` is the term ID for the Media Use term you want to apply to the media.
* `--model_tid` is the term ID for the Model you want your nodes to be.
* `--drupal_filesystem` is either 'fedora://' or 'public://'.

Using the sample data, the output of the sample command above should look something like:

```
Node for 'Small boats in Havana Harbour' created at http://localhost:8000/node/52.
-File media for IMG_1410.tif created.
Node for 'Manhatten Island' created at http://localhost:8000/node/53.
-File media for IMG_2549.jp2 created.
Node for 'Looking across Burrard Inlet' created at http://localhost:8000/node/54.
-Image media for IMG_2940.JPG created.
Node for 'Amsterdam waterfront' created at http://localhost:8000/node/55.
-Image media for IMG_2958.JPG created.
Node for 'Alcatraz Island' created at http://localhost:8000/node/56.
-Image media for IMG_5083.JPG created.
```

## Input data

The directory that contains the data to be ingested (identified by the `--input_dir` argument) needs to be arranged like this:

```
your_folder/
├── image1.JPG
├── pic_saturday.jpg
├── image-27262.jpg
├── IMG_2958.JPG
├── someimage.jpg
└── metadata.csv
```

The names of the files can take any form you want since they are included in the CSV file (which can also be named whatever you want). That file must contain three columns, `file`, `title`, and `description`. The `file` column contains the full filename of the file, and the `title` and `description` columns contain values that will be applied to the nodes.

Files of any extension are allowed.

## Code style

`pycodestyle --show-source --show-pep8 workbench`

## License

The Unlicense.
