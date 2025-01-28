#!/usr/bin/env python3

"""
Extract a segment from the beginning of a video file using ffmpeg.
"""

import argparse
import subprocess
import os
from typing import Optional


def extract_segment(input_file: str, output_file: str, duration: str) -> None:
    """
    Extract a segment from a video file using ffmpeg.

    Args:
        input_file (str): Path to the input video file.
        output_file (str): Path to the output video file.
        duration (str): Duration of the segment to extract (e.g., "00:01:00" for 1 minute).
    """
    # Check if the output file exists and ask for confirmation
    if os.path.exists(output_file):
        overwrite = input(f"The file '{output_file}' already exists. Overwrite? (y/n): ").lower()
        if overwrite != 'y':
            print("Aborting to prevent overwriting the file.")
            return

    # Run the ffmpeg command
    try:
        subprocess.run(
            [
                "ffmpeg",
                "-i", input_file,
                "-t", duration,
                "-c", "copy",
                output_file
            ],
            check=True
        )
        print(f"Successfully extracted segment to {output_file}")
    except subprocess.CalledProcessError as e:
        print(f"Error while extracting segment: {e}")
        raise


def main():
    parser = argparse.ArgumentParser(
        description="Extract a segment from the beginning of a video file using ffmpeg."
    )
    parser.add_argument(
        "input_file",
        type=str,
        help="Path to the input video file."
    )
    parser.add_argument(
        "-o", "--output_file",
        type=str,
        help="Path to the output video file. Defaults to '<original_name>_segment.ext'."
    )
    parser.add_argument(
        "-d", "--duration",
        type=str,
        default="00:01:00",
        help="Duration of the segment to extract (default: 1 minute, '00:01:00')."
    )

    args = parser.parse_args()

    # Determine the output filename if not provided
    if not args.output_file:
        base, ext = os.path.splitext(args.input_file)
        args.output_file = f"{base}_segment{ext}"

    # Call the extraction function
    extract_segment(args.input_file, args.output_file, args.duration)


if __name__ == "__main__":
    main()
