const inactivityLengthSeconds = 15 * 60;
const baselineStorageKey = "startech-sac-baseline-v2";

const abortButton = document.querySelector("#abort-calibration");
const goBackButton = document.querySelector("#go-back");
const previousConfigFile = document.querySelector("#previous-config-file");
const sourceDialog = document.querySelector("#source-dialog");
const sourceDialogTitle = document.querySelector("#source-dialog-title");
const sourceDialogCopy = document.querySelector("#source-dialog-copy");
const sessionTime = document.querySelector("#session-time");

let remainingSeconds = inactivityLengthSeconds;
let lastResetAt = 0;
let nextPageAfterDialog = null;

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

function storeBaseline(source, baseline) {
  sessionStorage.setItem("startech-sac-source", source);
  sessionStorage.setItem(baselineStorageKey, JSON.stringify(baseline));
}

function showSourceDialog(title, copy, nextPage = null) {
  sourceDialogTitle.textContent = title;
  sourceDialogCopy.textContent = copy;
  nextPageAfterDialog = nextPage;
  sourceDialog.showModal();
}

document.querySelectorAll("[data-source]").forEach((button) => {
  button.addEventListener("click", () => {
    const source = button.dataset.source;
    const sourceLabel = button.dataset.sourceLabel;

    if (source === "car") {
      storeBaseline(source, window.StartechSacV2.defaultBaseline());
      window.startechNavigate("sac-connection.html");
      return;
    }

    if (source === "old-version") {
      previousConfigFile.value = "";
      previousConfigFile.click();
      return;
    }

    storeBaseline(source, window.StartechSacV2.defaultBaseline());
    showSourceDialog(
      `${sourceLabel} selected`,
      "The stable SAC model will inherit its measured values from this baseline.",
      "sac-preflight.html"
    );
  });
});

previousConfigFile.addEventListener("change", async () => {
  const [file] = previousConfigFile.files;
  if (!file) return;

  try {
    const baseline = window.StartechSacV2.parseImportedConfiguration(await file.text());
    storeBaseline("old-version", baseline);
    showSourceDialog(
      "Previous configuration loaded",
      "Calibration v1 and settings v1 will be inherited into a new merged v2 configuration.",
      "sac-preflight.html"
    );
  } catch (error) {
    sessionStorage.removeItem(baselineStorageKey);
    showSourceDialog(
      "That configuration cannot be used",
      error instanceof Error ? error.message : "Select a valid merged configuration v2."
    );
  }
});

abortButton.addEventListener("click", () => {
  sessionStorage.removeItem("startech-sac-name");
  sessionStorage.removeItem("startech-sac-source");
  sessionStorage.removeItem(baselineStorageKey);
  window.startechNavigate("startech_calibration_dashboard.html");
});

goBackButton.addEventListener("click", () => {
  window.startechNavigate("sac-name.html");
});

sourceDialog.addEventListener("click", (event) => {
  if (event.target === sourceDialog) sourceDialog.close();
});

sourceDialog.addEventListener("close", () => {
  if (!nextPageAfterDialog) return;
  const nextPage = nextPageAfterDialog;
  nextPageAfterDialog = null;
  window.startechNavigate(nextPage);
});

["pointerdown", "keydown"].forEach((eventName) => {
  document.addEventListener(eventName, resetTimer, { passive: true });
});

window.setInterval(() => {
  remainingSeconds = Math.max(0, remainingSeconds - 1);
  renderTimer();
}, 1000);

renderTimer();
