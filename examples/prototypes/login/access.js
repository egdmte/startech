const sessionLengthSeconds = 15 * 60;
const codePattern = /^[A-Z0-9]{4}(?:-[A-Z0-9]{4}){1,3}$/;

const form = document.querySelector(".code-form");
const codeInput = document.querySelector("#web-code");
const codeMessage = document.querySelector("#code-message");
const sendButton = document.querySelector(".send-action");
const offlineButton = document.querySelector(".offline-action");
const minutesNode = document.querySelector("#timer-minutes");
const secondsNode = document.querySelector("#timer-seconds");
const sessionStatus = document.querySelector(".session-status");

let remainingSeconds = sessionLengthSeconds;
let sessionExpired = false;

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

function setMessage(message, isError = false) {
  codeMessage.textContent = message;
  codeMessage.classList.toggle("is-error", isError);
}

function expireSession() {
  sessionExpired = true;
  codeInput.disabled = true;
  sendButton.disabled = true;
  setMessage("This code-entry session has expired. Return to login to continue.", true);
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  if (sessionExpired) return;

  const valid = codePattern.test(codeInput.value.trim());
  codeInput.setAttribute("aria-invalid", String(!valid));
  if (!valid) {
    setMessage("Enter the complete code shown by YAREN.", true);
    codeInput.focus();
    return;
  }

  window.startechNavigate("safety.html");
});

codeInput.addEventListener("input", () => {
  codeInput.value = codeInput.value.toUpperCase().replace(/\s+/g, "");
  codeInput.setAttribute("aria-invalid", "false");
  setMessage("");
});

offlineButton.addEventListener("click", () => {
  setMessage("The offline calibration workspace will be connected in a later slice.");
});

window.setInterval(() => {
  if (sessionExpired) return;
  remainingSeconds = Math.max(0, remainingSeconds - 1);
  renderTimer();
  if (remainingSeconds === 0) expireSession();
}, 1000);

renderTimer();
