# Islandora Workbench

A command-line tool that allows creation, updating, and deletion of Islandora content from CSV data. Islandora Workbench is an alternative to using Drupal's built-in Migrate tools for [ingesting Islandora content from CSV files](https://github.com/Islandora/migrate_islandora_csv). Unlike the Migrate tools, Islandora Workbench can be run anywhere - it does not need to run on the Islandora server. The Migrate tools, however, are much more flexible than Islandora Workbench, and can be extended using plugins in ways that Workbench cannot.

Note that this tool is not related in any way to the Drupal contrib module called [Workbench](https://www.drupal.org/project/workbench).

## Features

* Allows creation of Islandora nodes and media, updating of nodes, and deletion of nodes and media from CSV files
* Allows creation of paged/compound content
* Can run from anywhere - it communicates with Drupal via HTTP interfaces
* Can be built as a Docker container, and run from within that container
* Provides robust data validation functionality
* Supports a variety of Drupal entity field types (text, integer, term reference, typed relation, geolocation)
* Can provide a CSV file template based on Drupal content type
* Can use a Google Sheet or an Excel file instead of a local CSV file as input
* Allows assignment of Drupal vocabulary terms using term IDs, term names, or term URIs
* Allows creation of new taxonomy terms from CSV field data, including complex and hierarchical terms
* Allows the assignment of URL aliases
* Allows creation of URL redirects
* Allows adding alt text to images (and updating exisiting alt text)
* Supports transmission fixity auditing for media files
* Cross platform (written in Python, tested on Linux, Mac, and Windows)
* Well tested
* Well documented
* Provides both sensible default configuration values and rich configuration options for power users
* Can be run from within a Docker container.

## Documentation

Complete documentation is [available](https://mjordan.github.io/islandora_workbench_docs/).

## Contributing to Workbench

Metadata, files, and Drupal configurations are, in the real world, extremly complex and varied. Testing Islandora Workbench in the wild is best way to help make it better for everyone. If you encouter a difficulty, an unexpected behavior, or Workbench crashes on you, reach out on the #islandoraworkbench Slack channel or open an issue in this Github repo.

If you have a suggestion for improving the documentation, please open an issue on [this repository's queue](https://github.com/mjordan/islandora_workbench/issues).

If you want to contribute code (bug fixes, optimizations, new features, etc.), consult the [developer's guide](https://mjordan.github.io/islandora_workbench_docs/development_guide/).

Using Workbench and reporting problems is the best way you can help make it better!

## Current maintainer

[Mark Jordan](https://github.com/mjordan)

## License

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
