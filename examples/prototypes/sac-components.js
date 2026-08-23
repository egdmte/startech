const inactivityLengthSeconds = 15 * 60;

const partInformation = {
  power: {
    name: "Battery and power",
    path: "sac-power.html",
    storageKey: "startech-sac-power",
    elements: "the 3S motor supply, 2S Raspberry Pi supply, switches and voltage profile",
    assistance: "battery-profile selection, warning thresholds and power-source documentation",
    tests: "measure voltage with the car restrained and verify each physical power switch",
    assembly: "the motor and Raspberry Pi supplies remain isolated and use separate holders"
  },
  compute: {
    name: "Raspberry Pi and compute stack",
    path: "sac-compute.html",
    storageKey: "startech-sac-compute",
    elements: "the Raspberry Pi, YAREN connection and enabled STARTECH software modules",
    assistance: "module availability, process startup, schema selection and request validation",
    tests: "verify boot, heartbeat, temperature and module health without arming the motors",
    assembly: "USB, camera and motor interfaces connect here, but motor output remains gated"
  },
  vision: {
    name: "Camera and recognition",
    path: "sac-camera.html",
    storageKey: "startech-sac-camera",
    elements: "the USB or Raspberry Pi camera, image source and recognition pipeline",
    assistance: "source priority, frame size, orientation, confidence and tracking tolerance",
    tests: "use fixed recorded clips before supervised live-camera testing",
    assembly: "camera mounting angle and cable strain can change the useful field of view"
  },
  drive: {
    name: "Motor driver and steering",
    path: "sac-drive.html",
    storageKey: "startech-sac-drive",
    elements: "the headless motor driver, steering controller and their safe output limits",
    assistance: "direction, minimum PWM, steering centre, travel limits and command validation",
    tests: "disconnect or raise the wheels and begin with the lowest permitted motor power",
    assembly: "no module may bypass the motor-driver safety gate to produce physical output"
  },
  wheel: {
    name: "Wheel and motor balance",
    path: "sac-wheel.html",
    storageKey: "startech-sac-wheel",
    elements: "wheel direction, left/right drive balance and mechanical alignment",
    assistance: "dead-zone, minimum movement power and side-to-side correction",
    tests: "perform a wheels-raised direction test before a restrained low-speed floor test",
    assembly: "wheel fit, motor mounting and friction should be checked before software correction"
  }
};

let selectedPart = null;
const hotspots = [...document.querySelectorAll("[data-part]")];
const details = document.querySelector("#component-details");
const sessionTime = document.querySelector("#session-time");
const componentProgress = document.querySelector("#component-progress");
const componentProgressValue = document.querySelector("#component-progress-value");

let remainingSeconds = inactivityLengthSeconds;
let lastResetAt = 0;

