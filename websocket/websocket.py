#!/usr/bin/env nix-shell
#!nix-shell -i python3 -p python3Packages.websockets python3Packages.inotify-simple

import asyncio
import websockets
import threading
import os
import time
import random
import inotify_simple


CONNECTIONS = set()

if "WEB_PATH" in os.environ.keys():
    WEB_PATH = os.environ["WEB_PATH"]
else:
    WEB_PATH = "/run/media/user/ST1000/dump/videos/watch-together"

if WEB_PATH[-1] != "/":
    WEB_PATH += "/"

VIDEO_PATH = "videos"
CURRENT_PATH = WEB_PATH + VIDEO_PATH
CURRENT_VIDEO = ""

CURRENT_TIME = 0

IS_PAUSED = False
PAUSED_LAST_TIME = 0

TIME_TO_EXIT = False

PRELOAD_SEGMENTS_COUNT = 0
PRELOAD_TOTAL_SIZE = 0
PRELOAD_IS_UPDATED = False
PRELOAD_REFRESH_MIN_INTERVAL = 30

INOTIFY_WATCH_PATH = ""


def generate_client_name():
    adjectives = [ "admiring", "adoring", "affectionate", "agitated", "amazing", "angry", "awesome", "beautiful", "blissful", "bold", "boring", "brave", "busy", "charming", "clever", "cool", "compassionate", "competent", "condescending", "confident", "cranky", "crazy", "dazzling", "determined", "distracted", "dreamy", "eager", "ecstatic", "elastic", "elated", "elegant", "eloquent", "epic", "exciting", "fervent", "festive", "flamboyant", "focused", "friendly", "frosty", "funny", "gallant", "gifted", "goofy", "gracious", "great", "happy", "hardcore", "heuristic", "hopeful", "hungry", "infallible", "inspiring", "interesting", "intelligent", "jolly", "jovial", "keen", "kind", "laughing", "loving", "lucid", "magical", "mystifying", "modest", "musing", "naughty", "nervous", "nice", "nifty", "nostalgic", "objective", "optimistic", "peaceful", "pedantic", "pensive", "practical", "priceless", "quirky", "quizzical", "recursing", "relaxed", "reverent", "romantic", "sad", "serene", "sharp", "silly", "sleepy", "stoic", "strange", "stupefied", "suspicious", "sweet", "tender", "thirsty", "trusting", "unruffled", "upbeat", "vibrant", "vigilant", "vigorous", "wizardly", "wonderful", "xenodochial", "youthful", "zealous", "zen" ]
    names = [ "agnesi", "albattani", "allen", "almeida", "antonelli", "archimedes", "ardinghelli", "aryabhata", "austin", "babbage", "banach", "banzai", "bardeen", "bartik", "bassi", "beaver", "bell", "benz", "bhabha", "bhaskara", "black", "blackburn", "blackwell", "bohr", "booth", "borg", "bose", "bouman", "boyd", "brahmagupta", "brattain", "brown", "buck", "burnell", "cannon", "carson", "cartwright", "carver", "cerf", "chandrasekhar", "chaplygin", "chatelet", "chatterjee", "chaum", "chebyshev", "clarke", "cohen", "colden", "cori", "cray", "curran", "curie", "darwin", "davinci", "dewdney", "dhawan", "diffie", "dijkstra", "dirac", "driscoll", "dubinsky", "easley", "edison", "einstein", "elbakyan", "elgamal", "elion", "ellis", "engelbart", "euclid", "euler", "faraday", "feistel", "fermat", "fermi", "feynman", "franklin", "gagarin", "galileo", "galois", "ganguly", "gates", "gauss", "germain", "goldberg", "goldstine", "goldwasser", "golick", "goodall", "gould", "greider", "grothendieck", "haibt", "hamilton", "haslett", "hawking", "hellman", "heisenberg", "hermann", "herschel", "hertz", "heyrovsky", "hodgkin", "hofstadter", "hoover", "hopper", "hugle", "hypatia", "ishizaka", "jackson", "jang", "jemison", "jennings", "jepsen", "johnson", "joliot", "jones", "kalam", "kapitsa", "kare", "keldysh", "keller", "kepler", "khayyam", "khorana", "kilby", "kirch", "knuth", "kowalevski", "lalande", "lamarr", "lamport", "leakey", "leavitt", "lederberg", "lehmann", "lewin", "lichterman", "liskov", "lovelace", "lumiere", "mahavira", "margulis", "matsumoto", "maxwell", "mayer", "mccarthy", "mcclintock", "mclaren", "mclean", "mcnulty", "mendel", "mendeleev", "meitner", "meninsky", "merkle", "mestorf", "mirzakhani", "montalcini", "moore", "morse", "murdock", "moser", "napier", "nash", "neumann", "newton", "nightingale", "nobel", "noether", "northcutt", "noyce", "panini", "pare", "pascal", "pasteur", "payne", "perlman", "pike", "poincare", "poitras", "proskuriakova", "ptolemy", "raman", "ramanujan", "ride", "ritchie", "rhodes", "robinson", "roentgen", "rosalind", "rubin", "saha", "sammet", "sanderson", "satoshi", "shamir", "shannon", "shaw", "shirley", "shockley", "shtern", "sinoussi", "snyder", "solomon", "spence", "stonebraker", "sutherland", "swanson", "swartz", "swirles", "taussig", "tereshkova", "tesla", "tharp", "thompson", "torvalds", "tu", "turing", "varahamihira", "vaughan", "villani", "visvesvaraya", "volhard", "wescoff", "wilbur", "wiles", "williams", "williamson", "wilson", "wing", "wozniak", "wright", "wu", "yalow", "yonath", "zhukovsky" ]
    return f"{random.choice(adjectives)}_{random.choice(names)}"


