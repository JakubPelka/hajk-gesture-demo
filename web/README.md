# Web demo

Browser-side demo for the Hajk Gesture Control proof of concept.

This folder contains the OpenLayers test page and the browser bridge that receives gesture commands from the Python app.

The purpose of this folder is to test the full gesture-control chain before connecting anything to Hajk.

## Files

```text
web/
  demo-openlayers.html
  gesture-bridge.js
  README.md
```

## What this demo does

The browser demo:

* displays a simple OpenLayers map,
* connects to the Python WebSocket server,
* receives gesture commands as JSON,
* pans and zooms the map,
* shows a laser pointer,
* shows a click ripple for air tap,
* embeds the Python camera preview as an MJPEG stream,
* lets the camera panel be shown or hidden.

## Required Python services

The Python app starts two local services:

```text
WebSocket command server:
ws://127.0.0.1:8765
```

```text
Camera preview stream:
http://127.0.0.1:8766/video
```

## How to use

From the repository root, start the Python app:

```bat
start.bat
```

Expected console output:

```text
WebSocket server started: ws://127.0.0.1:8765
Video stream started: http://127.0.0.1:8766/video
```

Then open locally:

```text
web/demo-openlayers.html
```

Do not open the GitHub-rendered file in the browser for testing. The demo expects the Python services to be running on the same local computer.

## Expected browser result

The page should show:

* OpenLayers map,
* WebSocket connection status,
* active/inactive status,
* detected and stable gesture names,
* FPS value from Python,
* video client count,
* optional camera preview panel,
* laser pointer when `Pointing_Up` is active.

## Current gesture mapping

```text
Thumb_Up       → activate gesture control
Thumb_Down     → deactivate gesture control
Open_Palm      → pan map
Pinch close    → zoom in
Pinch spread   → zoom out
Pointing_Up    → laser pointer
Air tap        → click ripple
ILoveYou       → reset map
Closed_Fist    → pause / hide pointer
```

Browser keyboard shortcuts such as `A`, `R`, `Q`, and `ESC` are intentionally not used as global shortcuts, so text input inside the map UI remains safe.

## Browser buttons

The demo includes buttons for:

```text
Show / hide camera panel
Toggle active
Reset map
Quit Python
```

The buttons are mainly for testing and fallback control. Normal demo control should be gesture-based.

## Camera panel

The camera panel is mainly for checking where the hand is in the camera field of view.

The debug text drawn into the camera frame is not intended to be read comfortably inside the small browser preview.

Use the browser debug panel for readable status values.

## JSON command examples

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
  "source": "pinch_close"
}
```

```json
{
  "type": "zoom",
  "delta": -1,
  "source": "pinch_spread"
}
```

### Pointer

```json
{
  "type": "pointer",
  "visible": true,
  "x": 0.42,
  "y": 0.31,
  "source": "pointing_up"
}
```

### Click

```json
{
  "type": "click",
  "x": 0.42,
  "y": 0.31,
  "source": "index_air_tap"
}
```

### Reset

```json
{
  "type": "reset",
  "source": "iloveyou"
}
```

## Map tuning

Important tuning values are in `gesture-bridge.js`:

```text
PAN_SENSITIVITY
ZOOM_STEP
ZOOM_ANIMATION_MS
PAN_ANIMATION_MS
POINTER_HIDE_TIMEOUT_MS
```

Useful changes:

```text
Increase PAN_SENSITIVITY for faster panning.
Decrease ZOOM_STEP for smaller zoom steps.
Increase ZOOM_ANIMATION_MS for softer zoom animation.
```

## Troubleshooting

### Camera preview does not show

Open this directly in the browser:

```text
http://127.0.0.1:8766/video
```

If it works directly but not in `demo-openlayers.html`, refresh the demo page with cache bypass:

```text
Ctrl + F5
```

### WebSocket does not connect

Check that Python printed:

```text
WebSocket server started: ws://127.0.0.1:8765
```

Then reload the browser demo.

### Map does not react

Check:

1. WebSocket status is connected.
2. Active mode is true.
3. Browser debug panel shows gesture status.
4. Last command changes when gestures are performed.
5. The map page is opened locally, not through GitHub.

## Notes for future Hajk integration

This web demo creates its own OpenLayers map.

The future Hajk bridge should reuse the same command logic, but instead of creating a map, it should use the OpenLayers map instance already available inside Hajk.

The current demo is therefore a safe test environment before real Hajk integration.
