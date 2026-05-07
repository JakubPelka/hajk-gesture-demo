# Hajk Gesture Control Demo

Proof of concept for controlling an OpenLayers / Hajk-style web map with hand gestures detected from a regular webcam.

This is a separate experimental repository. It uses computer vision, but it is not part of ComputerVisionCounter.

The project is currently a working MVP demo. The main purpose is to test the full control chain before attempting any deeper Hajk integration.

## Current status

Current stage: **Stage 4.5 — browser-based demo with embedded camera preview**.

The project currently supports:

* webcam capture through OpenCV,
* hand and gesture detection through MediaPipe Tasks Gesture Recognizer,
* gesture state logic in Python,
* WebSocket JSON commands from Python to the browser,
* OpenLayers map control in the browser,
* MJPEG camera preview embedded in the browser demo,
* active / inactive mode,
* debug overlays in both Python-generated camera preview and browser UI.

The current demo already proves this flow:

```text
webcam
  ↓
OpenCV frame capture
  ↓
MediaPipe Tasks Gesture Recognizer
  ↓
Python GestureEngine
  ↓
WebSocket JSON command server
  ↓
Browser gesture bridge
  ↓
OpenLayers map view control
```

A second parallel flow sends the camera preview to the browser:

```text
OpenCV frame with landmarks and debug overlay
  ↓
MJPEG HTTP video stream
  ↓
browser camera preview panel
```

## What works now

The current demo can:

1. Start the webcam from Python.
2. Detect hand landmarks.
3. Recognize basic MediaPipe gestures.
4. Show the camera preview directly in the browser.
5. Connect browser and Python over WebSocket.
6. Send gesture commands as JSON.
7. Pan the OpenLayers map with an open hand.
8. Zoom the map with gesture commands.
9. Toggle active / inactive mode from the browser.
10. Reset the map from the browser.
11. Quit the Python app from the browser.

## Current gesture mapping

```text
Browser key A / button        → toggle active / inactive mode
Open_Palm + hand movement     → pan map
Closed_Fist                   → pause / stop pan commands
Thumb_Up                      → zoom in fallback
Thumb_Down                    → zoom out fallback
Victory                       → zoom out fallback
Pinch close                   → zoom in experimental
Pinch spread                  → zoom out experimental
Browser key R / button        → reset map view
Browser key Q / ESC / button  → quit Python app
```

## Important notes about gestures

The project uses MediaPipe Tasks Gesture Recognizer.

The built-in gesture classes include:

```text
None
Closed_Fist
Open_Palm
Pointing_Up
Thumb_Down
Thumb_Up
Victory
ILoveYou
```

Pinch is not a built-in MediaPipe gesture in this model. It is calculated manually from hand landmarks by measuring the distance between:

```text
4 = THUMB_TIP
8 = INDEX_FINGER_TIP
```

The pinch value is normalized against palm size, so it should be more stable than a raw pixel distance.

At the current stage, pinch zoom is experimental. It works, but the thresholds may need calibration for different cameras, lighting, hand sizes, and user distance from the camera.

## Repository structure

```text
hajk-gesture-demo/
  README.md
  requirements.txt
  .gitignore
  start.bat
  models/
    gesture_recognizer.task
  python/
    main.py
    camera.py
    command_server.py
    config.py
    gesture_state.py
    hand_tracker.py
    video_stream_server.py
  web/
    demo-openlayers.html
    gesture-bridge.js
    README.md
```

## Main components

### `python/main.py`

Main application entry point.

Current responsibilities:

* start WebSocket command server,
* start MJPEG video stream server,
* start camera capture,
* run MediaPipe hand tracking,
* run gesture state logic,
* send JSON commands to browser clients,
* draw debug overlay on camera frames,
* update browser camera preview,
* handle control messages from the browser.

### `python/camera.py`

OpenCV camera wrapper.

Current responsibilities:

* open selected camera,
* use DirectShow on Windows where possible,
* read frames,
* optionally mirror preview,
* calculate smoothed FPS,
* release camera safely.

### `python/hand_tracker.py`

MediaPipe Tasks Gesture Recognizer wrapper.

Current responsibilities:

* load `models/gesture_recognizer.task`,
* detect hand landmarks,
* return handedness,
* return recognized MediaPipe gesture,
* return gesture confidence,
* calculate palm center,
* draw landmarks and labels on the camera frame.

### `python/gesture_state.py`

Gesture logic and command generator.

Current responsibilities:

* active / inactive mode,
* gesture stabilization,
* pan smoothing,
* pan deadzone,
* zoom cooldown,
* pinch distance calculation,
* conversion from gestures to normalized JSON commands.

### `python/command_server.py`

WebSocket server.

