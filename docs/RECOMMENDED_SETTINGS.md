# Recommended Slider Settings for Each Module

This guide provides optimal slider ranges and recommended settings for your Arducam IMX298 (B0290) camera with red LED detection.

---

## Module 1: Hardware Setup & The Physics of Vision

### Slider Ranges
| Slider | Range | Recommended Start Value | Description |
|--------|-------|------------------------|-------------|
| **Brightness** | 0-100 (±50) | 50 (center) | 0=Dark, 50=Normal, 100=Bright |
| **Contrast** | 0-100 (±50) | 50 (center) | 0=Low, 50=Normal, 100=High |
| **Saturation** | 0-100 (0x-2x) | 50 (1x) | 0=B&W, 50=Normal, 100=2x |
| **Show Grid** | 0-1 | 1 | Toggle alignment grid |
| **Show Histogram** | 0-1 | 1 | Toggle RGB histogram |
| **Zoom** | 10-20 (1x-2x) | 10 (1x) | 10=1x, 20=2x |

### Recommended Settings by Scenario
| Scenario | Brightness | Contrast | Saturation | Zoom |
|----------|-----------|----------|------------|------|
| **Bright Room** | 45-50 | 55-60 | 50-60 | 10 |
| **Dim Room** | 50-55 | 50-55 | 55-65 | 10 |
| **Direct LED (blooming)** | 40-45 | 60-70 | 50 | 10-12 |
| **Far LED (small)** | 50 | 55 | 60 | 14-16 |
| **Close LED (large)** | 50 | 50 | 50 | 10 |

### Tips
- **Tilt camera 15-30°** before adjusting sliders
- If LED appears white (overexposed), lower Brightness first
- Use Histogram to check if colors are clipping (bars touching edges)

---

## Module 2: Digital Color Mastery (HSV)

### Slider Ranges
| Slider | Range | Recommended Start Value | Description |
|--------|-------|------------------------|-------------|
| **H Lower** | 0-179 | 0 | Lower hue bound |
| **S Lower** | 0-255 | 100 | Lower saturation bound |
| **V Lower** | 0-255 | 100 | Lower value bound |
| **H Upper** | 0-179 | 10 | Upper hue bound |
| **S Upper** | 0-255 | 255 | Upper saturation bound |
| **V Upper** | 0-255 | 255 | Upper value bound |
| **Red Mode** | 0-1 | 1 | Dual-range for red LEDs |

### Recommended Settings by LED Color

#### 🔴 RED LED (Most Common)
```
Red Mode: ON (1)
H Lower: 0      H Upper: 10
S Lower: 120    S Upper: 255
V Lower: 80     V Upper: 255
```
**Why**: Red wraps at hue 0, so we combine ranges 0-10 and 170-179

#### 🟢 GREEN LED
```
Red Mode: OFF (0)
H Lower: 35     H Upper: 85
S Lower: 100    S Upper: 255
V Lower: 80     V Upper: 255
```

#### 🔵 BLUE LED
```
Red Mode: OFF (0)
H Lower: 90     H Upper: 130
S Lower: 100    S Upper: 255
V Lower: 80     V Upper: 255
```

#### 🟡 YELLOW LED
```
Red Mode: OFF (0)
H Lower: 20     H Upper: 40
S Lower: 100    S Upper: 255
V Lower: 80     V Upper: 255
```

### Fine-Tuning Guide
| Problem | Solution |
|---------|----------|
| Background noise in mask | Increase S Lower (try 150-200) |
| LED not fully white in mask | Increase H Upper / Decrease H Lower |
| LED too dim to detect | Decrease V Lower (try 50-80) |
| White objects also detected | Increase S Lower (needs color, not white) |
| LED appears white in camera | Decrease V Upper (reduce overexposure) |

### Visualization Toggles
| Toggle | Recommended | Purpose |
|--------|-------------|---------|
| Show HSV | ON | Verify color conversion |
| Show Mask | ON | Main tuning reference |
| Show Result | ON | Verify isolated LED |
| Show Channels | OFF (toggle as needed) | Debug individual H/S/V |
| Show Color Wheel | OFF (toggle as needed) | Understand hue selection |

---

## Module 3: Pre-Processing & Cleaning

### Slider Ranges
| Slider | Range | Recommended Start Value | Description |
|--------|-------|------------------------|-------------|
| **Blur Kernel** | 1-5 (3x3 to 11x11) | 1-2 (3x3 to 5x5) | Gaussian blur size |
| **Erode Iter** | 0-5 | 1-2 | Noise removal strength |
| **Dilate Iter** | 0-5 | 1-2 | Hole filling strength |
| **Morph Kernel** | 1-5 (3x3 to 11x11) | 1 (3x3) | Morphological operator size |

