# filename: Dockerfile
FROM python:3.10.6

# Build the image and name it workbench-docker-image-name (or whatever you want)
# docker build --build-arg USER_ID=$(id -u) --build-arg GROUP_ID=$(id -g) -t workbench-docker .

# Build the container from the built image and run workbench:
# docker run -it --rm --network="host" -v .:/workbench --name update_existing_objects workbench-docker bash -lc "./workbench --config /workbench/prod/update_islandora_objects.yml --check"
# Another example but with mounted directories for the migration to have access to.
# docker run -it --rm --network="host" -v .:/workbench -v /path/to/your/tmp:/tmp -v /path/to/your/files:/mnt/data/local --name update_existing_objects workbench-docker bash -lc "./workbench --config /workbench/prod/update_islandora_objects.yml --check"
# To export a CSV file, that includes the available Drupal fields, run:
# docker run -it --rm --network="host" -v .:/workbench --name workbench-docker-container-name workbench-docker-image-name bash -lc "./workbench --config /workbench/islandora_workbench_demo_content/idc_example_geo.yml --get_csv_template"
#   The directory this file is in is mounted within the container at /workbench
#   Rename example.yml to your YML file. 

# Create a non-root user and set up the environment
ARG USER_ID
ARG GROUP_ID

# Create a group with the specified GID
RUN groupadd -g $GROUP_ID dockeruser || true

# Create a user with the specified UID and GID
RUN useradd -m -u $USER_ID -g $GROUP_ID -s /bin/bash dockeruser

# Set the working directory
WORKDIR /workbench

# Copy the current directory contents into the container at /workbench
COPY . /workbench/

# Set ownership and permissions for the non-root user
RUN chown -R $USER_ID:$GROUP_ID /workbench

# Set the PATH environment variable to include .local/bin
ENV PATH=/home/dockeruser/.local/bin:$PATH

# Switch to the non-root user
USER dockeruser

# Install dependencies and setup the environment
RUN python -m pip install --user --upgrade pip setuptools build && \
    python -m pip install --user --no-cache-dir "urllib3>=1.21.1" libmagic && \
    python -m build && \
    python -m pip install --user dist/*.whl
