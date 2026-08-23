const componentStorageKeys = {
  power: "startech-sac-power",
  compute: "startech-sac-compute",
  camera: "startech-sac-camera",
  drive: "startech-sac-drive",
  wheel: "startech-sac-wheel"
};

const createCalibrationButton = document.querySelector("#create-calibration");
const goBackButton = document.querySelector("#go-back");
const summaryCopy = document.querySelector("#summary-copy");
const summaryMessage = document.querySelector("#summary-message");

function readJson(key) {
  try {
    return JSON.parse(sessionStorage.getItem(key) || "null");
  } catch {
    return null;
  }
}

function readSections() {
  return Object.fromEntries(
    Object.entries(componentStorageKeys).map(([section, key]) => [section, readJson(key)])
  );
}

function missingSections(sections) {
  return Object.entries(sections)
    .filter(([, value]) => !value || typeof value !== "object")
    .map(([section]) => section);
}

function generateTag() {
  const bytes = new Uint8Array(3);
  crypto.getRandomValues(bytes);
  return [...bytes].map((byte) => byte.toString(16).padStart(2, "0")).join("");
}

function safeFileName(name) {
  const normalized = name
    .trim()
    .replace(/[^a-z0-9_-]+/gi, "-")
    .replace(/^-+|-+$/g, "")
    .toLowerCase();
  return normalized || "startech-sac";
}

function downloadCalibration(calibration) {
  const payload = `${JSON.stringify(calibration, null, 2)}\n`;
  const blob = new Blob([payload], { type: "application/json" });
  const downloadUrl = URL.createObjectURL(blob);
  const downloadLink = document.createElement("a");
  downloadLink.href = downloadUrl;
  downloadLink.download = `${safeFileName(calibration.name)}-${calibration.tag}.json`;
  document.body.append(downloadLink);
  downloadLink.click();
  downloadLink.remove();
  window.setTimeout(() => URL.revokeObjectURL(downloadUrl), 1000);
}

function refreshGate() {
  const sections = readSections();
  const missing = missingSections(sections);
  const complete = missing.length === 0;
  createCalibrationButton.disabled = !complete;
  createCalibrationButton.classList.toggle("cam-action--primary", complete);
  createCalibrationButton.classList.toggle("cam-action--secondary", !complete);

  if (!complete) {
    summaryCopy.textContent = "Some assisted sections are incomplete. Return to the car map before creating the file.";
    summaryMessage.textContent = `Missing: ${missing.join(", ")}.`;
    summaryMessage.classList.add("is-warning");
  }
}

createCalibrationButton.addEventListener("click", () => {
  const sections = readSections();
  if (missingSections(sections).length > 0) {
    refreshGate();
    return;
  }

  const tag = generateTag();
  const calibration = {
    schemaVersion: "cam-sac-prototype-1",
    tag,
    name: sessionStorage.getItem("startech-sac-name") || "MySAC",
    workflow: "SAC",
    createdAt: new Date().toISOString(),
    safety: {
      simulationOnly: true,
      physicalOutputArmed: false,
      physicalValidationPerformed: false
    },
    sections
  };

  sessionStorage.setItem("startech-sac-created-calibration", JSON.stringify(calibration));
  downloadCalibration(calibration);
  window.startechNavigate("sac-created.html");
});

goBackButton.addEventListener("click", () => {
  window.startechNavigate("sac-components.html");
});

refreshGate();
