"""
Module 1: Hardware Setup & The Physics of Vision

Single-screen layout with toggleable panels.
Click on any panel to expand it to fullscreen. Press ESC or click again to return.
"""

import cv2
import time
import numpy as np


# Global state for fullscreen toggle
fullscreen_mode = False
fullscreen_panel = None


def nothing(x):
    pass


def initialize_camera(device_index: int = 0) -> cv2.VideoCapture:
    """Initialize camera with fallback backends."""
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


def create_trackbars(window_name: str) -> None:
    """Create sliders on the control panel window."""
    cv2.namedWindow("Controls", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Controls", 400, 300)
    cv2.createTrackbar("Brightness", "Controls", 50, 100, nothing)
    cv2.createTrackbar("Contrast", "Controls", 50, 100, nothing)
    cv2.createTrackbar("Saturation", "Controls", 50, 100, nothing)
    cv2.createTrackbar("Show Grid", "Controls", 1, 1, nothing)
    cv2.createTrackbar("Show Histogram", "Controls", 0, 1, nothing)
    cv2.createTrackbar("Zoom", "Controls", 10, 20, nothing)


def apply_brightness_contrast(image: np.ndarray, brightness: int, contrast: int) -> np.ndarray:
    brightness = brightness - 50
    contrast = contrast - 50
    if contrast != 0:
        f = 131 * (contrast + 127) / (127 * (131 - contrast))
        adjusted = cv2.addWeighted(image, f, image, 0, 127 * (1 - f))
    else:
        adjusted = image.copy()
    if brightness != 0:
        adjusted = cv2.convertScaleAbs(adjusted, alpha=1, beta=brightness)
    return adjusted


def draw_grid(image: np.ndarray, spacing: int = 100) -> np.ndarray:
    h, w = image.shape[:2]
    grid_img = image.copy()
    for y in range(0, h, spacing):
        cv2.line(grid_img, (0, y), (w, y), (0, 255, 0), 1)
        cv2.putText(grid_img, f"{y}px", (5, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
    for x in range(0, w, spacing):
        cv2.line(grid_img, (x, 0), (x, h), (0, 255, 0), 1)
        cv2.putText(grid_img, f"{x}px", (x + 5, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
    cx, cy = w // 2, h // 2
    cv2.line(grid_img, (cx - 30, cy), (cx + 30, cy), (0, 0, 255), 2)
    cv2.line(grid_img, (cx, cy - 30), (cx, cy + 30), (0, 0, 255), 2)
    cv2.circle(grid_img, (cx, cy), 5, (0, 0, 255), -1)
    return grid_img


def draw_histogram(image: np.ndarray) -> np.ndarray:
    h, w = image.shape[:2]
    hist_h = 100
    hist_w = 256
    hist_img = np.zeros((hist_h, hist_w, 3), dtype=np.uint8)
    colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255)]
    for i, color in enumerate(colors):
        hist = cv2.calcHist([image], [i], None, [256], [0, 256])
        cv2.normalize(hist, hist, 0, hist_h, cv2.NORM_MINMAX)
        # calcHist returns shape (256, 1). Indexing it yields a 1-element
        # array, and numpy >= 2.0 refuses to coerce that to int. Flatten to
        # a plain (256,) vector so the bin values are scalars.
        hist = hist.flatten()
        for j in range(1, 256):
            pt1 = (j - 1, hist_h - int(hist[j - 1]))
            pt2 = (j, hist_h - int(hist[j]))
            cv2.line(hist_img, pt1, pt2, color, 1)
    # Resize histogram to match image width, then stack vertically
    hist_resized = cv2.resize(hist_img, (w, hist_h))
    combined = np.vstack([image, hist_resized])
    return combined


def zoom_image(image: np.ndarray, zoom_factor: float) -> np.ndarray:
    h, w = image.shape[:2]
    if zoom_factor <= 1.0:
        return image.copy()
    new_w = int(w / zoom_factor)
    new_h = int(h / zoom_factor)
    x1 = max(0, w // 2 - new_w // 2)
    y1 = max(0, h // 2 - new_h // 2)
    x2 = min(w, x1 + new_w)
    y2 = min(h, y1 + new_h)
    cropped = image[y1:y2, x1:x2]
    return cv2.resize(cropped, (w, h))


def create_single_screen(panels: dict, labels: dict, screen_w: int = 1600, screen_h: int = 900) -> np.ndarray:
    """
    Arrange multiple panels into a single screen layout.
    panels: dict of panel_name -> image
    labels: dict of panel_name -> label text
    """
    # Define layout: 2x2 grid
    panel_h = screen_h // 2
    panel_w = screen_w // 2
    
    layout = {
        'top_left': ('main', (0, 0)),
        'top_right': ('histogram', (0, panel_w)),
        'bottom_left': ('grid', (panel_h, 0)),
        'bottom_right': ('zoom', (panel_h, panel_w)),
    }
    
    screen = np.zeros((screen_h, screen_w, 3), dtype=np.uint8)
    
    for slot_name, (panel_key, (y, x)) in layout.items():
        if panel_key not in panels:
            continue
        panel = panels[panel_key]
        # Resize panel to fit slot
        resized = cv2.resize(panel, (panel_w, panel_h))
        # Add label
        label = labels.get(panel_key, panel_key.upper())
        cv2.putText(resized, label, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        # Add border
        cv2.rectangle(resized, (0, 0), (panel_w - 1, panel_h - 1), (100, 100, 100), 2)
        # Place on screen
        screen[y:y + panel_h, x:x + panel_w] = resized
    
    # Add instruction overlay
    instruction = "Click any panel to fullscreen | Press 'q' to quit"
    cv2.putText(screen, instruction, (10, screen_h - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
    
    return screen


def mouse_callback(event, x, y, flags, param):
    """Handle mouse clicks to toggle fullscreen on panels."""
    if event == cv2.EVENT_LBUTTONDOWN:
        screen_h, screen_w = param['screen_shape']
        panel_h = screen_h // 2
        panel_w = screen_w // 2

        # Determine which panel was clicked
        if y < panel_h and x < panel_w:
            clicked = 'main'
        elif y < panel_h and x >= panel_w:
            clicked = 'histogram'
        elif y >= panel_h and x < panel_w:
            clicked = 'grid'
        else:
            clicked = 'zoom'

        param['clicked'] = clicked
        param['toggle'] = True


def main():
    global fullscreen_mode, fullscreen_panel
    print("Module 1: Hardware Setup - Single Screen Mode")
    print("==============================================")
    print("Click any panel to expand to fullscreen.")
    print("Click again or press ESC to return to grid view.")
    print("Press 'q' to quit.")
    print("==============================================\n")

    try:
        cap = initialize_camera(device_index=0)
        create_trackbars("Controls")

        exposure = cap.get(cv2.CAP_PROP_EXPOSURE)
        gain = cap.get(cv2.CAP_PROP_GAIN)
        prev_time = time.time()
        fps = 0.0

        # Main display window
        screen_w, screen_h = 1600, 900
        cv2.namedWindow("Module 1 - Single Screen", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("Module 1 - Single Screen", screen_w, screen_h)
        mouse_state = {'screen_shape': (screen_h, screen_w), 'clicked': None, 'toggle': False}
        cv2.setMouseCallback("Module 1 - Single Screen", mouse_callback, mouse_state)

        while True:
            ret, frame = cap.read()
            if not ret:
                continue

            current_time = time.time()
            fps = 1.0 / (current_time - prev_time) if (current_time - prev_time) > 0 else 0
            prev_time = current_time

            # Get slider values
            brightness = cv2.getTrackbarPos("Brightness", "Controls")
            contrast = cv2.getTrackbarPos("Contrast", "Controls")
            saturation = cv2.getTrackbarPos("Saturation", "Controls")
            show_grid = cv2.getTrackbarPos("Show Grid", "Controls")
            show_histogram = cv2.getTrackbarPos("Show Histogram", "Controls")
            zoom = cv2.getTrackbarPos("Zoom", "Controls")

            # Process main image
            display = apply_brightness_contrast(frame, brightness, contrast)
            saturation_scale = saturation / 50.0
            hsv = cv2.cvtColor(display, cv2.COLOR_BGR2HSV).astype(np.float32)
            hsv[:, :, 1] = np.clip(hsv[:, :, 1] * saturation_scale, 0, 255)
            display = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)

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

            # Create panels
            panels = {}
            labels = {}
            
            # Main panel
            main_panel = display.copy()
            info_lines = [
                f"FPS: {fps:.1f}",
                f"Res: {int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))}x{int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))}",
                f"Exp: {exposure:.1f} Gain: {gain:.1f}",
                f"B:{brightness-50:+d} C:{contrast-50:+d} S:{saturation/50.0:.1f}x",
            ]
            y = 30
            for line in info_lines:
                cv2.putText(main_panel, line, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                y += 20
            panels['main'] = main_panel
            labels['main'] = "MAIN VIEW"
            
            # Grid panel
            if show_grid:
                grid_panel = draw_grid(display.copy())
            else:
                grid_panel = np.zeros_like(display)
                cv2.putText(grid_panel, "GRID OFF", (display.shape[1]//2 - 50, display.shape[0]//2), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (100, 100, 100), 2)
            panels['grid'] = grid_panel
            labels['grid'] = "GRID OVERLAY"
            
            # Zoom panel
            zoom_factor = zoom / 10.0
            if zoom_factor > 1.0:
                zoom_panel = zoom_image(display.copy(), zoom_factor)
                cv2.putText(zoom_panel, f"Zoom: {zoom_factor:.1f}x", (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
            else:
                zoom_panel = display.copy()
                cv2.putText(zoom_panel, "Zoom: 1.0x", (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
            panels['zoom'] = zoom_panel
            labels['zoom'] = "ZOOM VIEW"
            
            # Histogram panel
            if show_histogram:
                # draw_histogram() already returns the frame with the RGB
                # histogram stacked beneath it. Stacking `display` on top of
                # that result again duplicated the camera view in the panel.
                hist_panel = draw_histogram(display)
            else:
                hist_panel = display.copy()
                cv2.putText(hist_panel, "HISTOGRAM OFF", (display.shape[1]//2 - 80, display.shape[0]//2), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (100, 100, 100), 2)
            panels['histogram'] = hist_panel
            labels['histogram'] = "HISTOGRAM"

            # Render
            if fullscreen_mode and fullscreen_panel in panels:
                # Show fullscreen panel
                fullscreen_img = cv2.resize(panels[fullscreen_panel], (screen_w, screen_h))
                cv2.putText(fullscreen_img, f"{labels[fullscreen_panel]} - CLICK TO EXIT", 
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                cv2.imshow("Module 1 - Single Screen", fullscreen_img)
            else:
                # Show grid layout
                screen = create_single_screen(panels, labels, screen_w, screen_h)
                cv2.imshow("Module 1 - Single Screen", screen)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == 27:  # ESC
                fullscreen_mode = False
                fullscreen_panel = None
                mouse_state['toggle'] = False
            elif key == ord('+') or key == ord('='):
                exposure = min(exposure + 0.5, 0)
                cap.set(cv2.CAP_PROP_EXPOSURE, exposure)
            elif key == ord('-'):
                exposure = max(exposure - 0.5, -13)
                cap.set(cv2.CAP_PROP_EXPOSURE, exposure)

    except RuntimeError as e:
        print(f"Error: {e}")
    finally:
        if 'cap' in locals():
            cap.release()
        cv2.destroyAllWindows()
        print("\nModule 1 complete.")


if __name__ == "__main__":
    main()
