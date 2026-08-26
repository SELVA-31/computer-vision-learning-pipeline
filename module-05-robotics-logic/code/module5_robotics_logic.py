"""
Module 5: Robotics Implementation & Logic

Single-screen layout with tracking views and dashboard in a 2x2 grid.
Click any panel to expand to fullscreen. Click again to return.
"""

import cv2
import numpy as np
import math
import time


fullscreen_mode = False
fullscreen_panel = None


PANEL_ORDER = ['tracking', 'mask', 'position', 'dashboard']
HINT = "Click panel to fullscreen | 'q' quit"


def nothing(x):
    pass


class LEDTracker:
    def __init__(self, min_area=200, max_area=50000, circularity_thresh=0.6, stability_frames=3):
        self.min_area = min_area
        self.max_area = max_area
        self.circularity_thresh = circularity_thresh
        self.stability_frames = stability_frames
        self.detection_history = []
        self.last_valid_centroid = None
        self.last_valid_area = None
        self.detection_count = 0
        self.total_frames = 0

    def calculate_circularity(self, contour):
        area = cv2.contourArea(contour)
        perimeter = cv2.arcLength(contour, True)
        if perimeter == 0:
            return 0.0
        return (4 * math.pi * area) / (perimeter ** 2)

    def get_centroid(self, contour):
        M = cv2.moments(contour)
        if M["m00"] == 0:
            return None
        return (int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"]))

    def estimate_distance(self, area):
        if area <= 0:
            return 0.0
        return min(area / self.max_area, 1.0)

    def update(self, frame, mask):
        self.total_frames += 1
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            self.detection_history.append(False)
            if len(self.detection_history) > self.stability_frames:
                self.detection_history.pop(0)
            return {
                "detected": False, "centroid": self.last_valid_centroid,
                "area": self.last_valid_area, "distance_factor": 0.0,
                "circularity": 0.0, "stable": False,
                "reason": "No contours", "detection_rate": self.detection_count / max(self.total_frames, 1),
            }
        best_contour = None
        best_score = -1
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < self.min_area or area > self.max_area:
                continue
            circ = self.calculate_circularity(cnt)
            if circ < self.circularity_thresh:
                continue
            score = area * circ
            if score > best_score:
                best_score = score
                best_contour = cnt
        if best_contour is None:
            self.detection_history.append(False)
            if len(self.detection_history) > self.stability_frames:
                self.detection_history.pop(0)
            return {
                "detected": False, "centroid": self.last_valid_centroid,
                "area": self.last_valid_area, "distance_factor": 0.0,
                "circularity": 0.0, "stable": False,
                "reason": "No valid contour", "detection_rate": self.detection_count / max(self.total_frames, 1),
            }
        self.detection_count += 1
        area = cv2.contourArea(best_contour)
        centroid = self.get_centroid(best_contour)
        circ = self.calculate_circularity(best_contour)
        dist = self.estimate_distance(area)
        self.last_valid_centroid = centroid
        self.last_valid_area = area
        self.detection_history.append(True)
        if len(self.detection_history) > self.stability_frames:
            self.detection_history.pop(0)
        stable = all(self.detection_history) and len(self.detection_history) >= self.stability_frames
        return {
            "detected": True, "centroid": centroid, "area": area,
            "distance_factor": dist, "circularity": circ, "stable": stable,
            "reason": "OK", "detection_rate": self.detection_count / max(self.total_frames, 1),
        }


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
    cv2.resizeWindow("Controls", 400, 250)
    cv2.createTrackbar("Min Area", "Controls", 200, 2000, nothing)
    cv2.createTrackbar("Max Area", "Controls", 500, 1000, nothing)
    cv2.createTrackbar("Circularity", "Controls", 60, 100, nothing)
    cv2.createTrackbar("Stability", "Controls", 3, 10, nothing)


def get_params() -> dict:
    return {
        "min_area": cv2.getTrackbarPos("Min Area", "Controls"),
        "max_area": cv2.getTrackbarPos("Max Area", "Controls") * 100,
        "circularity": cv2.getTrackbarPos("Circularity", "Controls") / 100.0,
        "stability": cv2.getTrackbarPos("Stability", "Controls"),
    }


def preprocess_frame(frame: np.ndarray) -> np.ndarray:
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


def draw_tracking_overlay(frame: np.ndarray, data: dict) -> np.ndarray:
    panel = frame.copy()
    h, w = panel.shape[:2]
    cx_frame, cy_frame = w // 2, h // 2
    cv2.line(panel, (cx_frame - 20, cy_frame), (cx_frame + 20, cy_frame), (200, 200, 200), 1)
    cv2.line(panel, (cx_frame, cy_frame - 20), (cx_frame, cy_frame + 20), (200, 200, 200), 1)
    if data["detected"] and data["centroid"]:
        cx, cy = data["centroid"]
        color = (0, 255, 0) if data["stable"] else (0, 165, 255)
        cv2.circle(panel, (cx, cy), 8, color, -1)
        cv2.circle(panel, (cx, cy), 12, color, 2)
        cv2.line(panel, (cx_frame, cy_frame), (cx, cy), color, 2)
        dx, dy = cx - cx_frame, cy - cy_frame
        cv2.putText(panel, f"Offset: ({dx:+d}, {dy:+d})", (cx + 15, cy - 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        info = [
            f"Centroid: ({cx}, {cy})",
            f"Area: {int(data['area'])}",
            f"Dist: {data['distance_factor']:.2f}",
            f"Circ: {data['circularity']:.2f}",
            f"Stable: {'YES' if data['stable'] else 'NO'}",
        ]
        y = 30
        for line in info:
            cv2.putText(panel, line, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
            y += 20
    else:
        cv2.putText(panel, f"NO DETECTION: {data['reason']}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
    return panel


def create_distance_graph(data: dict, width: int = 400, height: int = 200) -> np.ndarray:
    graph = np.zeros((height, width, 3), dtype=np.uint8)
    for x in range(width):
        intensity = int(255 * (x / width))
        cv2.line(graph, (x, 0), (x, height), (0, intensity, 255 - intensity), 1)
    for i in range(6):
        x = int((i / 5) * width)
        cv2.line(graph, (x, 0), (x, height), (255, 255, 255), 1)
        cv2.putText(graph, f"{i/5:.1f}", (x - 10, height - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
    if data["detected"]:
        pos_x = int(data["distance_factor"] * width)
        pos_x = min(pos_x, width - 10)
        cv2.circle(graph, (pos_x, height // 2), 15, (255, 255, 255), -1)
        cv2.circle(graph, (pos_x, height // 2), 15, (0, 0, 0), 2)
        cv2.putText(graph, f"{data['distance_factor']:.2f}", (pos_x - 25, height // 2 - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    cv2.putText(graph, "Distance (0=Far, 1=Close)", (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    return graph


def create_position_tracker(data: dict, width: int = 400, height: int = 400) -> np.ndarray:
    tracker = np.zeros((height, width, 3), dtype=np.uint8)
    for i in range(0, width, 50):
        cv2.line(tracker, (i, 0), (i, height), (50, 50, 50), 1)
    for i in range(0, height, 50):
        cv2.line(tracker, (0, i), (width, i), (50, 50, 50), 1)
    cx, cy = width // 2, height // 2
    cv2.line(tracker, (cx - 20, cy), (cx + 20, cy), (200, 200, 200), 2)
    cv2.line(tracker, (cx, cy - 20), (cx, cy + 20), (200, 200, 200), 2)
    if data["detected"] and data["centroid"]:
        pos_x = int((data["centroid"][0] / 1280) * width)
        pos_y = int((data["centroid"][1] / 720) * height)
        color = (0, 255, 0) if data["stable"] else (0, 165, 255)
        cv2.circle(tracker, (pos_x, pos_y), 10, color, -1)
        cv2.circle(tracker, (pos_x, pos_y), 15, color, 2)
        cv2.putText(tracker, f"({data['centroid'][0]}, {data['centroid'][1]})",
                    (pos_x + 15, pos_y - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
    cv2.putText(tracker, "Position Tracker", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
    return tracker


def create_dashboard(data: dict, params: dict, fps: float) -> np.ndarray:
    width, height = 600, 500
    dash = np.zeros((height, width, 3), dtype=np.uint8)
    cv2.putText(dash, "ROBOTICS DASHBOARD", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
    if data["detected"]:
        status_color = (0, 255, 0) if data["stable"] else (0, 165, 255)
        status_text = "DETECTED" if data["stable"] else "DETECTED (UNSTABLE)"
    else:
        status_color = (0, 0, 255)
        status_text = "NOT DETECTED"
    cv2.putText(dash, f"Status: {status_text}", (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.6, status_color, 2)
    y = 110
    metrics = [
        f"FPS: {fps:.1f}",
        f"Centroid: {data['centroid'] if data['centroid'] else 'N/A'}",
        f"Area: {int(data['area']) if data['area'] else 'N/A'}",
        f"Distance: {data['distance_factor']:.3f}" if data['distance_factor'] else "Distance: N/A",
        f"Circularity: {data['circularity']:.3f}" if data['circularity'] else "Circularity: N/A",
        f"Detection Rate: {data['detection_rate']:.1%}",
        f"Min Area: {params['min_area']}  Max Area: {params['max_area']}",
        f"Circularity Threshold: {params['circularity']:.2f}",
        f"Stability Frames: {params['stability']}",
    ]
    for metric in metrics:
        cv2.putText(dash, metric, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        y += 25
    y += 15
    if data["stable"] and data["centroid"]:
        cx = data["centroid"][0]
        if abs(cx - 640) < 50:
            action = "MOVE FORWARD"
        elif cx < 640:
            action = "TURN LEFT"
        else:
            action = "TURN RIGHT"
        cv2.putText(dash, f"Action: {action}", (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    else:
        cv2.putText(dash, "Action: SEARCH", (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
    return dash


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
    print("Module 5: Robotics Logic - Single Screen")
    print("Click any panel to fullscreen. Click again to return.")
    print("Press 'q' to quit.\n")

    try:
        cap = initialize_camera(device_index=0)
        create_trackbars()

        screen_w, screen_h = 1600, 900
        cv2.namedWindow("Module 5 - Single Screen", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("Module 5 - Single Screen", screen_w, screen_h)
        mouse_state = {'screen_shape': (screen_h, screen_w), 'clicked': None,
                       'toggle': False, 'order': PANEL_ORDER}
        cv2.setMouseCallback("Module 5 - Single Screen", mouse_callback, mouse_state)

        fps = 0.0
        prev_time = time.time()
        tracker = LEDTracker()

        while True:
            ret, frame = cap.read()
            if not ret:
                continue

            current_time = time.time()
            fps = 1.0 / (current_time - prev_time) if (current_time - prev_time) > 0 else 0
            prev_time = current_time

            params = get_params()
            tracker.min_area = params["min_area"]
            tracker.max_area = params["max_area"]
            tracker.circularity_thresh = params["circularity"]
            tracker.stability_frames = params["stability"]

            mask = preprocess_frame(frame)
            data = tracker.update(frame, mask)

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

            # Tracking overlay
            tracking = draw_tracking_overlay(frame, data)
            cv2.putText(tracking, f"FPS: {fps:.1f}", (tracking.shape[1] - 100, 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            panels['tracking'] = tracking
            labels['tracking'] = "TRACKING"

            # Mask
            mask_color = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
            panels['mask'] = mask_color
            labels['mask'] = "MASK"

            # Position tracker
            pos_tracker = create_position_tracker(data)
            panels['position'] = pos_tracker
            labels['position'] = "POSITION"

            # Dashboard
            dashboard = create_dashboard(data, params, fps)
            panels['dashboard'] = dashboard
            labels['dashboard'] = "DASHBOARD"

            # Distance graph (extra panel for fullscreen)
            dist_graph = create_distance_graph(data)
            panels['distance'] = dist_graph
            labels['distance'] = "DISTANCE"

            # Render
            if fullscreen_mode and fullscreen_panel in panels:
                fs_img = cv2.resize(panels[fullscreen_panel], (screen_w, screen_h))
                cv2.putText(fs_img, f"{labels[fullscreen_panel]} - CLICK TO EXIT", 
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                cv2.imshow("Module 5 - Single Screen", fs_img)
            else:
                screen = create_single_screen(panels, labels, PANEL_ORDER, HINT,
                                              screen_w, screen_h)
                cv2.imshow("Module 5 - Single Screen", screen)

            if data["stable"]:
                print(f"\r[STABLE] C:{data['centroid']} A:{int(data['area'])} D:{data['distance_factor']:.2f}", end="")

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
        print("\n\nModule 5 complete.")


if __name__ == "__main__":
    main()
