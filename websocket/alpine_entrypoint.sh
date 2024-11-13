#!/bin/ash

apk update
apk --no-cache add ca-certificates
apk add \
    python3 \
    py3-websockets \
    py3-inotify_simple \
    ffmpeg
python3 /app/websocket.py
