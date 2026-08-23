const sessionLengthSeconds = 15 * 60;

const continueButton = document.querySelector(".continue-action");
const minutesNode = document.querySelector("#timer-minutes");
const secondsNode = document.querySelector("#timer-seconds");
const sessionStatus = document.querySelector(".session-status");

let remainingSeconds = sessionLengthSeconds;

function renderTimer() {
  const minutes = Math.floor(remainingSeconds / 60);
  const seconds = remainingSeconds % 60;
  minutesNode.textContent = String(minutes).padStart(2, "0");
  secondsNode.textContent = String(seconds).padStart(2, "0");
  sessionStatus.setAttribute(
    "aria-label",
    `Session expires in ${minutes} minutes and ${seconds} seconds`
  );
}

function expireSession() {
  continueButton.disabled = true;
  continueButton.textContent = "Session expired";
}

continueButton.addEventListener("click", () => {
  if (remainingSeconds === 0) return;
  window.startechNavigate("../startech_calibration_dashboard.html");
});

window.setInterval(() => {
  remainingSeconds = Math.max(0, remainingSeconds - 1);
  renderTimer();
  if (remainingSeconds === 0) expireSession();
}, 1000);

renderTimer();
