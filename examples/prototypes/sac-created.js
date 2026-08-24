const calibrationTag = document.querySelector("#calibration-tag");
const editWithMacButton = document.querySelector("#edit-with-mac");
const sideloadButton = document.querySelector("#sideload-to-pi");
const mainMenuButton = document.querySelector("#main-menu");
const createdMessage = document.querySelector("#created-message");

function readCreatedCalibration() {
  try {
    return JSON.parse(sessionStorage.getItem("startech-sac-created-calibration") || "null");
  } catch {
    return null;
  }
}

const calibration = readCreatedCalibration();

if (calibration?.tag) {
  calibrationTag.textContent = calibration.tag;
  editWithMacButton.textContent = `Edit ${calibration.tag} with MAC`;
} else {
  document.querySelector("#created-title").textContent = "No calibration was created.";
  calibrationTag.parentElement.textContent = "Return to the summary screen to create and download a calibration file.";
  editWithMacButton.disabled = true;
  sideloadButton.disabled = true;
  createdMessage.textContent = "This direct preview does not create a calibration.";
  createdMessage.classList.add("is-warning");
}

editWithMacButton.addEventListener("click", () => {
  if (!calibration?.tag) return;
  sessionStorage.setItem("startech-mac-source-tag", calibration.tag);
  sessionStorage.setItem("startech-mac-source-config", JSON.stringify(calibration.configuration));
  window.startechNavigate(
    `mac-source.html?source=${encodeURIComponent(calibration.tag)}`
  );
});

sideloadButton.addEventListener("click", () => {
  if (!calibration?.tag) return;
  createdMessage.textContent = "Prototype only: no command or calibration was sent to the Raspberry Pi.";
  createdMessage.classList.add("is-warning");
});

mainMenuButton.addEventListener("click", () => {
  window.startechNavigate("startech_calibration_dashboard.html");
});