### Recommended Settings by Noise Level

| Scenario | Blur | Erode | Dilate | Morph | Result |
|----------|------|-------|--------|-------|--------|
| **Clean image, little noise** | 1 (3x3) | 1 | 1 | 1 (3x3) | Minimal processing |
| **Moderate sensor noise** | 2 (5x5) | 1-2 | 1-2 | 1 (3x3) | Balanced |
| **Heavy noise / stray light** | 2-3 (5x5 to 7x7) | 2-3 | 2-3 | 2 (5x5) | Aggressive |
| **LED has white core (holes)** | 1-2 (3x3 to 5x5) | 1 | 2-3 | 1 (3x3) | More dilation |
| **Small distant LED** | 1 (3x3) | 0-1 | 1 | 1 (3x3) | Minimal (preserve size) |
| **Large close LED** | 2 (5x5) | 1-2 | 1-2 | 1-2 (3x3 to 5x5) | Standard |

### Step-by-Step Tuning Process
1. **Start with**: Blur=1, Erode=1, Dilate=1, Morph=1
2. **Check Raw Mask**: If noise pixels visible → increase Blur or Erode
3. **Check Eroded**: If LED breaks apart → decrease Erode or Blur
4. **Check Cleaned**: If holes in LED → increase Dilate
5. **If LED disappears** → decrease all values

### Visualization Toggles
| Toggle | Recommended | Purpose |
|--------|-------------|---------|
| Show Blur | OFF | Debug only |
| Show Erode | OFF | Debug only |
| Show Dilate | OFF | Debug only |
| **Show Compare** | **ON** | **Main 2x2 comparison view** |
| Show Diff | OFF (toggle as needed) | See what each step removes/adds |

---

## Module 4: Pattern Detection & Shape Analysis

### Slider Ranges
| Slider | Range | Recommended Start Value | Description |
|--------|-------|------------------------|-------------|
| **Min Area** | 0-2000 | 100-300 | Minimum contour area (pixels²) |
| **Circularity** | 0-100 (0.00-1.00) | 60-75 (0.60-0.75) | Shape roundness threshold |
| **Hough DP** | 1-30 (0.1-3.0) | 12 (1.2) | Accumulator resolution inverse |
| **Hough Param1** | 0-300 | 100 | Canny edge threshold |
| **Hough Param2** | 0-100 | 20-30 | Circle center accumulator threshold |
| **Min Radius** | 0-100 | 5-10 | Minimum circle radius |
| **Max Radius** | 0-200 | 50-100 | Maximum circle radius |

### Recommended Settings by LED Distance

| Scenario | Min Area | Circularity | Hough DP | Param2 | Min R | Max R |
|----------|----------|-------------|----------|--------|-------|-------|
| **Very close LED (<20cm)** | 1000-2000 | 70-85 | 12 | 30-40 | 30 | 100 |
| **Close LED (20-50cm)** | 300-800 | 65-80 | 12 | 25-35 | 15 | 60 |
| **Medium LED (50-100cm)** | 100-300 | 60-75 | 12 | 20-30 | 8 | 40 |
| **Far LED (100-200cm)** | 50-150 | 55-70 | 12 | 15-25 | 5 | 25 |
| **Very far LED (>200cm)** | 20-80 | 50-65 | 10 | 10-20 | 3 | 15 |

### Circularity Guidelines
| Circularity | Shape Description | Use Case |
|-------------|-------------------|----------|
| 0.90-1.00 | Perfect circle | Ideal LED, clean image |
| 0.75-0.90 | Round-ish | Good LED detection |
| 0.60-0.75 | Somewhat round | Tolerant, slight blur |
| 0.40-0.60 | Oval/irregular | May include non-LEDs |
| <0.40 | Rectangle/blob | Not recommended for LEDs |

### Hough Circle Parameter Guide
| Problem | Solution |
|---------|----------|
| No circles detected | Lower Param2 (try 10-20) |
| Too many false circles | Raise Param2 (try 40-60) |
| Circles too large/small | Adjust Min/Max Radius |
| Circles offset from actual | Lower DP (try 1.0) |
| Performance slow | Raise DP (try 2.0) |

### Visualization Toggles
| Toggle | Recommended | Purpose |
|--------|-------------|---------|
| **Show Contours** | **ON** | **Main contour detection** |
| **Show Hough** | **ON** | **Circle-specific detection** |
| Show Shape Info | ON | Detailed metrics per contour |
| **Show Compare** | **ON** | **4-panel comparison view** |
| Show Only Valid | OFF | Toggle to see rejected contours |

---

## Module 5: Robotics Implementation & Logic

