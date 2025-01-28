#!/usr/bin/env python3
"""
A script to extract audio as MP3 from a video file (MP4/MOV) using `ffmpeg`.
"""

import os
import subprocess
import argparse
from typing import Optional

def extract_audio(input_file: str, output_file: str) -> None:
    """
    Extract audio from a video file and save it as an MP3 file.

    Args:
        input_file (str): Path to the input video file.
        output_file (str): Path to the output MP3 file.

    Raises:
        RuntimeError: If the ffmpeg command fails.
    """
    try:
        subprocess.run(
            ["ffmpeg", "-i", input_file, "-vn", "-ab", "192k", "-ar", "44100", output_file],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"ffmpeg failed with error: {e.stderr.decode('utf-8')}") from e

def confirm_overwrite(file_path: str) -> bool:
    """
    Confirm with the user before overwriting an existing file.

    Args:
        file_path (str): Path to the file to check.

    Returns:
        bool: True if the file can be overwritten, False otherwise.
    """
    if os.path.exists(file_path):
        response = input(f"File '{file_path}' already exists. Overwrite? (y/n) [n]: ").strip().lower()
        return response == "y"
    return True

def main():
    """
    Main function to parse arguments and execute the audio extraction.
    """
    parser = argparse.ArgumentParser(description="Extract audio as MP3 from a video file using ffmpeg.")
    parser.add_argument("input_file", help="Path to the input video file (e.g., MP4, MOV).")
    parser.add_argument(
        "-o", "--output", help="Path to the output MP3 file.", default=None
    )

    args = parser.parse_args()
    
    input_file = args.input_file

    # Determine output file name
    if args.output:
        output_file = args.output
    else:
        base, _ = os.path.splitext(input_file)
        output_file = f"{base}_extracted.mp3"

    # Confirm overwrite if necessary
    if not confirm_overwrite(output_file):
        print("Operation canceled by user.")
        return

    print(f"Extracting audio from '{input_file}' to '{output_file}'...")

    try:
        extract_audio(input_file, output_file)
        print(f"Audio successfully extracted to '{output_file}'.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
