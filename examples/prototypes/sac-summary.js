const componentStorageKeys = {
  power: "startech-sac-power",
  compute: "startech-sac-compute",
  camera: "startech-sac-camera",
  drive: "startech-sac-drive",
  wheel: "startech-sac-wheel"
};
const baselineStorageKey = "startech-sac-baseline-v2";

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

function readBaseline() {
  return readJson(baselineStorageKey);
}

function missingSections(sections) {
  return Object.entries(sections)
    .filter(([, value]) => !value || typeof value !== "object")
    .map(([section]) => section);
}

function safeFileName(name) {
  const normalized = name
    .trim()
    .replace(/[^a-z0-9_-]+/gi, "-")
    .replace(/^-+|-+$/g, "")
    .toLowerCase();
  return normalized || "startech-sac";
}

function downloadCalibration(configuration) {
  const payload = `${JSON.stringify(configuration, null, 2)}\n`;
  const blob = new Blob([payload], { type: "application/json" });
  const downloadUrl = URL.createObjectURL(blob);
  const downloadLink = document.createElement("a");
  downloadLink.href = downloadUrl;
  downloadLink.download = `${safeFileName(configuration.profil.ad)}-${configuration.profil.kimlik}.json`;
  document.body.append(downloadLink);
  downloadLink.click();
  downloadLink.remove();
  window.setTimeout(() => URL.revokeObjectURL(downloadUrl), 1000);
}

function refreshGate() {
  const sections = readSections();
  const missing = missingSections(sections);
  const baseline = readBaseline();
  const complete = missing.length === 0 && baseline !== null;
  createCalibrationButton.disabled = !complete;
  createCalibrationButton.classList.toggle("cam-action--primary", complete);
  createCalibrationButton.classList.toggle("cam-action--secondary", !complete);

  if (baseline === null) {
    summaryCopy.textContent = "The selected calibration source is unavailable. Return to the source screen before creating the file.";
    summaryMessage.textContent = "Missing configuration v2 baseline.";
    summaryMessage.classList.add("is-warning");
  } else if (!complete) {
    summaryCopy.textContent = "Some assisted sections are incomplete. Return to the car map before creating the file.";
    summaryMessage.textContent = `Missing: ${missing.join(", ")}.`;
    summaryMessage.classList.add("is-warning");
  }
}

createCalibrationButton.addEventListener("click", () => {
  const sections = readSections();
  const baseline = readBaseline();
  if (missingSections(sections).length > 0 || baseline === null) {
    refreshGate();
    return;
  }

  try {
    const { configuration, identifier } = window.StartechSacV2.buildConfiguration({
      baseline,
      name: sessionStorage.getItem("startech-sac-name") || "MySAC",
      source: sessionStorage.getItem("startech-sac-source") || "default",
      sections
    });
    const createdCalibration = {
      tag: identifier,
      name: configuration.profil.ad,
      configuration
    };

    sessionStorage.setItem("startech-sac-created-calibration", JSON.stringify(createdCalibration));
    downloadCalibration(configuration);
    window.startechNavigate("sac-created.html");
  } catch (error) {
    summaryMessage.textContent = error instanceof Error ? error.message : "The merged configuration could not be created.";
    summaryMessage.classList.add("is-warning");
  }
});

goBackButton.addEventListener("click", () => {
  window.startechNavigate("sac-components.html");
});

refreshGate();
