const inactivityLengthSeconds = 15 * 60;

const abortButton = document.querySelector("#abort-calibration");
const goBackButton = document.querySelector("#go-back");
const sourceDialog = document.querySelector("#source-dialog");
const sourceDialogTitle = document.querySelector("#source-dialog-title");
const sourceDialogCopy = document.querySelector("#source-dialog-copy");
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

document.querySelectorAll("[data-source]").forEach((button) => {
  button.addEventListener("click", () => {
    const sourceLabel = button.dataset.sourceLabel;
    sessionStorage.setItem("startech-sac-source", button.dataset.source);

    if (button.dataset.source === "car") {
      window.startechNavigate("sac-connection.html");
      return;
    }

    sourceDialogTitle.textContent = `${sourceLabel} selected`;
    sourceDialogCopy.textContent = "This starting point is saved for the next calibration screen.";
    sourceDialog.showModal();
  });
});

abortButton.addEventListener("click", () => {
  sessionStorage.removeItem("startech-sac-name");
  sessionStorage.removeItem("startech-sac-source");
  window.startechNavigate("startech_calibration_dashboard.html");
});

goBackButton.addEventListener("click", () => {
  window.startechNavigate("sac-name.html");
});

sourceDialog.addEventListener("click", (event) => {
  if (event.target === sourceDialog) sourceDialog.close();
});

["pointerdown", "keydown"].forEach((eventName) => {
  document.addEventListener(eventName, resetTimer, { passive: true });
});

window.setInterval(() => {
  remainingSeconds = Math.max(0, remainingSeconds - 1);
  renderTimer();
}, 1000);

renderTimer();
