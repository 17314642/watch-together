#!/usr/bin/env bash

podman run -d --rm                                                  \
    --name watch-together-websocket                                 \
    --pod=nginx_proxy                                               \
    -v ./:/app:ro                                                   \
    -v /run/media/user/ST1000/dump/videos/watch-together:/videos:ro \
    -e WEB_PATH=/videos                                             \
    alpine:latest /bin/ash /app/alpine_entrypoint.sh
