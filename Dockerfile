# filename: Dockerfile
FROM python:3

# Run this
# $ docker build -t workbench-docker .
# $ docker run -it --rm --network="host" -v $(pwd):/workbench --name my-running-workbench workbench-docker bash -lc "(cd /workbench && python setup.py install --user && ./workbench --config demoBDcreate_all_localhost.yml --check)"

# Works with and without this line
RUN python -m pip install setuptools

RUN pip install filemagic libmagic
