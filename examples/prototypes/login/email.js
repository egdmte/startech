const sessionLengthSeconds = 15 * 60;
const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

const form = document.querySelector(".email-form");
const emailInput = document.querySelector("#email-address");
const emailError = document.querySelector("#email-error");
const emailStatus = document.querySelector("#email-status");
const sendButton = document.querySelector(".send-action");
const offlineButton = document.querySelector(".offline-action");
const minutesNode = document.querySelector("#timer-minutes");
const secondsNode = document.querySelector("#timer-seconds");
const sessionStatus = document.querySelector(".session-status");

let remainingSeconds = sessionLengthSeconds;
let sessionExpired = false;
let lastResetAt = 0;

function isValidEmail(value) {
  return emailPattern.test(value.trim());
}

function setEmailValidity(valid) {
  emailInput.setAttribute("aria-invalid", String(!valid));
  emailError.hidden = valid;
}

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
  sessionExpired = true;
  emailInput.disabled = true;
  sendButton.disabled = true;
  emailStatus.textContent = "Your session expired. Return to the login screen to continue.";
}

function resetTimer() {
  if (sessionExpired) return;

  const now = Date.now();
  if (now - lastResetAt < 1000) return;

  remainingSeconds = sessionLengthSeconds;
  lastResetAt = now;
  renderTimer();
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  if (sessionExpired) return;

  const valid = isValidEmail(emailInput.value);
  setEmailValidity(valid);

  if (!valid) {
    emailStatus.textContent = "";
    emailInput.focus();
    return;
  }

  emailStatus.textContent =
    "Email delivery will be connected when the Resend authentication slice is implemented.";
});

emailInput.addEventListener("input", () => {
  if (emailInput.value.trim()) setEmailValidity(emailInput.value.includes("@"));
  emailStatus.textContent = "";
});

offlineButton.addEventListener("click", () => {
  emailStatus.textContent = "The offline calibration workspace will be connected in a later slice.";
});

["pointerdown", "keydown"].forEach((eventName) => {
  document.addEventListener(eventName, resetTimer, { passive: true });
});

window.setInterval(() => {
  if (sessionExpired) return;

  remainingSeconds = Math.max(0, remainingSeconds - 1);
  renderTimer();

  if (remainingSeconds === 0) expireSession();
}, 1000);

setEmailValidity(true);
renderTimer();
