# filename: Dockerfile
FROM python:3.11.0

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
RUN useradd -l -m -u $USER_ID -g $GROUP_ID -s /bin/bash dockeruser

# Set the working directory
WORKDIR /workbench
RUN chown $USER_ID:$GROUP_ID /workbench

# Set the PATH environment variable to include .local/bin
ENV PATH=/home/dockeruser/.local/bin:$PATH

# Set an environment variable to indicate Workbench is running in a Docker container.
ENV ISLANDORA_WORKBENCH_IS_RUNNING_IN_DOCKER=True

# Install dependencies from the project metadata before copying the application source.
# This layer remains cached when only Workbench's source files change.
COPY --chown=$USER_ID:$GROUP_ID pyproject.toml README.md requirements-docker.txt /workbench/

# USER_ID is supplied as a numeric UID by the documented build command.
# hadolint ignore=DL3066
USER $USER_ID

# Install build and runtime dependencies.
RUN python -m pip install --user --no-cache-dir --requirement requirements-docker.txt && \
    python -m pip install --user --no-cache-dir --only-deps .

# Copy and install the application separately so source changes only invalidate
# the comparatively inexpensive application build layer.
COPY --chown=$USER_ID:$GROUP_ID . /workbench/

RUN python -m build --wheel --no-isolation && \
    python -m pip install --user --no-cache-dir --no-deps dist/*.whl
