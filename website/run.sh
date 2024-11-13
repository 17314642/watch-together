#!/usr/bin/env bash

podman run -d --rm                                      \
    --name watch-together-nginx                         \
    --pod=nginx_proxy                                   \
    -v ./logs:/var/log/nginx                            \
    -v ./nginx-config:/etc/nginx/conf.d/default.conf:ro \
    -v ./www:/usr/share/nginx/html:ro                   \
    -v /run/media/user/ST1000/dump/videos/watch-together/videos:/usr/share/nginx/html/videos:ro \
    nginx:latest
