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

echo "Pulling image: ${IMAGE}"
# docker pull
docker pull ${ECR_URI}/dearbelly-cv:latest

# 새 컨테이너 실행
docker run --gpus all -d \
  --name "app-${AFTER_COLOR}" \
  --env-file ./.env \
  -p "${HOST_PORT}:8000" \
  ${ECR_URI}/dearbelly-cv:latest

# 새 컨테이너가 running 될 때까지 대기
for i in $(seq 1 60); do
  if docker ps --filter "name=^/app-${AFTER_COLOR}$" --filter "status=running" --format '{{.Names}}' | grep -q .; then
    echo "New app-${AFTER_COLOR} container is running."
    break
  fi
  sleep 1
  if [ "$i" -eq 60 ]; then
    echo "New container failed to start in time." >&2
    exit 1
  fi
done

# 새로운 컨테이너 확인 후 Nginx 설정 변경
if docker ps --filter "name=app-${AFTER_COMPOSE_COLOR}" --filter "status=running" --format '{{.Names}}' | grep -q .; then
  echo "New app-${AFTER_COMPOSE_COLOR} container is running."
  # reload nginx
  NGINX_ID=$(sudo docker ps --filter "name=nginx" --quiet)
  NGINX_CONFIG="/home/ubuntu/deployment/nginx.conf"

  echo "Switching Nginx upstream config..."
  if ! sed -i "s/app-${BEFORE_COMPOSE_COLOR}:8000/app-${AFTER_COMPOSE_COLOR}:8000/" $NGINX_CONFIG; then
        echo "Error occured: Failed to update Nginx config. Exiting deploy script."
        exit 1
  fi

  echo "Reloding Nginx in Container"
  if ! docker exec $NGINX_ID nginx -s reload; then
    ERR_MSG='Failed to update Nginx config'
    exit 1
  fi

  if ! docker compose restart nginx; then
    ERR_MSG='Failed to reload Nginx'
    exit 1
  fi

  # 이전 컨테이너 종료
  docker stop app-${BEFORE_COMPOSE_COLOR}
  docker rm app-${BEFORE_COMPOSE_COLOR}
  docker image prune -af
fi

echo "Deployment success."
exit 0