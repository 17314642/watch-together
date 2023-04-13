#!/usr/bin/env python3

import asyncio
import websockets
import pathlib
import subprocess
import threading
import os
import time
import json

CONNECTIONS = set()
TOTAL_CLIENTS = 0

WEB_PATH = "/media/user/ST1000/Scripts/watch-together/www/"
VIDEO_PATH = "videos"
CURRENT_PATH = WEB_PATH + VIDEO_PATH
CURRENT_VIDEO = ""
CURRENT_TIME = 0
VIDEO_DURATION = 0
QUALITY_LEVELS = ""
IS_PAUSED = False
PAUSED_LAST_TIME = 0
TIME_TO_EXIT = False

async def send_message_to_all_clients(message, exclude_clients={}):
    disconnected_clients = set()

    # Copy is used here because someone might connect during enumeration and then we'll receive
    # 'RuntimeError: Set changed size during iteration' if copy is not used
    for client in CONNECTIONS.copy():
        # print(f"sending \"{message}\" to client {client.id}")
        if len(exclude_clients) > 0:
            if not client in exclude_clients:
                try:
                    await client.send(message)
                except:
                    disconnected_clients.add(client)
        try:
            await client.send(message)
        except:
            disconnected_clients.add(client)

    for client in disconnected_clients:
        CONNECTIONS.discard(client)
        await send_message_to_all_clients(f"delete_client_info;{client.id}")


async def update_client_info():
    for client in CONNECTIONS.copy():
            await send_message_to_all_clients(f"update_client_info;{client.id};{client.remote_address[0]};{int(float(client.current_time))};{int(client.paused)}")


async def refresh_time():
    global CURRENT_TIME, CURRENT_VIDEO

    old_video_path = CURRENT_VIDEO
    while not TIME_TO_EXIT:
        if CURRENT_VIDEO != "":
            while CURRENT_TIME != VIDEO_DURATION:
                if TIME_TO_EXIT:
                    return

                if old_video_path != CURRENT_VIDEO:
                    old_video_path = CURRENT_VIDEO
                    CURRENT_TIME = 0
                    break

                if not IS_PAUSED:
                    CURRENT_TIME += 1

                if VIDEO_DURATION != -1:
                    await send_message_to_all_clients(f"set_time;{CURRENT_TIME}")

                await update_client_info()
                time.sleep(1)


        await update_client_info()
        time.sleep(1)


async def process_request(websocket, arg):
    global CURRENT_VIDEO, CURRENT_TIME, VIDEO_DURATION, QUALITY_LEVELS, IS_PAUSED, PAUSED_LAST_TIME, TOTAL_CLIENTS

    if not websocket in CONNECTIONS:
        websocket.id = TOTAL_CLIENTS
        websocket.current_time = 0
        websocket.paused = False

        CONNECTIONS.add(websocket)
        TOTAL_CLIENTS += 1

        if len(CURRENT_VIDEO) > 0:
            await websocket.send(f"set_source;{VIDEO_PATH}/{CURRENT_VIDEO};{QUALITY_LEVELS}")

    try:
        async for message in websocket:
            array = message.split(";")

            cmd = array[0]
            arg = array[1]

            dont_send = False

            if cmd == "set_source":
                print(f"Trying to load \"{CURRENT_PATH}/{arg}\"")
                if os.path.exists(f"{CURRENT_PATH}/{arg}"):
                    video_info = json.loads(subprocess.run(f"ffprobe -allowed_extensions ALL -v error -select_streams v -show_entries stream -of json {CURRENT_PATH}/{arg}", shell=True, capture_output=True).stdout.decode()[:-1])['streams']

                    # Grab video resolutions, then sort them and convert all of them to strings so join() would work.
                    quality_levels = [ x['height'] for x in video_info ]
                    quality_levels.sort()
                    quality_levels = [ str(x) + "p" for x in quality_levels ]

                    QUALITY_LEVELS = ' '.join(quality_levels)

                    message = f"set_source;{VIDEO_PATH}/{arg};{QUALITY_LEVELS}"
                    CURRENT_VIDEO = arg

                    if arg.endswith("m3u8"):
                        duration_file = arg[:arg.rfind("/") + 1] + "duration.txt"
                        VIDEO_DURATION = int(open(f"{CURRENT_PATH}/{duration_file}").read())
                    else:
                        try:
                            VIDEO_DURATION = int(float(subprocess.run(f"ffprobe -allowed_extensions ALL -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 \"{CURRENT_PATH}/{arg}\"", shell=True, capture_output=True).stdout.decode()))
                        except:
                            VIDEO_DURATION = -1
                else:
                    dont_send = True
                    await websocket.send("set_source;NOT_FOUND")
            elif cmd == "play":
                IS_PAUSED = False
            elif cmd == "pause":
                # Limit pause to once every 2 seconds to try and fix race condition.
                # This is more like a patch than fix.
                if time.time() - PAUSED_LAST_TIME > 2:
                    IS_PAUSED = True
                    PAUSED_LAST_TIME = time.time()
                else:
                    dont_send = True
            elif cmd == "set_time":
                dont_send = True
                CURRENT_TIME = int(float(arg))
            elif cmd == "update_player_info":
                dont_send = True
                websocket.current_time = arg
                websocket.paused = False if array[2] == '0' else True
            elif cmd == "resync_time":
                dont_send = True
                await send_message_to_all_clients("resync_time;" + str(CURRENT_TIME))

            if not dont_send:
                await send_message_to_all_clients(message, exclude_clients={websocket})
    except Exception as e:
        print(f"Exception: {e}")


async def start_server():
    async with websockets.serve(process_request, "0.0.0.0", 8000, ping_interval=5):
        await asyncio.Future()  # run forever


def launch_thread_1():
    asyncio.run(start_server())


def launch_thread_2():
    asyncio.run(refresh_time())


try:
    t1 = threading.Thread(target=launch_thread_1)
    t2 = threading.Thread(target=launch_thread_2)

    t1.start()
    t2.start()
except KeyboardInterrupt:
    TIME_TO_EXIT = True
    t1.join()
    t2.join()
