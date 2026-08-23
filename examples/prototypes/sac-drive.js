const inactivityLengthSeconds = 15 * 60;
const storageKey = "startech-sac-drive";

const outputModes = [...document.querySelectorAll('input[name="output-mode"]')];
const steeringCentre = document.querySelector("#steering-centre");
const steeringTravel = document.querySelector("#steering-travel");
const steeringCentreOutput = document.querySelector("#steering-centre-output");
const steeringTravelOutput = document.querySelector("#steering-travel-output");
const outputSummary = document.querySelector("#output-summary");
const outputSummaryTitle = document.querySelector("#output-summary-title");
const outputSummaryCopy = document.querySelector("#output-summary-copy");
const fullOutputGate = document.querySelector("#full-output-gate");
const fullProfileAcknowledgement = document.querySelector("#full-profile-acknowledgement");
const prototypeLockAcknowledgement = document.querySelector("#prototype-lock-acknowledgement");
const continueButton = document.querySelector("#continue-drive");
const sessionTime = document.querySelector("#session-time");

let remainingSeconds = inactivityLengthSeconds;
let lastResetAt = 0;

function readSettings() {
  try {
    return JSON.parse(sessionStorage.getItem(storageKey) || "null");
  } catch {
    return null;
  }
}

function selectRadio(name, value) {
  const option = document.querySelector(`input[name="${name}"][value="${value}"]`);
  if (option) option.checked = true;
}

function hydrateSettings() {
  const saved = readSettings();
  if (!saved) return;
  selectRadio("loss-action", saved.lossOfCommandAction);
  selectRadio("output-mode", saved.driverOutputMode);
  steeringCentre.value = String(saved.steeringCentreOffsetPercent ?? 0);
  steeringTravel.value = String(saved.maximumSteeringTravelPercent ?? 40);
  fullProfileAcknowledgement.checked = Boolean(saved.fullOutputAcknowledged);
  prototypeLockAcknowledgement.checked = Boolean(saved.prototypeLockAcknowledged);
}

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

function updateSteeringOutputs() {
  const centre = Number(steeringCentre.value);
  steeringCentreOutput.textContent = `${centre > 0 ? "+" : ""}${centre}%`;
  steeringTravelOutput.textContent = `${steeringTravel.value}%`;
}

function updateOutputGate() {
  const selectedMode = document.querySelector('input[name="output-mode"]:checked').value;
  outputSummary.classList.remove("output-summary--off", "output-summary--semi", "output-summary--full");
  outputSummary.classList.add(`output-summary--${selectedMode}`);
  fullOutputGate.hidden = selectedMode !== "full";

  if (selectedMode === "off") {
    outputSummaryTitle.textContent = "Simulation only";
    outputSummaryCopy.textContent = "The draft records steering values, but this page sends no command to a driver.";
  } else if (selectedMode === "semi") {
    outputSummaryTitle.textContent = "Steering profile only";
    outputSummaryCopy.textContent = "The exported profile may request steering, but activation remains a separate local-car decision.";
  } else {
    outputSummaryTitle.textContent = "Full output profile requested";
    outputSummaryCopy.textContent = "This is a high-impact profile choice. The browser still cannot arm or physically test the car.";
  }

  const fullGateComplete =
    selectedMode !== "full" ||
    (fullProfileAcknowledgement.checked && prototypeLockAcknowledgement.checked);
  continueButton.disabled = !fullGateComplete;
  continueButton.classList.toggle("cam-action--primary", fullGateComplete);
  continueButton.classList.toggle("cam-action--secondary", !fullGateComplete);
}

function saveSettings() {
  const settings = {
    lossOfCommandAction: document.querySelector('input[name="loss-action"]:checked').value,
    driverOutputMode: document.querySelector('input[name="output-mode"]:checked').value,
    steeringCentreOffsetPercent: Number(steeringCentre.value),
    maximumSteeringTravelPercent: Number(steeringTravel.value),
    fullOutputAcknowledged: fullProfileAcknowledgement.checked,
    prototypeLockAcknowledged: prototypeLockAcknowledgement.checked,
    physicalOutputArmed: false,
    mode: "simulation-only"
  };
  sessionStorage.setItem(storageKey, JSON.stringify(settings));
  sessionStorage.setItem("startech-sac-parts", JSON.stringify(["drive"]));
}

outputModes.forEach((option) => option.addEventListener("change", updateOutputGate));
[fullProfileAcknowledgement, prototypeLockAcknowledgement].forEach((control) => {
  control.addEventListener("change", updateOutputGate);
});
[steeringCentre, steeringTravel].forEach((control) => {
  control.addEventListener("input", updateSteeringOutputs);
});

continueButton.addEventListener("click", () => {
  if (continueButton.disabled) return;
  saveSettings();
  window.startechNavigate("sac-components.html");
});

["pointerdown", "keydown"].forEach((eventName) => {
  document.addEventListener(eventName, resetTimer, { passive: true });
});

window.setInterval(() => {
  remainingSeconds = Math.max(0, remainingSeconds - 1);
  renderTimer();
}, 1000);

hydrateSettings();
updateSteeringOutputs();
updateOutputGate();
renderTimer();
