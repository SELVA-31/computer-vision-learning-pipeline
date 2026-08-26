"""
Module 4: Pattern Detection & Shape Analysis

Single-screen layout with all detection views in a 2x2 grid.
Click any panel to expand to fullscreen. Click again to return.
"""

import cv2
import numpy as np
import math


fullscreen_mode = False
fullscreen_panel = None


PANEL_ORDER = ['original', 'mask', 'contours', 'hough']
HINT = "Click panel to fullscreen | 'q' quit"


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
    cv2.resizeWindow("Controls", 400, 350)
    cv2.createTrackbar("Min Area", "Controls", 200, 2000, nothing)
    cv2.createTrackbar("Circularity", "Controls", 60, 100, nothing)
    cv2.createTrackbar("Hough DP", "Controls", 12, 30, nothing)
    cv2.createTrackbar("Hough Param2", "Controls", 25, 100, nothing)
    cv2.createTrackbar("Min Radius", "Controls", 5, 100, nothing)
    cv2.createTrackbar("Max Radius", "Controls", 100, 200, nothing)


def get_params() -> dict:
    return {
        "min_area": cv2.getTrackbarPos("Min Area", "Controls"),
        "circularity": cv2.getTrackbarPos("Circularity", "Controls") / 100.0,
        "hough_dp": cv2.getTrackbarPos("Hough DP", "Controls") / 10.0,
        "hough_param2": cv2.getTrackbarPos("Hough Param2", "Controls"),
        "min_radius": cv2.getTrackbarPos("Min Radius", "Controls"),
        "max_radius": cv2.getTrackbarPos("Max Radius", "Controls"),
    }


def preprocess_for_detection(frame: np.ndarray) -> np.ndarray:
    blurred = cv2.GaussianBlur(frame, (5, 5), 0)
    hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)
    lower1 = np.array([0, 120, 80])
    upper1 = np.array([10, 255, 255])
    mask1 = cv2.inRange(hsv, lower1, upper1)
    lower2 = np.array([170, 120, 80])
    upper2 = np.array([179, 255, 255])
    mask2 = cv2.inRange(hsv, lower2, upper2)
    mask = cv2.bitwise_or(mask1, mask2)
    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.erode(mask, kernel, iterations=1)
    mask = cv2.dilate(mask, kernel, iterations=1)
    return mask


def calculate_circularity(contour: np.ndarray) -> float:
    area = cv2.contourArea(contour)
    perimeter = cv2.arcLength(contour, True)
    if perimeter == 0:
        return 0.0
    return (4 * math.pi * area) / (perimeter ** 2)


def detect_contours(mask: np.ndarray, min_area: int, circularity_thresh: float) -> list:
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    results = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < min_area:
            continue
        circ = calculate_circularity(cnt)
        results.append({
            "contour": cnt,
            "area": area,
            "circularity": circ,
            "valid": circ >= circularity_thresh,
        })
    results.sort(key=lambda x: x["area"], reverse=True)
    return results


def detect_hough_circles(gray: np.ndarray, params: dict) -> np.ndarray:
    return cv2.HoughCircles(
        gray, cv2.HOUGH_GRADIENT,
        dp=params["hough_dp"], minDist=50,
        param1=100, param2=params["hough_param2"],
        minRadius=params["min_radius"], maxRadius=params["max_radius"],
    )


def draw_contour_panel(frame: np.ndarray, contours_info: list) -> np.ndarray:
    panel = frame.copy()
    for info in contours_info:
        color = (0, 255, 0) if info["valid"] else (0, 0, 255)
        cv2.drawContours(panel, [info["contour"]], -1, color, 2)
        M = cv2.moments(info["contour"])
        if M["m00"] != 0:
            cx = int(M["m10"] / M["m00"])
            cy = int(M["m01"] / M["m00"])
            cv2.circle(panel, (cx, cy), 5, (255, 0, 0), -1)
            cv2.putText(panel, f"C:{info['circularity']:.2f}", (cx + 10, cy - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
    return panel


def draw_hough_panel(frame: np.ndarray, circles: np.ndarray) -> np.ndarray:
    panel = frame.copy()
    if circles is not None:
        circles = np.uint16(np.around(circles))
        for c in circles[0, :]:
            cv2.circle(panel, (c[0], c[1]), c[2], (255, 255, 0), 2)
            cv2.circle(panel, (c[0], c[1]), 3, (0, 0, 255), -1)
            cv2.putText(panel, f"r={c[2]}", (c[0] + 10, c[1] - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 0), 1)
    return panel


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
    print("Module 4: Pattern Detection - Single Screen")
    print("Click any panel to fullscreen. Click again to return.")
    print("Press 'q' to quit.\n")

    try:
        cap = initialize_camera(device_index=0)
        create_trackbars()

        screen_w, screen_h = 1600, 900
        cv2.namedWindow("Module 4 - Single Screen", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("Module 4 - Single Screen", screen_w, screen_h)
        mouse_state = {'screen_shape': (screen_h, screen_w), 'clicked': None,
                       'toggle': False, 'order': PANEL_ORDER}
        cv2.setMouseCallback("Module 4 - Single Screen", mouse_callback, mouse_state)

        while True:
            ret, frame = cap.read()
            if not ret:
                continue

            params = get_params()
            mask = preprocess_for_detection(frame)
            contours_info = detect_contours(mask, params["min_area"], params["circularity"])
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            hough_circles = detect_hough_circles(gray, params)

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

            # Original with stats
            orig = frame.copy()
            valid_count = sum(1 for c in contours_info if c["valid"])
            hough_count = hough_circles.shape[1] if hough_circles is not None else 0
            stats = [
                f"Contours: {valid_count}/{len(contours_info)} valid",
                f"Hough: {hough_count} circles",
                f"Min Area: {params['min_area']}  Circ: {params['circularity']:.2f}",
            ]
            y = 30
            for line in stats:
                cv2.putText(orig, line, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                y += 20
            panels['original'] = orig
            labels['original'] = "ORIGINAL"

            # Mask
            mask_color = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
            panels['mask'] = mask_color
            labels['mask'] = "MASK"

            # Contours
            contour_panel = draw_contour_panel(frame, contours_info)
            panels['contours'] = contour_panel
            labels['contours'] = "CONTOURS"

            # Hough
            hough_panel = draw_hough_panel(frame, hough_circles)
            panels['hough'] = hough_panel
            labels['hough'] = "HOUGH CIRCLES"

            # Render
            if fullscreen_mode and fullscreen_panel in panels:
                fs_img = cv2.resize(panels[fullscreen_panel], (screen_w, screen_h))
                cv2.putText(fs_img, f"{labels[fullscreen_panel]} - CLICK TO EXIT", 
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                cv2.imshow("Module 4 - Single Screen", fs_img)
            else:
                screen = create_single_screen(panels, labels, PANEL_ORDER, HINT,
                                              screen_w, screen_h)
                cv2.imshow("Module 4 - Single Screen", screen)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == 27:
                fullscreen_mode = False
                fullscreen_panel = None
                mouse_state['toggle'] = False

    except RuntimeError as e:
        print(f"Error: {e}")
    finally:
        if 'cap' in locals():
            cap.release()
        cv2.destroyAllWindows()
        print("\nModule 4 complete.")


if __name__ == "__main__":
    main()
