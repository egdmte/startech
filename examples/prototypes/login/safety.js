const sessionLengthSeconds = 15 * 60;

const form = document.querySelector(".acknowledgement-form");
const checkboxes = [...form.querySelectorAll('input[type="checkbox"]')];
const continueButton = document.querySelector(".continue-action");
const formMessage = document.querySelector(".form-message");
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

function updateGate() {
  const complete = checkboxes.every((checkbox) => checkbox.checked);
  continueButton.disabled = sessionExpired || !complete;
}

function expireSession() {
  sessionExpired = true;
  checkboxes.forEach((checkbox) => {
    checkbox.disabled = true;
  });
  continueButton.disabled = true;
  formMessage.textContent = "This session has expired. Return to login to continue.";
}

checkboxes.forEach((checkbox) => {
  checkbox.addEventListener("change", updateGate);
});

document.querySelectorAll("[data-document]").forEach((link) => {
  link.addEventListener("click", (event) => {
    event.preventDefault();
    event.stopPropagation();
    formMessage.textContent = "This manual link will be connected when the document is added.";
  });
});

form.addEventListener("submit", (event) => {
  event.preventDefault();
  if (sessionExpired || !checkboxes.every((checkbox) => checkbox.checked)) {
    updateGate();
    return;
  }

  window.location.href = "../startech_calibration_dashboard.html";
});

window.setInterval(() => {
  if (sessionExpired) return;
  remainingSeconds = Math.max(0, remainingSeconds - 1);
  renderTimer();
  if (remainingSeconds === 0) expireSession();
}, 1000);

renderTimer();
updateGate();
