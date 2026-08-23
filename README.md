# Computer Vision Learning Pipeline

A five-module Python + OpenCV pipeline for LED detection, built from camera
acquisition through to robot decision logic. Each module is a standalone,
interactive diagnostic tool with live parameter controls.

![Python](https://img.shields.io/badge/Python-3.13-blue)
![OpenCV](https://img.shields.io/badge/OpenCV-4.10-green)
![License](https://img.shields.io/badge/License-MIT-lightgrey)

Built and tested against an **Arducam IMX298 (B0290)** USB camera on Windows 11.

---

## What this repository is

Five programs that each isolate one stage of a detection pipeline, so the effect
of every parameter can be observed live rather than inferred from a final result.
Module 1 conditions the camera, module 2 segments by colour, module 3 cleans the
mask, module 4 finds shapes, and module 5 turns detections into decisions.

The value here is not the individual OpenCV calls. It is what the staged
diagnostics revealed about why the pipeline failed on real hardware — documented
in each module's README with the frames that show it.

---

## The finding that shaped the project

The pipeline was built assuming the target LED would be the most colour-saturated
object in the frame. On this hardware, the opposite was true.

Sampling HSV values from a captured frame ([module 2](module-02-hsv-segmentation/)):

| Region | H | S | V |
|---|---:|---:|---:|
| Red LED core | 33 | **11** | 255 |
| Red LED core | 146 | **6** | 255 |
| Background / breadboard | 59 | **246** | 203 |

The LEDs are clipped to white — `V = 255` with almost no saturation left, so their
hue readings are meaningless. Meanwhile the background carries strong chroma,
because auto white balance is disabled in code and the scene sits under a heavy
green cast.

An HSV colour threshold assumes a saturated target against a neutral background.
Here that assumption is inverted, which is why the binary mask stays empty through
modules 2, 3 and 4 regardless of how the sliders are set. Tuning cannot fix an
exposure problem.

> Measured from a JPEG-compressed screen recording, not raw sensor frames, so
> treat the values as indicative. The gap between `S = 11` and `S = 246` is far
> larger than compression error, so the conclusion holds.

---

## Pipeline

| Module | Focus | Key controls |
|---|---|---|
| [01 — Camera Conditioning](module-01-camera-conditioning/) | Acquisition, exposure, brightness/contrast/saturation, grid, histogram, zoom, FPS | 6 trackbars, `+`/`-` exposure keys |
| [02 — HSV Segmentation](module-02-hsv-segmentation/) | BGR→HSV, dual-range red masking, H/S/V channel inspection | 7 trackbars |
| [03 — Preprocessing](module-03-preprocessing/) | Blur, erosion, dilation, morphological cleanup | 4 trackbars |
| [04 — Pattern Detection](module-04-pattern-detection/) | Contours, circularity, Hough circles | 6 trackbars |
| [05 — Robotics Logic](module-05-robotics-logic/) | Area gates, stability frames, tracking, decisions | 4 trackbars |

Each module opens a single window split into four panels. Clicking a panel
expands it to fullscreen; clicking again or pressing `ESC` returns to the grid.

---

## Requirements

```
Python 3.13.6
opencv-python 4.10.0.84
numpy 2.5.0
```

A USB camera on device index 0. All five modules open the camera directly and
have no headless mode.

## Setup

```bash
git clone https://github.com/SELVA-31/computer-vision-learning-pipeline.git
cd computer-vision-learning-pipeline
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Running a module

```bash
python module-01-camera-conditioning/code/module1_hardware_setup.py
```

Each module prints its key bindings on startup. `q` quits.

## Verifying without a camera

The processing functions are pure — frame in, frame out — so they can be checked
against a synthetic frame with no hardware attached:

```bash
python tools/verify_modules.py
```

This compiles all five modules and exercises the conditioning, masking and
contour functions. It found a latent crash in module 1's histogram renderer under
numpy 2.x, described in [module 1](module-01-camera-conditioning/).

---

## Repository layout

```
module-0N-name/
  code/      the module script
  images/    stills extracted from the recordings
  video/     short clips (full recordings hosted externally)
  results/   captured output
docs/        parameter reference
tools/       frame extraction, clip encoding, verification
assets/      contact sheets
```

## Tools

| Script | Purpose |
|---|---|
| `tools/verify_modules.py` | Camera-free checks over the processing functions |
| `tools/check_repo.py` | Audits the docs against the code: control tables, cited line numbers, image links, file sizes, dependencies |
| `tools/extract_frames.py` | Contact sheets and full-resolution stills from a recording |
| `tools/make_clip.py` | Cut a short, repo-sized clip (finds ffmpeg, or uses `imageio-ffmpeg`) |

```bash
# Browse a recording as a timestamped thumbnail grid
python tools/extract_frames.py sheet path/to/video.mp4 -o assets/sheets --cols 4 --rows 4

# Export exact frames
python tools/extract_frames.py grab path/to/video.mp4 -o module-01-camera-conditioning/images --at 01:13 --names 01_grid_overlay
```

---

## Evidence

Every claim in the module READMEs is tied to source code or to a frame from a
recording. Screenshots are extracted from the recordings, never recreated.

Full recordings run 70–270 MB each, past GitHub's 100 MB file limit, so they are
hosted externally and linked per module. Short clips and stills are committed.

**One version gap:** the module 1 recordings predate a layout refactor and show
an earlier single-view build. The image-conditioning behaviour and all parameter
maths are identical; only the panel arrangement and two overlay lines differ.
This is noted again in module 1.

## Known limitations

- Requires a live camera at device index 0; no file or headless input path.
- Backend selection is Windows-oriented (`CAP_DSHOW`, `CAP_MSMF`, `CAP_VFW`).
- Tuned values are not persisted between runs. Module 2's `s` key prints bounds
  to the console; it does not write a file.
- Modules 3–5 use hardcoded HSV bounds internally rather than reading module 2's
  output, so a value tuned in module 2 must be transferred by editing the source.
- Parameters are tuned for one camera under one lighting setup and will not
  transfer unchanged.

## License

MIT — see [LICENSE](LICENSE).
