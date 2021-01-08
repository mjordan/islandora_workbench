# Islandora Workbench

A command-line tool that allows creation, updating, and deletion of Islandora content from CSV data. Islandora Workbench is an alternative to using Drupal's built-in Migrate tools for [ingesting Islandora content from CSV files](https://github.com/Islandora/migrate_islandora_csv). Unlike the Migrate tools, Islandora Workbench can be run anywhere - it does not need to run on the Islandora server. Migrate, however, is much more flexible than Islandora Workbench, and can be extended using plugins in ways that Workbench cannot.

## Features

* Allows creation of Islandora nodes and media, updating of nodes, and deletion of nodes and media from CSV files
* Allows creation of paged/compound content
* Can run from anywhere - it communicates with Drupal via HTTP interfaces
* Provides robust [data validation functionality](https://mjordan.github.io/islandora_workbench_docs/check/)
* Supports a variety of Drupal entity field types (text, integer, term reference, typed relation, geolocation)
* Can provide a CSV file template based on Drupal content type
* Can use a Google Sheet or an Excel file instead of a local CSV file as input
* Allows assignment of Drupal vocabulary terms using term IDs, term names, or term URIs
* Allows creation of new taxonomy terms from CSV field data
* Allows the assignment of URL aliases
* Allows adding alt text to images
* Cross platform (written in Python)
* Well tested
* [Well documented](https://mjordan.github.io/islandora_workbench_docs/)
* Provides both sensible default [configuration](https://mjordan.github.io/islandora_workbench_docs/configuration/) values and rich configuation options for power users
* A companion project under development, [Islandora Workbench Desktop](https://github.com/mjordan/islandora_workbench_desktop), will add a graphical user interface that enables users not familiar or comfortable with the command line to use Workbench.

> This tool is not related in any way to the Drupal contrib module called [Workbench](https://www.drupal.org/project/workbench).

## Documentation

Complete documentation is [available](https://mjordan.github.io/islandora_workbench_docs/).

## Current maintainer

[Mark Jordan](https://github.com/mjordan)

## Contributing

Bug reports, improvements, feature requests, and PRs welcome. Before you open a pull request, please open an issue.

If you open a PR, please check your code with pycodestyle:

`pycodestyle --show-source --show-pep8 --ignore=E402,W504 --max-line-length=200 .`

Also provide tests where applicable. Tests in Workbench fall into two categories:

* Unit tests (that do not require Islandora) which are all in `tests/unit_tests.py` and can be run with `python3 tests/unit_tests.py`
* Integration tests that require a live Islandora instance, which are all in `tests/islandora_tests.py` and can be run with `python3 tests/islandora_tests.py`
   * The [Islandora Playbook](https://github.com/Islandora-Devops/islandora-playbook) is recommended way to deploy the Islandora used in these tests. Note that if an Islandora integration test fails, nodes and taxonomy terms created by the test before it fails may not be removed from Islandora.
   * Some integration tests output text that beings with "Error:." This is normal, it's the text that Workbench outputs when it finds something wrong (which is probably what the test is testing). Successful test (whether they test for success or failure) runs will exit with "OK". If you can figure out how to suppress this output, please visit [this issue](https://github.com/mjordan/islandora_workbench/issues/160).
* If you want to run the tests within a specific class in one of these files, include the class name like this: `python3 tests/unit_tests.py TestCompareStings`

## Contributing to documentation

Contributions to Islandora Workbench's documentation are welcome. If you have a suggestion for improving the documentation, please open an issue on [this repository's queue](https://github.com/mjordan/islandora_workbench/issues) and tag your issue "documentation".

## License

[![License: Unlicense](https://img.shields.io/badge/license-Unlicense-blue.svg)](http://unlicense.org/)
