# Makefile
# using Docker Compose version v2.30.3-desktop.1
# and Ubuntu 24.04

.PHONY: build up remove down logs

# build and start containers
build:
	docker compose up -d --build

# start containers
up:
	docker compose up -d

# remove containers
remove:
	docker compose down

# stop containers
stop:
	docker compose stop

# show logs
logs:
	docker compose logs -f