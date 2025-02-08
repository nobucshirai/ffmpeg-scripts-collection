#!/usr/bin/env python3
"""
Merge multiple movie files (e.g. MOV, MP4) into a single output file.

This script uses ffprobe to gather information about each input file and then
constructs an ffmpeg filter_complex that scales and pads each video to a common
resolution before concatenating them. Audio streams are also processed; for any
input file lacking an audio stream, silent audio is generated to keep the
concatenation in sync.

Usage:
    python merge_movies.py input1.mp4 input2.mov -o output.mp4

If the output file already exists, the script will prompt for confirmation before
overwriting.
"""

import argparse
import json
import os
import subprocess
import sys
from typing import Any, Dict, List


def get_video_info(filename: str) -> Dict[str, Any]:
    """
    Retrieve video information (resolution, duration, audio presence) for a given file.

    Uses ffprobe to extract information.

    Args:
        filename: Path to the movie file.

    Returns:
        A dictionary with keys:
            - 'width': width of the video (int)
            - 'height': height of the video (int)
            - 'duration': duration of the file in seconds (float)
            - 'has_audio': True if an audio stream is present, False otherwise.
    """
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        filename,
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe error on file '{filename}': {result.stderr}")

    info = json.loads(result.stdout)
    width, height = None, None
    has_audio = False

    # Extract video stream info.
    for stream in info.get("streams", []):
        if stream.get("codec_type") == "video" and width is None:
            try:
                width = int(stream.get("width"))
                height = int(stream.get("height"))
            except (TypeError, ValueError):
                raise ValueError(f"Invalid resolution data in file '{filename}'")
        elif stream.get("codec_type") == "audio":
            has_audio = True

    # Get duration from the format section.
    duration_str = info.get("format", {}).get("duration")
    if duration_str is not None:
        try:
            duration = float(duration_str)
        except ValueError:
            duration = 0.0
    else:
        duration = 0.0

    if width is None or height is None:
        raise ValueError(f"Could not determine resolution for file '{filename}'")

    return {"width": width, "height": height, "duration": duration, "has_audio": has_audio}


def confirm_overwrite(filename: str) -> bool:
    """
    Ask the user for confirmation before overwriting an existing file.

    Args:
        filename: Path to the file that exists.

    Returns:
        True if the user confirms (input begins with 'y' or 'Y'), False otherwise.
    """
    answer = input(f"File '{filename}' exists. Overwrite? (y)es/(n)o [n]: ").strip().lower()
    return answer.startswith("y")


def build_filter_complex(video_infos: List[Dict[str, Any]]) -> str:
    """
    Build the ffmpeg filter_complex string to scale/pad and concatenate inputs.

    For each input, a video filter is built to scale the video to a common
    target resolution and pad it so that all videos have the same size.
    For the audio, if an input lacks an audio stream, silent audio is generated
    matching its duration.

    Args:
        video_infos: List of dictionaries containing video info for each input.

    Returns:
        A string suitable for the ffmpeg '-filter_complex' argument.
    """
    # Determine target resolution: use the maximum width and height among inputs.
    target_width = max(info["width"] for info in video_infos)
    target_height = max(info["height"] for info in video_infos)

    filters = []

    # Create filters for each input.
    for i, info in enumerate(video_infos):
        # Video filter: scale with force_original_aspect_ratio=decrease and then pad.
        video_filter = (
            f"[{i}:v]scale=w={target_width}:h={target_height}:force_original_aspect_ratio=decrease,"
            f"pad={target_width}:{target_height}:(({target_width}-iw)/2):(({target_height}-ih)/2)"
            f"[v{i}]"
        )
        filters.append(video_filter)

        # Audio filter: if the input has audio, use it; otherwise, generate silent audio.
        if info["has_audio"]:
            audio_filter = f"[{i}:a]aresample=async=1,asetpts=PTS-STARTPTS[a{i}]"
        else:
            # Generate silent audio with anullsrc and trim it to the duration of the video.
            audio_filter = (
                f"anullsrc=channel_layout=stereo:sample_rate=44100,"
                f"atrim=duration={info['duration']:.3f},asetpts=PTS-STARTPTS[a{i}]"
            )
        filters.append(audio_filter)

    # Build the input labels for the concat filter.
    concat_inputs = "".join(f"[v{i}][a{i}]" for i in range(len(video_infos)))
    concat_filter = f"{concat_inputs}concat=n={len(video_infos)}:v=1:a=1[v][a]"
    filters.append(concat_filter)

    # Join all filter parts with semicolons.
    filter_complex = ";".join(filters)
    return filter_complex


def main() -> None:
    """
    Parse arguments, process input files, and merge them using ffmpeg.
    """
    parser = argparse.ArgumentParser(
        description="Merge multiple movie files (mov, mp4, etc.) into a single file."
    )
    parser.add_argument(
        "input_files",
        nargs="+",
        help="Input movie files to merge (e.g., file1.mp4 file2.mov).",
    )
    parser.add_argument(
        "-o",
        "--output",
        help=(
            "Output filename. "
            "If not provided, the default is the basename of the first input file "
            "with '_merged' appended if more than one file is specified."
        ),
    )
    args = parser.parse_args()

    # Verify that all input files exist.
    for infile in args.input_files:
        if not os.path.isfile(infile):
            print(f"Error: Input file '{infile}' does not exist.", file=sys.stderr)
            sys.exit(1)

    # Gather video info for each input file.
    video_infos: List[Dict[str, Any]] = []
    for infile in args.input_files:
        try:
            info = get_video_info(infile)
            video_infos.append(info)
        except Exception as err:
            print(f"Error processing file '{infile}': {err}", file=sys.stderr)
            sys.exit(1)

    # Determine output filename.
    if args.output:
        output_file = args.output
    else:
        base, ext = os.path.splitext(os.path.basename(args.input_files[0]))
        # If more than one input file, append '_merged' to the base name.
        output_file = base + ("_merged" if len(args.input_files) > 1 else "") + ext

    # Ask for confirmation if the output file already exists.
    if os.path.exists(output_file):
        if not confirm_overwrite(output_file):
            print("Aborted by user.")
            sys.exit(0)

    # Build the filter_complex string.
    filter_complex = build_filter_complex(video_infos)

    # Build the ffmpeg command.
    ffmpeg_cmd = ["ffmpeg"]
    # Add each input file.
    for infile in args.input_files:
        ffmpeg_cmd.extend(["-i", infile])
    # Append the filter_complex, mapping, and codecs.
    ffmpeg_cmd.extend(
        [
            "-filter_complex",
            filter_complex,
            "-map",
            "[v]",
            "-map",
            "[a]",
            "-c:v",
            "libx264",
            "-c:a",
            "aac",
            "-strict",
            "experimental",
            output_file,
        ]
    )

    print("Running ffmpeg command:")
    print(" ".join(ffmpeg_cmd))
    try:
        subprocess.run(ffmpeg_cmd, check=True)
    except subprocess.CalledProcessError as err:
        print(f"ffmpeg failed with error: {err}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

