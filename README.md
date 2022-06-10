# Islandora Workbench

A command-line tool that allows creation, updating, and deletion of Islandora content from CSV data. Islandora Workbench is an alternative to using Drupal's built-in Migrate tools for [ingesting Islandora content from CSV files](https://github.com/Islandora/migrate_islandora_csv). Unlike the Migrate tools, Islandora Workbench can be run anywhere - it does not need to run on the Islandora server. The Migrate tools, however, are much more flexible than Islandora Workbench, and can be extended using plugins in ways that Workbench cannot.

Note that this tool is not related in any way to the Drupal contrib module called [Workbench](https://www.drupal.org/project/workbench).

## Features

* Allows creation of Islandora nodes and media, updating of nodes, and deletion of nodes and media from CSV files
* Allows creation of paged/compound content
* Can run from anywhere - it communicates with Drupal via HTTP interfaces
* Provides robust data validation functionality
* Supports a variety of Drupal entity field types (text, integer, term reference, typed relation, geolocation)
* Can provide a CSV file template based on Drupal content type
* Can use a Google Sheet or an Excel file instead of a local CSV file as input
* Allows assignment of Drupal vocabulary terms using term IDs, term names, or term URIs
* Allows creation of new taxonomy terms from CSV field data, including complex and hierarchical terms
* Allows the assignment of URL aliases
* Allows adding alt text to images
* Supports transmission fixity auditing for media files
* Cross platform (written in Python, tested on Linux, Mac, and Windows)
* Well tested
* Well documented
* Provides both sensible default configuration values and rich configuration options for power users
* A companion project under development, [Islandora Workbench Desktop](https://github.com/mjordan/islandora_workbench_desktop), will add a graphical user interface that enables users not familiar or comfortable with the command line to use Workbench.

## Documentation

Complete documentation is [available](https://mjordan.github.io/islandora_workbench_docs/).

## Post-merge hook script

Islandora Workbench requires the [Islandora Workbench Integration](https://github.com/mjordan/islandora_workbench_integration) Drupal module, and it is important to keep Workbench and the Integration module in sync. When you pull in updates to this git repo, the following script will check the repo's log and if it finds the word "module" in the commit message of the last three commits, it will print the message "NOTE: Make sure you are running the latest version of the Islandora Workbench Integration module."

This script will also tell you if you need to run Python's `setup.py` script to install newly added libraries.

```shell
#!/bin/sh
#
# Git hook script that notifies you to update the Islandora Worbench Integration
# module if the last 3 commit messsages contain the word 'module.' Also notifies
# you if you need to run setup.py to install newly added libraries.
#
# To enable this hook, place create a file in your .git/hooks directory named 'post-merge'.

if git log -n3 --format=format:"%s" | grep -qi module; then
    echo "NOTE: Make sure you are running the latest version of the Islandora Workbench Integration module."
fi

if git log -n3 --format=format:"%s" | grep -qi setup; then
    echo "NOTE: You need to run 'python3 setup.py install' to install some newly added Python libraries."
fi
```

To use this reminder, place the script above at `islandora_workbench/.git/hooks/post-merge` and make it executable (i.e., `chmod +x post-merge`).

## Current maintainer

[Mark Jordan](https://github.com/mjordan)

## Contributing to Workbench

Contributions to Islandora Workbench are welcome, but please open an issue before opening a pull request. If you don't open one, I'll ask you to do so.

### Testing

Metadata, files, and Drupal configurations can, in the real world, be extremly complex and varied. Testing Islandora Workbench in the wild is best way to help make it better for everyone. If you encouter a difficulty, an unexpected behavior, or Workbench crashes on you, reach out on the #islandoraworkbench Slack channel or open an issue in this Github repo.

Using Workbench and reporting problems is the best way you can contibute!

## Documentation and code

* If you have a suggestion for improving the documentation, please open an issue on [this repository's queue](https://github.com/mjordan/islandora_workbench/issues) and tag your issue "documentation".
* If you want to contribute code (bug fixes, optimizations, new features, etc.), consult the [developer's guide](https://mjordan.github.io/islandora_workbench_docs/development_guide/).

## License

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
