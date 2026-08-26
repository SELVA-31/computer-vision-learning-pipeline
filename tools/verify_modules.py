"""
verify_modules.py - exercise the image-processing helpers without a camera.

Every module opens a camera in main(), so none of them can run headless. The
processing functions themselves are pure: frame in, frame out. This feeds them
a synthetic frame and checks the contracts that matter.

Run:  python tools/verify_modules.py
"""

import importlib.util
import pathlib
import py_compile
import sys

import cv2
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent


def load(rel_path: str, name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def synthetic_frame() -> np.ndarray:
    """A dark 1280x720 field with one saturated red disc - stands in for an LED."""
    frame = np.full((720, 1280, 3), 40, np.uint8)
    cv2.circle(frame, (640, 360), 60, (0, 0, 255), -1)
    return frame


def main() -> int:
    failures = []

    def check(label: str, condition: bool, detail: str = "") -> None:
        if condition:
            print(f"  PASS  {label}")
        else:
            print(f"  FAIL  {label}  {detail}")
            failures.append(label)

    print("Compiling all modules")
    for path in sorted(ROOT.glob("module-0*/code/*.py")):
        try:
            py_compile.compile(str(path), doraise=True)
            print(f"  PASS  {path.name}")
        except py_compile.PyCompileError as exc:
            print(f"  FAIL  {path.name}  {exc}")
            failures.append(path.name)

    frame = synthetic_frame()
    disc_px = int(np.pi * 60 * 60)

    print("\nModule 1 - camera conditioning")
    m1 = load("module-01-camera-conditioning/code/module1_hardware_setup.py", "m1")
    hist_panel = m1.draw_histogram(frame)
    # draw_histogram() returns the frame with a 100px histogram strip beneath it.
    # A 2x-frame height here means the view was stacked twice.
    check("draw_histogram returns frame height + 100",
          hist_panel.shape == (820, 1280, 3), f"got {hist_panel.shape}")
    check("draw_grid preserves frame size", m1.draw_grid(frame).shape == frame.shape)
    check("zoom_image preserves frame size", m1.zoom_image(frame, 1.5).shape == frame.shape)
    check("zoom_image is a no-op at 1.0x", np.array_equal(m1.zoom_image(frame, 1.0), frame))
    check("apply_brightness_contrast preserves frame size",
          m1.apply_brightness_contrast(frame, 70, 60).shape == frame.shape)
    check("apply_brightness_contrast is a no-op at centre",
          np.array_equal(m1.apply_brightness_contrast(frame, 50, 50), frame))

    print("\nModule 2 - HSV segmentation")
    m2 = load("module-02-hsv-segmentation/code/module2_hsv_color_mastery.py", "m2")
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    red = dict(h_lower=0, s_lower=120, v_lower=80,
               h_upper=10, s_upper=255, v_upper=255, red_mode=1)
    mask = m2.apply_hsv_mask(hsv, red)
    covered = int((mask > 0).sum())
    check(f"dual-range red mask covers the disc ({covered}/{disc_px} px)",
          covered > disc_px * 0.9)

    # Known behaviour, documented in the module README rather than fixed:
    # with Red Mode on, the hue bounds are hardcoded and the H sliders do nothing.
    shifted = m2.apply_hsv_mask(hsv, dict(red, h_lower=90, h_upper=130))
    check("Red Mode bypasses the H sliders (known, documented)",
          np.array_equal(shifted, mask))

    # With Red Mode off the sliders take effect, and a blue window finds no red.
    blue = dict(red, red_mode=0, h_lower=90, h_upper=130)
    check("Red Mode off - a blue hue window rejects the red disc",
          int((m2.apply_hsv_mask(hsv, blue) > 0).sum()) == 0)

    check("draw_hsv_channels returns three 200x200 tiles",
          m2.draw_hsv_channels(hsv).shape == (200, 600, 3))

    print("\nModule 4 - pattern detection")
    m4 = load("module-04-pattern-detection/code/module4_pattern_detection.py", "m4")
    detect_mask = m4.preprocess_for_detection(frame)
    found = m4.detect_contours(detect_mask, min_area=200, circularity_thresh=0.6)
    check(f"contour path finds the disc ({len(found)} contour(s))", len(found) >= 1)
    if found:
        circ = found[0]["circularity"]
        check(f"disc circularity is near 1.0 (got {circ:.3f})", 0.85 <= circ <= 1.05)

    print()
    print("All modules - 2x2 layout and click routing")
    for module_dir in sorted(ROOT.glob("module-0*")):
        sources = sorted((module_dir / "code").glob("*.py"))
        if not sources:
            continue
        mod = load(sources[0].relative_to(ROOT).as_posix(), sources[0].stem)
        order, hint = mod.PANEL_ORDER, mod.HINT
        panels = {key: frame for key in order}
        labels = {key: key.upper() for key in order}

        screen = mod.create_single_screen(panels, labels, order, hint, 1600, 900)
        check(f"{module_dir.name}: composite is 900x1600",
              screen.shape == (900, 1600, 3), f"got {screen.shape}")
        quadrants = [screen[0:450, 0:800], screen[0:450, 800:1600],
                     screen[450:900, 0:800], screen[450:900, 800:1600]]
        check(f"{module_dir.name}: all four quadrants painted",
              all(q.any() for q in quadrants))

        # A click in each quadrant must select the panel that was drawn there.
        centres = [(400, 200), (1200, 200), (400, 700), (1200, 700)]
        routed = []
        for (cx, cy) in centres:
            state = {"screen_shape": (900, 1600), "clicked": None,
                     "toggle": False, "order": order}
            mod.mouse_callback(cv2.EVENT_LBUTTONDOWN, cx, cy, 0, state)
            routed.append(state["clicked"])
        check(f"{module_dir.name}: clicks route to {order}", routed == order,
              f"got {routed}")

        state = {"screen_shape": (900, 1600), "clicked": None,
                 "toggle": False, "order": order}
        mod.mouse_callback(cv2.EVENT_MOUSEMOVE, 400, 200, 0, state)
        check(f"{module_dir.name}: mouse move does not toggle fullscreen",
              state["toggle"] is False)

    print()
    if failures:
        print(f"{len(failures)} check(s) FAILED: {', '.join(failures)}")
        return 1
    print("All checks passed - no camera required.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