def set_preload_info():
    global PRELOAD_SEGMENTS_COUNT, PRELOAD_TOTAL_SIZE, PRELOAD_IS_UPDATED

    PRELOAD_SEGMENTS_COUNT = 0
    PRELOAD_TOTAL_SIZE = 0

    #segments_dir = f"{CURRENT_PATH}/{CURRENT_VIDEO[:CURRENT_VIDEO.rfind('/')]}/segments/video"
    segments_dir = f"{CURRENT_PATH}/{CURRENT_VIDEO}/segments/video"
    print(f"Counting segments in \"{segments_dir}\"")
    for f in os.listdir(segments_dir):
        if f.endswith(".m4s"):
            PRELOAD_SEGMENTS_COUNT += 1
            PRELOAD_TOTAL_SIZE += os.stat(f"{segments_dir}/{f}").st_size

    PRELOAD_IS_UPDATED = True


def get_available_videos():
    videos = []

    for (root, dirs, files) in os.walk(CURRENT_PATH):
        for f in files:
            if f != "master.m3u8":
                continue

            video_dir = root.replace(f"{CURRENT_PATH}/", "")
            videos.append(video_dir)

    videos.sort()
    return ";".join(videos)


async def send_message_to_all_clients(message, exclude_clients={}, verbose=True):
    disconnected_clients = set()

    # Copy is used here because someone might connect during enumeration and then we'll receive
    # 'RuntimeError: Set changed size during iteration'
    for client in CONNECTIONS.copy():
        if verbose:
            print(f"sending \"{message}\" to client {client.name}")

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
        await send_message_to_all_clients(f"delete_client_info;{client.name}")


async def update_client_info():
    for client in CONNECTIONS.copy():
        await send_message_to_all_clients(f"update_client_info;{client.name};{int(float(client.current_time))};{int(client.paused)}", verbose=False)


def should_update_time():
    if IS_PAUSED or not CURRENT_VIDEO:
        return False

    return True


async def refresh_time():
    global CURRENT_TIME, PRELOAD_IS_UPDATED

    old_video_path = CURRENT_VIDEO
    while not TIME_TO_EXIT:
        if old_video_path != CURRENT_VIDEO:
            old_video_path = CURRENT_VIDEO
            CURRENT_TIME = 0

        if PRELOAD_IS_UPDATED:
            PRELOAD_IS_UPDATED = False
            await send_message_to_all_clients(f"preload_info;{PRELOAD_SEGMENTS_COUNT};{PRELOAD_TOTAL_SIZE}")

        if should_update_time():
            CURRENT_TIME += 1
            await send_message_to_all_clients(f"set_time;{CURRENT_TIME}")

        await update_client_info()
        time.sleep(1)


