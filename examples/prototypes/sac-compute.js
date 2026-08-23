const inactivityLengthSeconds = 15 * 60;

const requiredModules = [...document.querySelectorAll("[data-required-module]")];
const allModules = [...document.querySelectorAll("#module-picker input")];
const continueButton = document.querySelector("#continue-compute");
const computeDialog = document.querySelector("#compute-dialog");
const sessionTime = document.querySelector("#session-time");

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

function updateRequiredModules() {
  const allRequiredSelected = requiredModules.every((module) => module.checked);
  continueButton.disabled = !allRequiredSelected;
  continueButton.classList.toggle("cam-action--secondary", !allRequiredSelected);
  continueButton.classList.toggle("cam-action--primary", allRequiredSelected);
}

allModules.forEach((module) => {
  module.addEventListener("change", updateRequiredModules);
});

continueButton.addEventListener("click", () => {
  const startupPrecaution = document.querySelector('input[name="startup-precaution"]:checked');
  const aggressiveness = document.querySelector('input[name="m3th-aggressiveness"]:checked');
  const serviceStatus = document.querySelector('input[name="service-status"]:checked');
  const settings = {
    startupPrecaution: startupPrecaution.value,
    serviceStatus: serviceStatus.value,
    m3thAggressiveness: aggressiveness.value,
    enabledModules: allModules.filter((module) => module.checked).map((module) => module.value),
    raspberryPiTemperatureC: null,
    mode: "simulation-only"
  };
  sessionStorage.setItem("startech-sac-compute", JSON.stringify(settings));
  computeDialog.showModal();
});

computeDialog.addEventListener("click", (event) => {
  if (event.target === computeDialog) computeDialog.close();
});

["pointerdown", "keydown"].forEach((eventName) => {
  document.addEventListener(eventName, resetTimer, { passive: true });
});

window.setInterval(() => {
  remainingSeconds = Math.max(0, remainingSeconds - 1);
  renderTimer();
}, 1000);

renderTimer();
updateRequiredModules();
