#!/usr/bin/env python3

import subprocess
import os

RESOLUTIONS = ["426x240", "640x360", "854x480", "1280x720", "1920x1080"]
OUT_DIRS = [ "3", "4", "5", "6", "7", "8", "9", "10", "11" ]

def convert(filename, outputfile):
    for i, res in enumerate(RESOLUTIONS):
        width, height = res.split("x")

        if os.path.exists(f"{outputfile}/{height}.webm"):
            continue

        cmd = f"docker run --privileged -v \"$(pwd):/videos\" --user $(id -u):$(id -g) -it --rm masterofzen/av1an:latest -i \"{filename}\" -v \" --threads=8 -b 10 --cpu-used=6 --end-usage=q --cq-level=30 --tile-columns=2 --tile-rows=1 --width={width} --height={height}\" -a \" -an -sn -dn\" -o \"{outputfile}/{height}.webm\""
        proc = subprocess.run(cmd, shell=True)

dir = "."
files = []

for path in os.listdir(dir):
    if os.path.isfile(path):
        files.append(path)

files.sort()

for i, filename in enumerate(files):
    print(f"Converting \"{filename}\"")

    """
    if not OUT_DIRS:
        os.makedirs(f"out/{i + 1}", exist_ok=True)
    else:
        os.makedirs(f"out/{OUT_DIRS[i]}", exist_ok=True)

    if not OUT_DIRS:
        convert(f"{filename}", f"out/{i + 1}")
    else:
        convert(f"{filename}", f"out/{OUT_DIRS[i]}")

    continue
    """

    # Extract audio
    subprocess.run(f"ffmpeg -y -i \"{filename}\" -map 0:a:1 -c:a libopus -ac 2 -b:a 96k \"out/{OUT_DIRS[i]}/en.webm\"", shell=True)
    #subprocess.run(f"ffmpeg -y -i \"{filename}\" -map 0:a:0 -c:a libopus -ac 2 \"out/{OUT_DIRS[i]}/ru.webm\"", shell=True)

    # Extract subtitles
    #subprocess.run(f"ffmpeg -y -i \"{filename}\" -map 0:s:0 \"out/{OUT_DIRS[i]}/en.vtt\"", shell=True)
    subprocess.run(f"ffmpeg -y -i \"{filename}\" -map 0:s:0 \"out/{OUT_DIRS[i]}/ru.vtt\"", shell=True)

    previous_dir = os.getcwd()
    os.chdir(f"out/{OUT_DIRS[i]}")

    cmd = ("packager "
           "--mpd_output manifest.mpd "
           "in=en.webm,stream=audio,output=en.webm,language=en "
           #"in=ru.webm,stream=audio,output=ru.webm,language=ru "
           #"in=en.vtt,stream=text,output=en.vtt,language=en "
           "in=ru.vtt,stream=text,output=ru.vtt,language=ru ")

    for res in RESOLUTIONS:
        width, height = res.split("x")
        cmd += f"in={height}.webm,stream=video,output={height}.webm "

    subprocess.run(cmd, shell=True)
    os.chdir(previous_dir)
