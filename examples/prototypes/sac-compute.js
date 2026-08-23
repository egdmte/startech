const inactivityLengthSeconds = 15 * 60;

const requiredModules = [...document.querySelectorAll("[data-required-module]")];
const allModules = [...document.querySelectorAll("#module-picker input")];
const continueButton = document.querySelector("#continue-compute");
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

function selectRadio(name, value) {
  const option = document.querySelector(`input[name="${name}"][value="${value}"]`);
  if (option) option.checked = true;
}

function hydrateSettings() {
  try {
    const saved = JSON.parse(sessionStorage.getItem("startech-sac-compute") || "null");
    if (!saved) return;
    selectRadio("startup-precaution", saved.startupPrecaution);
    selectRadio("service-status", saved.serviceStatus);
    selectRadio("m3th-aggressiveness", saved.m3thAggressiveness);
    const enabled = new Set(saved.enabledModules || []);
    allModules.forEach((module) => {
      module.checked = enabled.has(module.value);
    });
  } catch {
    sessionStorage.removeItem("startech-sac-compute");
  }
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
  sessionStorage.setItem("startech-sac-parts", JSON.stringify(["compute"]));
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
updateRequiredModules();
renderTimer();
