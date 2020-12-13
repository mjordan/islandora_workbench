## Deleting media

You can delete media and their associate files by providing a CSV file with a `media_id` column that contains the Drupal IDs of media you want to delete. For example, your CSV file could look like this:

```csv
media_id
100
103
104
```

The config file for update operations looks like this (note the `task` option is 'delete_media'):

```yaml
task: delete_media
host: "http://localhost:8000"
username: admin
password: islandora
input_csv: delete_media.csv
```
