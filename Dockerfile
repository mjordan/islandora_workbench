# filename: Dockerfile
FROM python:3

# Always run this before running `$ docker run ...`
# $ docker build -t workbench-docker .

# Linux Users
----------------------
# $ docker run -it --rm --network="host" --name my-running-workbench workbench-docker bash -lc "(./workbench --config hackdoc.yml --check)"


# Mac & Windows Users
----------------------
# If Islandora is at localhost (Example: http://localhost:8000). Change your YML file
# - From
# host: "localhost:8000"
# - To
# host: "host.docker.internal:8000"

# Then run
# $ docker run -it --rm --name my-running-workbench workbench-docker bash -lc "(./workbench --config hackdoc.yml --check)"

ADD . /

# Works with and without this line
#RUN python -m pip install setuptools

RUN pip install filemagic libmagic
RUN python setup.py install --user
