const inactivityLengthSeconds = 15 * 60;

const namingForm = document.querySelector(".naming-form");
const calibrationName = document.querySelector("#calibration-name");
const changeOwnerButton = document.querySelector("#change-owner");
const formMessage = document.querySelector("#form-message");
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

namingForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const name = calibrationName.value.trim();

  if (!name) {
    calibrationName.setAttribute("aria-invalid", "true");
    formMessage.textContent = "Enter a name for this calibration to continue.";
    calibrationName.focus();
    return;
  }

  calibrationName.removeAttribute("aria-invalid");
  sessionStorage.setItem("startech-sac-name", name);
  formMessage.textContent = `“${name}” is ready for the next calibration step.`;
  window.startechNavigate("sac-source.html");
});

calibrationName.addEventListener("input", () => {
  calibrationName.removeAttribute("aria-invalid");
  formMessage.textContent = "";
});

changeOwnerButton.addEventListener("click", () => {
  window.startechNavigate("login/index.html");
});

["pointerdown", "keydown"].forEach((eventName) => {
  document.addEventListener(eventName, resetTimer, { passive: true });
});

window.setInterval(() => {
  remainingSeconds = Math.max(0, remainingSeconds - 1);
  renderTimer();
}, 1000);

renderTimer();