Current responsibilities:

* expose local WebSocket server at `ws://127.0.0.1:8765`,
* send JSON commands from Python to the browser,
* receive browser control messages,
* track connected browser clients.

### `python/video_stream_server.py`

MJPEG camera preview server.

Current responsibilities:

* expose local video stream at `http://127.0.0.1:8766/video`,
* expose snapshot endpoint at `http://127.0.0.1:8766/snapshot.jpg`,
* send OpenCV frames to the browser as MJPEG,
* track connected video clients.

### `web/demo-openlayers.html`

Browser demo page.

Current responsibilities:

* create a simple OpenLayers map,
* display WebSocket status,
* display gesture status,
* display embedded camera preview,
* expose buttons for active toggle, reset, and quit.

### `web/gesture-bridge.js`

Browser-side bridge between WebSocket commands and OpenLayers.

Current responsibilities:

* connect to Python WebSocket server,
* receive JSON commands,
* pan the OpenLayers view,
* zoom the OpenLayers view,
* reset the map,
* send browser control messages back to Python.

## Requirements

Recommended environment:

* Windows 10 / 11,
* Python 3.10+,
* webcam,
* modern browser,
* internet access for the browser OpenLayers and OSM tile demo,
* Git, optional but recommended.

The project is currently Windows-first.

## Python dependencies

Current `requirements.txt`:

```text
opencv-python>=4.9.0,<5.0.0
mediapipe>=0.10.31
numpy>=1.26.0
websockets>=12.0,<16.0
```

## Required model file

The project expects this file:

```text
models/gesture_recognizer.task
```

If the model file is missing, the app will not start.

The file is used by MediaPipe Tasks Gesture Recognizer.

## Windows quick start

From the repository root, run:

```bat
start.bat
```

The script should:

1. Create `.venv` if it does not exist.
2. Install / update requirements.
3. Start the Python app.
4. Start the WebSocket server.
5. Start the video stream server.

Expected console output includes:

```text
WebSocket server started: ws://127.0.0.1:8765
Video stream started: http://127.0.0.1:8766/video
```

Then open:

```text
web/demo-openlayers.html
```

Expected browser result:

* OpenLayers map is visible,
* camera preview is visible in the right panel,
* WebSocket status becomes connected,
* gesture status updates in the left panel,
* browser controls work.

## Manual setup on Windows

Create virtual environment:

```bat
python -m venv .venv
```

Activate environment in CMD:

```bat
.venv\Scripts\activate.bat
```

Or in PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Install dependencies:

```bat
pip install -r requirements.txt
```

Run the app:

```bat
python python\main.py
```

Then open:

```text
web/demo-openlayers.html
```

## Browser controls

The browser tab should be focused for keyboard shortcuts to work.

```text
A      toggle active / inactive mode
R      reset map view
Q      quit Python app
ESC    quit Python app
```

The browser UI also includes buttons for:

```text
Toggle active
Reset map
Quit Python
```

## JSON command examples

### Active state

```json
{
  "type": "active",
  "value": true,
  "source": "keyboard"
}
```

### Pan

```json
{
  "type": "pan",
  "dx": 12,
  "dy": -6,
  "strength": 0.8,
  "source": "open_palm"
}
```

### Zoom

```json
{
  "type": "zoom",
  "delta": 1,
  "source": "thumb_up"
}
```

```json
{
  "type": "zoom",
  "delta": -1,
  "source": "victory_fallback"
}
```

```json
{
  "type": "zoom",
  "delta": 1,
  "source": "pinch_close"
}
```

### Status

```json
{
  "type": "status",
  "active": true,
  "detected_gesture": "Open_Palm",
  "stable_gesture": "Open_Palm",
  "confidence": 0.82,
  "pinch_ratio": 0.45,
  "hands": 1,
  "fps": 27.4,
  "clients": 1,
  "video_clients": 1
}
```

### Browser-to-Python control message

```json
{
  "type": "control",
  "action": "toggle_active"
}
```

```json
{
  "type": "control",
  "action": "quit"
}
```

## Current tuning parameters

Important tuning values are currently split between Python and JavaScript.

### Python gesture tuning

In `python/gesture_state.py`:

```text
stable_frames
min_gesture_confidence
pan_smoothing
pan_deadzone_px
pan_max_step_px
zoom_cooldown_sec
pinch_zoom_in_threshold
pinch_zoom_out_threshold
pinch_min_hand_scale
```

### Browser map tuning

In `web/gesture-bridge.js`:

```text
PAN_SENSITIVITY
ZOOM_STEP
ZOOM_ANIMATION_MS
PAN_ANIMATION_MS
```

Useful tuning examples:

