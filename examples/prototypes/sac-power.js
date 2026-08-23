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
const powerDialog = document.querySelector("#power-dialog");
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
  powerDialog.showModal();
});

powerDialog.addEventListener("click", (event) => {
  if (event.target === powerDialog) powerDialog.close();
});

["pointerdown", "keydown"].forEach((eventName) => {
  document.addEventListener(eventName, resetTimer, { passive: true });
});

window.setInterval(() => {
  remainingSeconds = Math.max(0, remainingSeconds - 1);
  renderTimer();
}, 1000);

renderTimer();
updateSpeedControls();
