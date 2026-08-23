"""
extract_frames.py - pull still evidence out of the module screen recordings.

Two modes:

  1. Contact sheet  - render a grid of timestamped thumbnails for a whole video.
                      Use this to *browse* a recording and decide which moments
                      are worth capturing.

  2. Timestamp grab - export full-resolution PNG frames at exact timestamps.
                      Use this to produce the images referenced by a README.

Uses OpenCV only (no ffmpeg dependency).

Examples
--------
# Build a 5x4 contact sheet for module 1
python tools/extract_frames.py sheet "vedios/modile_1.mp4" -o assets/sheets/ --cols 5 --rows 4

# Export three exact frames as PNGs
python tools/extract_frames.py grab "vedios/modile_1.mp4" \
    -o module-01-camera-conditioning/images/ \
    --at 00:04 00:27 01:15 \
    --names 01_grid_view 02_histogram_panel 03_zoom_2x
"""

import argparse
import os
import sys

import cv2
import numpy as np


def parse_timestamp(text: str) -> float:
    """Accept SS, MM:SS or HH:MM:SS and return seconds as float."""
    parts = text.strip().split(":")
    if len(parts) > 3:
        raise ValueError(f"Unrecognised timestamp: {text}")
    seconds = 0.0
    for part in parts:
        seconds = seconds * 60.0 + float(part)
    return seconds


def open_video(path: str) -> tuple:
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        sys.exit(f"Could not open video: {path}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    duration = total / fps if fps > 0 else 0.0
    return cap, fps, total, width, height, duration


def label(image: np.ndarray, text: str) -> np.ndarray:
    """Draw a readable timestamp badge in the top-left corner."""
    out = image.copy()
    (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
    cv2.rectangle(out, (0, 0), (tw + 10, th + 10), (0, 0, 0), -1)
    cv2.putText(out, text, (5, th + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
    return out


def fmt(seconds: float) -> str:
    minutes, secs = divmod(int(seconds), 60)
    return f"{minutes:02d}:{secs:02d}"


def make_sheet(path: str, out_dir: str, cols: int, rows: int, thumb_w: int) -> None:
    cap, fps, total, width, height, duration = open_video(path)
    print(f"{os.path.basename(path)}: {width}x{height} @ {fps:.2f} fps, "
          f"{total} frames, {fmt(duration)} long")

    count = cols * rows
    # Sample evenly, skipping the very first and very last frame.
    positions = np.linspace(0, max(total - 1, 0), count + 2)[1:-1].astype(int)

    thumb_h = int(thumb_w * height / width) if width else thumb_w
    sheet = np.zeros((rows * thumb_h, cols * thumb_w, 3), dtype=np.uint8)

    for index, frame_no in enumerate(positions):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(frame_no))
        ok, frame = cap.read()
        if not ok:
            continue
        thumb = cv2.resize(frame, (thumb_w, thumb_h))
        stamp = fmt(frame_no / fps) if fps > 0 else f"f{frame_no}"
        thumb = label(thumb, stamp)
        cv2.rectangle(thumb, (0, 0), (thumb_w - 1, thumb_h - 1), (60, 60, 60), 1)
        r, c = divmod(index, cols)
        sheet[r * thumb_h:(r + 1) * thumb_h, c * thumb_w:(c + 1) * thumb_w] = thumb

    cap.release()
    os.makedirs(out_dir, exist_ok=True)
    stem = os.path.splitext(os.path.basename(path))[0]
    out_path = os.path.join(out_dir, f"{stem}_sheet.png")
    cv2.imwrite(out_path, sheet)
    print(f"  wrote {out_path}  ({cols}x{rows} thumbnails)")


def grab(path: str, out_dir: str, stamps: list, names: list, jpeg: bool) -> None:
    cap, fps, total, width, height, duration = open_video(path)
    print(f"{os.path.basename(path)}: {width}x{height} @ {fps:.2f} fps, {fmt(duration)} long")
    os.makedirs(out_dir, exist_ok=True)
    stem = os.path.splitext(os.path.basename(path))[0]

    for index, stamp in enumerate(stamps):
        seconds = parse_timestamp(stamp)
        if duration and seconds > duration:
            print(f"  skip {stamp}: past end of video ({fmt(duration)})")
            continue
        cap.set(cv2.CAP_PROP_POS_MSEC, seconds * 1000.0)
        ok, frame = cap.read()
        if not ok:
            print(f"  skip {stamp}: read failed")
            continue
        if names and index < len(names):
            base = names[index]
        else:
            base = f"{stem}_{stamp.replace(':', 'm')}s"
        ext = ".jpg" if jpeg else ".png"
        out_path = os.path.join(out_dir, base + ext)
        params = [cv2.IMWRITE_JPEG_QUALITY, 92] if jpeg else []
        cv2.imwrite(out_path, frame, params)
        size_kb = os.path.getsize(out_path) / 1024
        print(f"  {stamp} -> {out_path}  ({size_kb:.0f} KB)")

    cap.release()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="mode", required=True)

    p_sheet = sub.add_parser("sheet", help="render a grid of timestamped thumbnails")
    p_sheet.add_argument("video")
    p_sheet.add_argument("-o", "--out", default="assets/sheets")
    p_sheet.add_argument("--cols", type=int, default=5)
    p_sheet.add_argument("--rows", type=int, default=4)
    p_sheet.add_argument("--thumb-width", type=int, default=420)

    p_grab = sub.add_parser("grab", help="export full-resolution frames at timestamps")
    p_grab.add_argument("video")
    p_grab.add_argument("-o", "--out", required=True)
    p_grab.add_argument("--at", nargs="+", required=True,
                        help="timestamps, e.g. 00:04 01:15 02:30")
    p_grab.add_argument("--names", nargs="*", default=[],
                        help="output filenames (no extension), in the same order as --at")
    p_grab.add_argument("--jpeg", action="store_true",
                        help="write JPEG instead of PNG (smaller, use for photographic frames)")

    args = parser.parse_args()

    if args.mode == "sheet":
        make_sheet(args.video, args.out, args.cols, args.rows, args.thumb_width)
    else:
        grab(args.video, args.out, args.at, args.names, args.jpeg)


if __name__ == "__main__":
    main()