```text
Increase PAN_SENSITIVITY for faster map panning.
Decrease ZOOM_STEP for less jumpy zoom.
Increase ZOOM_ANIMATION_MS for smoother zoom animation.
```

## Current known limitations

This is still an MVP demo.

Known limitations:

* zoom is still more step-based than fully smooth,
* pinch zoom needs calibration,
* the current MVP is optimized for one hand,
* lighting and background strongly affect gesture stability,
* OpenCV / MediaPipe logs may appear in the console,
* browser demo uses CDN OpenLayers and OSM tiles,
* Hajk integration has not been implemented yet,
* no production UI or settings panel exists yet,
* no installer or packaged release exists yet.

## Troubleshooting

### Camera does not open

Check camera index in `python/config.py`:

```python
camera_index: int = 0
```

Try:

```python
camera_index: int = 1
```

or:

```python
camera_index: int = 2
```

### Browser does not connect to WebSocket

Check that Python console shows:

```text
WebSocket server started: ws://127.0.0.1:8765
```

Then refresh:

```text
web/demo-openlayers.html
```

### Camera preview does not show in browser

Check directly in browser:

```text
http://127.0.0.1:8766/video
```

If that works, the video stream server is running and the issue is likely in the HTML page or browser cache.

### Gestures are detected but map does not move

Check:

1. WebSocket status is connected.
2. Browser shows active mode as `true`.
3. Python/browser debug panel shows `Command: pan ...`.
4. Open_Palm is stable enough.
5. Browser tab is not frozen or disconnected.

### Panning is too slow

Increase in `web/gesture-bridge.js`:

```javascript
const PAN_SENSITIVITY = 2.0;
```

Try higher values if needed:

```javascript
const PAN_SENSITIVITY = 3.0;
```

### Zoom is too jumpy

Decrease in `web/gesture-bridge.js`:

```javascript
const ZOOM_STEP = 0.25;
```

Also consider increasing:

```javascript
const ZOOM_ANIMATION_MS = 180;
```

### Pinch zoom triggers too often

Adjust thresholds in `python/gesture_state.py`:

```python
pinch_zoom_in_threshold: float = 0.35
pinch_zoom_out_threshold: float = 1.30
```

If zoom in triggers too often, lower `pinch_zoom_in_threshold`.

If zoom out almost never triggers, lower `pinch_zoom_out_threshold`.

## Development stages

### Stage 0 — Camera preview

Status: done.

Goal:

* open webcam,
* show preview,
* show FPS,
* exit with keyboard.

### Stage 1 — MediaPipe hand landmarks

Status: done.

Goal:

* detect hand landmarks,
* draw landmarks,
* show hand metadata.

### Stage 2 — Gesture debug

Status: done.

Goal:

* recognize gestures,
* show detected and stable gestures,
* add active / inactive mode,
* generate internal commands.

### Stage 3 — WebSocket command server

Status: done.

Goal:

* send JSON commands from Python to browser,
* show connected clients,
* receive browser control messages.

### Stage 4 — OpenLayers demo

Status: done.

Goal:

* connect browser to Python WebSocket,
* control a clean OpenLayers map,
* test pan / zoom / reset outside Hajk.

### Stage 4.5 — Browser camera preview

Status: done.

Goal:

* stream camera preview to the browser,
* avoid switching between OpenCV window and browser,
* control the demo mostly from one browser window.

### Stage 5 — Hajk bridge

Status: not started.

Goal:

* reuse the same WebSocket command stream,
* connect the gesture bridge to a local Hajk instance,
* control the OpenLayers map view inside Hajk.

## Next planned improvements

Recommended next steps:

1. Smooth zoom improvement.
2. Better pinch calibration.
3. Optional config values for pan/zoom sensitivity.
4. Cleaner browser UI for demo presentation.
5. Add browser-side indicator for command frequency.
6. Add optional two-hand mode later.
7. Create a first Hajk bridge experiment.

## Hajk integration plan

The current OpenLayers demo is intentionally independent from Hajk.

The next integration should be thin:

```text
Python gesture engine
  ↓
WebSocket JSON command stream
  ↓
Hajk gesture bridge
  ↓
existing OpenLayers map view inside Hajk
```

The first Hajk bridge should not modify deep Hajk logic. It should only:

* connect to the existing Python WebSocket server,
* find or receive access to the OpenLayers map instance,
* map existing JSON commands to OpenLayers view operations,
* expose simple connection and active status in the UI if needed.

## Project goal reminder

This repository is a proof of concept.

The goal is not to replace normal mouse and keyboard map navigation. The goal is to test whether webcam-based gesture control can become a useful presentation, accessibility, or experimental interaction layer for Hajk / OpenLayers maps.
