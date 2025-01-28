#!/usr/bin/env python3

"""
A script to make a video file silent using `ffmpeg` through `subprocess`.

This script takes an input video file, removes the audio track, and saves the output.
You can specify an output filename or let the script generate one with a specific suffix.
The script ensures the user is prompted before overwriting an existing file.
"""

import subprocess
import argparse
import os
from typing import Optional

def make_video_silent(input_file: str, output_file: str) -> None:
    """
    Remove the audio from a video file using ffmpeg.

    Args:
        input_file (str): Path to the input video file.
        output_file (str): Path to the output video file.
    """
    try:
        subprocess.run(
            ["ffmpeg", "-i", input_file, "-an", output_file],
            check=True,
            text=True,
        )
        print(f"Successfully created silent video: {output_file}")
    except subprocess.CalledProcessError as e:
        print(f"Error while processing the video: {e}")

def confirm_overwrite(file_path: str) -> bool:
    """
    Prompt the user to confirm overwriting an existing file.

    Args:
        file_path (str): Path to the file to potentially overwrite.

    Returns:
        bool: True if the user confirms overwrite, False otherwise.
    """
    while True:
        choice = input(f"The file '{file_path}' already exists. Overwrite? (y/n): ").lower()
        if choice in ["y", "yes"]:
            return True
        elif choice in ["n", "no"]:
            return False
        else:
            print("Please answer with 'y' or 'n'.")

def parse_arguments() -> argparse.Namespace:
    """
    Parse command-line arguments.

    Returns:
        argparse.Namespace: Parsed arguments.
    """
    parser = argparse.ArgumentParser(
        description="Make a video file silent by removing its audio track using ffmpeg."
    )
    parser.add_argument(
        "input_file",
        type=str,
        help="Path to the input video file.",
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        help="Path to the output video file. Default: adds '_silent' to the input file name.",
    )
    parser.add_argument(
        "-y", "--yes",
        action="store_true",
        help="Automatically confirm overwriting an existing file.",
    )
    return parser.parse_args()

def generate_output_filename(input_file: str) -> str:
    """
    Generate a default output filename by adding a '_silent' suffix.

    Args:
        input_file (str): Path to the input video file.

    Returns:
        str: Generated output file name.
    """
    base, ext = os.path.splitext(input_file)
    return f"{base}_silent{ext}"

def main() -> None:
    """
    Main function to handle the logic of the script.
    """
    args = parse_arguments()

    input_file = args.input_file
    output_file = args.output or generate_output_filename(input_file)

    if not os.path.exists(input_file):
        print(f"Error: The input file '{input_file}' does not exist.")
        return

    if os.path.exists(output_file) and not args.yes:
        if not confirm_overwrite(output_file):
            print("Operation cancelled by the user.")
            return

    make_video_silent(input_file, output_file)

if __name__ == "__main__":
    main()
