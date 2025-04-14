USER_ID=`id -u`
GROUP_ID=`id -g`
GIT_COMMIT=`git rev-parse HEAD`

.PHONY: build-islandora-workbench
# This command will build a new image for the current git revision, if none exists
build-islandora-workbench:
	(docker image ls | grep $(GIT_COMMIT)) || $(MAKE) rebuild-islandora-workbench

.PHONY: rebuild-islandora-workbench
# This command will force build a new image for the current git revision, regardless of whether one exists
rebuild-islandora-workbench:
	docker build --build-arg USER_ID=$(USER_ID) --build-arg GROUP_ID=$(GROUP_ID) -t "workbench-docker-$(GIT_COMMIT)" . 

.PHONY: run-workbench-in-docker
# This command will bring up the container and drop you into a shell.
# The current working directory will be mounted at /workbench inside the container.
run-workbench-in-docker: build-islandora-workbench
	docker run -it --rm --network="host" -v $$(pwd):/workbench -v --name "workbench-docker-$(GIT_COMMIT)" bash 