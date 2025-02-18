#!/usr/bin/env python3
"""
Video Silence Remover

This script removes silent parts from video files. It works by:
  1. Extracting the audio track to a temporary WAV file.
  2. Detecting silent intervals using ffmpeg’s silencedetect filter.
  3. Removing the corresponding silent segments (both video and audio)
     from the video file.
  4. Outputting a cleaned video file (default format: MP4).

Usage:
    video_silence_remover.py [-h] [-o OUTPUT]
                              [--noise-threshold NOISE_THRESHOLD]
                              [--min-silence-duration MIN_SILENCE_DURATION]
                              [--margin MARGIN]
                              input_files [input_files ...]

Examples:
    Remove silence from one file and output "movie.mp4":
        ./video_silence_remover.py movie.mkv -o movie.mp4

    Process multiple files (if -o is provided and is a directory, outputs are placed there):
        ./video_silence_remover.py clip1.mp4 clip2.avi

    Customize silence detection parameters:
        ./video_silence_remover.py --noise-threshold -40 --min-silence-duration 1.5 --margin 0.5 video.mkv
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
from typing import List, Tuple

def get_media_duration(filename: str) -> float:
    """
    Retrieve the duration (in seconds) of the given media file using ffprobe.
    """
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        filename
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
    try:
        return float(result.stdout.strip())
    except ValueError:
        return 0.0

def detect_silence_intervals(wav_file: str, noise: str = "-50", duration: float = 2.0, margin: float = 1.0) -> List[Tuple[float, float]]:
    """
    Run ffmpeg silencedetect on the wav file and return a list of silence intervals.
    The noise parameter should be provided as a numeric value (dB). A "dB" suffix is added if missing.
    The returned intervals are ordered from later to earlier in the timeline.
    """
    noise_param = noise if noise.endswith("dB") else noise + "dB"
    cmd = [
        "ffmpeg", "-i", wav_file,
        "-af", f"silencedetect=noise={noise_param}:d={duration}",
        "-f", "null", "-"
    ]
    proc = subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    output = proc.stderr

    silence_starts: List[float] = []
    silence_ends: List[float] = []

    for line in output.splitlines():
        if "silence_start:" in line:
            m = re.search(r"silence_start:\s*([0-9.]+)", line)
            if m:
                silence_starts.append(float(m.group(1)))
        if "silence_end:" in line:
            m = re.search(r"silence_end:\s*([0-9.]+)", line)
            if m:
                silence_ends.append(float(m.group(1)))
    intervals: List[Tuple[float, float]] = []
    # Pair detected starts and ends in reverse order
    for start, end in zip(reversed(silence_starts), reversed(silence_ends)):
        if start != 0:
            start += margin
        intervals.append((start, end))
    return intervals

def remove_silence_segment_video(input_video: str, start: float, end: float) -> None:
    """
    Remove a silent segment from input_video between start and end seconds.
    Both the video and audio streams are trimmed and concatenated.
    The operation overwrites input_video with the new file.
    """
    tmp_out = input_video + ".nosilence.mp4"
    total_duration = get_media_duration(input_video)

    filters = []
    v_segments = []
    a_segments = []
    seg_index = 1

    # If there's a segment before the silence, add it.
    if start > 0:
        filters.append(f"[0:v]trim=0:{start},setpts=PTS-STARTPTS[v{seg_index}]")
        filters.append(f"[0:a]atrim=0:{start},asetpts=PTS-STARTPTS[a{seg_index}]")
        v_segments.append(f"v{seg_index}")
        a_segments.append(f"a{seg_index}")
        seg_index += 1
    # If there's a segment after the silence, add it.
    if end < total_duration:
        filters.append(f"[0:v]trim={end}:{total_duration},setpts=PTS-STARTPTS[v{seg_index}]")
        filters.append(f"[0:a]atrim={end}:{total_duration},asetpts=PTS-STARTPTS[a{seg_index}]")
        v_segments.append(f"v{seg_index}")
        a_segments.append(f"a{seg_index}")

    if not v_segments:
        # If the entire file is silent, copy it as is.
        shutil.copy(input_video, tmp_out)
        os.replace(tmp_out, input_video)
        return

    if len(v_segments) == 1:
        # Only one segment remains; no concatenation required.
        filter_complex = "; ".join(filters)
        map_args = ["-map", f"[{v_segments[0]}]", "-map", f"[{a_segments[0]}]"]
    else:
        # Concatenate the two segments.
        filter_complex = "; ".join(filters) + f"; [{v_segments[0]}][{a_segments[0]}][{v_segments[1]}][{a_segments[1]}]concat=n=2:v=1:a=1[outv][outa]"
        map_args = ["-map", "[outv]", "-map", "[outa]"]

    cmd = [
        "ffmpeg", "-y", "-i", input_video,
        "-filter_complex", filter_complex,
    ] + map_args + [tmp_out]
    subprocess.run(cmd, check=True)
    os.replace(tmp_out, input_video)

def process_video_file(input_file: str, noise: str, duration: float, margin: float) -> str:
    """
    Process a video file:
      1. Make a working copy (in MP4 format).
      2. Extract its audio track to WAV.
      3. Detect and remove silent parts from the video (using the audio intervals).
    
    Returns:
        Path to the processed video file.
    """
    base, _ = os.path.splitext(input_file)
    working_video = base + ".temp_video.mp4"
    print(f"Copying {input_file} to working file {working_video} ...")
    # Copy input video to a working MP4 file (using stream copy).
    cmd_copy = ["ffmpeg", "-y", "-i", input_file, "-c", "copy", working_video]
    subprocess.run(cmd_copy, check=True)

    # Extract audio track to WAV for silence detection.
    temp_wav = base + ".temp_audio.wav"
    print(f"Extracting audio from {working_video} to {temp_wav} ...")
    cmd_extract = ["ffmpeg", "-y", "-i", working_video, "-vn", "-acodec", "pcm_s16le", "-ar", "44100", temp_wav]
    subprocess.run(cmd_extract, check=True)

    intervals = detect_silence_intervals(temp_wav, noise=noise, duration=duration, margin=margin)
    if os.path.exists(temp_wav):
        os.remove(temp_wav)

    # Process detected silent intervals in reverse order.
    for start, end in intervals:
        print(f"Removing silence from {start:.2f}s to {end:.2f}s in {working_video} ...")
        remove_silence_segment_video(working_video, start, end)
    return working_video

def confirm_overwrite(filename: str) -> bool:
    """
    Ask the user for confirmation before overwriting an existing file.
    """
    if os.path.exists(filename):
        answer = input(f"File '{filename}' exists. Overwrite? (y)es/(n)o [n]: ").strip().lower()
        if answer not in ("y", "yes"):
            return False
    return True

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Process video files by removing silent parts (based on the audio track) and outputting a cleaned video."
    )
    parser.add_argument(
        "input_files",
        nargs="+",
        help="Input video file(s) (e.g. .mp4, .mkv, .avi, etc.)"
    )
    parser.add_argument(
        "-o", "--output",
        help=("For a single input file, specify the output video filename. "
              "For multiple files, if provided and is a directory, "
              "the output files will be placed in that directory. "
              "Otherwise, this flag is ignored for multiple input files.")
    )
    parser.add_argument(
        "--noise-threshold",
        type=str,
        default="-50",
        help="Noise threshold for silence detection (in dB). Provide the numeric value only, e.g. -50. Default: -50"
    )
    parser.add_argument(
        "--min-silence-duration",
        type=float,
        default=2.0,
        help="Minimum duration (in seconds) to consider as silence. Default: 2.0"
    )
    parser.add_argument(
        "--margin",
        type=float,
        default=1.0,
        help="Margin (in seconds) added to nonzero silence starts. Default: 1.0"
    )
    args = parser.parse_args()

    cleaned_videos: List[str] = []
    for infile in args.input_files:
        print(f"\nProcessing file: {infile}")
        cleaned_video = process_video_file(infile, args.noise_threshold, args.min_silence_duration, args.margin)
        cleaned_videos.append(cleaned_video)

    # Handle output naming.
    if len(cleaned_videos) == 1:
        final_video = cleaned_videos[0]
        default_output = os.path.splitext(args.input_files[0])[0] + ".mp4"
        output_file = args.output if args.output else default_output

        if not confirm_overwrite(output_file):
            print("Operation cancelled by user.")
            sys.exit(1)

        print(f"\nSaving cleaned video as: {output_file} ...")
        os.replace(final_video, output_file)
    else:
        for infile, cleaned_video in zip(args.input_files, cleaned_videos):
            default_output = os.path.splitext(infile)[0] + ".mp4"
            output_file = default_output
            if args.output:
                if os.path.isdir(args.output):
                    output_file = os.path.join(args.output, os.path.basename(default_output))
                else:
                    print("Warning: -o flag is ignored for multiple input files.")
            if not confirm_overwrite(output_file):
                print("Operation cancelled by user.")
                sys.exit(1)
            print(f"\nSaving cleaned video for {infile} as: {output_file} ...")
            os.replace(cleaned_video, output_file)

    print("\nProcessing complete.")

if __name__ == "__main__":
    main()
