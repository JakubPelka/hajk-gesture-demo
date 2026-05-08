(function () {
  "use strict";

  const WS_URL = "ws://127.0.0.1:8765";
  const RECONNECT_DELAY_MS = 1500;
  const PAN_SENSITIVITY = 2.5;
  const ZOOM_STEP = 1;
  const ZOOM_ANIMATION_MS = 800;
  const PAN_ANIMATION_MS = 20;
  const POINTER_HIDE_TIMEOUT_MS = 350;

  let socket = null;
  let reconnectTimer = null;
  let lastMessageTime = null;
  let lastPointerTime = null;

  const elements = {
    wsStatus: document.getElementById("gesture-ws-status"),
    wsUrl: document.getElementById("gesture-ws-url"),
    lastCommand: document.getElementById("gesture-last-command"),
    active: document.getElementById("gesture-active"),
    cameraIndex: document.getElementById("gesture-camera-index"),
    detected: document.getElementById("gesture-detected"),
    stable: document.getElementById("gesture-stable"),
    fps: document.getElementById("gesture-fps"),
    videoClients: document.getElementById("gesture-video-clients"),
    pointer: document.getElementById("gesture-pointer"),
    laserPointer: document.getElementById("laser-pointer"),
    cameraPanel: document.getElementById("camera-panel"),
    helpModal: document.getElementById("help-modal"),
    btnToggleCameraPanel: document.getElementById("btn-toggle-camera-panel"),
    btnToggleActive: document.getElementById("btn-toggle-active"),
    btnSwitchCamera: document.getElementById("btn-switch-camera"),
    btnHelp: document.getElementById("btn-help"),
    btnCloseHelp: document.getElementById("btn-close-help"),
    btnResetMap: document.getElementById("btn-reset-map"),
    btnQuit: document.getElementById("btn-quit")
  };

  function getDemoState() {
    return window.hajkGestureDemo || {};
  }

  function getMap() {
    return getDemoState().map || window.map || null;
  }

  function setText(element, value) {
    if (element) {
      element.textContent = String(value);
    }
  }

  function setStatus(text, className) {
    if (!elements.wsStatus) {
      return;
    }

    elements.wsStatus.textContent = text;
    elements.wsStatus.className = "debug-value " + className;
  }

  function connect() {
    clearReconnectTimer();

    setText(elements.wsUrl, WS_URL);
    setStatus("connecting...", "status-warn");

    try {
      socket = new WebSocket(WS_URL);
    } catch (error) {
      setStatus("connection failed", "status-error");
      scheduleReconnect();
      return;
    }

    socket.addEventListener("open", function () {
      setStatus("connected", "status-ok");
    });

    socket.addEventListener("message", function (event) {
      handleMessage(event.data);
    });

    socket.addEventListener("close", function () {
      setStatus("disconnected", "status-error");
      hidePointer();
      scheduleReconnect();
    });

    socket.addEventListener("error", function () {
      setStatus("error", "status-error");
    });
  }

  function scheduleReconnect() {
    clearReconnectTimer();

    reconnectTimer = window.setTimeout(function () {
      connect();
    }, RECONNECT_DELAY_MS);
  }

  function clearReconnectTimer() {
    if (reconnectTimer !== null) {
      window.clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }
  }

  function handleMessage(rawMessage) {
    let command;

    try {
      command = JSON.parse(rawMessage);
    } catch (error) {
      setText(elements.lastCommand, "Invalid JSON");
      return;
    }

    lastMessageTime = Date.now();

    updateDebugPanel(command);
    applyCommand(command);
  }

  function updateDebugPanel(command) {
    setText(elements.lastCommand, formatCommand(command));

    if (command.type === "status") {
      setText(elements.active, command.active);
      setText(elements.cameraIndex, command.camera_index ?? "-");
      setText(elements.detected, command.detected_gesture || "None");
      setText(elements.stable, command.stable_gesture || "None");
      setText(elements.fps, command.fps ?? "-");
      setText(elements.videoClients, command.video_clients ?? "-");

      if (command.pointer_visible) {
        setText(
          elements.pointer,
          "x=" + formatNumber(command.pointer_x) + " y=" + formatNumber(command.pointer_y)
        );
      } else {
        setText(elements.pointer, "hidden");
      }
    }

    if (command.type === "active") {
      setText(elements.active, command.value);
    }

    if (command.type === "camera") {
      if (command.error) {
        setText(elements.lastCommand, "camera error: " + command.error);
      } else {
        setText(elements.cameraIndex, command.index ?? "-");
      }
    }
  }

  function applyCommand(command) {
    if (!command || !command.type) {
      return;
    }

    if (command.type === "pan") {
      handlePan(command);
      return;
    }

    if (command.type === "zoom") {
      handleZoom(command);
      return;
    }

    if (command.type === "reset") {
      resetView();
      return;
    }

    if (command.type === "help") {
      handleHelp(command);
      return;
    }

    if (command.type === "pointer") {
      handlePointer(command);
      return;
    }

    if (command.type === "click") {
      handleClick(command);
    }
  }

  function handlePan(command) {
    const map = getMap();

    if (!map) {
      return;
    }

    const view = map.getView();
    const resolution = view.getResolution();

    if (!resolution) {
      return;
    }

    const dx = Number(command.dx) || 0;
    const dy = Number(command.dy) || 0;

    const mapDx = -dx * resolution * PAN_SENSITIVITY;
    const mapDy = dy * resolution * PAN_SENSITIVITY;

    if (typeof view.adjustCenter === "function") {
      view.adjustCenter([mapDx, mapDy]);
      return;
    }

    const center = view.getCenter();

    if (!center) {
      return;
    }

    view.animate({
      center: [
        center[0] + mapDx,
        center[1] + mapDy
      ],
      duration: PAN_ANIMATION_MS
    });
  }

  function handleZoom(command) {
    const map = getMap();

    if (!map) {
      return;
    }

    const view = map.getView();
    const currentZoom = view.getZoom();

    if (typeof currentZoom !== "number") {
      return;
    }

    const delta = Number(command.delta) || 0;

    if (delta === 0) {
      return;
    }

    const nextZoom = currentZoom + delta * ZOOM_STEP;

    view.animate({
      zoom: nextZoom,
      duration: ZOOM_ANIMATION_MS
    });
  }

  function handlePointer(command) {
    if (!command.visible) {
      hidePointer();
      return;
    }

    const x = Number(command.x);
    const y = Number(command.y);

    if (!Number.isFinite(x) || !Number.isFinite(y)) {
      hidePointer();
      return;
    }

    showPointer(x, y);
  }

  function handleClick(command) {
    const x = Number(command.x);
    const y = Number(command.y);

    if (!Number.isFinite(x) || !Number.isFinite(y)) {
      return;
    }

    showPointer(x, y);
    showClickRipple(x, y);
  }

  function handleHelp(command) {
    const action = command.action || "toggle";

    if (action === "show") {
      showHelp();
      return;
    }

    if (action === "hide") {
      hideHelp();
      return;
    }

    toggleHelp();
  }

  function showPointer(x, y) {
    const position = normalizedToViewport(x, y);

    if (!elements.laserPointer) {
      return;
    }

    elements.laserPointer.style.left = position.x + "px";
    elements.laserPointer.style.top = position.y + "px";
    elements.laserPointer.classList.add("visible");

    lastPointerTime = Date.now();

    setText(elements.pointer, "x=" + x.toFixed(2) + " y=" + y.toFixed(2));
  }

  function hidePointer() {
    if (elements.laserPointer) {
      elements.laserPointer.classList.remove("visible");
    }

    setText(elements.pointer, "hidden");
  }

  function showClickRipple(x, y) {
    const position = normalizedToViewport(x, y);

    const ripple = document.createElement("div");
    ripple.className = "click-ripple";
    ripple.style.left = position.x + "px";
    ripple.style.top = position.y + "px";

    document.body.appendChild(ripple);

    window.setTimeout(function () {
      ripple.remove();
    }, 650);
  }

  function normalizedToViewport(x, y) {
    return {
      x: x * window.innerWidth,
      y: y * window.innerHeight
    };
  }

  function showHelp() {
    if (elements.helpModal) {
      elements.helpModal.classList.add("visible");
    }
  }

  function hideHelp() {
    if (elements.helpModal) {
      elements.helpModal.classList.remove("visible");
    }
  }

  function toggleHelp() {
    if (elements.helpModal) {
      elements.helpModal.classList.toggle("visible");
    }
  }

  function resetView() {
    const map = getMap();

    if (!map) {
      return;
    }

    const state = getDemoState();
    const view = map.getView();

    view.animate({
      center: state.initialCenter,
      zoom: state.initialZoom,
      rotation: state.initialRotation || 0,
      duration: 250
    });
  }

  function sendControl(action) {
    if (!socket || socket.readyState !== WebSocket.OPEN) {
      setText(elements.lastCommand, "Cannot send control: WebSocket not connected");
      return;
    }

    socket.send(
      JSON.stringify({
        type: "control",
        action: action
      })
    );
  }

  function formatCommand(command) {
    if (!command || !command.type) {
      return "None";
    }

    if (command.type === "status") {
      return "status";
    }

    if (command.type === "active") {
      return "active=" + command.value + " source=" + (command.source || "");
    }

    if (command.type === "pan") {
      return (
        "pan dx=" +
        command.dx +
        " dy=" +
        command.dy +
        " source=" +
        (command.source || "")
      );
    }

    if (command.type === "zoom") {
      return (
        "zoom delta=" +
        command.delta +
        " source=" +
        (command.source || "")
      );
    }

    if (command.type === "pointer") {
      return (
        "pointer visible=" +
        command.visible +
        " x=" +
        formatNumber(command.x) +
        " y=" +
        formatNumber(command.y)
      );
    }

    if (command.type === "click") {
      return (
        "click x=" +
        formatNumber(command.x) +
        " y=" +
        formatNumber(command.y) +
        " source=" +
        (command.source || "")
      );
    }

    if (command.type === "reset") {
      return "reset source=" + (command.source || "");
    }

    if (command.type === "help") {
      return (
        "help action=" +
        (command.action || "toggle") +
        " source=" +
        (command.source || "")
      );
    }

    if (command.type === "camera") {
      if (command.error) {
        return "camera error: " + command.error;
      }

      return "camera index=" + command.index + " source=" + (command.source || "");
    }

    return JSON.stringify(command);
  }

  function formatNumber(value) {
    if (value === null || value === undefined) {
      return "-";
    }

    const numberValue = Number(value);

    if (!Number.isFinite(numberValue)) {
      return "-";
    }

    return numberValue.toFixed(2);
  }

  function toggleCameraPanel() {
    if (!elements.cameraPanel || !elements.btnToggleCameraPanel) {
      return;
    }

    const isHidden = elements.cameraPanel.classList.toggle("hidden");

    elements.btnToggleCameraPanel.textContent = isHidden
      ? "Show camera"
      : "Hide camera";
  }

  function setupButtons() {
    if (elements.btnToggleCameraPanel) {
      elements.btnToggleCameraPanel.addEventListener("click", function () {
        toggleCameraPanel();
      });
    }

    if (elements.btnToggleActive) {
      elements.btnToggleActive.addEventListener("click", function () {
        sendControl("toggle_active");
      });
    }

    if (elements.btnSwitchCamera) {
      elements.btnSwitchCamera.addEventListener("click", function () {
        sendControl("next_camera");
      });
    }

    if (elements.btnHelp) {
      elements.btnHelp.addEventListener("click", function () {
        toggleHelp();
      });
    }

    if (elements.btnCloseHelp) {
      elements.btnCloseHelp.addEventListener("click", function () {
        hideHelp();
      });
    }

    if (elements.btnResetMap) {
      elements.btnResetMap.addEventListener("click", function () {
        resetView();
      });
    }

    if (elements.btnQuit) {
      elements.btnQuit.addEventListener("click", function () {
        sendControl("quit");
      });
    }
  }

  function setupConnectionHealthCheck() {
    window.setInterval(function () {
      if (!lastMessageTime) {
        return;
      }

      const ageMs = Date.now() - lastMessageTime;

      if (ageMs > 3000 && socket && socket.readyState === WebSocket.OPEN) {
        setStatus("connected, no recent data", "status-warn");
      }

      if (lastPointerTime && Date.now() - lastPointerTime > POINTER_HIDE_TIMEOUT_MS) {
        hidePointer();
      }
    }, 100);
  }

  setupButtons();
  setupConnectionHealthCheck();
  connect();
})();