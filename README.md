# hajk-gesture-demo
To navigate Hajk with hand gestures with usage of MediaPipe hand landmarks and openCv.

# Hajk Gesture Control Demo

Proof of concept for controlling a Hajk / OpenLayers map with simple hand gestures detected from a regular webcam.

This is a separate experimental repository. It uses computer vision, but it is not part of ComputerVisionCounter.

The project will be developed step by step. The first goal is a stable MVP, not a production-ready tool.

## Goal

Build a simple demo where a webcam detects hand gestures and sends commands to a map.

First MVP goals:

1. Move / pan the map with an open hand.
2. Zoom in and zoom out with simple gestures.
3. Use an active / inactive mode to avoid accidental actions.
4. Test everything first on a minimal OpenLayers demo.
5. Connect the same logic to Hajk later.

## Current status

Stage 0: camera preview.

The app opens the default webcam, displays a live preview, shows FPS, and exits with `ESC` or `Q`.

No MediaPipe yet.  
No WebSocket yet.  
No OpenLayers / Hajk integration yet.

## Target architecture

```text
webcam
  ↓
OpenCV frame capture
  ↓
MediaPipe hand detection / gesture recognition
  ↓
Python gesture state machine
  ↓
WebSocket JSON command
  ↓
OpenLayers / Hajk gesture bridge
  ↓
map view action
```

## Planned gesture mapping

Initial MVP mapping:

```text
Keyboard A       → toggle active mode
Open palm        → pan map
Closed fist      → pause / stop sending pan commands
Thumb up         → zoom in
Thumb down       → zoom out
ESC              → quit Python app
```

Fallback option if `Thumb down` is unstable:

```text
Thumb up         → zoom in
Victory gesture  → zoom out
```

## JSON command draft

Examples of future WebSocket messages:

```json
{ "type": "active", "value": true }
```

```json
{ "type": "pan", "dx": 12, "dy": -6, "strength": 0.8 }
```

```json
{ "type": "zoom", "delta": 1 }
```

```json
{ "type": "zoom", "delta": -1 }
```

```json
{ "type": "reset" }
```

```json
{
  "type": "status",
  "gesture": "OpenPalm",
  "confidence": 0.82,
  "fps": 27
}
```

## Requirements

- Windows 10 / 11
- Python 3.10+
- Webcam
- Git, optional but recommended

The project is Windows-first at the start.

OpenCV camera capture uses DirectShow on Windows where possible:

```python
cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
```

## Repository structure

```text
hajk-gesture-demo/
  README.md
  requirements.txt
  .gitignore
  start.bat
  python/
    main.py
    camera.py
    config.py
```

## Windows quick start

The easiest way is to run:

```text
start.bat
```

The script will:

1. Create `.venv` if it does not exist.
2. Install / update requirements.
3. Start the camera preview.

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

Expected result:

- webcam preview opens,
- FPS is visible in the top-left corner,
- `ESC` or `Q` closes the app.

## Current files

### `python/main.py`

Application entry point.

Current responsibilities:

- open camera,
- show preview window,
- draw FPS overlay,
- close app with `ESC` or `Q`.

### `python/camera.py`

OpenCV camera wrapper.

Current responsibilities:

- open selected camera,
- read frames,
- optionally mirror preview,
- calculate smoothed FPS,
- release camera safely.

### `python/config.py`

Shared configuration.

Current settings:

- camera index,
- preview resolution,
- requested FPS,
- preview window name,
- mirror preview,
- overlay text settings.

## Development stages

### Stage 0 — Camera preview

Status: current stage.

Goal:

- Open webcam.
- Show preview.
- Show FPS.
- Exit with `ESC` or `Q`.

Success criteria:

```text
python python\main.py
```

opens a camera preview window and closes cleanly.

### Stage 1 — MediaPipe hand landmarks

Goal:

- Add MediaPipe.
- Detect hand landmarks.
- Draw landmarks on camera preview.
- Keep FPS visible.

Planned new file:

```text
python/hand_tracker.py
```

Success criteria:

- hand is detected,
- landmarks are drawn,
- preview remains stable.

### Stage 2 — Gesture debug

Goal:

- Recognize basic gestures.
- Show current gesture on preview.
- Add active / inactive mode.

Planned gestures:

```text
Open_Palm
Closed_Fist
Thumb_Up
Thumb_Down
Victory fallback
```

Planned new file:

```text
python/gesture_state.py
```

Success criteria:

Preview shows:

```text
Mode: ACTIVE / INACTIVE
Gesture: Open_Palm / Closed_Fist / Thumb_Up / Thumb_Down
FPS: current FPS
```

### Stage 3 — WebSocket command server

Goal:

- Add Python WebSocket server.
- Send normalized JSON commands.
- Show number of connected clients in debug overlay.

Planned new file:

```text
python/command_server.py
```

Success criteria:

Python sends messages like:

```json
{ "type": "pan", "dx": 4, "dy": -2 }
```

and:

```json
{ "type": "zoom", "delta": 1 }
```

### Stage 4 — OpenLayers demo

Goal:

- Create a minimal local OpenLayers page.
- Connect to Python WebSocket.
- React to pan / zoom / reset commands.

Planned files:

```text
web/demo-openlayers.html
web/gesture-bridge.js
web/README.md
```

Success criteria:

A simple OpenLayers map reacts to hand gesture commands.

### Stage 5 — Hajk bridge

Goal:

- Reuse the same WebSocket command stream.
- Add a thin bridge to a local Hajk instance.
- Control the OpenLayers map view inside Hajk.

Success criteria:

Hajk reacts to:

```text
Open palm + movement → pan
Thumb up             → zoom in
Thumb down           → zoom out
Closed fist          → pause
Keyboard A           → active / inactive
```

## MVP success criteria

The MVP is successful when:

1. It works on a normal laptop webcam.
2. It does not require training a custom model.
3. OpenLayers or Hajk reacts to at least two gestures.
4. Pan is reasonably smooth.
5. Zoom does not trigger every frame.
6. There is an active / inactive mode.
7. Code is split into small modules.
8. The repository has clear run instructions.

## Coding principles

Use:

- small modules,
- clear names,
- configuration in `config.py`,
- simple terminal + OpenCV preview first,
- WebSocket JSON commands for map control,
- OpenLayers demo before Hajk integration.

Avoid:

- one large `main.py`,
- too many gestures at the start,
- training a custom model for MVP,
- deep Hajk integration before the OpenLayers demo works,
- using `pyautogui` as the main control mechanism.

## First commit suggestion

```bat
git add .
git commit -m "Add stage 0 camera preview"
```

## Next step

After Stage 0 works, add MediaPipe hand landmark detection in:

```text
python/hand_tracker.py
```