async def process_request(websocket, arg):
    global CURRENT_VIDEO, CURRENT_TIME, IS_PAUSED, \
        PAUSED_LAST_TIME, PRELOAD_SEGMENTS_COUNT, \
        INOTIFY_WATCH_PATH

    if not websocket in CONNECTIONS:
        websocket.current_time = 0
        websocket.paused = False
        websocket.name = generate_client_name()

        CONNECTIONS.add(websocket)

        if len(CURRENT_VIDEO) > 0:
            await websocket.send(f"set_source;{VIDEO_PATH}/{CURRENT_VIDEO}/master.m3u8")
            await websocket.send(f"preload_info;{PRELOAD_SEGMENTS_COUNT};{PRELOAD_TOTAL_SIZE}")

        await websocket.send(f"client_name;{websocket.name}")
        await websocket.send(f"available_videos;{get_available_videos()}")

    try:
        async for message in websocket:
            array = message.split(";")

            cmd = array[0]
            arg = array[1]

            print(f"Received message \"{array}\"")

            dont_send = False

            if cmd == "set_source":
                video = f"{CURRENT_PATH}/{arg}/master.m3u8"

                print(f"Trying to load \"{video}\"")

                if f"{CURRENT_PATH}/{CURRENT_VIDEO}/master.m3u8" == video:
                    print("Skipping video because it is already loaded.")
                elif os.path.exists(video):
                    message = f"set_source;{VIDEO_PATH}/{arg}/master.m3u8"
                    CURRENT_VIDEO = arg
                    IS_PAUSED = True

                    set_preload_info()
                    await send_message_to_all_clients(f"preload_info;{PRELOAD_SEGMENTS_COUNT};{PRELOAD_TOTAL_SIZE}")

                    INOTIFY_WATCH_PATH = video[:video.rfind("/") + 1] + "segments/video"
                    print(f"INOTIFY_WATCH_PATH='{INOTIFY_WATCH_PATH}'")

                    print(f"Loaded \"{video}\"")
                else:
                    print(f"\"{video}\" not found.")
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
                await send_message_to_all_clients("resync_time;" + str(websocket.current_time))

            if not dont_send:
                await send_message_to_all_clients(message, exclude_clients={websocket})
    except Exception as e:
        print(f"Unexpected exception occured: \"{type(e)}\" ({e})")


async def start_server():
    async with websockets.serve(process_request, "127.0.0.1", 8002, ping_interval=5):
        await asyncio.Future()


def launch_thread_1():
    asyncio.run(start_server())


def launch_thread_2():
    asyncio.run(refresh_time())


def launch_thread_3():
    while not TIME_TO_EXIT:
        cur_watch_path = INOTIFY_WATCH_PATH

        if not cur_watch_path:
            time.sleep(1)
            continue

        print(f"inotify: setting up inotify for \"{cur_watch_path}\"")

        inotify = inotify_simple.INotify()
        watch_flags = inotify_simple.flags.CREATE
        inotify.add_watch(cur_watch_path, watch_flags)

        last_segments_change = time.time()

        while not TIME_TO_EXIT:
            # video was changed, restart inotify
            if cur_watch_path != INOTIFY_WATCH_PATH:
                print("inotify: video changed, restarting inotify watcher")
                break

            for event in inotify.read(timeout=1000):
                (_, mask, _, _) = event

                print(f"inotify: {event}")

                if watch_flags in inotify_simple.flags.from_mask(mask):
                    if time.time() - last_segments_change > PRELOAD_REFRESH_MIN_INTERVAL:
                        set_preload_info()
                        last_segments_change = time.time()

try:
    t1 = threading.Thread(target=launch_thread_1)
    t2 = threading.Thread(target=launch_thread_2)
    t3 = threading.Thread(target=launch_thread_3)

    t1.start()
    t2.start()
    t3.start()
except KeyboardInterrupt:
    print("TIME_TO_EXIT")
    TIME_TO_EXIT = True
    t1.join()
    t2.join()
    t3.join()
