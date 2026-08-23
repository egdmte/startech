const inactivityLengthSeconds = 15 * 60;

const downloadWindowsButton = document.querySelector("#download-windows");
const continueOnlineButton = document.querySelector("#continue-online");
const goBackButton = document.querySelector("#go-back");
const connectionDialog = document.querySelector("#connection-dialog");
const connectionDialogTitle = document.querySelector("#connection-dialog-title");
const connectionDialogCopy = document.querySelector("#connection-dialog-copy");
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

function showPrototypeChoice(title, copy) {
  connectionDialogTitle.textContent = title;
  connectionDialogCopy.textContent = copy;
  connectionDialog.showModal();
}

downloadWindowsButton.addEventListener("click", () => {
  sessionStorage.setItem("startech-sac-connection", "windows");
  showPrototypeChoice(
    "Windows module selected",
    "No installer is attached to this design prototype yet."
  );
});

continueOnlineButton.addEventListener("click", () => {
  sessionStorage.setItem("startech-sac-connection", "online");
  window.startechNavigate("sac-preflight.html");
});

goBackButton.addEventListener("click", () => {
  window.startechNavigate("sac-source.html");
});

connectionDialog.addEventListener("click", (event) => {
  if (event.target === connectionDialog) connectionDialog.close();
});

["pointerdown", "keydown"].forEach((eventName) => {
  document.addEventListener(eventName, resetTimer, { passive: true });
});

window.setInterval(() => {
  remainingSeconds = Math.max(0, remainingSeconds - 1);
  renderTimer();
}, 1000);

renderTimer();
