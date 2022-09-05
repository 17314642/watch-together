#!/usr/bin/env python

import asyncio
import websockets
import pathlib
import ssl
import subprocess
import threading
import os
import time

CONNECTIONS = set()
TOTAL_CLIENTS = 0

WEB_PATH = "/var/www/html/"
VIDEO_PATH = "videos"
CURRENT_PATH = WEB_PATH + VIDEO_PATH
CURRENT_VIDEO = ""
CURRENT_TIME = 0
IS_PAUSED = False
TIME_TO_EXIT = False

async def send_message_to_all_clients(message, exclude_clients):
    disconnected_clients = set()

    # Copy is used here because someone might connect during enumeration and then we'll receive
    # 'RuntimeError: Set changed size during iteration' if copy is not used
    for client in CONNECTIONS.copy():
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
        await send_message_to_all_clients(f"delete_client_info;{client.id}", exclude_clients={})


async def refresh_time():
    global CURRENT_TIME, CURRENT_VIDEO

    old_video_path = CURRENT_VIDEO
    while not TIME_TO_EXIT:
        if CURRENT_VIDEO != "":
            video_duration = int(float(subprocess.run(f"ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 {CURRENT_PATH}/{CURRENT_VIDEO}", shell=True, capture_output=True).stdout.decode()))

            for current_second in range(video_duration):
                if TIME_TO_EXIT:
                    return

                if old_video_path != CURRENT_VIDEO:
                    old_video_path = CURRENT_VIDEO
                    CURRENT_TIME = 0
                    break

                if not IS_PAUSED:
                    CURRENT_TIME += 1

                await send_message_to_all_clients(f"set_time;{CURRENT_TIME}", exclude_clients={})

                for client in CONNECTIONS.copy():
                    await send_message_to_all_clients(f"update_client_info;{client.id};{client.ip};{int(float(client.current_time))};{int(client.paused)}", exclude_clients={})

                time.sleep(1)


        for client in CONNECTIONS.copy():
            await send_message_to_all_clients(f"update_client_info;{client.id};{client.ip};{int(float(client.current_time))};{int(client.paused)}", exclude_clients={})

        time.sleep(1)


async def process_request(websocket, arg):
    global CURRENT_VIDEO, CURRENT_TIME, IS_PAUSED, TOTAL_CLIENTS

    if not websocket in CONNECTIONS:
        websocket.id = TOTAL_CLIENTS
        websocket.current_time = 0
        websocket.paused = False

        CONNECTIONS.add(websocket)
        TOTAL_CLIENTS += 1

        if len(CURRENT_VIDEO) > 0:
            await websocket.send(f"set_source;{VIDEO_PATH}/{CURRENT_VIDEO}")

    try:
        async for message in websocket:
            array = message.split(";")

            cmd = array[0]
            arg = array[1]

            dont_send = False

            if cmd == "set_source":
                if os.path.exists(f"{CURRENT_PATH}/{arg}"):
                    message = f"set_source;{VIDEO_PATH}/{arg}"
                    CURRENT_VIDEO = arg
                else:
                    dont_send = True
                    await websocket.send("set_source;NOT_FOUND")
            elif cmd == "play":
                IS_PAUSED = False
            elif cmd == "pause":
                IS_PAUSED = True
            elif cmd == "set_time":
                dont_send = True
                CURRENT_TIME = int(float(arg))
            elif cmd == "update_player_info":
                dont_send = True
                websocket.current_time = arg
                websocket.paused = False if array[2] == '0' else True

            if not dont_send:
                await send_message_to_all_clients(message, exclude_clients={websocket})
    except Exception as e:
        print(f"Exception: {e}")


ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
ssl_file = pathlib.Path(__file__).with_name("fullchain.pem")
ssl_key = pathlib.Path(__file__).with_name("privkey.pem")
ssl_context.load_cert_chain(ssl_file, keyfile=ssl_key)
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

async def start_server():
    async with websockets.serve(process_request, "0.0.0.0", 22966, ssl=ssl_context, ping_interval=5):
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
