## Generating sample Islandora content

`generate_image_files.py` will generate .png images from a list of titles. It and a sample list of titles are available Workbench's `scripts` directory. Running this script will result in a group of images whose filenames are normalized versions of the lines in the sample title file. You can then load this sample content into Islandora using the `create_from_files` task. If you want to have Workbench generate the sample content automatically, configure the `generate_image_files.py` script as a bootstrap script. See the `autogen_content.yml` configuration file for an example of how to do that.

