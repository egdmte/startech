const sessionLengthSeconds = 15 * 60;

const warningStates = {
  checking: {
    icon: "hand",
    title: "Stop!",
    paragraphs: [
      "We found a problem with your car’s calibration file and we are looking for the reason."
    ],
    actions: []
  },
  "update-available": {
    icon: "gear",
    title: "Update available.",
    paragraphs: [
      "Your calibration version seems old (Server has version 2, you have version 1).",
      "If you want to edit a version 1 calibration file, it must be updated to version 2. You can create a new calibration without updating your version as well."
    ],
    actions: [
      { label: "Update", tone: "primary", action: "update" },
      { label: "Proceed with outdated calibration", tone: "secondary", action: "outdated" }
    ]
  },
  "server-updated": {
    icon: "gear",
    title: "Server is updated",
    paragraphs: [
      "Your calibration was in a newer version, so we updated our server to target it. You don’t need to take any steps."
    ],
    actions: [
      { label: "OK", tone: "primary", action: "continue" }
    ]
  },
  restricted: {
    icon: "hand",
    title: "Operation not permitted.",
    paragraphs: [
      "A module in your schema restricts CAM from updating it. Please update your schema by creating a new one and filling your old information."
    ],
    actions: [
      { label: "OK", tone: "primary", action: "continue" }
    ]
  },
  "missing-variables": {
    icon: "hand",
    title: "Operation not permitted.",
    paragraphs: [
      "There are missing/extra variables in your JSON schema. CAM will not be able to chance them in MAC, causing fatal errors."
    ],
    actions: [
      { label: "Add new variables →", tone: "primary", action: "add-variables" }
    ]
  }
};

const params = new URLSearchParams(window.location.search);
const requestedState = params.get("state") || "checking";
const activeStateName = Object.hasOwn(warningStates, requestedState)
  ? requestedState
  : "checking";
const activeState = warningStates[activeStateName];

const warningCard = document.querySelector("#warning-card");
const statusIcon = document.querySelector("#status-icon");
const warningTitle = document.querySelector("#warning-title");
const warningCopy = document.querySelector("#warning-copy");
const warningActions = document.querySelector("#warning-actions");
const prototypeMessage = document.querySelector("#prototype-message");
const minutesNode = document.querySelector("#timer-minutes");
const secondsNode = document.querySelector("#timer-seconds");
const sessionStatus = document.querySelector(".session-status");

let remainingSeconds = sessionLengthSeconds;
let sessionExpired = false;

function renderWarning() {
  warningCard.dataset.state = activeStateName;
  statusIcon.dataset.icon = activeState.icon;
  statusIcon.textContent = activeState.icon === "gear" ? "⚙︎" : "✋︎";
  warningTitle.textContent = activeState.title;
  document.title = `${activeState.title} — STARTECH CAM`;

  activeState.paragraphs.forEach((paragraph) => {
    const node = document.createElement("p");
    node.textContent = paragraph;
    warningCopy.append(node);
  });

  activeState.actions.forEach((action) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `cam-action cam-action--${action.tone}`;
    button.dataset.action = action.action;
    button.dataset.motionButton = "";
    button.textContent = action.label;
    warningActions.append(button);
  });
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
  warningActions.querySelectorAll("button").forEach((button) => {
    button.disabled = true;
  });
  prototypeMessage.textContent = "This session has expired. Return to login to continue.";
}

function handleAction(action) {
  if (sessionExpired) return;

  if (action === "update") {
    sessionStorage.setItem("startech-cam-schema-choice", "update");
    window.startechNavigate("schema-warning.html?state=server-updated");
    return;
  }

  if (action === "outdated") {
    sessionStorage.setItem("startech-cam-schema-choice", "outdated");
    window.startechNavigate("sac-components.html");
    return;
  }

  if (action === "continue") {
    window.startechNavigate("sac-components.html");
    return;
  }

  if (action === "add-variables") {
    sessionStorage.setItem("startech-cam-schema-choice", "add-variables");
    prototypeMessage.textContent = "The add-variable page will be connected after its design is supplied.";
  }
}

warningActions.addEventListener("click", (event) => {
  const button = event.target.closest("button[data-action]");
  if (!button) return;
  handleAction(button.dataset.action);
});

const nextState = params.get("next");
if (
  activeStateName === "checking" &&
  nextState &&
  Object.hasOwn(warningStates, nextState)
) {
  window.setTimeout(() => {
    window.startechNavigate(`schema-warning.html?state=${encodeURIComponent(nextState)}`);
  }, 1800);
}

window.setInterval(() => {
  if (sessionExpired) return;
  remainingSeconds = Math.max(0, remainingSeconds - 1);
  renderTimer();
  if (remainingSeconds === 0) expireSession();
}, 1000);

renderWarning();
renderTimer();