function renderTimer() {
  const minutes = Math.floor(remainingSeconds / 60);
  const seconds = remainingSeconds % 60;
  sessionTime.textContent = `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}

function resetTimer() {
  const now = Date.now();
  if (now - lastResetAt < 1000) return;
  remainingSeconds = inactivityLengthSeconds;
  lastResetAt = now;
  renderTimer();
}

function addDetailItem(list, label, value) {
  const item = document.createElement("li");
  const heading = document.createElement("strong");
  heading.textContent = `${label}: `;
  item.append(heading, value);
  list.append(item);
}

function hasStoredSettings(part) {
  try {
    const value = JSON.parse(sessionStorage.getItem(partInformation[part].storageKey) || "null");
    return Boolean(value && typeof value === "object");
  } catch {
    return false;
  }
}

function configuredParts() {
  return Object.keys(partInformation).filter(hasStoredSettings);
}

function createSummaryButton() {
  const button = document.createElement("button");
  button.className = "cam-action cam-action--primary component-details__continue";
  button.type = "button";
  button.textContent = "Review and create calibration";
  button.addEventListener("click", () => {
    window.startechNavigate("sac-summary.html");
  });
  return button;
}

function updateMapStatus() {
  const completed = configuredParts();
  const completedSet = new Set(completed);
  hotspots.forEach((hotspot) => {
    const configured = completedSet.has(hotspot.dataset.part);
    hotspot.classList.toggle("is-configured", configured);
    hotspot.dataset.status = configured ? "configured" : "not-configured";
  });

  const progress = 26 + completed.length * 12;
  componentProgress.setAttribute("aria-valuenow", String(progress));
  componentProgress.setAttribute(
    "aria-label",
    `Service Assisted Calibration progress, ${completed.length} of 5 component sections configured`
  );
  componentProgressValue.style.setProperty("--cam-progress", `${progress}%`);
}

function renderOverview() {
  const completed = configuredParts();
  const heading = document.createElement("h2");
  const copy = document.createElement("p");
  const list = document.createElement("ul");

  if (completed.length === 0) {
    heading.textContent = "NO PARTS SELECTED";
    copy.textContent = "As you click/touch the blue areas, we will";
    [
      "list which elements your selection corresponds to",
      "what kind of assistance is possible",
      "what kind of real-life tests should be done",
      "more information about the assembly of the relevant section."
    ].forEach((text) => {
      const item = document.createElement("li");
      item.textContent = text;
      list.append(item);
    });
  } else {
    heading.textContent = completed.length === 5
      ? "ALL 5 SECTIONS CONFIGURED"
      : `${completed.length} OF 5 SECTIONS CONFIGURED`;
    copy.textContent = completed.length === 5
      ? "The saved SAC draft is ready for your summary and download screen."
      : "Configured sections stay available for review:";
    completed.forEach((part) => {
      const item = document.createElement("li");
      item.textContent = partInformation[part].name;
      list.append(item);
    });
  }

  details.append(heading, copy, list);

  if (completed.length === 5) {
    details.append(createSummaryButton());
  }
}

function renderDetails() {
  details.replaceChildren();

  if (!selectedPart) {
    renderOverview();
    return;
  }

  const selection = partInformation[selectedPart];
  const configured = hasStoredSettings(selectedPart);
  const heading = document.createElement("h2");
  const selectionNames = document.createElement("p");
  const status = document.createElement("p");
  const list = document.createElement("ul");
  const continueButton = document.createElement("button");

  heading.textContent = "1 PART SELECTED";
  selectionNames.className = "component-details__selection";
  selectionNames.textContent = selection.name;
  status.className = `component-details__status ${configured ? "is-configured" : "is-pending"}`;
  status.textContent = configured ? "CONFIGURED — saved draft available" : "NOT CONFIGURED";

  addDetailItem(list, "Elements", selection.elements);
  addDetailItem(list, "Assistance", selection.assistance);
  addDetailItem(list, "Real-life tests", selection.tests);
  addDetailItem(list, "Assembly", selection.assembly);

  continueButton.className = "cam-action cam-action--primary component-details__continue";
  continueButton.type = "button";
  continueButton.textContent = configured ? "Review configured part" : "Continue with selected part";
  continueButton.addEventListener("click", () => {
    window.startechNavigate(selection.path);
  });

  details.append(heading, selectionNames, status, list, continueButton);
  if (configuredParts().length === 5) {
    details.append(createSummaryButton());
  }
  sessionStorage.setItem("startech-sac-parts", JSON.stringify([selectedPart]));
}

hotspots.forEach((hotspot) => {
  hotspot.addEventListener("click", () => {
    const part = hotspot.dataset.part;
    const isDeselecting = selectedPart === part;
    selectedPart = isDeselecting ? null : part;
    hotspots.forEach((control) => {
      control.setAttribute("aria-pressed", String(!isDeselecting && control === hotspot));
    });
    if (!selectedPart) sessionStorage.removeItem("startech-sac-parts");
    renderDetails();
  });
});

["pointerdown", "keydown"].forEach((eventName) => {
  document.addEventListener(eventName, resetTimer, { passive: true });
});

window.setInterval(() => {
  remainingSeconds = Math.max(0, remainingSeconds - 1);
  renderTimer();
}, 1000);

function restoreSelection() {
  try {
    const saved = JSON.parse(sessionStorage.getItem("startech-sac-parts") || "[]");
    const candidate = Array.isArray(saved) ? saved[0] : null;
    if (!Object.hasOwn(partInformation, candidate)) return;
    selectedPart = candidate;
    const hotspot = hotspots.find((control) => control.dataset.part === selectedPart);
    if (hotspot) hotspot.setAttribute("aria-pressed", "true");
  } catch {
    sessionStorage.removeItem("startech-sac-parts");
  }
}

restoreSelection();
updateMapStatus();
renderDetails();
renderTimer();
