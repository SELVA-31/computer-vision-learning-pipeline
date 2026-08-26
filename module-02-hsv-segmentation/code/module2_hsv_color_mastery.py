"""
Module 2: Digital Color Mastery (HSV)

Single-screen layout with all visualizations in a 2x2 grid.
Click any panel to expand to fullscreen. Click again to return.
"""

import cv2
import numpy as np


# Global state for fullscreen toggle
fullscreen_mode = False
fullscreen_panel = None


PANEL_ORDER = ['original', 'mask', 'result', 'channels']
HINT = "Click panel to fullscreen | 'q' quit | 's' save"


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
    cv2.resizeWindow("Controls", 400, 400)
    cv2.createTrackbar("H Lower", "Controls", 0, 179, nothing)
    cv2.createTrackbar("S Lower", "Controls", 120, 255, nothing)
    cv2.createTrackbar("V Lower", "Controls", 80, 255, nothing)
    cv2.createTrackbar("H Upper", "Controls", 10, 179, nothing)
    cv2.createTrackbar("S Upper", "Controls", 255, 255, nothing)
    cv2.createTrackbar("V Upper", "Controls", 255, 255, nothing)
    cv2.createTrackbar("Red Mode", "Controls", 1, 1, nothing)


def get_hsv_bounds() -> dict:
    return {
        "h_lower": cv2.getTrackbarPos("H Lower", "Controls"),
        "s_lower": cv2.getTrackbarPos("S Lower", "Controls"),
        "v_lower": cv2.getTrackbarPos("V Lower", "Controls"),
        "h_upper": cv2.getTrackbarPos("H Upper", "Controls"),
        "s_upper": cv2.getTrackbarPos("S Upper", "Controls"),
        "v_upper": cv2.getTrackbarPos("V Upper", "Controls"),
        "red_mode": cv2.getTrackbarPos("Red Mode", "Controls"),
    }


def apply_hsv_mask(hsv_frame: np.ndarray, bounds: dict) -> np.ndarray:
    if bounds["red_mode"] == 1:
        lower1 = np.array([0, bounds["s_lower"], bounds["v_lower"]])
        upper1 = np.array([10, bounds["s_upper"], bounds["v_upper"]])
        mask1 = cv2.inRange(hsv_frame, lower1, upper1)
        lower2 = np.array([170, bounds["s_lower"], bounds["v_lower"]])
        upper2 = np.array([179, bounds["s_upper"], bounds["v_upper"]])
        mask2 = cv2.inRange(hsv_frame, lower2, upper2)
        mask = cv2.bitwise_or(mask1, mask2)
    else:
        lower = np.array([bounds["h_lower"], bounds["s_lower"], bounds["v_lower"]])
        upper = np.array([bounds["h_upper"], bounds["s_upper"], bounds["v_upper"]])
        mask = cv2.inRange(hsv_frame, lower, upper)
    return mask


def draw_hsv_channels(hsv_frame: np.ndarray) -> np.ndarray:
    h, s, v = cv2.split(hsv_frame)
    h_color = cv2.applyColorMap(h, cv2.COLORMAP_HSV)
    s_color = cv2.cvtColor(s, cv2.COLOR_GRAY2BGR)
    v_color = cv2.cvtColor(v, cv2.COLOR_GRAY2BGR)
    target_h = 200
    h_r = cv2.resize(h_color, (200, target_h))
    s_r = cv2.resize(s_color, (200, target_h))
    v_r = cv2.resize(v_color, (200, target_h))
    cv2.putText(h_r, "HUE", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
    cv2.putText(s_r, "SAT", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
    cv2.putText(v_r, "VAL", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
    return np.hstack([h_r, s_r, v_r])


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
    print("Module 2: HSV Color Mastery - Single Screen")
    print("Click any panel to fullscreen. Click again to return.")
    print("Press 'q' to quit, 's' to save HSV values.\n")

    try:
        cap = initialize_camera(device_index=0)
        create_trackbars()

        screen_w, screen_h = 1600, 900
        cv2.namedWindow("Module 2 - Single Screen", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("Module 2 - Single Screen", screen_w, screen_h)
        mouse_state = {'screen_shape': (screen_h, screen_w), 'clicked': None,
                       'toggle': False, 'order': PANEL_ORDER}
        cv2.setMouseCallback("Module 2 - Single Screen", mouse_callback, mouse_state)

        saved_bounds = None

        while True:
            ret, frame = cap.read()
            if not ret:
                continue

            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            bounds = get_hsv_bounds()
            mask = apply_hsv_mask(hsv, bounds)
            result = cv2.bitwise_and(frame, frame, mask=mask)

            # Build panels
            panels = {}
            labels = {}

            # Original with info
            orig = frame.copy()
            info = [
                f"Red Mode: {'ON' if bounds['red_mode'] else 'OFF'}",
                f"H: {bounds['h_lower']}-{bounds['h_upper']}",
                f"S: {bounds['s_lower']}-{bounds['s_upper']}",
                f"V: {bounds['v_lower']}-{bounds['v_upper']}",
            ]
            y = 30
            for line in info:
                cv2.putText(orig, line, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                y += 20
            panels['original'] = orig
            labels['original'] = "ORIGINAL"

            # Mask
            mask_color = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
            panels['mask'] = mask_color
            labels['mask'] = "BINARY MASK"

            # Result
            panels['result'] = result
            labels['result'] = "MASKED RESULT"

            # HSV Channels
            channels = draw_hsv_channels(hsv)
            # Resize to match frame aspect
            ch_h, ch_w = channels.shape[:2]
            target_w = frame.shape[1]
            target_h = int(ch_h * target_w / ch_w)
            channels_resized = cv2.resize(channels, (target_w, target_h))
            # Pad or crop to frame height
            if channels_resized.shape[0] < frame.shape[0]:
                pad = np.zeros((frame.shape[0] - channels_resized.shape[0], target_w, 3), dtype=np.uint8)
                channels_resized = np.vstack([channels_resized, pad])
            else:
                channels_resized = channels_resized[:frame.shape[0], :]
            panels['channels'] = channels_resized
            labels['channels'] = "HSV CHANNELS"

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
            
            # Render
            if fullscreen_mode and fullscreen_panel in panels:
                fs_img = cv2.resize(panels[fullscreen_panel], (screen_w, screen_h))
                cv2.putText(fs_img, f"{labels[fullscreen_panel]} - CLICK TO EXIT", 
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                cv2.imshow("Module 2 - Single Screen", fs_img)
            else:
                screen = create_single_screen(panels, labels, PANEL_ORDER, HINT,
                                              screen_w, screen_h)
                cv2.imshow("Module 2 - Single Screen", screen)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == 27:
                fullscreen_mode = False
                fullscreen_panel = None
                mouse_state['toggle'] = False
            elif key == ord('s'):
                saved_bounds = bounds.copy()
                print("Saved HSV bounds:")
                print(f"  Lower: ({bounds['h_lower']}, {bounds['s_lower']}, {bounds['v_lower']})")
                print(f"  Upper: ({bounds['h_upper']}, {bounds['s_upper']}, {bounds['v_upper']})")
                if bounds['red_mode']:
                    print("  Red Mode: ON")

    except RuntimeError as e:
        print(f"Error: {e}")
    finally:
        if 'cap' in locals():
            cap.release()
        cv2.destroyAllWindows()
        print("\nModule 2 complete.")


if __name__ == "__main__":
    main()
