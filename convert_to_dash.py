#!/usr/bin/env python3

import argparse
import os
import subprocess
import json
import tqdm
import sys

SUPPORTED_CODECS = {
    "av1": ".webm",
    "x264": ".mp4"
}


def show_ffmpeg_progress_bar(proc, video_duration):
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
            with tqdm.tqdm(total=video_duration) as pbar:
                previous_total = 0
                ffmpeg_speed = ""
                while proc.poll() == None:
                    line = proc.stdout.readline().decode()[:-1]
                    log.write(line + "\n")

                    if line.startswith("speed="):
                        ffmpeg_speed = line
                    if line.startswith("out_time_ms="):
                        total_time_converted = round(int(line.replace("out_time_ms=", "")) / 1000 / 1000)

                        pbar.bar_format = "{l_bar}{bar}| " + convert_to_time(total_time_converted) + "/" + convert_to_time(video_duration) + " [{elapsed} < {remaining}] " + ffmpeg_speed

                        new_total = total_time_converted
                        pbar.update(new_total - previous_total)
                        previous_total = new_total

                if proc.returncode == 0:
                    pbar.update(video_duration - previous_total)
                else:
                    print("ffmpeg returned code", proc.returncode)
                    print("Check \"convert.log\" for errors.")
    except Exception as e:
        print(e)
        subprocess.run("killall ffmpeg", shell=True)
        exit(-1)


def get_track(input_file, track_type):
    tracks = json.loads(subprocess.run(f"ffprobe \"{input_file}\" -show_entries stream=index:stream_tags=language -select_streams {track_type} -of json", shell=True, capture_output=True).stdout.decode())

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


def extract_track(input_file, video_duration, track_num, output_path, add_args=""):
    proc = subprocess.Popen(f"ffmpeg -y -progress pipe:1 -i '{input_file}' -map 0:{track_num} {add_args} '{output_path}'", shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    show_ffmpeg_progress_bar(proc, video_duration)

    return True if proc.returncode == 0 else False


def convert_to_av1(input_file: str, output_file: str, width, height):
    last_slash_position = input_file.rfind("/")
    input_video_dir: str = input_file[:last_slash_position]
    input_file: str = input_file[last_slash_position + 1:]

    last_slash_position = output_file.rfind("/")
    output_video_dir: str = output_file[:last_slash_position]
    output_file: str = output_file[last_slash_position + 1:]

    cmd = f"docker run --privileged -v \"{os.getcwd()}/{output_video_dir}:/output\" -v \"{input_video_dir}:/videos\" --user $(id -u):$(id -g) -it --rm masterofzen/av1an:latest -i \"{input_file}\" -v \" --threads=8 -b 10 --cpu-used=6 --end-usage=q --cq-level=30 --tile-columns=2 --tile-rows=1 --width={width} --height={height}\" -a \" -an -sn -dn\" -o \"/output/{output_file}\""
    proc = subprocess.run(cmd, shell=True)

    return True if proc.returncode == 0 else False


def main():
    try:
        parser = argparse.ArgumentParser(description='Convert video to HLS source.')
        parser.add_argument('-i', "--input_video", required=True, type=str, help='Input video')
        parser.add_argument('-c', "--codec", required=True, type=str, help='Codec to use (av1, x264)')
        parser.add_argument('-o', "--output_path", required=True, type=str, help='Output path')
        parser.add_argument('-m', "--multiple_resolutions", action='store_true', help='Convert to multiple resolutions')
        parser.add_argument('-y', "--replace_existing", action='store_true', help='Overwrite existing output files.')
        args = parser.parse_args()

        video = args.input_video
        subs = video[:video.rfind(".")] + ".vtt"

        if not os.path.exists(video):
            print("Video file not found.")
            exit(-1)

        if not os.path.exists(args.output_path):
            print(f"Output path \"{args.output_path}\" doesn't exist")
            exit(-1)

        if not args.output_path[-1] == "/":
            args.output_path += "/"

        if args.codec not in SUPPORTED_CODECS:
            print(f"Codec \"{args.codec}\" is not supported.")
            print("Supported codecs are:", ", ".join(SUPPORTED_CODECS))
            exit(-1)

        video_duration = int(float(subprocess.run(f"ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 \"{video}\"", shell=True, capture_output=True).stdout.decode()))
        video_resolution = 'x'.join(subprocess.run(f"ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of default=noprint_wrappers=1:nokey=1 \"{video}\"", shell=True, capture_output=True).stdout.decode()[:-1].split("\n"))

        print("Choose audio.")
        audio_track = get_track(video, "a")

        print("Choose subtitle.")
        subtitle_track = get_track(video, "s")

        print("Extracting subtitles...")

        if not extract_track(video, video_duration, subtitle_track, args.output_path + "ru.vtt", "-c:s webvtt"):
            print("Error extracting subtitle track")
            exit(-1)

        print("Extracting audio...")

        if not extract_track(video, video_duration, audio_track, "en.webm", "-c:a libopus -ac 2 -b:a 96k"):
            print("Error extracting audio track")
            exit(-1)

        print("Converting video...")

        resolutions = ["426x240", "640x360", "854x480", "1280x720", "1920x1080"] if args.multiple_resolutions else [video_resolution]

        for resolution in resolutions:
            print(f"Converting \"{video}\" to {resolution} resolution.")
            width, height = resolution.split("x")
            output_file = args.output_path + height + SUPPORTED_CODECS[args.codec]

            if os.path.exists(output_file) and not args.replace_existing:
                print(f"Skipping converting input file \"{video}\" because output file \"{output_file}\" already exists and --replace_existing is not specified.")
                continue

            if args.codec == "av1":
                ret = convert_to_av1(video, output_file, width, height)
            elif args.codec == "x264":
                ret = extract_track(video, video_duration, 0, output_file, f"-c:v libx264 -vf \"scale={width}:{height}\" -movflags +faststart -an")

            if not ret:
                print("Error converting video.")
                exit(-1)

        cmd = f"packager --default_text_language ru --mpd_output manifest.mpd in=en.webm,stream=audio,output=en.webm,language=en in=ru.vtt,stream=text,output=ru.vtt,language=ru"

        for file in os.listdir(args.output_path):
            if file.endswith(SUPPORTED_CODECS[args.codec]) and file[:file.rfind(".")].isdigit():
                cmd += f" in={file},stream=video,output={file}"

        proc = subprocess.run(cmd, shell=True)

        if proc.returncode != 0:
            print("Error packaging to dash.")
            exit(-1)

        print("Done!")
    except Exception as e:
        exc_type, exc_object, exc_traceback = sys.exc_info()
        exc_filename = exc_traceback.tb_frame.f_code.co_filename
        print(f"Unexpected exception happened in \"{exc_filename}\" at line {exc_traceback.tb_lineno}")
        print(f"e = \"{e}\"")
        print(f"type(e) = \"{type(e)}\"")


if __name__ == "__main__":
    main()
