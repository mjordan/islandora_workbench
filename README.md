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

## Contributing to Workbench

Contributions to Islandora Workbench are welcome, but please open an issue before opening a pull request.

### Testing

Metadata, files, and Drupal configurations are, in the real world, extremly complex and varied. Testing Islandora Workbench in the wild is best way to help make it better for everyone. If you encouter a difficulty, an unexpected behavior, or Workbench crashes on you, reach out on the #islandoraworkbench Slack channel or open an issue in this Github repo.

Using Workbench and reporting problems is the best way you can help make it better!

### Documentation and code

* If you have a suggestion for improving the documentation, please open an issue on [this repository's queue](https://github.com/mjordan/islandora_workbench/issues) and tag your issue "documentation".
* If you want to contribute code (bug fixes, optimizations, new features, etc.), consult the [developer's guide](https://mjordan.github.io/islandora_workbench_docs/development_guide/).

## Current maintainer

[Mark Jordan](https://github.com/mjordan)

## License

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
