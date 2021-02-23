# filename: Dockerfile
FROM python:3.6.9

# Run this
# $ docker build -t workbench-docker .
# $ docker run -it --rm --name my-running-workbench workbench-docker

ADD . /

# Works with and without this line
#RUN python -m pip install setuptools

RUN pip install filemagic libmagic

RUN python setup.py install --user

# CMD [ "python", "workbench", "--config", "config.yml", "--check" ]
CMD [ "python", "workbench", "--config", "hackdoc_demo.yml", "--check" ]
