# filename: Dockerfile
FROM python:3.10.6

# Build the image and name it workbench-docker-image-name (or whatever you want)
# docker build -t workbench-docker-image-name .

# Build the container from the built image and run workbench:
# docker run -it --rm --network="host" -v $(pwd):/workbench --name workbench-docker-container-name workbench-docker-image-name bash -lc "(./workbench --config example.yml --check)"
# docker run -it --rm --network="host" -v $(pwd)/islandora_workbench:/workbench --name workbench-docker-container-name workbench-docker-image-name bash -lc "./workbench --config /workbench/islandora_workbench_demo_content/example.yml --check"
# To export a CSV file, that includes the available Drupal fields, run:
# docker run -it --rm --network="host" -v $(pwd)/islandora_workbench:/workbench --name workbench-docker-container-name workbench-docker-image-name bash -lc "./workbench --config /workbench/islandora_workbench_demo_content/idc_example_geo.yml --get_csv_template"
#   The directory this file is in is mounted within the container at /workbench
#   Rename example.yml to your YML file. 

ADD . /workbench/
WORKDIR /workbench

# Works with and without this line
RUN python -m pip install setuptools libmagic urllib3>=1.21.1

RUN python setup.py install
