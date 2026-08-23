const inactivityLengthSeconds = 15 * 60;
const preflightStepDelay = 700;

const preflightList = document.querySelector(".preflight-list");
const preflightItems = [...document.querySelectorAll("[data-preflight-item]")];
const preflightNote = document.querySelector("#preflight-note");
const continueButton = document.querySelector("#continue-preflight");
const preflightDialog = document.querySelector("#preflight-dialog");
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

function wait(milliseconds) {
  return new Promise((resolve) => window.setTimeout(resolve, milliseconds));
}

async function runPrototypePreflight() {
  for (const item of preflightItems) {
    item.classList.add("is-active");
    await wait(preflightStepDelay);
    item.classList.remove("is-active");
    item.classList.add(item.dataset.result === "unavailable" ? "is-unavailable" : "is-complete");
  }

  preflightList.classList.add("is-finished");
  preflightNote.textContent = "Prototype preflight complete. No Pi was contacted and the car will not move.";
  continueButton.disabled = false;
  continueButton.classList.remove("cam-action--secondary");
  continueButton.classList.add("cam-action--primary");
  continueButton.textContent = "Continue in simulation";

  sessionStorage.setItem("startech-sac-preflight", "simulation-only");
}

continueButton.addEventListener("click", () => {
  preflightDialog.showModal();
});

preflightDialog.addEventListener("click", (event) => {
  if (event.target === preflightDialog) preflightDialog.close();
});

["pointerdown", "keydown"].forEach((eventName) => {
  document.addEventListener(eventName, resetTimer, { passive: true });
});

window.setInterval(() => {
  remainingSeconds = Math.max(0, remainingSeconds - 1);
  renderTimer();
}, 1000);

renderTimer();
runPrototypePreflight();
