# ffmpeg-scripts-collection

A set of Python scripts that leverage [ffmpeg](https://ffmpeg.org/) for basic video **and audio** operations:

- **silent_video_creator.py**: Remove audio track from a video.
- **video_speedup.py**: Speed up video playback.
- **trim_video.py**: Trim a segment from the beginning of a video.
- **extract_audio_mp3.py**: Extract MP3 audio from a video file.
- **downsize_movie.py**: Resize or downscale a video while preserving aspect ratio.
- **video_merger.py**: Merge multiple movie files (MOV, MP4, etc.) into a single output file.
- **video_silence_remover.py**: Convert video files to WAV, detect and remove silent parts, and then convert them to MP4.
- **audio_silence_remover.py**: Convert audio files to WAV, detect and remove silent parts, and then convert them to MP3.

## Installation

1. Make sure [ffmpeg](https://ffmpeg.org/) is installed and available on your system path.
2. Clone this repository or download the scripts.

## Usage

Each script contains a `--help` option to guide you on usage:

```bash
python3 silent_video_creator.py --help
```

## Acknowledgment

These scripts were partially generated with the assistance of ChatGPT.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
