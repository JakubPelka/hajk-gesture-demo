(function () {
  "use strict";

  const WS_URL = "ws://127.0.0.1:8765";
  const RECONNECT_DELAY_MS = 1500;
  const PAN_SENSITIVITY = 1.0;
  const ZOOM_STEP = 1;
  const ZOOM_ANIMATION_MS = 120;
  const PAN_ANIMATION_MS = 40;

  let socket = null;
  let reconnectTimer = null;
  let lastMessageTime = null;

  const elements = {
    wsStatus: document.getElementById("gesture-ws-status"),
    wsUrl: document.getElementById("gesture-ws-url"),
    lastCommand: document.getElementById("gesture-last-command"),
    active: document.getElementById("gesture-active"),
    detected: document.getElementById("gesture-detected"),
    stable: document.getElementById("gesture-stable"),
    fps: document.getElementById("gesture-fps")
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
      setText(elements.detected, command.detected_gesture || "None");
      setText(elements.stable, command.stable_gesture || "None");
      setText(elements.fps, command.fps ?? "-");
    }

    if (command.type === "active") {
      setText(elements.active, command.value);
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

  function formatCommand(command) {
    if (!command || !command.type) {
      return "None";
    }

    if (command.type === "status") {
      return "status";
    }

    if (command.type === "active") {
      return "active=" + command.value;
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

    return JSON.stringify(command);
  }

  function setupKeyboardShortcuts() {
    window.addEventListener("keydown", function (event) {
      if (event.key === "r" || event.key === "R") {
        resetView();
      }
    });
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
    }, 1000);
  }

  setupKeyboardShortcuts();
  setupConnectionHealthCheck();
  connect();
})();