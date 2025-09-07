#!/bin/bash

set -e

ERR_MSG=''

trap 'echo "Error occured: $ERR_MSG. Exiting deploy script."; exit 1' ERR


# 현재 포트 파악
if sudo docker ps --filter "name=app-blue" --quiet | grep -E .; then
  echo "Blue down, Green Up "
  BEFORE_COMPOSE_COLOR="blue"
  AFTER_COMPOSE_COLOR="green"
  HOST_PORT="8001"
else
  echo "Green down, Blue up"
  BEFORE_COMPOSE_COLOR="green"
  AFTER_COMPOSE_COLOR="blue"
  HOST_PORT="8000"
fi

echo "Pulling new image"
# docker pull
docker compose pull app-${AFTER_COMPOSE_COLOR}
docker compose up -d --no-deps --force-recreate app-${AFTER_COMPOSE_COLOR}


# 새 컨테이너가 running 될 때까지 대기
for i in $(seq 1 600); do
  if docker ps --filter "name=^/app-${AFTER_COMPOSE_COLOR}$" --filter "status=running" --format '{{.Names}}' | grep -q .; then
    echo "New app-${AFTER_COLOR} container is running."
    break
  fi
  sleep 1
  if [ "$i" -eq 60 ]; then
    echo "New container failed to start in time." >&2
    exit 1
  fi
done

# 이전 컨테이너 종료 및 정리
if docker ps --filter "name=app-${AFTER_COMPOSE_COLOR}" --filter "status=running" | grep -q .; then
  echo "Stopping old container app-${BEFORE_COMPOSE_COLOR}"
  docker stop app-${BEFORE_COMPOSE_COLOR} || true
  docker rm app-${BEFORE_COMPOSE_COLOR} || true
  docker image prune -af
fi

echo "Deployment success."
exit 0