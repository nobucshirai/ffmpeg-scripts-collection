#!/usr/bin/env python3
"""
Audio Silence Remover and Converter

This script converts input audio files to WAV, detects and removes silent parts using ffmpeg,
and then converts each cleaned WAV file to MP3. Input audio files can be in any format that ffmpeg supports.

Usage:
    audio_silence_remover.py [-h] [-o OUTPUT]
                              [--noise-threshold NOISE_THRESHOLD]
                              [--min-silence-duration MIN_SILENCE_DURATION]
                              [--margin MARGIN]
                              input_files [input_files ...]

Examples:
    Remove silence from one file and output "song.mp3":
        ./audio_silence_remover.py song.m4a

    Process multiple files and produce separate MP3 files for each:
        ./audio_silence_remover.py track1.mp3 track2.wav track3.aac

    Customize silence detection parameters:
        ./audio_silence_remover.py --noise-threshold -40 --min-silence-duration 1.5 --margin 0.5 song.m4a
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
from typing import List, Tuple

def get_audio_duration(filename: str) -> float:
    """
    Retrieve the duration (in seconds) of the given audio file using ffprobe.

    Args:
        filename: Path to the audio file.

    Returns:
        Duration in seconds.
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

    Args:
        wav_file: Path to the WAV file.
        noise: Noise threshold for silence detection (numeric value only, in dB).
        duration: Minimum duration (in seconds) to consider as silence.
        margin: Margin (in seconds) added to nonzero silence starts.

    Returns:
        A list of tuples (start, end) for silent segments. For nonzero starts an extra margin is added.
        The intervals are ordered from later to earlier in the timeline.
    """
    # Ensure the noise parameter has the "dB" suffix required by ffmpeg.
    noise_param = noise if noise.endswith("dB") else noise + "dB"
    cmd = [
        "ffmpeg", "-i", wav_file,
        "-af", f"silencedetect=noise={noise_param}:d={duration}",
        "-f", "null", "-"
    ]
    # ffmpeg sends silencedetect info to stderr
    proc = subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    output = proc.stderr

    silence_starts: List[float] = []
    silence_ends: List[float] = []

    # Look for lines like: "silence_start: 12.345" or "silence_end: 45.678"
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
    # Pair the detected starts and ends in reverse order to avoid shifting timestamps.
    for start, end in zip(reversed(silence_starts), reversed(silence_ends)):
        # If start is not zero, add the specified margin.
        if start != 0:
            start += margin
        intervals.append((start, end))
    return intervals

def remove_silence_segment(input_wav: str, start: float, end: float) -> None:
    """
    Remove a silent segment from input_wav between start and end seconds.
    The operation overwrites input_wav with the trimmed file.

    Args:
        input_wav: Path to the WAV file.
        start: Start time (in seconds) of the silent segment.
        end: End time (in seconds) of the silent segment.
    """
    tmp_out = input_wav + ".nosilence.wav"
    total_duration = get_audio_duration(input_wav)

    filters = []
    segments = []

    # If there's a segment before the silence, add it.
    if start > 0:
        filters.append(f"[0:a]atrim=0:{start},asetpts=PTS-STARTPTS[a1]")
        segments.append("a1")
    # If there's a segment after the silence, add it.
    if end < total_duration:
        filters.append(f"[0:a]atrim={end}:{total_duration},asetpts=PTS-STARTPTS[a2]")
        segments.append("a2")

    if not segments:
        # If the whole file is silence, simply copy the input using Python's shutil.
        shutil.copy(input_wav, tmp_out)
        os.replace(tmp_out, input_wav)
        return

    if len(segments) == 1:
        filter_complex = filters[0]
        map_args = ["-map", f"[{segments[0]}]"]
    else:
        # Concatenate head and tail segments.
        filter_complex = "; ".join(filters) + f"; [{segments[0]}][{segments[1]}]concat=n=2:v=0:a=1[out]"
        map_args = ["-map", "[out]"]

    cmd = [
        "ffmpeg", "-y", "-i", input_wav,
        "-filter_complex", filter_complex,
    ] + map_args + [tmp_out]
    subprocess.run(cmd, check=True)
    os.replace(tmp_out, input_wav)

def process_audio_file(input_file: str, noise: str, duration: float, margin: float) -> str:
    """
    Process an input audio file:
      1. Convert it to WAV using ffmpeg.
      2. Detect and remove silent parts.
    
    Args:
        input_file: Path to the input audio file.
        noise: Noise threshold for silence detection (numeric value only, in dB).
        duration: Minimum duration (in seconds) to consider as silence.
        margin: Margin (in seconds) added to nonzero silence starts.
    
    Returns:
        Path to the processed WAV file.
    """
    base, _ = os.path.splitext(input_file)
    wav_file = base + ".wav"
    print(f"Converting {input_file} to WAV ...")
    # Convert to WAV (PCM 16-bit, 44100 Hz)
    cmd = ["ffmpeg", "-y", "-i", input_file, "-acodec", "pcm_s16le", "-ar", "44100", wav_file]
    subprocess.run(cmd, check=True)

    intervals = detect_silence_intervals(wav_file, noise=noise, duration=duration, margin=margin)
    for start, end in intervals:
        print(f"Removing silence from {start:.2f}s to {end:.2f}s in {wav_file} ...")
        remove_silence_segment(wav_file, start, end)
    return wav_file

def convert_wav_to_mp3(input_wav: str, output_mp3: str) -> None:
    """
    Convert a WAV file to MP3 using ffmpeg.

    Args:
        input_wav: Path to the input WAV file.
        output_mp3: Path for the output MP3 file.
    """
    cmd = ["ffmpeg", "-y", "-i", input_wav, output_mp3]
    subprocess.run(cmd, check=True)

def confirm_overwrite(filename: str) -> bool:
    """
    Ask the user for confirmation before overwriting an existing file.

    Args:
        filename: The file that may be overwritten.

    Returns:
        True if the user confirms overwrite or file does not exist; False otherwise.
    """
    if os.path.exists(filename):
        answer = input(f"File '{filename}' exists. Overwrite? (y)es/(n)o [n]: ").strip().lower()
        if answer not in ("y", "yes"):
            return False
    return True

def main() -> None:
    """
    Parse command-line arguments and process the input audio file(s).
    """
    parser = argparse.ArgumentParser(
        description="Process audio files by removing silent parts and converting to MP3."
    )
    parser.add_argument(
        "input_files",
        nargs="+",
        help="Input audio file(s) (e.g. .m4a, .mp3, .aac, etc.)"
    )
    parser.add_argument(
        "-o", "--output",
        help=("For a single input file, specify the output MP3 filename. "
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

    cleaned_wavs: List[str] = []
    for infile in args.input_files:
        print(f"\nProcessing file: {infile}")
        cleaned_wav = process_audio_file(infile, args.noise_threshold, args.min_silence_duration, args.margin)
        cleaned_wavs.append(cleaned_wav)

    # If only one file is processed, use the output flag (if provided) for the MP3 filename.
    if len(cleaned_wavs) == 1:
        final_wav = cleaned_wavs[0]
        default_output = os.path.splitext(args.input_files[0])[0] + ".mp3"
        output_mp3 = args.output if args.output else default_output

        if not confirm_overwrite(output_mp3):
            print("Operation cancelled by user.")
            sys.exit(1)

        print(f"\nConverting {final_wav} to MP3: {output_mp3} ...")
        convert_wav_to_mp3(final_wav, output_mp3)
        if os.path.exists(final_wav):
            os.remove(final_wav)
    else:
        # For multiple files, process each cleaned WAV separately.
        for infile, cleaned_wav in zip(args.input_files, cleaned_wavs):
            default_output = os.path.splitext(infile)[0] + ".mp3"
            output_mp3 = default_output
            if args.output:
                # If -o is provided and is a directory, place output there.
                if os.path.isdir(args.output):
                    output_mp3 = os.path.join(args.output, os.path.basename(default_output))
                else:
                    print("Warning: -o flag is ignored for multiple input files.")
            if not confirm_overwrite(output_mp3):
                print("Operation cancelled by user.")
                sys.exit(1)
            print(f"\nConverting {cleaned_wav} to MP3: {output_mp3} ...")
            convert_wav_to_mp3(cleaned_wav, output_mp3)
            if os.path.exists(cleaned_wav):
                os.remove(cleaned_wav)

    print("\nProcessing complete.")

if __name__ == "__main__":
    main()
