const inactivityLengthSeconds = 15 * 60;

const flowDialog = document.querySelector("#flow-dialog");
const dialogTitle = document.querySelector("#dialog-title");
const dialogCopy = document.querySelector("#dialog-copy");
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

document.querySelectorAll("[data-flow]").forEach((control) => {
  control.addEventListener("click", () => {
    if (control.dataset.destination) {
      window.startechNavigate(control.dataset.destination);
      return;
    }

    dialogTitle.textContent = control.dataset.dialogTitle;
    dialogCopy.textContent = control.dataset.dialogCopy;
    flowDialog.showModal();
  });
});

flowDialog.addEventListener("click", (event) => {
  if (event.target === flowDialog) flowDialog.close();
});

["pointerdown", "keydown"].forEach((eventName) => {
  document.addEventListener(eventName, resetTimer, { passive: true });
});

window.setInterval(() => {
  remainingSeconds = Math.max(0, remainingSeconds - 1);
  renderTimer();
}, 1000);

renderTimer();
