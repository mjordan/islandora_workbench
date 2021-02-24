# filename: Dockerfile
FROM python:3

# Run this
# $ docker build -t workbench-docker .
# $ docker run -it --rm --name my-running-workbench workbench-docker bash -lc "(./workbench --config hackdoc_demo.yml --check)"

ADD . /

# Works with and without this line
#RUN python -m pip install setuptools

RUN pip install filemagic libmagic
RUN python setup.py install --user
