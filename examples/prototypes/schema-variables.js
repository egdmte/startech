const sessionLengthSeconds = 15 * 60;
const storageKey = "startech-cam-variable-draft";

const unresolvedVariables = [
  { key: "sign_untype", module: "OSMAN" },
  { key: "sign_untype", module: "OSMAN" },
  { key: "sign_untype", module: "OSMAN" },
  { key: "sign_untype", module: "OSMAN" },
  { key: "sign_untype", module: "OSMAN" }
];

const variableList = document.querySelector("#variable-list");
const variableTemplate = document.querySelector("#variable-card-template");
const variablesForm = document.querySelector("#variables-form");
const backButton = document.querySelector("#back-to-warning");
const formMessage = document.querySelector("#form-message");
const minutesNode = document.querySelector("#timer-minutes");
const secondsNode = document.querySelector("#timer-seconds");
const sessionStatus = document.querySelector(".session-status");

let remainingSeconds = sessionLengthSeconds;
let sessionExpired = false;

function readDraft() {
  try {
    const parsed = JSON.parse(sessionStorage.getItem(storageKey) || "[]");
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function collectDraft() {
  return [...variableList.querySelectorAll(".variable-card")].map((card, index) => ({
    key: unresolvedVariables[index].key,
    module: unresolvedVariables[index].module,
    value: card.querySelector('[data-field="value"]').value.trim(),
    type: card.querySelector('[data-field="type"]').value,
    acceptedValues: card.querySelector('[data-field="acceptedValues"]').value.trim(),
    defaultValue: card.querySelector('[data-field="defaultValue"]').value.trim(),
    required: card.querySelector('[data-field="required"]').checked,
    safetyClass: card.querySelector('[data-field="safetyClass"]').value
  }));
}

function saveDraft() {
  sessionStorage.setItem(storageKey, JSON.stringify(collectDraft()));
}

function renderVariables() {
  const savedDraft = readDraft();

  unresolvedVariables.forEach((variable, index) => {
    const fragment = variableTemplate.content.cloneNode(true);
    const card = fragment.querySelector(".variable-card");
    const saved = savedDraft[index] || {};

    card.dataset.variableIndex = String(index);
    card.querySelector("[data-variable-key]").textContent = variable.key;
    card.querySelector("[data-variable-module]").textContent = variable.module;
    card.querySelector('[data-field="value"]').value = saved.value || "";
    card.querySelector('[data-field="type"]').value = saved.type || "bool";
    card.querySelector('[data-field="acceptedValues"]').value = saved.acceptedValues || "";
    card.querySelector('[data-field="defaultValue"]').value = saved.defaultValue || "";
    card.querySelector('[data-field="required"]').checked = Boolean(saved.required);
    card.querySelector('[data-field="safetyClass"]').value = saved.safetyClass || "safe";

    card.querySelectorAll("input, select").forEach((control) => {
      const fieldName = control.dataset.field;
      control.name = `variable-${index}-${fieldName}`;
      if (control.type !== "checkbox") {
        control.setAttribute("aria-label", `${variable.key} ${fieldName}, entry ${index + 1}`);
      }
    });

    variableList.append(fragment);
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
  variablesForm.querySelectorAll("input, select, button").forEach((control) => {
    control.disabled = true;
  });
  formMessage.textContent = "This session has expired. Return to login to continue.";
}

function validateDraft() {
  let firstInvalid = null;

  variableList.querySelectorAll(".variable-card").forEach((card) => {
    const valueInput = card.querySelector('[data-field="value"]');
    const defaultInput = card.querySelector('[data-field="defaultValue"]');
    const complete = valueInput.value.trim() && defaultInput.value.trim();

    [valueInput, defaultInput].forEach((input) => {
      const invalid = !input.value.trim();
      input.setAttribute("aria-invalid", String(invalid));
      if (invalid && !firstInvalid) firstInvalid = input;
    });

    card.classList.toggle("is-incomplete", !complete);
  });

  return firstInvalid;
}

variablesForm.addEventListener("input", (event) => {
  if (sessionExpired) return;
  if (event.target.matches("input, select")) {
    event.target.setAttribute("aria-invalid", "false");
    formMessage.textContent = "";
    saveDraft();
  }
});

variablesForm.addEventListener("change", () => {
  if (!sessionExpired) saveDraft();
});

variablesForm.addEventListener("submit", (event) => {
  event.preventDefault();
  if (sessionExpired) return;

  const firstInvalid = validateDraft();
  if (firstInvalid) {
    formMessage.textContent = "Add a value and default for every unresolved variable.";
    firstInvalid.focus();
    return;
  }

  saveDraft();
  formMessage.textContent = "Draft definitions saved locally. Registration will be connected after its review screen is designed.";
});

backButton.addEventListener("click", () => {
  saveDraft();
  window.startechNavigate("schema-warning.html?state=missing-variables");
});

window.setInterval(() => {
  if (sessionExpired) return;
  remainingSeconds = Math.max(0, remainingSeconds - 1);
  renderTimer();
  if (remainingSeconds === 0) expireSession();
}, 1000);

renderVariables();
renderTimer();