### Slider Ranges
| Slider | Range | Recommended Start Value | Description |
|--------|-------|------------------------|-------------|
| **Min Area** | 0-2000 | 200-300 | Reject small noise |
| **Max Area** | 0-1000 (×100) | 500 (50,000) | Reject huge objects |
| **Circularity** | 0-100 (0.00-1.00) | 60 (0.60) | Shape quality gate |
| **Stability Frames** | 0-10 | 3-5 | Consecutive detections required |

### Recommended Settings by Application

| Application | Min Area | Max Area | Circularity | Stability | Purpose |
|-------------|----------|----------|-------------|-----------|---------|
| **Precision tracking** | 200-500 | 50,000 | 70-80 | 5-7 | Accurate, no false positives |
| **Fast response** | 100-200 | 50,000 | 55-65 | 2-3 | Quick, slightly more noise OK |
| **Long distance** | 50-150 | 30,000 | 50-60 | 3-5 | Small targets, tolerant |
| **Close range robot** | 500-1000 | 50,000 | 65-75 | 3-5 | Large targets, reliable |
| **Autonomous navigation** | 200-400 | 50,000 | 60-70 | 4-6 | Balanced performance |

### Stability Frames Guide
| Frames | Behavior | Use Case |
|--------|----------|----------|
| 1-2 | Very responsive, may flicker | Fast robots, low latency |
| 3-5 | Balanced, recommended | Most applications |
| 6-8 | Very stable, slower response | Precision tasks |
| 9-10 | Maximum stability | Stationary alignment |

### Threshold Tuning by Problem
| Problem | Adjust |
|---------|--------|
| Robot reacts to flickers | Increase Stability Frames |
| Robot ignores real LED | Decrease Min Area or Stability |
| Robot tracks background light | Increase Min Area, increase Circularity |
| Robot loses LED when moving | Decrease Stability Frames |
| False positives from reflections | Increase Circularity to 70+ |

### Visualization Toggles
| Toggle | Recommended | Purpose |
|--------|-------------|---------|
| **Show Overlay** | **ON** | **Main tracking display** |
| **Show Graph** | **ON** | **Distance indicator** |
| **Show History** | **ON** | **Position tracking** |
| **Show Dashboard** | **ON** | **Complete metrics** |

---

## Quick Start Cheat Sheet

### For First-Time Setup (Red LED, ~50cm distance)
```
Module 1: Brightness=50, Contrast=50, Saturation=50
Module 2: Red Mode=ON, H=(0,10), S=(120,255), V=(80,255)
Module 3: Blur=1, Erode=1, Dilate=1, Morph=1
Module 4: Min Area=200, Circularity=0.65, Hough DP=1.2, Param2=25
Module 5: Min Area=200, Max Area=50000, Circularity=0.60, Stability=3
```

### For Noisy Environment
```
Module 1: Brightness=45, Contrast=60, Saturation=55
Module 2: Red Mode=ON, H=(0,10), S=(150,255), V=(100,255)
Module 3: Blur=2, Erode=2, Dilate=2, Morph=2
Module 4: Min Area=300, Circularity=0.70, Hough DP=1.2, Param2=30
Module 5: Min Area=300, Max Area=50000, Circularity=0.65, Stability=4
```

### For Fast-Moving Robot
```
Module 1: Brightness=50, Contrast=55, Saturation=60
Module 2: Red Mode=ON, H=(0,15), S=(100,255), V=(60,255)
Module 3: Blur=1, Erode=1, Dilate=1, Morph=1
Module 4: Min Area=100, Circularity=0.55, Hough DP=1.2, Param2=20
Module 5: Min Area=100, Max Area=50000, Circularity=0.55, Stability=2
```

---

## Calibration Procedure

1. **Position LED at target distance** (e.g., 50cm)
2. **Run Module 1**: Adjust exposure until LED is bright but not blooming
3. **Run Module 2**: Tune HSV until mask shows LED as solid white
4. **Run Module 3**: Adjust morphological ops until mask is clean
5. **Run Module 4**: Verify contours and Hough circles detect the LED
6. **Run Module 5**: Set thresholds to reject false positives
7. **Test at multiple distances** and refine settings

---

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| LED not detected | HSV bounds too tight | Widen H/S/V ranges |
| Everything detected | HSV bounds too loose | Tighten S/V lower bounds |
| Mask has holes | Not enough dilation | Increase Dilate Iter |
| Mask has noise | Not enough erosion | Increase Erode Iter |
| Contours jittery | Stability too low | Increase Stability Frames |
| Detection laggy | Stability too high | Decrease Stability Frames |
| Circles not found | Hough Param2 too high | Lower Param2 |
| Too many circles | Hough Param2 too low | Raise Param2 |
