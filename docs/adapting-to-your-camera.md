# Adapting this to your camera

The camera settings in this repository are fixed values chosen for one specific
camera — an Arducam IMX298 (B0290) on Windows 11, pointed at a breadboard about
30 cm away.

**They will almost certainly be wrong for your camera.** That is not a bug in the
code; fixed values are the point. But it does mean the first thing you see may
look broken. This page explains what to change and how to tell when it is right.

---

## The one function you need to edit

`initialize_camera()` is byte-identical in all five modules, near the top of each
file. Change it in the module you are running, or in all five to keep them
consistent — `tools/check_repo.py` will tell you if they drift apart.

```python
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)   # 0.25 = manual on most Windows drivers
cap.set(cv2.CAP_PROP_EXPOSURE, -6.0)        # the value most likely to need changing
cap.set(cv2.CAP_PROP_GAIN, 0.0)
cap.set(cv2.CAP_PROP_AUTO_WB, 0.0)          # auto white balance off
cap.set(cv2.CAP_PROP_FPS, 30)
```

---

## What each setting does

| Setting | What it controls | If it is wrong |
|---|---|---|
| `CAP_PROP_AUTO_EXPOSURE` | Whether the camera picks its own exposure. `0.25` means manual on most Windows drivers; `0.75` means auto. | Stuck on auto, the next line is ignored |
| `CAP_PROP_EXPOSURE` | How long the sensor collects light. **More negative is darker.** | Picture is black, or bright areas are pure white |
| `CAP_PROP_GAIN` | Electronic brightening after capture | Raising it brightens the image and the noise together |
| `CAP_PROP_AUTO_WB` | Whether the camera corrects colour automatically. `0.0` turns it off. | With it off, everything may take on a colour tint |
| `CAP_PROP_FRAME_WIDTH` / `HEIGHT` | Capture resolution | Camera silently gives you the nearest size it supports |
| `CAP_PROP_FPS` | Requested frame rate | A request only. Cameras often ignore it. |

Not every camera supports every setting. `cap.set()` returns `False` when a
property is refused, and this code does not check the return value — so a setting
can be silently ignored. If a change appears to do nothing, that is the likely
reason.

---

## Finding an exposure value in about a minute

Module 1 lets you change exposure live, which is much faster than editing and
rerunning.

1. Run module 1.
2. Watch the `Exposure:` line in the top-left overlay.
3. Press `+` to brighten, `-` to darken. Each press moves the value by `0.5`.
4. Stop when the LED is clearly bright but its centre is **not** pure white.
5. Copy that number into `cap.set(cv2.CAP_PROP_EXPOSURE, ...)`.

Typical range is `-4` to `-9`. Some cameras use a completely different scale —
values like `100` or `300` — in which case the `+`/`-` keys will barely move the
picture and you should try much larger jumps by editing the source directly.

---

## Getting white balance right

Two options, and this repository deliberately picked the harder one.

**Leave it off (`0.0`), as the code does.** Colours stay consistent between
frames and between sessions, so a threshold tuned today still works tomorrow.
The cost is a colour tint, and you have to live with it.

**Turn it on (`1.0`).** Colours look natural, but the camera re-adjusts between
frames. A hue value you measure now may not hold in the next frame.

If your image comes out heavily tinted with auto white balance off, that is
exactly what happened here — every recording in this repository has a strong
green cast for this reason. It is documented in
[module 1](../module-01-camera-conditioning/) and it turned out to matter more
than expected.

---

## How to tell your settings are actually right

This is the part worth reading carefully, because it is the mistake this whole
project is built around.

Run module 2 and look at the **HSV CHANNELS** panel, bottom right.

**Good:** the LED is bright in the VAL channel *and* bright in the SAT channel.
Bright in SAT means it has real colour the mask can select on.

**Bad:** the LED is bright in VAL but **dark in SAT**. That means the LED is
overexposed to white. It has no colour left, and no threshold anywhere downstream
can recover it.

Measured values from this repository's own frames:

| Region | Saturation |
|---|---|
| LED core (overexposed) | 11 |
| Background wall | 246 |

The background had more colour than the target. HSV thresholding assumes the
opposite, which is why the mask stayed empty through modules 2, 3 and 4.

**If your LED is dark in the SAT channel, lower your exposure before changing
anything else.** No slider in modules 2 to 5 can fix it.

Full explanation: [module 2](../module-02-hsv-segmentation/).

---

## Other things you may need to change

**Wrong camera opens.** `initialize_camera(device_index=0)` takes the first
camera. On a laptop with a built-in webcam plus a USB camera, try `1`, then `2`.

**Not on Windows.** The backend list is Windows-oriented:

```python
backends = [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_VFW, cv2.CAP_ANY]
```

On Linux or macOS the first three will not open and the loop falls through to
`cv2.CAP_ANY`, which generally works. You can shorten the list to `[cv2.CAP_ANY]`.

**A colour other than red.** Modules 2 to 5 are set up for red, which is the one
colour that wraps around the ends of the hue range and needs two windows. For any
other colour, switch `Red Mode` off in module 2 and use the H sliders. Suggested
starting ranges are in [RECOMMENDED_SETTINGS.md](RECOMMENDED_SETTINGS.md).

Note that modules 3, 4 and 5 keep their own copies of the HSV bounds in source —
a value tuned in module 2 does not carry over automatically. Each module's README
says where its copy lives.

---

## After changing anything

```bash
python tools/verify_modules.py
python tools/check_repo.py
```

The second one checks that the five copies of `initialize_camera()` still match.
If you changed one and not the others, it will say so.
