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
input_csv: delete.csv
```

Note that when you delete nodes using this method, all media associated with the nodes are also deleted, unless the `delete_media_with_nodes` configuration option is set to `false` (it defaults to `true`). Typical output produced by a `delete` task looks like this:

```
Node http://localhost:8000/node/89 deleted.
+ Media http://localhost:8000/media/329 deleted.
+ Media http://localhost:8000/media/331 deleted.
+ Media http://localhost:8000/media/335 deleted.
```
Note that taxonomy terms created with new nodes are not removed when you delete the nodes.
