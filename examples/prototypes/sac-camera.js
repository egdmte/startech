const inactivityLengthSeconds = 15 * 60;

const orientationOptions = [...document.querySelectorAll("[data-orientation]")];
const orientationPreview = document.querySelector("#orientation-preview");
const continueButton = document.querySelector("#continue-camera");
const prioritizeRpicam = document.querySelector("#prioritize-rpicam");
const sessionTime = document.querySelector("#session-time");

let selectedOrientation = null;
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

function selectOrientation(option) {
  selectedOrientation = Number(option.dataset.orientation);
  orientationOptions.forEach((control) => {
    control.setAttribute("aria-pressed", String(control === option));
  });
  orientationPreview.style.setProperty("--camera-rotation", `${selectedOrientation}deg`);
  continueButton.disabled = false;
  continueButton.classList.remove("cam-action--secondary");
  continueButton.classList.add("cam-action--primary");
}

function selectRadio(name, value) {
  const option = document.querySelector(`input[name="${name}"][value="${value}"]`);
  if (option) option.checked = true;
}

function hydrateSettings() {
  try {
    const saved = JSON.parse(sessionStorage.getItem("startech-sac-camera") || "null");
    if (!saved) return;
    selectRadio("capture-profile", saved.captureProfile);
    selectRadio("recognition-sensitivity", saved.recognitionSensitivity);
    prioritizeRpicam.checked = Boolean(saved.prioritizeRaspberryPi);
    const orientation = orientationOptions.find(
      (option) => Number(option.dataset.orientation) === Number(saved.orientationDegrees)
    );
    if (orientation) selectOrientation(orientation);
  } catch {
    sessionStorage.removeItem("startech-sac-camera");
  }
}

orientationOptions.forEach((option) => {
  option.addEventListener("click", () => selectOrientation(option));
});

continueButton.addEventListener("click", () => {
  const captureProfile = document.querySelector('input[name="capture-profile"]:checked');
  const sensitivity = document.querySelector('input[name="recognition-sensitivity"]:checked');
  const settings = {
    orientationDegrees: selectedOrientation,
    captureProfile: captureProfile.value,
    recognitionSensitivity: sensitivity.value,
    prioritizeRaspberryPi: prioritizeRpicam.checked,
    mode: "simulation-only"
  };
  sessionStorage.setItem("startech-sac-camera", JSON.stringify(settings));
  sessionStorage.setItem("startech-sac-parts", JSON.stringify(["vision"]));
  window.startechNavigate("sac-components.html");
});

["pointerdown", "keydown"].forEach((eventName) => {
  document.addEventListener(eventName, resetTimer, { passive: true });
});

window.setInterval(() => {
  remainingSeconds = Math.max(0, remainingSeconds - 1);
  renderTimer();
}, 1000);

hydrateSettings();
renderTimer();
