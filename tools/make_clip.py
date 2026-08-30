"""
make_clip.py - cut a short, repo-sized demo clip out of a long screen recording.

The source recordings are 70-270 MB each. GitHub rejects anything over 100 MB and
renders small MP4s inline, so a README clip wants to land under ~10 MB.

Finds ffmpeg in this order:
  1. ffmpeg on PATH
  2. the static binary bundled with the imageio-ffmpeg package
     (pip install imageio-ffmpeg  - no PATH changes needed)

Examples
--------
python tools/make_clip.py "vedios/module_2.mp4" -o module-02-hsv-segmentation/video/module_2_clip.mp4 --start 01:10 --dur 30

# Lower quality / smaller file
python tools/make_clip.py "vedios/module_4.mp4" -o out.mp4 --start 01:20 --dur 25 --crf 32 --width 1100
"""

import argparse
import os
import shutil
import subprocess
import sys


def find_ffmpeg() -> str:
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        sys.exit(
            "ffmpeg not found.\n"
            "  Quick fix (no PATH changes):  pip install imageio-ffmpeg\n"
            "  Or system-wide:               winget install Gyan.FFmpeg\n"
            "  (winget needs a new terminal afterwards)"
        )


def parse_timestamp(text: str) -> str:
    """Normalise SS / MM:SS / HH:MM:SS into HH:MM:SS for ffmpeg."""
    parts = text.strip().split(":")
    if len(parts) > 3:
        sys.exit(f"Unrecognised timestamp: {text}")
    seconds = 0.0
    for part in parts:
        seconds = seconds * 60.0 + float(part)
    hours, rem = divmod(int(seconds), 3600)
    minutes, secs = divmod(rem, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("video", help="source recording")
    parser.add_argument("-o", "--out", required=True, help="output .mp4 path")
    parser.add_argument("--start", default="0", help="start timestamp, e.g. 01:10")
    parser.add_argument("--dur", type=float, default=30.0, help="clip length in seconds")
    parser.add_argument("--width", type=int, default=1280,
                        help="output width, height follows aspect")
    parser.add_argument("--fps", type=int, default=20, help="output frame rate")
    parser.add_argument("--crf", type=int, default=30,
                        help="quality, 18=near-lossless 30=small 35=tiny")

    args = parser.parse_args()
    ffmpeg = find_ffmpeg()

    if not os.path.isfile(args.video):
        sys.exit(f"No such file: {args.video}")

    out_dir = os.path.dirname(os.path.abspath(args.out))
    os.makedirs(out_dir, exist_ok=True)

    cmd = [
        ffmpeg, "-y",
        "-ss", parse_timestamp(args.start),
        "-i", args.video,
        "-t", str(args.dur),
        "-vf", f"scale={args.width}:-2,fps={args.fps}",
        "-c:v", "libx264",
        "-crf", str(args.crf),
        "-preset", "slow",
        "-pix_fmt", "yuv420p",   # required for playback in browsers and GitHub
        "-movflags", "+faststart",
        "-an",                   # screen recordings carry no useful audio
        args.out,
    ]

    print(f"ffmpeg: {ffmpeg}")
    print(f"cutting {args.dur:.0f}s from {args.video} at {args.start} ...")
    result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)

    if result.returncode != 0:
        tail = "\n".join(result.stderr.strip().splitlines()[-12:])
        sys.exit(f"ffmpeg failed:\n{tail}")

    size_mb = os.path.getsize(args.out) / (1024 * 1024)
    print(f"  wrote {args.out}  ({size_mb:.1f} MB)")
    if size_mb > 10:
        print(f"  NOTE: {size_mb:.1f} MB is large for an inline README clip.")
        print(f"        Re-run with a higher --crf (try {args.crf + 3}) or a shorter --dur.")


if __name__ == "__main__":
    main()
