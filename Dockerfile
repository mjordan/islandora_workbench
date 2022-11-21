# filename: Dockerfile
FROM python:3.10.6

# Run this
# $ docker build -t workbench-docker .
# $ docker run -it --rm --network="host" -v $(shell pwd):/workbench --name my-running-workbench workbench-docker bash -lc "(cd /workbench && python setup.py install --user && ./workbench --config hackdoc.yml --check)"

# Works with and without this line
RUN python -m pip install setuptools

# RUN pip install filemagic
RUN pip install urllib3>=1.21.1
RUN pip install libmagic
