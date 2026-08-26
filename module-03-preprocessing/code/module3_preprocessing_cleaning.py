"""
Module 3: Pre-Processing & Cleaning

Single-screen layout showing all pipeline stages in a 2x2 grid.
Click any panel to expand to fullscreen. Click again to return.
"""

import cv2
import numpy as np


fullscreen_mode = False
fullscreen_panel = None


PANEL_ORDER = ['blurred', 'raw_mask', 'eroded', 'cleaned']
HINT = "Click panel to fullscreen | 'q' quit | 'r' reset"


def nothing(x):
    pass


def initialize_camera(device_index: int = 0) -> cv2.VideoCapture:
    """Open the camera and pin every automatic control.

    Identical in all five modules on purpose: each one must produce the same
    frames regardless of which module ran before it. Windows camera drivers
    retain property state between processes, so a module that leaves a control
    unset inherits whatever the previous run left behind.
    """
    backends = [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_VFW, cv2.CAP_ANY]
    cap = None
    for backend in backends:
        cap = cv2.VideoCapture(device_index, backend)
        if cap.isOpened():
            print(f"Camera opened with backend: {backend}")
            break
        cap.release()
    if cap is None or not cap.isOpened():
        raise RuntimeError("Failed to open camera. Check USB connection.")
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)
    cap.set(cv2.CAP_PROP_EXPOSURE, -6.0)
    cap.set(cv2.CAP_PROP_GAIN, 0.0)
    cap.set(cv2.CAP_PROP_AUTO_WB, 0.0)
    cap.set(cv2.CAP_PROP_FPS, 30)
    return cap


def create_trackbars() -> None:
    cv2.namedWindow("Controls", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Controls", 400, 300)
    cv2.createTrackbar("Blur Kernel", "Controls", 1, 5, nothing)
    cv2.createTrackbar("Erode Iter", "Controls", 1, 5, nothing)
    cv2.createTrackbar("Dilate Iter", "Controls", 1, 5, nothing)
    cv2.createTrackbar("Morph Kernel", "Controls", 1, 5, nothing)


def get_params() -> dict:
    blur_n = cv2.getTrackbarPos("Blur Kernel", "Controls")
    erode = cv2.getTrackbarPos("Erode Iter", "Controls")
    dilate = cv2.getTrackbarPos("Dilate Iter", "Controls")
    morph_n = cv2.getTrackbarPos("Morph Kernel", "Controls")
    return {
        "blur_kernel": 2 * blur_n + 1,
        "erode_iter": max(erode, 0),
        "dilate_iter": max(dilate, 0),
        "morph_kernel": 2 * morph_n + 1,
    }


def preprocess_frame(frame: np.ndarray, params: dict, hsv_bounds: dict) -> dict:
    results = {}
    blurred = cv2.GaussianBlur(frame, (params["blur_kernel"], params["blur_kernel"]), 0)
    results["blurred"] = blurred
    hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)
    if hsv_bounds.get("red_mode", 0):
        lower1 = np.array([0, hsv_bounds["s_lower"], hsv_bounds["v_lower"]])
        upper1 = np.array([10, hsv_bounds["s_upper"], hsv_bounds["v_upper"]])
        mask1 = cv2.inRange(hsv, lower1, upper1)
        lower2 = np.array([170, hsv_bounds["s_lower"], hsv_bounds["v_lower"]])
        upper2 = np.array([179, hsv_bounds["s_upper"], hsv_bounds["v_upper"]])
        mask2 = cv2.inRange(hsv, lower2, upper2)
        mask = cv2.bitwise_or(mask1, mask2)
    else:
        lower = np.array([hsv_bounds["h_lower"], hsv_bounds["s_lower"], hsv_bounds["v_lower"]])
        upper = np.array([hsv_bounds["h_upper"], hsv_bounds["s_upper"], hsv_bounds["v_upper"]])
        mask = cv2.inRange(hsv, lower, upper)
    results["raw_mask"] = mask
    morph_kernel = np.ones((params["morph_kernel"], params["morph_kernel"]), np.uint8)
    eroded = cv2.erode(mask, morph_kernel, iterations=params["erode_iter"])
    results["eroded"] = eroded
    dilated = cv2.dilate(eroded, morph_kernel, iterations=params["dilate_iter"])
    results["cleaned_mask"] = dilated
    results["isolated"] = cv2.bitwise_and(frame, frame, mask=dilated)
    return results


