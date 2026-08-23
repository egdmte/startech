const inactivityLengthSeconds = 15 * 60;
const storageKey = "startech-sac-wheel";

const leftCorrection = document.querySelector("#left-correction");
const rightCorrection = document.querySelector("#right-correction");
const leftCorrectionOutput = document.querySelector("#left-correction-output");
const rightCorrectionOutput = document.querySelector("#right-correction-output");
const reviewChecks = [...document.querySelectorAll("#mechanical-review input")];
const continueButton = document.querySelector("#continue-wheel");
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
  leftCorrection.value = String(saved.leftCorrectionPercent ?? 0);
  rightCorrection.value = String(saved.rightCorrectionPercent ?? 0);
  selectRadio("left-direction", saved.leftDirection);
  selectRadio("right-direction", saved.rightDirection);
  const reviewed = new Set(saved.mechanicalReview || []);
  reviewChecks.forEach((check) => {
    check.checked = reviewed.has(check.value);
  });
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

function signedPercent(value) {
  const numeric = Number(value);
  return `${numeric > 0 ? "+" : ""}${numeric}%`;
}

function updateCorrections() {
  leftCorrectionOutput.textContent = signedPercent(leftCorrection.value);
  rightCorrectionOutput.textContent = signedPercent(rightCorrection.value);
}

function updateGate() {
  const complete = reviewChecks.every((check) => check.checked);
  continueButton.disabled = !complete;
  continueButton.classList.toggle("cam-action--primary", complete);
  continueButton.classList.toggle("cam-action--secondary", !complete);
}

function saveSettings() {
  const settings = {
    leftCorrectionPercent: Number(leftCorrection.value),
    rightCorrectionPercent: Number(rightCorrection.value),
    leftDirection: document.querySelector('input[name="left-direction"]:checked').value,
    rightDirection: document.querySelector('input[name="right-direction"]:checked').value,
    mechanicalReview: reviewChecks.filter((check) => check.checked).map((check) => check.value),
    physicalAlignmentVerified: false,
    mode: "simulation-only"
  };
  sessionStorage.setItem(storageKey, JSON.stringify(settings));
  sessionStorage.setItem("startech-sac-parts", JSON.stringify(["wheel"]));
}

[leftCorrection, rightCorrection].forEach((control) => {
  control.addEventListener("input", updateCorrections);
});
reviewChecks.forEach((check) => check.addEventListener("change", updateGate));

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
updateCorrections();
updateGate();
renderTimer();
