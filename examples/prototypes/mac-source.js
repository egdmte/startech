const macDraftStorageKey = "startech-mac-draft";
const uploadButton = document.querySelector("#upload-json");
const versionHistoryButton = document.querySelector("#version-history");
const emptyJsonButton = document.querySelector("#empty-json");
const fileInput = document.querySelector("#json-file");
const saveButton = document.querySelector("#save-mac");
const sourceMessage = document.querySelector("#mac-source-message");

let currentDraft = null;

function readJsonStorage(key) {
  try {
    return JSON.parse(sessionStorage.getItem(key) || "null");
  } catch {
    return null;
  }
}

function setMessage(message, isError = false) {
  sourceMessage.textContent = message;
  sourceMessage.classList.toggle("is-error", isError);
}

function setDraft(documentValue, source) {
  currentDraft = {
    workflow: "MAC",
    interfaceVersion: "0.1",
    state: "draft",
    source,
    document: documentValue,
    savedAt: null,
    simulationOnly: true
  };
  sessionStorage.setItem(macDraftStorageKey, JSON.stringify(currentDraft));
  saveButton.disabled = false;
  setMessage(`${source.label} is loaded. The variable editor will use this draft.`);
}

function loadStoredDraft() {
  const saved = readJsonStorage(macDraftStorageKey);
  if (!saved || typeof saved !== "object" || Array.isArray(saved)) return;
  currentDraft = saved;
  saveButton.disabled = false;
  setMessage(`${saved.source?.label || "The MAC draft"} is loaded.`);
}

function loadVersionHistory() {
  const latestSac = readJsonStorage("startech-sac-created-calibration");
  if (!latestSac || typeof latestSac !== "object" || Array.isArray(latestSac)) {
    setMessage("No browser-local calibration is available in version history.", true);
    return;
  }

  setDraft(latestSac, {
    kind: "version-history",
    tag: latestSac.tag || null,
    label: latestSac.tag ? `Calibration ${latestSac.tag}` : "Latest SAC calibration"
  });
}

async function loadUploadedFile(file) {
  if (!file) return;

  try {
    const parsed = JSON.parse(await file.text());
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
      throw new Error("The JSON root must be an object.");
    }
    setDraft(parsed, {
      kind: "uploaded-json",
      fileName: file.name,
      label: file.name
    });
  } catch (error) {
    setMessage(`Could not load ${file.name}: ${error.message}`, true);
  } finally {
    fileInput.value = "";
  }
}

uploadButton.addEventListener("click", () => fileInput.click());
fileInput.addEventListener("change", () => loadUploadedFile(fileInput.files?.[0]));
versionHistoryButton.addEventListener("click", loadVersionHistory);

emptyJsonButton.addEventListener("click", () => {
  setDraft(
    {
      schemaVersion: null,
      tag: null,
      name: "Untitled MAC",
      values: {}
    },
    { kind: "empty-json", label: "Empty .json" }
  );
});

saveButton.addEventListener("click", () => {
  if (!currentDraft) return;
  currentDraft.savedAt = new Date().toISOString();
  sessionStorage.setItem(macDraftStorageKey, JSON.stringify(currentDraft));
  setMessage("Draft saved in this browser session. Nothing was published or sent to the car.");
});

function loadRequestedSource() {
  const requestedSource = new URLSearchParams(window.location.search).get("source");
  if (!requestedSource) return false;

  const latestSac = readJsonStorage("startech-sac-created-calibration");
  if (latestSac?.tag === requestedSource) {
    setDraft(latestSac, {
      kind: "sac-handoff",
      tag: requestedSource,
      label: `Calibration ${requestedSource}`
    });
  } else {
    setMessage(`Calibration ${requestedSource} is not available in this browser session.`, true);
  }
  return true;
}

if (!loadRequestedSource()) loadStoredDraft();
