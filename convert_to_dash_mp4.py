#!/usr/bin/env python3

import argparse
import os
import subprocess
import json
import tqdm

parser = argparse.ArgumentParser(description='Convert video to HLS source.')
parser.add_argument('-i', "--input_video", required=True, type=str, help='Input video')
args = parser.parse_args()

VIDEO = args.input_video
SUBS = VIDEO[:VIDEO.rfind(".")] + ".vtt"

if not os.path.exists(VIDEO):
    print("Video file not found.")
    exit(-1)

VIDEO_DURATION = int(float(subprocess.run(f"ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 \"{VIDEO}\"", shell=True, capture_output=True).stdout.decode()))

with open("duration.txt", "w") as f:
    f.write(str(VIDEO_DURATION))

def show_ffmpeg_progress_bar(proc):
    def convert_to_time(raw_time):
        time_str = {"hours": 0, "minutes": 0, "seconds": 0}

        time_str["hours"] = raw_time // 3600
        time_str["minutes"] = (raw_time - (time_str["hours"] * 60 * 60)) // 60
        time_str["seconds"] = raw_time - (time_str["minutes"] * 60) - (time_str["hours"] * 3600)

        for key in time_str.keys():
            if len(str(time_str[key])) == 1:
                time_str[key] = "0" + str(time_str[key])

        return f"{time_str['hours']}:{time_str['minutes']}:{time_str['seconds']}"

    try:
        with open("convert.log", "w") as log:
            with tqdm.tqdm(total=VIDEO_DURATION) as pbar:
                previous_total = 0
                ffmpeg_speed = ""
                while proc.poll() == None:
                    line = proc.stdout.readline().decode()[:-1]
                    log.write(line + "\n")

                    if line.startswith("speed="):
                        ffmpeg_speed = line
                    if line.startswith("out_time_ms="):
                        total_time_converted = round(int(line.replace("out_time_ms=", "")) / 1000 / 1000)

                        pbar.bar_format = "{l_bar}{bar}| " + convert_to_time(total_time_converted) + "/" + convert_to_time(VIDEO_DURATION) + " [{elapsed} < {remaining}] " + ffmpeg_speed

                        new_total = total_time_converted
                        pbar.update(new_total - previous_total)
                        previous_total = new_total

                if proc.returncode == 0:
                    pbar.update(VIDEO_DURATION - previous_total)
                else:
                    print("ffmpeg returned code", proc.returncode)
                    print("Check \"convert.log\" for errors.")
    except Exception as e:
        print(e)
        subprocess.run("killall ffmpeg", shell=True)
        exit(-1)


def get_track(type):
    tracks = json.loads(subprocess.run(f"ffprobe \"{VIDEO}\" -show_entries stream=index:stream_tags=language -select_streams {type} -of json", shell=True, capture_output=True).stdout.decode())

    track_nums = set()
    for track in tracks['streams']:
        print(f"{track['index']}: {track['tags']['language']}")
        track_nums.add(track['index'])

    while True:
        try:
            track = int(input("Choose track: "))
            if not track in track_nums:
                print("Selected track doesn't exist.")
                continue

            break
        except ValueError:
            print("Type number of track you want to use.")

    return track


def extract_track(num, name, add_args=""):
    if os.path.exists(name):
        print(f"Track \"{name}\" already exists. Do you want to overwrite it?")
        answer = input("Answer (Y/N): ")
        if answer.lower() == "n":
            print("Using existing track for \"{name}\"")
            return True

    proc = subprocess.Popen(f"ffmpeg -y -progress pipe:1 -i '{VIDEO}' -map 0:{num} {add_args} '{name}'", shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    show_ffmpeg_progress_bar(proc)

    return True if proc.returncode == 0 else False

print("Choose audio.")
audio_track = get_track("a")

print("Choose subtitle.")
subtitle_track = get_track("s")

print("Extracting subtitles...")

if not extract_track(subtitle_track, "ru.vtt", "-c:s webvtt"):
    print("Error extracting subtitle track")
    exit(-1)

print("Extracting audio...")

if not extract_track(audio_track, "en.webm", "-c:a libopus -ac 2 -b:a 96k"):
    print("Error extracting audio track")
    exit(-1)

print("Extracting video...")

if not extract_track(0, "1080.mp4", "-c:v libx264 -movflags +faststart -an"):
    print("Error extracting video track")
    exit(-1)

cmd = f"packager --default_text_language ru --mpd_output manifest.mpd in=en.webm,stream=audio,output=en.webm,language=en in=ru.vtt,stream=text,output=ru.vtt,language=ru in=1080.mp4,stream=video,output=1080.mp4"
proc = subprocess.run(cmd, shell=True)

if proc.returncode != 0:
    print("Error packaging to dash.")
    exit(-1)

print("Done!")
