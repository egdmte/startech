const finishSessionLengthSeconds = 15 * 60;
const finishMinutes = document.querySelector("#timer-minutes");
const finishSeconds = document.querySelector("#timer-seconds");
const finishSessionStatus = document.querySelector(".finish-session-status");

let finishRemainingSeconds = finishSessionLengthSeconds;
let finishLastResetAt = 0;

function renderFinishTimer() {
  const minutes = Math.floor(finishRemainingSeconds / 60);
  const seconds = finishRemainingSeconds % 60;
  finishMinutes.textContent = String(minutes).padStart(2, "0");
  finishSeconds.textContent = String(seconds).padStart(2, "0");
  finishSessionStatus.setAttribute(
    "aria-label",
    `Session expires in ${minutes} minutes and ${seconds} seconds`
  );
}

function resetFinishTimer() {
  const now = Date.now();
  if (now - finishLastResetAt < 1000) return;
  finishRemainingSeconds = finishSessionLengthSeconds;
  finishLastResetAt = now;
  renderFinishTimer();
}

["pointerdown", "keydown"].forEach((eventName) => {
  document.addEventListener(eventName, resetFinishTimer, { passive: true });
});

window.setInterval(() => {
  finishRemainingSeconds = Math.max(0, finishRemainingSeconds - 1);
  renderFinishTimer();
}, 1000);

renderFinishTimer();
