#!/usr/bin/env python3
"""
A script to downsize movie files using ffmpeg.
"""

import argparse
import os
import subprocess
import sys

def confirm_overwrite(filepath: str) -> bool:
    """
    Ask the user if they want to overwrite an existing file.

    :param filepath: Path to the file that might be overwritten.
    :return: True if the user confirms overwrite, False otherwise.
    """
    while True:
        response = input(f"File '{filepath}' already exists. Overwrite? (y/N): ").strip().lower()
        if response == "y":
            return True
        elif response == "" or response == "n":
            return False
        else:
            print("Please answer 'y' or 'n'.")

def downsize_video(input_file: str, output_file: str, scale: str) -> None:
    """
    Downsize a video using ffmpeg.

    :param input_file: Path to the input video file.
    :param output_file: Path to the output downsized video file.
    :param scale: The scale argument for ffmpeg, e.g., '1280:-1'.
    """
    try:
        # Example ffmpeg command to resize while maintaining aspect ratio
        subprocess.run(
            [
                "ffmpeg", 
                "-i", input_file, 
                "-vf", f"scale={scale}",
                "-c:a", "copy",  # copy audio as-is
                output_file
            ],
            check=True
        )
        print(f"Successfully downsized '{input_file}' to '{output_file}'")
    except subprocess.CalledProcessError as e:
        print(f"Error downsizing '{input_file}' to '{output_file}': {e}")
        sys.exit(1)

def parse_args() -> argparse.Namespace:
    """
    Parse command-line arguments.

    :return: Parsed arguments as a Namespace object.
    """
    parser = argparse.ArgumentParser(
        description="Downsize a video file using ffmpeg."
    )
    parser.add_argument(
        "input_file",
        help="Path to the input video file."
    )
    parser.add_argument(
        "-o", "--output",
        help="Path to the output downsized video file. "
             "If not provided, a default will be used."
    )
    parser.add_argument(
        "-s", "--scale",
        default="1280:-2",
        help="The scale string for ffmpeg (default: '1280:-2'). "
             "Use -1 or -2 for the second dimension to keep aspect ratio."
    )
    return parser.parse_args()

def get_default_output_filename(input_file: str, suffix: str = "_downsized") -> str:
    """
    Construct a default output filename by adding a suffix to the base name.

    :param input_file: Path to the original video file.
    :param suffix: Suffix to append before the file extension.
    :return: A string with the default output filename.
    """
    base, ext = os.path.splitext(input_file)
    return f"{base}{suffix}{ext}"

def main() -> None:
    """
    Main entry point for the script.
    """
    args = parse_args()

    input_file = args.input_file
    # Derive default output filename if not given
    output_file = args.output or get_default_output_filename(input_file)
    scale = args.scale

    # Check if output file already exists
    if os.path.exists(output_file):
        if not confirm_overwrite(output_file):
            print("Operation cancelled.")
            sys.exit(0)

    # Perform the downsizing
    downsize_video(input_file, output_file, scale)

if __name__ == "__main__":
    main()
