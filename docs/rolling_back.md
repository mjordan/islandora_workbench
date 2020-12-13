## Rolling back nodes and media

In the `create` and `create_from_files` tasks, Workbench generates a `rollback.yml` configuration file and a `rollback.csv` file in the format described in "Deleting nodes", below. These files allow you to easily roll back (i.e., delete) all the nodes and accompanying media you just created. Specifically, this configuration file defines a `delete` task. See the "Deleting nodes" section below for more information.

To roll back all the nodes and media you just created, run `./workbench --config rollback.yml`.

Note that Workbench overwrites the rollback configuration and CSV files each time it runs, so these files only apply to the most recent `create` and `create_from_files` runs.
