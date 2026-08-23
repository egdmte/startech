const inactivityLengthSeconds = 15 * 60;
const recommendedMaximumSpeed = 57;
const recommendedMinimumSpeed = 25;

const maximumSpeed = document.querySelector("#maximum-speed");
const minimumSpeed = document.querySelector("#minimum-speed");
const maximumSpeedControl = document.querySelector("#maximum-speed-control");
const minimumSpeedControl = document.querySelector("#minimum-speed-control");
const maximumSpeedWarning = document.querySelector("#maximum-speed-warning");
const minimumSpeedWarning = document.querySelector("#minimum-speed-warning");
const continueButton = document.querySelector("#continue-power");
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

function hydrateSettings() {
  try {
    const saved = JSON.parse(sessionStorage.getItem("startech-sac-power") || "null");
    if (!saved) return;
    maximumSpeed.value = String(saved.maximumSpeedPercent ?? 0);
    minimumSpeed.value = String(saved.minimumSpeedPercent ?? 0);
  } catch {
    sessionStorage.removeItem("startech-sac-power");
  }
}

function setWarning(element, message) {
  element.textContent = message;
  element.classList.toggle("is-clear", !message);
}

function updateSpeedControls() {
  const maximum = Number(maximumSpeed.value);
  const minimum = Number(minimumSpeed.value);
  const maximumIsSafe = maximum >= recommendedMaximumSpeed;
  const minimumIsSafe = minimum >= recommendedMinimumSpeed;
  const rangeIsOrdered = minimum <= maximum;

  maximumSpeedControl.style.setProperty("--position", `${maximum}%`);
  minimumSpeedControl.style.setProperty("--position", `${minimum}%`);
  maximumSpeed.setAttribute("aria-valuetext", `${maximum}% maximum motor speed`);
  minimumSpeed.setAttribute("aria-valuetext", `${minimum}% minimum motor speed`);

  setWarning(
    maximumSpeedWarning,
    maximumIsSafe ? "" : "You are underpowering the motors!"
  );

  if (!minimumIsSafe) {
    setWarning(minimumSpeedWarning, "You are underpowering the motors!");
  } else if (!rangeIsOrdered) {
    setWarning(minimumSpeedWarning, "Minimum speed cannot exceed maximum speed!");
  } else {
    setWarning(minimumSpeedWarning, "");
  }

  const canContinue = maximumIsSafe && minimumIsSafe && rangeIsOrdered;
  continueButton.disabled = !canContinue;
  continueButton.classList.toggle("cam-action--secondary", !canContinue);
  continueButton.classList.toggle("cam-action--primary", canContinue);
}

[maximumSpeed, minimumSpeed].forEach((control) => {
  control.addEventListener("input", updateSpeedControls);
});

continueButton.addEventListener("click", () => {
  const settings = {
    maximumSpeedPercent: Number(maximumSpeed.value),
    minimumSpeedPercent: Number(minimumSpeed.value),
    mode: "simulation-only"
  };
  sessionStorage.setItem("startech-sac-power", JSON.stringify(settings));
  sessionStorage.setItem("startech-sac-parts", JSON.stringify(["power"]));
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
updateSpeedControls();
renderTimer();
