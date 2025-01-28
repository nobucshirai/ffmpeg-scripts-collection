#!/usr/bin/env python3

"""
A script to speed up a video file using ffmpeg through subprocess.

Features:
- Specify output filename with a default name using a specific suffix.
- Specify the playback speed (default: 1.5x).
- Prompt before overwriting an existing file.
- Includes a help option using argparse.
"""

import argparse
import subprocess
import os
from typing import Optional


def speed_up_video(input_file: str, output_file: str, speed: float) -> None:
    """
    Speeds up a video using ffmpeg.
    
    Args:
        input_file (str): The path to the input video file.
        output_file (str): The path to the output video file.
        speed (float): The speed multiplier (e.g., 1.5 for 1.5x speed).
    """
    # ffmpeg command to speed up video
    command = [
        "ffmpeg", "-i", input_file, 
        "-filter:v", f"setpts={1/speed}*PTS",
        "-an", output_file
    ]
    subprocess.run(command, check=True)


def get_default_output_filename(input_file: str, suffix: str = "_speedup") -> str:
    """
    Generates a default output filename by adding a suffix to the basename of the input file.

    Args:
        input_file (str): The input file name.
        suffix (str): The suffix to add to the basename.

    Returns:
        str: The generated output file name.
    """
    base, ext = os.path.splitext(input_file)
    return f"{base}{suffix}{ext}"


def main():
    parser = argparse.ArgumentParser(description="Speed up a video file using ffmpeg.")
    parser.add_argument("input_file", type=str, help="Path to the input video file.")
    parser.add_argument("-o", "--output_file", type=str, 
                        help="Path to the output video file (default: adds '_speedup' to input file name).")
    parser.add_argument("-s", "--speed", type=float, default=1.5, 
                        help="Speed multiplier (e.g., 1.5 for 1.5x speed). Default: 1.5.")
    args = parser.parse_args()

    # Determine output filename
    output_file = args.output_file or get_default_output_filename(args.input_file)

    # Check if the output file exists
    if os.path.exists(output_file):
        overwrite = input(f"The file '{output_file}' already exists. Overwrite? (y/n): ").strip().lower()
        if overwrite != 'y':
            print("Aborting to prevent overwriting.")
            return

    try:
        print(f"Processing '{args.input_file}' with speed {args.speed}x...")
        speed_up_video(args.input_file, output_file, args.speed)
        print(f"Output saved to '{output_file}'.")
    except subprocess.CalledProcessError as e:
        print(f"Error: Failed to process video. {e}")


if __name__ == "__main__":
    main()