def create_diff_visualization(raw_mask: np.ndarray, eroded: np.ndarray, dilated: np.ndarray) -> np.ndarray:
    removed = cv2.subtract(raw_mask, eroded)
    added = cv2.subtract(dilated, eroded)
    vis = np.zeros((raw_mask.shape[0], raw_mask.shape[1], 3), dtype=np.uint8)
    vis[removed > 0] = [0, 0, 255]  # Red = removed
    vis[added > 0] = [0, 255, 0]    # Green = added
    cv2.putText(vis, "RED=Erosion removed | Green=Dilation added", (10, 25),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    return vis


def create_single_screen(panels: dict, labels: dict, order: list, hint: str,
                         screen_w: int = 1600, screen_h: int = 900) -> np.ndarray:
    """Composite four panels into one 2x2 window.

    `order` names the panels top-left, top-right, bottom-left, bottom-right.
    Identical in all five modules -- only the names passed in differ, so this
    cannot drift between copies. Enforced by tools/check_repo.py.
    """
    panel_h = screen_h // 2
    panel_w = screen_w // 2
    slots = [(0, 0), (0, panel_w), (panel_h, 0), (panel_h, panel_w)]
    screen = np.zeros((screen_h, screen_w, 3), dtype=np.uint8)
    for panel_key, (y, x) in zip(order, slots):
        if panel_key not in panels:
            continue
        resized = cv2.resize(panels[panel_key], (panel_w, panel_h))
        label = labels.get(panel_key, panel_key.upper())
        cv2.putText(resized, label, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        cv2.rectangle(resized, (0, 0), (panel_w - 1, panel_h - 1), (100, 100, 100), 2)
        screen[y:y + panel_h, x:x + panel_w] = resized
    cv2.putText(screen, hint, (10, screen_h - 15),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
    return screen


def mouse_callback(event, x, y, flags, param):
    """Map a click to one of the four quadrants.

    Panel names are read from param['order'], so this function is identical in
    all five modules. Enforced by tools/check_repo.py.
    """
    if event != cv2.EVENT_LBUTTONDOWN:
        return
    screen_h, screen_w = param['screen_shape']
    col = 0 if x < screen_w // 2 else 1
    row = 0 if y < screen_h // 2 else 1
    param['clicked'] = param['order'][row * 2 + col]
    param['toggle'] = True


def main():
    global fullscreen_mode, fullscreen_panel
    print("Module 3: Pre-Processing - Single Screen")
    print("Click any panel to fullscreen. Click again to return.")
    print("Press 'q' to quit, 'r' to reset sliders.\n")

    hsv_bounds = {
        "h_lower": 0, "s_lower": 120, "v_lower": 80,
        "h_upper": 10, "s_upper": 255, "v_upper": 255,
        "red_mode": 1,
    }

    try:
        cap = initialize_camera(device_index=0)
        create_trackbars()

        screen_w, screen_h = 1600, 900
        cv2.namedWindow("Module 3 - Single Screen", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("Module 3 - Single Screen", screen_w, screen_h)
        mouse_state = {'screen_shape': (screen_h, screen_w), 'clicked': None,
                       'toggle': False, 'order': PANEL_ORDER}
        cv2.setMouseCallback("Module 3 - Single Screen", mouse_callback, mouse_state)

        while True:
            ret, frame = cap.read()
            if not ret:
                continue

            params = get_params()
            results = preprocess_frame(frame, params, hsv_bounds)

            # Handle mouse click toggle
            if mouse_state['toggle']:
                clicked = mouse_state['clicked']
                if fullscreen_mode and fullscreen_panel == clicked:
                    fullscreen_mode = False
                    fullscreen_panel = None
                else:
                    fullscreen_mode = True
                    fullscreen_panel = clicked
                mouse_state['toggle'] = False

            # Build panels
            panels = {}
            labels = {}

            panels['blurred'] = results["blurred"]
            labels['blurred'] = f"BLURRED ({params['blur_kernel']}x{params['blur_kernel']})"

            raw_color = cv2.cvtColor(results["raw_mask"], cv2.COLOR_GRAY2BGR)
            panels['raw_mask'] = raw_color
            labels['raw_mask'] = "RAW MASK"

            eroded_color = cv2.cvtColor(results["eroded"], cv2.COLOR_GRAY2BGR)
            panels['eroded'] = eroded_color
            labels['eroded'] = f"ERODED ({params['erode_iter']}x)"

            cleaned_color = cv2.cvtColor(results["cleaned_mask"], cv2.COLOR_GRAY2BGR)
            panels['cleaned'] = cleaned_color
            labels['cleaned'] = f"CLEANED ({params['dilate_iter']}x dilate)"

            # Also create diff panel for fullscreen viewing
            diff_vis = create_diff_visualization(results["raw_mask"], results["eroded"], results["cleaned_mask"])
            panels['diff'] = diff_vis
            labels['diff'] = "DIFF VISUALIZATION"

            # Render
            if fullscreen_mode and fullscreen_panel in panels:
                fs_img = cv2.resize(panels[fullscreen_panel], (screen_w, screen_h))
                cv2.putText(fs_img, f"{labels[fullscreen_panel]} - CLICK TO EXIT", 
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                cv2.imshow("Module 3 - Single Screen", fs_img)
            else:
                screen = create_single_screen(panels, labels, PANEL_ORDER, HINT,
                                              screen_w, screen_h)
                cv2.imshow("Module 3 - Single Screen", screen)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == 27:
                fullscreen_mode = False
                fullscreen_panel = None
                mouse_state['toggle'] = False
            elif key == ord('r'):
                cv2.setTrackbarPos("Blur Kernel", "Controls", 1)
                cv2.setTrackbarPos("Erode Iter", "Controls", 1)
                cv2.setTrackbarPos("Dilate Iter", "Controls", 1)
                cv2.setTrackbarPos("Morph Kernel", "Controls", 1)
                print("Trackbars reset.")

    except RuntimeError as e:
        print(f"Error: {e}")
    finally:
        if 'cap' in locals():
            cap.release()
        cv2.destroyAllWindows()
        print("\nModule 3 complete.")


if __name__ == "__main__":
    main()
