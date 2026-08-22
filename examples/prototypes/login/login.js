const translations = {
  en: {
    pageTitle: "Calibrate your STARTECH instance",
    panelLabel: "Login",
    languageLabel: "Language",
    introTitle: "Calibrate your STARTECH<br> instance",
    introDescription:
      "Any car with compatible code can receive a new calibration without manually transferring a file.",
    learn: "Learn how to update your code",
    nameLabel: "Your full legal name",
    passwordLabel: "Password provided",
    login: "Log in",
    offline: "Continue without access to the car",
    nameError: "Enter your name.",
    passwordError: "Enter the access password.",
    prototypeStatus: "Opening temporary code verification.",
    learnStatus: "The code-update guide will be connected when that document is ready.",
    offlineStatus: "The offline calibration workspace will be connected in the next slice."
  },
  tr: {
    pageTitle: "STARTECH aracını kalibre et",
    panelLabel: "Giriş",
    languageLabel: "Dil",
    introTitle: "STARTECH aracını<br> kalibre et",
    introDescription:
      "Uyumlu koda sahip araçlar, elle dosya aktarmadan yeni bir kalibrasyon alabilir.",
    learn: "Kodu nasıl güncelleyeceğini öğren",
    nameLabel: "Adın ve soyadın",
    passwordLabel: "Verilen parola",
    login: "Giriş yap",
    offline: "Araca erişmeden devam et",
    nameError: "Adını ve soyadını yaz.",
    passwordError: "Erişim parolasını yaz.",
    prototypeStatus: "Geçici kod doğrulaması açılıyor.",
    learnStatus: "Kod güncelleme kılavuzu hazırlandığında bu bağlantı etkinleştirilecek.",
    offlineStatus: "Çevrimdışı kalibrasyon alanı bir sonraki aşamada bağlanacak."
  }
};

const form = document.querySelector(".auth-form");
const authPanel = document.querySelector(".auth-panel");
const languageGroup = document.querySelector(".language-switcher");
const nameInput = document.querySelector("#full-name");
const passwordInput = document.querySelector("#password");
const nameError = document.querySelector("#name-error");
const passwordError = document.querySelector("#password-error");
const status = document.querySelector(".form-status");
let activeLanguage = "en";

function setFieldValidity(input, error, valid) {
  input.setAttribute("aria-invalid", String(!valid));
  error.hidden = valid;
}

function clearFieldError(input, error) {
  if (input.value.trim()) setFieldValidity(input, error, true);
}

function setStatus(messageKey) {
  status.textContent = translations[activeLanguage][messageKey];
}

function applyLanguage(language) {
  const copy = translations[language];
  activeLanguage = language;
  document.documentElement.lang = language;
  document.title = copy.pageTitle;
  authPanel.setAttribute("aria-label", copy.panelLabel);
  languageGroup.setAttribute("aria-label", copy.languageLabel);

  document.querySelectorAll("[data-copy]").forEach((element) => {
    const key = element.dataset.copy;
    if (key === "introTitle") {
      element.innerHTML = copy[key];
    } else {
      element.textContent = copy[key];
    }
  });

  document.querySelectorAll("[data-language]").forEach((button) => {
    const isActive = button.dataset.language === language;
    button.classList.toggle("is-active", isActive);
    button.setAttribute("aria-pressed", String(isActive));
  });

  status.textContent = "";
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  const nameValid = Boolean(nameInput.value.trim());
  const passwordValid = Boolean(passwordInput.value);

  setFieldValidity(nameInput, nameError, nameValid);
  setFieldValidity(passwordInput, passwordError, passwordValid);

  if (!nameValid) {
    nameInput.focus();
    return;
  }

  if (!passwordValid) {
    passwordInput.focus();
    return;
  }

  setStatus("prototypeStatus");
  window.location.href = "access.html";
});

nameInput.addEventListener("input", () => clearFieldError(nameInput, nameError));
passwordInput.addEventListener("input", () => clearFieldError(passwordInput, passwordError));

document.querySelectorAll("[data-language]").forEach((button) => {
  button.addEventListener("click", () => applyLanguage(button.dataset.language));
});

document.querySelector('[data-action="learn"]').addEventListener("click", () => {
  setStatus("learnStatus");
});

document.querySelector('[data-action="offline"]').addEventListener("click", () => {
  setStatus("offlineStatus");
});

applyLanguage(activeLanguage);
